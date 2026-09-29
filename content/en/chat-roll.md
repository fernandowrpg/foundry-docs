# Chat Messages and Rolls

Post chat cards, roll dice with actor data, build a custom Roll class and react to buttons on a card.

::: changed
- **Roll Modes became Message Visibility Modes.** They apply to any message, not only rolls, and there is a new "In-Character" mode. Modes: `"public"`, `"self"`, `"gm"`, `"blind"`.
- `ChatMessage.applyRollMode(data, mode)` → `ChatMessage.applyMode(data, mode)` (and `message.applyMode(mode)` on an instance).
- `roll.toMessage(data, { rollMode })` → `roll.toMessage(data, { messageMode })`. The old names keep working with a deprecation warning until V16.
- `ChatLog.MESSAGE_PATTERNS` → `ChatLog.CHAT_COMMANDS` for custom chat commands (old name removed in V16).
- The chat input is now an inline ProseMirror editor.
- Booleans inside roll data evaluate as numbers (`true` → `1`, `false` → `0`).
- See [the full changelog](#changes-14).
:::

## What it is

A **ChatMessage** is a world document with HTML `content`, a `speaker`, an `author` (the user), optional `rolls`, `whisper` recipients and `flags`. Every client stores and renders the same message, so a chat card is also the simplest way to share the result of an action with everybody.

A **Roll** is not a document. It is a class that parses a formula (`"1d20 + @str"`), evaluates it and can serialize itself into a message's `rolls` array.

## Post a message

```js
await ChatMessage.create({
  speaker: ChatMessage.getSpeaker({ actor }),          // who is talking
  content: `<p>${game.i18n.localize("FORJA.Chat.Ready")}</p>`,
  flags: { forja: { kind: "ready" } }                  // your own data
});
```

`getSpeaker()` with no arguments uses the controlled token, then the user's character. Pass `{ actor }` or `{ token }` to be explicit.

### Whisper to the GMs

```js
await ChatMessage.create({
  content: "<p>Secret door found.</p>",
  whisper: game.users.filter(u => u.isGM).map(u => u.id)
});
```

### Use a template for rich cards

```js
// systems/forja/module/chat.mjs
const { renderTemplate } = foundry.applications.handlebars;

export async function postItemCard(item) {
  const content = await renderTemplate("systems/forja/templates/chat/item-card.hbs", {
    item, system: item.system, actorId: item.actor?.id
  });
  return ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor: item.actor }),
    content,
    flags: { forja: { itemUuid: item.uuid } }
  });
}
```

```hbs
{{!-- systems/forja/templates/chat/item-card.hbs --}}
<div class="forja chat-card" data-item-uuid="{{item.uuid}}">
  <header><img src="{{item.img}}" alt=""><h3>{{item.name}}</h3></header>
  <div class="card-body">{{{system.description}}}</div>
  <footer>
    <button type="button" data-action="rollDamage">{{localize "FORJA.Chat.RollDamage"}}</button>
  </footer>
</div>
```

## Roll dice

```js
// Formula with @references resolved from roll data
const roll = new Roll("1d20 + @abilities.str.mod", actor.getRollData());
await roll.evaluate();              // always await: evaluation is async

roll.total;                         // 17
roll.formula;                       // "1d20 + 3"
roll.dice[0].results;               // [{ result: 14, active: true }]
roll.isDeterministic;               // false (it has dice)
```

`actor.getRollData()` returns a copy of `actor.system` (plus anything your Actor class adds), so `@abilities.str.mod` works when your data model has that path. See [Actors](#actor).

### Send the roll to chat

::: v13
```js
await roll.toMessage({
  speaker: ChatMessage.getSpeaker({ actor }),
  flavor: game.i18n.format("FORJA.Roll.Attack", { name: actor.name, weapon: item.name })
}, {
  rollMode: game.settings.get("core", "rollMode")   // publicroll | gmroll | blindroll | selfroll
});
```

`CONST.DICE_ROLL_MODES` holds the values: `PUBLIC` = `"publicroll"`, `PRIVATE` = `"gmroll"`, `BLIND` = `"blindroll"`, `SELF` = `"selfroll"`.

When you build the message data yourself, apply the mode explicitly. Since V13, `ChatMessage#_preCreate` only applies it when `options.rollMode` is set:

```js
const data = { speaker: ChatMessage.getSpeaker({ actor }), rolls: [roll] };
ChatMessage.applyRollMode(data, game.settings.get("core", "rollMode"));
await ChatMessage.create(data);
```
:::

::: v14
```js
await roll.toMessage({
  speaker: ChatMessage.getSpeaker({ actor }),
  flavor: game.i18n.localize("FORJA.Roll.Attack", { name: actor.name, weapon: item.name })
}, {
  messageMode: "gm"          // "public" | "self" | "gm" | "blind"; omit to use the user's current mode
});
```

Visibility modes now work for any message, so you can hide a plain card the same way:

```js
const data = { speaker: ChatMessage.getSpeaker({ actor }), content: "<p>Trap disarmed.</p>" };
ChatMessage.applyMode(data, "blind");   // static: changes whisper/blind in the data
await ChatMessage.create(data);

// On an existing message
message.applyMode("public");
```
:::

## A custom Roll class

Subclass `Roll` when your system has its own dice logic (success counting, exploding dice, a custom chat template).

```js
// systems/forja/module/dice/forja-roll.mjs
export class ForjaRoll extends Roll {
  static CHAT_TEMPLATE = "systems/forja/templates/chat/roll.hbs";

  /** Success when the total reaches the target number stored in options. */
  get isSuccess() {
    if ( !this._evaluated ) return undefined;
    return this.total >= (this.options.target ?? 10);
  }

  /** Add our data to the chat template context. */
  async _prepareChatRenderContext(options = {}) {
    const context = await super._prepareChatRenderContext(options);
    context.isSuccess = this.isSuccess;
    context.target = this.options.target;
    return context;
  }
}
```

```js
// forja.mjs
import { ForjaRoll } from "./module/dice/forja-roll.mjs";

Hooks.once("init", () => {
  CONFIG.Dice.rolls.push(ForjaRoll);   // needed so messages can rebuild the class from JSON
});

// Usage
const roll = await new ForjaRoll("2d6 + @skill", { skill: 2 }, { target: 9 }).evaluate();
await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) });
```

::: warning
If you forget `CONFIG.Dice.rolls.push(...)`, the roll still posts, but after a reload the message rebuilds a plain `Roll` and your custom getters return `undefined`.
:::

::: v14
Roll data values that are booleans now evaluate as numbers. `@hasShield` with `true` becomes `1`, so formulas like `1d20 + @hasShield * 2` work without converting the value yourself.
:::

## React to buttons on a chat card

Chat cards are re-rendered for every client and after every reload, so attach listeners in the render hook, not when you create the message.

```js
// V13 and V14: html is an HTMLElement
Hooks.on("renderChatMessageHTML", (message, html, context) => {
  const card = html.querySelector(".forja.chat-card");
  if ( !card ) return;
  card.querySelector("[data-action='rollDamage']")?.addEventListener("click", async event => {
    event.preventDefault();
    const item = await fromUuid(card.dataset.itemUuid);
    if ( !item?.isOwner ) return ui.notifications.warn("FORJA.Warn.NotOwner", { localize: true });
    const roll = await new Roll(item.system.damage, item.getRollData()).evaluate();
    await roll.toMessage({ speaker: message.speaker, flavor: item.name });
  });
});
```

::: tip
Keep the data you need in the card (`data-item-uuid`) or in `message.flags`. Do not rely on variables from the moment the card was created: they are gone after a reload.
:::

## Custom chat commands

::: v13
The `chatMessage` hook runs before a typed message is sent. Return `false` to stop the default handling.

```js
Hooks.on("chatMessage", (chatLog, text, chatData) => {
  const match = text.match(/^\/forja\s+(\d+)/i);
  if ( !match ) return;                // not ours: let Foundry handle it
  const target = Number(match[1]);
  new ForjaRoll("2d6", {}, { target }).toMessage({ speaker: ChatMessage.getSpeaker() });
  return false;                        // we handled it
});
```
:::

::: v14
The `chatMessage` hook still works for simple cases. The core list of commands moved from `ChatLog.MESSAGE_PATTERNS` to `ChatLog.CHAT_COMMANDS`, which is the structure to extend when you want your command to behave like a core command. Check the `ChatLog` page of the V14 API for the entry format before adding to it.

```js
Hooks.on("chatMessage", (chatLog, text, chatData) => {
  const match = text.match(/^\/forja\s+(\d+)/i);
  if ( !match ) return;
  const target = Number(match[1]);
  new ForjaRoll("2d6", {}, { target }).toMessage({ speaker: ChatMessage.getSpeaker() });
  return false;
});
```
:::

## Common recipes

### Roll an item from the sheet

```js
// Inside ForjaItem (CONFIG.Item.documentClass)
async roll() {
  const roll = await new Roll(this.system.attackFormula, this.getRollData()).evaluate();
  return roll.toMessage({
    speaker: ChatMessage.getSpeaker({ actor: this.actor }),
    flavor: this.name,
    flags: { forja: { itemUuid: this.uuid } }
  });
}
```

### Read a roll back from a message

```js
const message = game.messages.contents.at(-1);
const [roll] = message.rolls;           // already rebuilt as ForjaRoll if registered
console.log(roll.total, roll.isSuccess);
```

### Show 3D dice or wait for animations

Modules such as Dice So Nice hook into `toMessage`. Always `await` it if your next step depends on the dice having been shown.

## Pitfalls

- **Forgetting `await roll.evaluate()`**: `roll.total` is `undefined` until the roll is evaluated.
- **Unsafe HTML**: `content` is stored as HTML. Never insert user text without escaping it (`Handlebars.escapeExpression(text)` or a template with `{{...}}`, which escapes by default).
- **Listeners in `createChatMessage`**: they run once, on one client. Use `renderChatMessageHTML`.
- **jQuery**: V13 and V14 pass `HTMLElement`. `html.find(...)` no longer exists.
