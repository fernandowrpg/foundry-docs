# Hooks

Hooks are Foundry's event bus: named events your code subscribes to so it can run at the right moment of startup, react to document changes, and extend the UI of other applications.

::: changed
- The `ready` hook now fires **after** scene transitions finish, so the canvas is really settled when your `ready` code runs.
- New `planToken` hook fires when a token's movement is planned.
- New `preRenderApplication` hook (and its per-class variants such as `preRenderActorSheetV2`) fires **before** an ApplicationV2 renders.
- Header controls and context menus share one implementation; `getHeaderControls{Class}` keeps working.
- See [the full changelog](#changes-14).
:::

## What a hook is

Foundry core (and any package) can call `Hooks.call("someEvent", ...args)` at a well-defined point. Every function that registered for `"someEvent"` then runs with those arguments. This is how you add behavior **without** editing or monkey-patching core code:

- **Lifecycle hooks** tell you when the game is being set up (`init`, `setup`, `ready`).
- **Document hooks** tell you a document is about to change or has changed (`preUpdateActor`, `updateActor`, …).
- **Render hooks** let you modify the HTML of an application after it renders (`renderActorSheetV2`, …).
- **UI construction hooks** let you add buttons to menus and toolbars (`getSceneControlButtons`, `getHeaderControlsApplicationV2`, …).

Hooks are purely client-side: each connected browser has its own `Hooks` registry, and a handler only runs in the browser that registered it.

## The Hooks API

| Method | What it does | Returns |
| --- | --- | --- |
| `Hooks.on(name, fn)` | Register `fn` to run every time the hook fires | numeric id |
| `Hooks.once(name, fn)` | Register `fn` to run only the next time, then unregister it | numeric id |
| `Hooks.off(name, fnOrId)` | Unregister by the function reference or by the id returned from `on` | — |
| `Hooks.call(name, ...args)` | Fire a hook; stops early if a handler returns `false` | `false` if stopped, otherwise `true` |
| `Hooks.callAll(name, ...args)` | Fire a hook; every handler runs, return values ignored | `true` |

```js
// modules/forja-extras/scripts/main.js

// Runs every time any Actor is updated
const hookId = Hooks.on("updateActor", (actor, changes, options, userId) => {
  console.log(`forja-extras | ${actor.name} was updated`, changes);
});

// Runs only once, the next time the hook fires
Hooks.once("ready", () => {
  console.log("forja-extras | The game is ready");
});

// Stop listening later, using the id (or the same function reference)
function stopListening() {
  Hooks.off("updateActor", hookId);
}
```

### call vs callAll

`Hooks.call` is used for events that can be **vetoed**: if any handler returns exactly `false`, the remaining handlers are skipped and the caller receives `false`. Core uses it for every `pre*` hook. `Hooks.callAll` is for notifications — nobody can stop it.

### Firing your own hooks

Your system or module can expose hooks so other packages can integrate with it. Prefix the name with your package id to avoid collisions.

```js
// systems/forja/scripts/rolls.js
export async function rollAttribute(actor, key) {
  // Let other packages cancel or tweak the roll before it happens
  const rollData = { formula: `1d20 + @attributes.${key}.value`, actor, key };
  const allowed = Hooks.call("forja.preRollAttribute", rollData);
  if (allowed === false) return null;

  const roll = await new Roll(rollData.formula, actor.getRollData()).evaluate();
  await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) });

  // Pure notification: nobody can cancel it any more
  Hooks.callAll("forja.rollAttribute", actor, key, roll);
  return roll;
}
```

```js
// modules/forja-extras/scripts/main.js
Hooks.on("forja.preRollAttribute", (rollData) => {
  // Add a flat +1 bonus to every Strength roll
  if (rollData.key === "strength") rollData.formula += " + 1";
});
```

::: tip
Handlers are called synchronously. If a handler is `async`, Foundry does **not** await it, and a returned Promise is not `false` — so an async `pre*` handler can never cancel an operation.
:::

## Lifecycle order

When a client loads a world, these hooks fire in this order, exactly once each:

| Hook | When | What is available | Typical use |
| --- | --- | --- | --- |
| `init` | Right after core classes load, before anything is prepared | `CONFIG`, `game.settings`, `game.keybindings`, `Hooks` | Register data models, document classes, sheets, settings, keybindings, Handlebars helpers |
| `i18nInit` | Translations are loaded | `game.i18n` fully usable | Localize static strings, `localizeDataModel` for custom models |
| `setup` | Documents are about to be created from world data | Settings values, `game.i18n` | Final `CONFIG` tweaks that depend on settings |
| `ready` | Everything is initialized and the canvas is drawn | `game.actors`, `game.user`, `canvas`, `game.ready === true` | Migrations, sockets, UI that needs documents |

::: v13
In V13, `ready` fires as soon as the game finishes initializing and the first scene is drawn.
:::

::: v14
In V14, `ready` fires **after any scene transition animation has finished**. If you start something visual in `ready` (a notification, a pan), it will no longer overlap the transition.
:::

```js
// systems/forja/forja.mjs
import { CharacterData } from "./data/character.mjs";
import { ForjaActor } from "./documents/actor.mjs";

Hooks.once("init", () => {
  console.log("forja | Initializing");
  CONFIG.Actor.documentClass = ForjaActor;
  CONFIG.Actor.dataModels.character = CharacterData;
});

Hooks.once("i18nInit", () => {
  // Translations are ready: safe to localize strings once
  CONFIG.forja = { sizes: { small: game.i18n.localize("FORJA.Size.Small") } };
});

Hooks.once("setup", () => {
  console.log("forja | Setup: settings can be read now");
});

Hooks.once("ready", () => {
  // Documents exist, the user is known
  if (game.user.isGM) console.log(`forja | ${game.actors.size} actors in this world`);
});
```

::: warning
Register data models, document classes and settings in `init`. By `ready` the world's documents have already been constructed with whatever was configured before, and changes to `CONFIG.Actor.dataModels` will not apply to them.
:::

## Document hooks

Every create, update and delete of a document fires a pair of hooks, named after the document type (`Actor`, `Item`, `ChatMessage`, `Token`, …):

| Hook | Arguments | Runs on | Can cancel? |
| --- | --- | --- | --- |
| `preCreate{Doc}` | `(document, data, options, userId)` | Only the client that requested the change | Yes, return `false` |
| `create{Doc}` | `(document, options, userId)` | Every connected client | No |
| `preUpdate{Doc}` | `(document, changes, options, userId)` | Only the requesting client | Yes, return `false` |
| `update{Doc}` | `(document, changes, options, userId)` | Every connected client | No |
| `preDelete{Doc}` | `(document, options, userId)` | Only the requesting client | Yes, return `false` |
| `delete{Doc}` | `(document, options, userId)` | Every connected client | No |

**Why the split?** The `pre*` hooks run *before* the request goes to the server, so only the client that asked for the change knows about it. You can inspect or modify the pending data (for `preCreate` use `document.updateSource(...)`; for `preUpdate` mutate `changes`) or return `false` to cancel. The post hooks run after the server has confirmed and broadcast the change, so every client runs them.

```js
// modules/forja-extras/scripts/document-hooks.js

// Give new weapons a default icon, and block creating one without a name
Hooks.on("preCreateItem", (item, data, options, userId) => {
  if (item.type !== "weapon") return;
  if (!data.name?.trim()) {
    ui.notifications.warn("forja-extras | Weapons need a name.");
    return false; // cancels the creation
  }
  if (!data.img) item.updateSource({ img: "icons/weapons/swords/sword-guard-steel.webp" });
});

// Prevent HP from being set below zero
Hooks.on("preUpdateActor", (actor, changes, options, userId) => {
  const hp = foundry.utils.getProperty(changes, "system.hp.value");
  if (hp !== undefined && hp < 0) foundry.utils.setProperty(changes, "system.hp.value", 0);
});

// React after the change: runs on EVERY client
Hooks.on("updateActor", async (actor, changes, options, userId) => {
  // Only the user who made the change should create follow-up documents
  if (userId !== game.user.id) return;
  if (foundry.utils.getProperty(changes, "system.hp.value") === 0) {
    await ChatMessage.create({ content: `${actor.name} has fallen!` });
  }
});
```

::: warning
Because `create*`, `update*` and `delete*` hooks run on every client, writing to the database inside them without a guard makes **each connected client** perform the write. Always filter with `userId === game.user.id` (or use a designated GM, see [sockets](#sockets)).
:::

There are also generic versions that fire for any document type: `preCreateDocument`, `createDocument`, `preUpdateDocument`, `updateDocument`, `preDeleteDocument`, `deleteDocument`. For logic inside your own system, prefer overriding `_preCreate` / `_onUpdate` on your document class (see [documents](#documents)).

## Render hooks for ApplicationV2

Every ApplicationV2 fires `render{ClassName}` after it renders, **and one hook for each parent class** in its inheritance chain. A character sheet class `ForjaCharacterSheet extends ActorSheetV2` fires `renderForjaCharacterSheet`, `renderActorSheetV2`, `renderDocumentSheetV2`, `renderApplicationV2`, in that order.

Signature: `(application, element, context, options)`. `element` is a plain **`HTMLElement`**, not a jQuery object.

```js
// modules/forja-extras/scripts/sheet-button.js
Hooks.on("renderActorSheetV2", (app, element, context, options) => {
  const actor = app.document;
  if (actor.type !== "character") return;

  // Avoid adding the button twice when only some parts re-render
  if (element.querySelector(".forja-extras-rest")) return;

  const button = document.createElement("button");
  button.type = "button";
  button.classList.add("forja-extras-rest");
  button.innerHTML = `<i class="fa-solid fa-bed"></i> Rest`;
  button.addEventListener("click", () => actor.update({ "system.hp.value": actor.system.hp.max }));

  element.querySelector(".window-content")?.prepend(button);
});
```

::: v13
Legacy (AppV1) applications fire `renderApplicationV1`-style hooks and still pass a jQuery object. All core V13 apps are ApplicationV2, so write your handlers against `HTMLElement`. If you must support both, normalize with `const el = html instanceof HTMLElement ? html : html[0];`.
:::

::: v14
V14 adds `preRenderApplication` (and per-class `preRender{ClassName}`, e.g. `preRenderActorSheetV2`), called **before** rendering with `(application, context, options)`. Use it to add data to `context` that your render hook or template expects.

```js
// modules/forja-extras/scripts/sheet-context.js
Hooks.on("preRenderActorSheetV2", (app, context, options) => {
  // Extra value to display on the sheet
  context.forjaExtras = { restCount: app.document.getFlag("forja-extras", "rests") ?? 0 };
});
```
:::

## getSceneControlButtons

Called when the left-hand scene controls are built. Since V13 `controls` is a **record** (an object keyed by control name), not an array, and each control's `tools` is also a record.

```js
// modules/forja-extras/scripts/controls.js
Hooks.on("getSceneControlButtons", (controls) => {
  const tokens = controls.tokens;
  if (!tokens) return;

  tokens.tools.forjaRest = {
    name: "forjaRest",
    title: "FORJA_EXTRAS.Controls.Rest", // localized automatically
    icon: "fa-solid fa-campground",
    order: Object.keys(tokens.tools).length,
    button: true,
    visible: game.user.isGM,
    onChange: (event, active) => {
      ui.notifications.info("The party takes a short rest.");
    }
  };
});
```

::: warning
Code written for V12 that does `controls.find(c => c.name === "token")` or `controls.push(...)` breaks: there is no array any more, and the token group key is `tokens`.
:::

## getHeaderControls{Class}

ApplicationV2 windows have a "…" header menu. Before it is shown, `getHeaderControls{ClassName}` fires for the class and each parent class, with `(application, controls)` where `controls` is an **array** of entries `{ icon, label, action, visible?, ownership?, onClick? }`.

```js
// modules/forja-extras/scripts/header.js
Hooks.on("getHeaderControlsActorSheetV2", (app, controls) => {
  controls.push({
    icon: "fa-solid fa-share-nodes",
    label: "FORJA_EXTRAS.Header.Share", // localized automatically
    action: "forjaExtrasShare",
    visible: () => game.user.isGM,
    onClick: () => ChatMessage.create({ content: `@UUID[${app.document.uuid}]` })
  });
});
```

## New hooks in V14

::: v13
The hooks below do not exist in V13. For token movement use `preMoveToken` / `moveToken`; for pre-render logic override `_prepareContext` in your own application.
:::

::: v14
| Hook | Arguments | Fires when |
| --- | --- | --- |
| `planToken` | `(tokenDocument)` | A token's movement is planned (drag preview / planned path) |
| `preRenderApplication` / `preRender{Class}` | `(application, context, options)` | Before an ApplicationV2 renders |

```js
// modules/forja-extras/scripts/movement.js
Hooks.on("planToken", (tokenDocument) => {
  console.log(`forja-extras | Movement planned for ${tokenDocument.name}`);
});
```
:::

## Debugging hooks

Turn on hook logging in the browser console (F12) to see every hook name and its arguments as it fires:

```js
CONFIG.debug.hooks = true;
```

This is the fastest way to discover which hook to use: open the sheet, move the token, or click the button you want to extend, and read the log. Set it back to `false` when done — it is very noisy.

## Pitfalls

- **`init` handlers registered too late.** A `Hooks.once("init", ...)` inside a `ready` handler never runs. Register lifecycle hooks at the top level of your entry script.
- **Async `pre*` handlers cannot cancel.** Return `false` synchronously.
- **Duplicate side effects.** Post-hooks run on every client; guard with `userId === game.user.id`.
- **Using jQuery on AppV2 elements.** `element.find(...)` is not a function; use `querySelector`.
- **Re-render duplication.** Render hooks fire on every render; check whether your injected element already exists.
- **Hook name typos fail silently.** `Hooks.on("updateactor", …)` just never fires. Use `CONFIG.debug.hooks` to verify names.
