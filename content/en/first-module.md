# Your first module

Build `forja-extras` step by step: manifest, entry script, a setting, translations, a chat command and a button on sheet headers.

::: changed
- `game.i18n.localize()` now accepts data for placeholders (it absorbed `format()`), and there is a global shortcut **`_loc(key, data)`**.
- Header controls and context-menu entries share one format (`label`, `icon`, `onClick`, `visible`).
- The chat input is now an inline ProseMirror editor, so the `chatMessage` hook may receive HTML — strip tags before parsing commands.
- See [the full changelog](#changes-14).
:::

## What we will build

A module that:

1. Logs when it loads (`init` and `ready` hooks).
2. Registers a **world setting** with a greeting text.
3. Posts the greeting to chat for the GM when the world is ready.
4. Handles a chat command `/forja hello`.
5. Adds a **"Quick roll"** button to every actor sheet's header menu.

It works in any system, but we declare `forja` as its target to match the rest of the guide.

## 1. Folder layout

```bash
Data/modules/forja-extras/
├── module.json
├── scripts/
│   └── main.mjs
├── lang/
│   ├── en.json
│   └── pt-BR.json
└── styles/
    └── forja-extras.css
```

If your repo lives elsewhere, symlink it in as explained in [Setup](#setup).

## 2. The manifest

::: v13
```json
{
  "id": "forja-extras",
  "title": "Forja Extras",
  "description": "Quality-of-life tools for the Forja system.",
  "version": "0.1.0",
  "compatibility": { "minimum": "13", "verified": "13.351" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "flags": {
    "hotReload": { "extensions": ["css", "json"], "paths": ["styles", "lang"] }
  }
}
```
:::

::: v14
```json
{
  "id": "forja-extras",
  "type": "module",
  "title": "Forja Extras",
  "description": "Quality-of-life tools for the Forja system.",
  "version": "0.1.0",
  "compatibility": { "minimum": "14", "verified": "14.368" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "flags": {
    "hotReload": { "extensions": ["css", "json"], "paths": ["styles", "lang"] }
  }
}
```
:::

We leave out `relationships.systems` for now so you can test in any world. Every field is explained in [the manifest](#manifest).

## 3. Translations

Put every user-facing string in language files. Keys are grouped under a prefix unique to your package (`FORJA_EXTRAS`) so they never collide with core or other packages.

```json
{
  "FORJA_EXTRAS": {
    "Settings": {
      "Greeting": { "Name": "Greeting message", "Hint": "Posted to chat for the GM when the world loads." }
    },
    "DefaultGreeting": "The forge is hot, {name}!",
    "QuickRoll": "Quick roll",
    "QuickRollFlavor": "{actor} makes a quick roll",
    "UnknownCommand": "Unknown command: {cmd}"
  }
}
```

Save that as `lang/en.json`. The Portuguese file has the **same keys**:

```json
{
  "FORJA_EXTRAS": {
    "Settings": {
      "Greeting": { "Name": "Mensagem de boas-vindas", "Hint": "Enviada ao chat para o Mestre quando o mundo carrega." }
    },
    "DefaultGreeting": "A forja está quente, {name}!",
    "QuickRoll": "Rolagem rápida",
    "QuickRollFlavor": "{actor} faz uma rolagem rápida",
    "UnknownCommand": "Comando desconhecido: {cmd}"
  }
}
```

::: tip
Nested JSON objects are flattened into dotted keys: `FORJA_EXTRAS.Settings.Greeting.Name`. See [Localization](#localization).
:::

## 4. The entry script

Create `scripts/main.mjs`. We keep the module id in a constant so it is never mistyped.

::: v13
```js
const MODULE_ID = "forja-extras";

// Helper: localize with or without placeholder data
const t = (key, data) =>
  data ? game.i18n.format(`FORJA_EXTRAS.${key}`, data) : game.i18n.localize(`FORJA_EXTRAS.${key}`);

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | init`);

  // Settings must be registered in init, before anything reads them
  game.settings.register(MODULE_ID, "greeting", {
    name: "FORJA_EXTRAS.Settings.Greeting.Name",
    hint: "FORJA_EXTRAS.Settings.Greeting.Hint",
    scope: "world",      // stored in the world, same for everyone; only GMs can change it
    config: true,        // show it in Configure Settings
    type: String,
    default: ""
  });
});

Hooks.once("ready", async () => {
  console.log(`${MODULE_ID} | ready`);
  if (!game.user.isGM) return;

  const custom = game.settings.get(MODULE_ID, "greeting");
  const text = custom || t("DefaultGreeting", { name: game.user.name });

  await ChatMessage.create({
    content: `<p>${text}</p>`,
    whisper: [game.user.id]   // only the GM sees it
  });
});
```
:::

::: v14
```js
const MODULE_ID = "forja-extras";

// Helper: in V14 localize() accepts placeholder data (format() is no longer needed)
const t = (key, data) => game.i18n.localize(`FORJA_EXTRAS.${key}`, data);
// Equivalent global shortcut: _loc("FORJA_EXTRAS.DefaultGreeting", { name })

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | init`);

  // Settings must be registered in init, before anything reads them
  game.settings.register(MODULE_ID, "greeting", {
    name: "FORJA_EXTRAS.Settings.Greeting.Name",
    hint: "FORJA_EXTRAS.Settings.Greeting.Hint",
    scope: "world",      // stored in the world, same for everyone; only GMs can change it
    config: true,        // show it in Configure Settings
    type: String,
    default: ""
  });
});

Hooks.once("ready", async () => {
  console.log(`${MODULE_ID} | ready`);
  if (!game.user.isGM) return;

  const custom = game.settings.get(MODULE_ID, "greeting");
  const text = custom || t("DefaultGreeting", { name: game.user.name });

  await ChatMessage.create({
    content: `<p>${text}</p>`,
    whisper: [game.user.id]   // only the GM sees it
  });
});
```
:::

### Why `init` and `ready`?

- **`init`** runs before the world's data is prepared. Registering settings, `CONFIG` changes, sheets and data models belongs here.
- **`ready`** runs once everything is loaded. Reading documents, creating chat messages and talking to other users belongs here.
- `Hooks.once` unregisters itself after the first call; use `Hooks.on` for events that repeat.

Reload the world (F5), enable **Forja Extras** in *Manage Modules*, and you should see the greeting in chat. Change it in **Configure Settings → Forja Extras**.

## 5. A chat command

The `chatMessage` hook fires when a user submits text in the chat box. Returning `false` stops Foundry from creating a normal message.

```js
Hooks.on("chatMessage", (chatLog, message, chatData) => {
  // Strip HTML (V14's chat input is a rich-text editor) and extra spaces
  const text = message.replace(/<[^>]*>/g, "").trim();
  if (!text.startsWith("/forja")) return; // not ours: let Foundry handle it

  const [, cmd = ""] = text.split(/\s+/);
  if (cmd === "hello") {
    ChatMessage.create({
      speaker: chatData.speaker,
      content: `<p>${t("DefaultGreeting", { name: game.user.name })}</p>`
    });
  } else {
    ui.notifications.warn(t("UnknownCommand", { cmd: cmd || "(empty)" }));
  }
  return false; // we handled it: do not post the raw "/forja ..." text
});
```

Add this below the `ready` hook in `main.mjs`. Type `/forja hello` in chat to try it.

::: warning
Core owns commands like `/roll`, `/whisper` and `/ooc`. Pick a prefix unique to your package, and never return `false` for text you did not handle — that would swallow the user's message.
:::

## 6. A button on sheet headers

ApplicationV2 windows have a header menu (the "⋮" button). Before it is built, Foundry calls a hook named `getHeaderControls` + **class name** for each class in the application's inheritance chain. Listening to `getHeaderControlsActorSheetV2` therefore reaches every actor sheet built on `ActorSheetV2`, whatever the system.

```js
Hooks.on("getHeaderControlsActorSheetV2", (app, controls) => {
  const actor = app.document;
  controls.push({
    icon: "fa-solid fa-dice-d20",
    label: "FORJA_EXTRAS.QuickRoll",       // localized automatically
    action: "forjaExtrasQuickRoll",        // unique name, prefixed to avoid clashes
    visible: () => actor.isOwner,          // only for users who own the actor
    onClick: async () => {
      const roll = await new Roll("1d20").evaluate();
      await roll.toMessage({
        speaker: ChatMessage.getSpeaker({ actor }),
        flavor: t("QuickRollFlavor", { actor: actor.name })
      });
    }
  });
});
```

Open any actor sheet, click the header menu, and choose **Quick roll**.

::: tip
Discover which hook names an application fires by setting `CONFIG.debug.hooks = true` and opening it: you will see `getHeaderControlsForjaActorSheet`, `getHeaderControlsActorSheetV2`, `getHeaderControlsDocumentSheetV2`, `getHeaderControlsApplicationV2`… Pick the most specific one that covers what you need.
:::

::: v13
In V13 a header control entry is `{ icon, label, action, onClick?, visible?, ownership? }`. `onClick` receives the click `PointerEvent`.
:::

::: v14
In V14 header controls and context-menu entries were unified, so an entry follows the context-menu format (`label`, `icon`, `onClick`, `visible`, `group`, `classes`) plus `action` and `ownership`. The code above works unchanged.
:::

## 7. A little CSS

`styles/forja-extras.css` is loaded on every page. Scope your rules with a class so you never restyle core UI by accident:

```css
/* Only affects chat messages we tag with this class */
.chat-message .forja-extras-greeting {
  font-style: italic;
  color: var(--color-text-secondary);
}
```

To use it, change the greeting content to `<p class="forja-extras-greeting">${text}</p>`. With `flags.hotReload` set, CSS edits apply without a reload.

## Checklist when it doesn't work

- The module is **enabled** in *Manage Modules* (and you reloaded).
- The console (F12) shows `forja-extras | init`. If not, check the `esmodules` path and look for a syntax error in red.
- Keys show up raw (`FORJA_EXTRAS.QuickRoll`) → the language file path is wrong or the JSON is invalid.
- `game.settings.get` throws "not a registered game setting" → it ran before `init`, or the id/key is misspelled.

## Next steps

- Turn this into a real package for your own game: [Your first system](#first-system).
- Go deeper: [Hooks](#hooks), [Settings](#settings), [Localization](#localization), [Chat & Rolls](#chat-roll).
- Ship it: [Packaging & release](#packaging).
