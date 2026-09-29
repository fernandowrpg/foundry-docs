# Other Documents

Shorter guides to Macro, Folder, Cards, Playlist, User and Setting documents, plus a complete "item pile" example built with flags.

::: changed
- New `Level` document embedded in Scenes (see [Scene Levels](#scene-token--scene-levels)).
- `MeasuredTemplate` is removed; areas of effect are [Template Regions](#regions).
- Active Effects are primary documents (sidebar, compendiums) — see [Active Effects](#active-effect).
- `MacroData#author` is nullable; Assistant GMs get more permissions (except `FILES_UPLOAD`, `MACRO_SCRIPT`, `SETTINGS_MODIFY`).
- `User.queryMany()` queries several users at once; handlers receive the sender id.
- See [the full changelog](#changes-14).
:::

## What it is

Besides Actors, Items and Scenes, Foundry has several smaller document types. They all share the
same API ([Documents](#documents)): `create`, `update`, `delete`, flags, ownership and hooks.
This page shows what each is for and the calls you will actually use.

| Document | Collection | Typical module use |
| --- | --- | --- |
| `Macro` | `game.macros` | hotbar shortcuts for items and abilities |
| `Folder` | `game.folders` | organise generated content |
| `Cards` / `Card` | `game.cards` | decks, hands, piles |
| `Playlist` / `PlaylistSound` | `game.playlists` | music and ambience |
| `User` | `game.users` | permissions, per-player data, "who acts" |
| `Setting` | `game.settings.storage` | the stored value of a [setting](#settings) |

## Macro

A Macro is a `"script"` (JavaScript) or `"chat"` (text sent as a chat message) command.

```js
const macro = await Macro.create({
  name: "Forja: Rest",
  type: "script",
  img: "icons/svg/sleep.svg",
  command: `
    // 'actor' and 'token' are provided by core (selected token or assigned character)
    if (!actor) return ui.notifications.warn("Select a token first.");
    await actor.update({ "system.hp.value": actor.system.hp.max });
    ChatMessage.create({ speaker: ChatMessage.getSpeaker({ actor }), content: "Rests." });
  `
});

// Run it from code; extra keys become variables inside the script
await macro.execute({ reason: "camp" });
```

Script macros run as an async function with `speaker`, `actor`, `token`, `character`, `event`
and your `scope` keys in scope. Creating script macros needs the `MACRO_SCRIPT` permission
(in V13+ it restricts creation only, not execution).

### Item macros on the hotbar

The `hotbarDrop` hook fires when something is dropped on the hotbar. It must return `false`
**synchronously** to stop the default behavior, so start the async work without awaiting it.

```js
// systems/forja/module/macros.mjs
Hooks.on("hotbarDrop", (bar, data, slot) => {
  if (data.type !== "Item") return;          // let core handle other types
  createItemMacro(data, slot);               // not awaited on purpose
  return false;
});

async function createItemMacro(data, slot) {
  const item = await fromUuid(data.uuid);
  if (!item?.parent) return ui.notifications.warn("FORJA.Macro.OwnedOnly", { localize: true });
  const command = `game.forja.rollItemMacro(${JSON.stringify(item.name)});`;
  let macro = game.macros.find(m => (m.command === command) && m.isAuthor);
  macro ??= await Macro.create({
    name: item.name, type: "script", img: item.img, command,
    flags: { forja: { itemMacro: true } }
  });
  await game.user.assignHotbarMacro(macro, slot);
}

// Exposed at init: game.forja = { rollItemMacro }
export function rollItemMacro(itemName) {
  const speaker = ChatMessage.getSpeaker();
  const actor = game.actors.tokens[speaker.token] ?? game.actors.get(speaker.actor);
  const item = actor?.items.getName(itemName);
  if (!item) return ui.notifications.warn(game.i18n.format("FORJA.Macro.NoItem", { name: itemName }));
  return item.roll();
}
```

Storing the item **name** (not its id) makes the macro work for any actor that has an item with
that name, which is what players usually expect.

## Folder

Folders are documents with a `type` (the document name they contain), an optional parent `folder`,
`color` and `sorting` (`"a"` alphabetical, `"m"` manual).

```js
const root = await Folder.create({ name: "Forja", type: "Item", color: "#7a3b12", sorting: "a" });
const weapons = await Folder.create({ name: "Weapons", type: "Item", folder: root.id });
await Item.create({ name: "Ember Blade", type: "weapon", folder: weapons.id });

console.log(weapons.contents);   // documents directly in the folder
console.log(root.children);      // sub-folder tree nodes
```

Nesting is limited to `CONST.FOLDER_MAX_DEPTH` levels. Folders also exist inside compendium packs.

## Cards

A `Cards` document is a **deck**, **hand** or **pile** (`type`); its embedded `Card` documents
have `faces` (each `{ name, text, img }`), a `back`, and `face` (index of the visible face, or
`null` for face-down).

```js
const deck = await Cards.create({
  name: "Forja Fate Deck",
  type: "deck",
  cards: [1, 2, 3, 4, 5].map(n => ({
    name: `Fate ${n}`,
    type: "base",
    value: n,
    faces: [{ name: `Fate ${n}`, img: `systems/forja/assets/cards/fate-${n}.webp` }],
    back: { img: "systems/forja/assets/cards/back.webp" },
    face: null
  }))
});
const hand = await Cards.create({ name: "Aria's Hand", type: "hand" });

await deck.shuffle();
await deck.deal([hand], 2);               // two cards from the deck into the hand
await hand.pass(deck, [hand.cards.contents[0].id]); // give one back
await deck.recall();                      // return every dealt card to the deck
```

## Playlist and PlaylistSound

```js
const playlist = await Playlist.create({
  name: "Forja Battle",
  mode: CONST.PLAYLIST_MODES.SEQUENTIAL,
  sounds: [
    { name: "Drums", path: "modules/forja-extras/audio/drums.ogg", volume: 0.5, repeat: true }
  ]
});
await playlist.playAll();
await playlist.stopAll();

// One-shot sound effect for everyone (second argument broadcasts it)
foundry.audio.AudioHelper.play({ src: "modules/forja-extras/audio/clang.ogg", volume: 0.8, loop: false }, true);
```

Playing a playlist is a document update (`playing: true`), so only users allowed to update the
playlist (normally GMs) can start it. `AudioHelper.play` with broadcast is the way for players to
trigger short effects.

## User

`game.user` is the current user; `game.users` holds everyone, connected or not.

```js
game.user.isGM;                  // GM or Assistant GM
game.user.role;                  // CONST.USER_ROLES value
game.user.character;             // assigned Actor, or null
game.user.hasPermission("FILES_UPLOAD");
game.users.activeGM;             // the active GM user that is connected (or null)
game.users.filter(u => u.active && !u.isGM);  // connected players
```

Many hooks run on every client. To make exactly one client act (create a document, apply damage),
choose a "designated" user:

```js
Hooks.on("combatTurnChange", (combat, prior, current) => {
  // V13+: true only on the one active GM client
  if (!game.user.isActiveGM) return;
  // ...do the work once
});
```

`game.users.getDesignatedUser(filter)` (V13+) picks a user deterministically among those matching
a filter; `user.isDesignated` checks it. Use it when no GM might be online.

Per-user data goes in user flags (`game.user.setFlag("forja-extras", "favoriteDice", "d20")`) or
in a `user`-scoped [setting](#settings) (V13+).

::: v14
`User.queryMany()` sends a [query](#sockets) to several users and collects their answers; query
handlers now also receive the id of the sender.
:::

## Setting

Each stored setting value is a `Setting` document (world settings in the database, client settings
in `localStorage`). You normally use `game.settings.get/set` ([Settings](#settings)), but the
document is useful for hooks:

```js
Hooks.on("updateSetting", (setting, changes) => {
  if (setting.key !== "forja.difficulty") return;
  console.log("Difficulty is now", game.settings.get("forja", "difficulty"));
});
```

::: v14
## Level

`Level` is a new document embedded in `Scene` (`scene.levels`) that describes one elevation slice
of a multi-level scene, with its own background, foreground and fog. See
[Scene Levels](#scene-token--scene-levels).

## MeasuredTemplate (removed)

The `MeasuredTemplate` document, `CONFIG.MeasuredTemplate` and `canvas.templates` are gone.
Areas of effect are Regions with template shapes; see [Regions and Templates](#regions).
:::

## Recipe: item piles with flags

A complete, compact pattern: any actor flagged as a "pile" accepts items dropped on its token, and
players can take items from it even though they don't own the pile. The ownership problem is solved
with a GM-side **query**.

```js
// modules/forja-extras/scripts/piles.mjs
const MODULE = "forja-extras";

/** Is this actor a pile? */
const isPile = actor => !!actor?.getFlag(MODULE, "pile");

Hooks.once("init", () => {
  // Runs on the GM's client; players call it with user.query()
  CONFIG.queries[`${MODULE}.transferItem`] = async ({ itemUuid, targetUuid }) => {
    const item = await fromUuid(itemUuid);
    const target = await fromUuid(targetUuid);
    if (!item?.parent || !target) return false;
    const data = item.toObject();
    delete data._id;
    await target.createEmbeddedDocuments("Item", [data]);
    await item.delete();
    return true;
  };
});

/** Move an item between two actors, via the GM if needed */
export async function transferItem(item, targetActor) {
  const payload = { itemUuid: item.uuid, targetUuid: targetActor.uuid };
  if (item.parent.isOwner && targetActor.isOwner) {
    return CONFIG.queries[`${MODULE}.transferItem`](payload);
  }
  const gm = game.users.activeGM;
  if (!gm) return ui.notifications.warn(game.i18n.localize("FORJA_EXTRAS.Pile.NoGM"));
  return gm.query(`${MODULE}.transferItem`, payload, { timeout: 10_000 });
}

// Drop an owned item from a sheet onto a pile token
Hooks.on("dropCanvasData", (canvas, data) => {
  if (data.type !== "Item") return;
  const token = canvas.tokens.placeables.find(t => t.bounds.contains(data.x, data.y));
  if (!isPile(token?.actor)) return;
  fromUuid(data.uuid).then(item => {
    if (item?.parent && item.parent !== token.actor) transferItem(item, token.actor);
  });
  return false; // don't let core create a new world item on the canvas
});

// Turn the selected token's actor into a pile (run as GM)
export async function makePile(actor) {
  await actor.setFlag(MODULE, "pile", true);
  await actor.update({ "ownership.default": CONST.DOCUMENT_OWNERSHIP_LEVELS.LIMITED });
}
```

To let players *take* items, call `transferItem(item, game.user.character)` from a button in the
pile's sheet or a dialog listing `pileActor.items`.

## Pitfalls

::: warning
- `hotbarDrop` and `dropCanvasData` must return `false` synchronously; an `async` handler returns
  a Promise, which core does not treat as `false`.
- `game.users.activeGM` is `null` when no GM is connected; always handle that case.
- Macro commands are code stored in the world: never build them by concatenating unescaped user
  input (use `JSON.stringify` as above).
- Starting a playlist from a player client fails silently without permission to update it.
- `CONFIG.queries` handlers (V13+) must be registered on every client (in `init`), because any
  client may be the one that answers.
:::
