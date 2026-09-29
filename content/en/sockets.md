# Sockets and user queries

Send messages between connected clients, and let players ask the GM to do things they are not allowed to do themselves.

::: changed
- `User.queryMany(users, name, data, options)` (static) queries several users at once and returns a `Map` of settled results.
- Query handlers now receive the id of the user who sent the query, so the GM can check permissions without trusting the payload.
- The socket API (`game.socket.on` / `emit`) and `CONFIG.queries` registration are unchanged.
- See [the full changelog](#changes-14).
:::

## What it is

Every Foundry client keeps a WebSocket connection to the server. Document operations
(create, update, delete) already travel over it, and every client is notified automatically.
You only need your own messages when you want to do something that is **not** a document
change, or when a player needs an operation their permissions do not allow — for example,
damaging an NPC they do not own.

Foundry gives you two tools:

| Tool | Direction | Returns a value? | Use it for |
| --- | --- | --- | --- |
| `game.socket.emit` / `on` | Broadcast to all *other* clients | No | Notifications, "play this animation", fire-and-forget events |
| User queries (`CONFIG.queries` + `user.query`) | Request to one specific user | Yes (a Promise) | "GM, please do X and tell me the result" |

## Enable the socket in the manifest

A package can only use its own channel if the manifest asks for it. Without this flag,
the server silently drops your messages.

```json
{
  "id": "forja",
  "title": "Forja",
  "socket": true
}
```

The channel name is derived from the package id:

- system → `system.forja`
- module → `module.forja-extras`

::: warning
Changing `socket` requires a full restart of the Foundry server (not just a reload), because
the server reads manifests on launch.
:::

## Raw sockets: game.socket

```js
// systems/forja/module/socket.mjs
const CHANNEL = "system.forja";

export function registerSocket() {
  game.socket.on(CHANNEL, (message) => {
    // The server does NOT echo the message back to the sender.
    switch (message.type) {
      case "ping":
        ui.notifications.info(`Ping from ${game.users.get(message.userId)?.name}`);
        break;
      case "shake":
        if (message.sceneId === canvas.scene?.id) canvas.animatePan({ duration: 250 });
        break;
    }
  });
}

export function emit(type, payload = {}) {
  game.socket.emit(CHANNEL, { type, userId: game.user.id, ...payload });
}

Hooks.once("ready", registerSocket);
```

Key points:

- Register listeners in `init`, `setup` or `ready`; `game.socket` exists from `init` on, but
  `ready` guarantees `game.user` and documents are loaded.
- The payload must be JSON-serializable. Send ids or UUIDs, never Document instances.
- The sender does not receive its own message. If the sender must also react, call the handler locally.
- Use a `type` field so one channel can carry many kinds of messages.

## The "GM executes" pattern

With raw sockets every connected GM would receive the message. If two GMs are online, both
would apply the damage — twice. Always elect exactly one client to act:

```js
game.socket.on("system.forja", async (message) => {
  if (message.type !== "applyDamage") return;
  if (!game.user.isActiveGM) return; // only ONE GM acts
  const actor = await fromUuid(message.actorUuid);
  await actor?.applyDamage(message.amount);
});
```

`game.user.isActiveGM` is true for exactly one connected GM (the "designated" one). If no
GM is connected, nobody acts — handle that case in the sender:

```js
if (!game.users.activeGM) {
  ui.notifications.warn("No GM is connected.");
  return;
}
```

::: tip
Before sending anything, check whether the user can simply do it: `actor.isOwner` means
the player can call `actor.update()` directly — no socket needed.
:::

## User queries

Queries are request/response messages built on top of the socket. You register a named
handler in `CONFIG.queries`, and any client can call `someUser.query(name, data)` and
`await` the handler's return value. You do **not** need `"socket": true` for queries,
because they travel over the core channel.

`user.query(queryName, queryData, { timeout })`:

- `queryName` — a key registered in `CONFIG.queries`.
- `queryData` — a JSON-serializable object.
- `timeout` — milliseconds before the Promise rejects.

The handler must be registered on **every** client (the receiving client is the one that runs it),
so register it in `init`.

::: v13
In V13 the handler receives `(queryData, { timeout })`. It does not know who sent the query,
so if you need the sender, put the user id in the payload — and remember that a malicious
client could lie about it.

```js
CONFIG.queries["forja.ping"] = async (queryData, { timeout }) => {
  return `pong to ${queryData.userId}`;
};

const reply = await game.users.activeGM.query("forja.ping", { userId: game.user.id }, { timeout: 5000 });
```
:::

::: v14
In V14 the handler also receives the id of the user who sent the query (in the second
argument, alongside `timeout`). Check the exact property name in the
[V14 API docs](https://foundryvtt.com/api/v14/classes/foundry.documents.User.html) for your build;
this guide reads it defensively and falls back to the payload.

`User.queryMany(users, queryName, queryData, { timeout })` is static. It returns a
`Map<User, PromiseSettledResult>` so one slow or disconnected user does not break the rest:

```js
const players = game.users.filter((u) => u.active && !u.isGM);
const results = await User.queryMany(players, "forja.ping", {}, { timeout: 5000 });
for (const [user, result] of results) {
  if (result.status === "fulfilled") console.log(user.name, result.value);
  else console.warn(user.name, "did not answer", result.reason);
}
```
:::

## Complete example: a player asks the GM to apply damage

The player's character attacks a goblin the player does not own. The player's client cannot
update the goblin, so it asks the GM.

### Shared damage method

```js
// systems/forja/module/documents/actor.mjs
export class ForjaActor extends Actor {
  /** Apply damage and return the new HP value. */
  async applyDamage(amount) {
    const hp = this.system.hp;
    const value = Math.clamp(hp.value - amount, 0, hp.max);
    await this.update({ "system.hp.value": value });
    return value;
  }
}
```

### Style 1 — raw socket (fire-and-forget)

```js
// systems/forja/module/socket.mjs
const CHANNEL = "system.forja";

Hooks.once("ready", () => {
  game.socket.on(CHANNEL, async (message) => {
    if (message.type !== "applyDamage") return;
    if (!game.user.isActiveGM) return;
    const target = await fromUuid(message.actorUuid);
    if (!target) return;
    const value = await target.applyDamage(message.amount);
    // Tell everyone (including the requester) via a chat message.
    ChatMessage.create({ content: `${target.name} takes ${message.amount} damage (HP ${value}).` });
  });
});

export async function requestDamage(actor, amount) {
  if (actor.isOwner) return actor.applyDamage(amount); // no need to ask
  if (!game.users.activeGM) return ui.notifications.warn("No GM is connected.");
  game.socket.emit(CHANNEL, { type: "applyDamage", actorUuid: actor.uuid, amount });
}
```

The drawback: the player never learns whether it worked, and the GM cannot answer with a value.

### Style 2 — user query (request/response)

```js
// systems/forja/module/queries.mjs
Hooks.once("init", () => {
  CONFIG.queries["forja.applyDamage"] = async (queryData, queryOptions = {}) => {
    // The query is sent to the active GM, so this runs on the GM's client.
    const senderId = queryOptions.userId ?? queryOptions.user ?? queryData.userId;
    const sender = game.users.get(senderId);
    const target = await fromUuid(queryData.actorUuid);
    if (!target) throw new Error("Target not found");

    // Validate: the amount must be a positive integer, and the sender must be a real user.
    const amount = Number(queryData.amount);
    if (!sender || !Number.isInteger(amount) || amount < 0) throw new Error("Invalid request");

    const value = await target.applyDamage(amount);
    return { hp: value };
  };
});

export async function requestDamage(actor, amount) {
  if (actor.isOwner) return { hp: await actor.applyDamage(amount) };
  const gm = game.users.activeGM;
  if (!gm) {
    ui.notifications.warn("No GM is connected.");
    return null;
  }
  try {
    return await gm.query(
      "forja.applyDamage",
      { actorUuid: actor.uuid, amount, userId: game.user.id },
      { timeout: 10_000 }
    );
  } catch (err) {
    ui.notifications.error(`The GM could not apply damage: ${err.message}`);
    return null;
  }
}
```

Usage from a sheet action or macro:

```js
const target = game.user.targets.first()?.actor;
if (target) {
  const result = await requestDamage(target, 5);
  if (result) ui.notifications.info(`${target.name} now has ${result.hp} HP.`);
}
```

## Common recipes

- **Run something on every client, including the sender**: call the handler locally, then `emit`.
- **Module channel**: in `forja-extras` use `"module.forja-extras"` and `"socket": true` in `module.json`.
- **Namespace query names**: prefix with your package id (`forja.applyDamage`) to avoid collisions.
- **Built-in queries**: core registers its own entries in `CONFIG.queries` (for example `dialog`); never overwrite them.

## Pitfalls

::: warning
- Forgetting `"socket": true` — `emit` succeeds but nobody receives anything.
- Acting on every GM client — always guard with `game.user.isActiveGM`.
- Sending Document objects — they cannot be serialized; send `uuid`.
- Trusting the payload — the GM handler runs with GM rights; validate every field.
- Registering a query handler only on the GM's client — the GM may change; register it on every client in `init`.
- Not handling timeouts — `user.query` rejects if the target disconnects or the handler throws.
:::
