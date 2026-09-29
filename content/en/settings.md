# Settings and keybindings

Settings store configuration values for your package — per world, per browser or per user — and keybindings let players trigger your features from the keyboard.

## What a setting is

A setting is a named value under your package namespace (`forja-extras.restHealing`). You **register** it once in `init`, then **read** and **write** it anywhere with `game.settings.get` / `game.settings.set`. Foundry takes care of storage, the Configure Settings UI, permissions and synchronization.

The most important decision is the **scope**:

| Scope | Stored in | Shared with | Who can change it | Use for |
| --- | --- | --- | --- | --- |
| `world` | The world database | Every user in the world | GM (users with `SETTINGS_MODIFY`) | Game rules, house rules |
| `client` | The browser's `localStorage` | Nobody — only this browser | The current user | Display preferences, performance options |
| `user` | The world database, per user | Only that user, on any device | That user | Personal preferences that should follow the player |

The `user` scope was added in V13. Before it, per-player preferences had to be `client` and were lost when the player switched computers.

## Register settings

```js
// modules/forja-extras/scripts/settings.js
export function registerSettings() {
  // World rule: shown in Configure Settings, GM only
  game.settings.register("forja-extras", "restHealing", {
    name: "FORJA_EXTRAS.Settings.RestHealing.Name",
    hint: "FORJA_EXTRAS.Settings.RestHealing.Hint",
    scope: "world",
    config: true,
    type: Boolean,
    default: true,
    onChange: (value) => console.log(`forja-extras | Rest healing is now ${value}`)
  });

  // Number with a slider
  game.settings.register("forja-extras", "restDice", {
    name: "FORJA_EXTRAS.Settings.RestDice.Name",
    scope: "world",
    config: true,
    type: Number,
    range: { min: 1, max: 6, step: 1 },
    default: 2
  });

  // Dropdown, per user (follows the player to any device)
  game.settings.register("forja-extras", "restAnnounce", {
    name: "FORJA_EXTRAS.Settings.RestAnnounce.Name",
    scope: "user",
    config: true,
    type: String,
    choices: {
      chat: "FORJA_EXTRAS.Settings.RestAnnounce.Chat",
      notify: "FORJA_EXTRAS.Settings.RestAnnounce.Notify",
      none: "FORJA_EXTRAS.Settings.RestAnnounce.None"
    },
    default: "chat"
  });

  // A DataField instance as the type: validated like a schema field
  game.settings.register("forja-extras", "maxRestsPerDay", {
    name: "FORJA_EXTRAS.Settings.MaxRests.Name",
    scope: "world",
    config: true,
    type: new foundry.data.fields.NumberField({ required: true, integer: true, min: 0, max: 10, initial: 1 }),
    default: 1,
    requiresReload: true
  });

  // Client-only, hidden from the settings UI: internal state for this browser
  game.settings.register("forja-extras", "lastSeenVersion", {
    scope: "client",
    config: false,
    type: String,
    default: ""
  });
}
```

```js
// modules/forja-extras/scripts/main.js
import { registerSettings, registerRestMenu } from "./settings.js";
import { registerKeybindings } from "./keybindings.js";

Hooks.once("init", () => {
  registerSettings();
  registerRestMenu();    // see "A settings menu" below
  registerKeybindings(); // see "Keybindings" below
});
```

### Registration options

| Option | Meaning |
| --- | --- |
| `name`, `hint` | Localization keys (or text) shown in Configure Settings |
| `scope` | `"world"`, `"client"` or `"user"` |
| `config` | `true` to show it in Configure Settings; `false` for hidden/internal settings |
| `type` | `String`, `Number`, `Boolean`, `Object`, `Array`, a `DataModel` class, or a `DataField` instance |
| `choices` | Object `{ value: labelKey }`; renders a dropdown (labels are localized) |
| `range` | `{ min, max, step }` for `Number`; renders a slider |
| `default` | Value returned until someone saves another one |
| `onChange` | Called with the new value on every client where it changed |
| `requiresReload` | Prompt the user to reload after changing it |
| `restricted` | (menus) Only GMs can open it |

::: warning
`Symbol` is not allowed as a setting type. Use `String` with `choices` instead.
:::

## Read and write

```js
// Read: synchronous
const healing = game.settings.get("forja-extras", "restHealing");

// Write: asynchronous, returns the saved value
await game.settings.set("forja-extras", "restDice", 3);
```

Writing a `world` setting requires the `SETTINGS_MODIFY` permission (a GM by default). If a player's action must change a world setting, send the request to a GM (see [sockets](#sockets)).

::: tip
Read settings in the `setup` hook or later. Registration happens in `init`, and world values are only guaranteed to be loaded after that.
:::

## A settings menu with ApplicationV2

When a group of options belongs together, register a **menu**: a button in Configure Settings that opens your own form. Store the values in one hidden setting whose type is a `DataModel`, so they are validated as a unit.

```js
// modules/forja-extras/scripts/rest-rules.js
const { NumberField, BooleanField } = foundry.data.fields;

export class RestRules extends foundry.abstract.DataModel {
  static LOCALIZATION_PREFIXES = ["FORJA_EXTRAS.RestRules"];

  static defineSchema() {
    return {
      healPercent: new NumberField({ required: true, integer: true, min: 0, max: 100, initial: 50 }),
      removeEffects: new BooleanField({ initial: true })
    };
  }
}
```

```js
// modules/forja-extras/scripts/rest-config.js
import { RestRules } from "./rest-rules.js";
const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

export class RestConfig extends HandlebarsApplicationMixin(ApplicationV2) {
  static DEFAULT_OPTIONS = {
    id: "forja-extras-rest-config",
    tag: "form",
    window: { title: "FORJA_EXTRAS.RestConfig.Title", icon: "fa-solid fa-bed", contentClasses: ["standard-form"] },
    position: { width: 420 },
    form: { handler: RestConfig.#onSubmit, closeOnSubmit: true }
  };

  static PARTS = {
    form: { template: "modules/forja-extras/templates/rest-config.hbs" },
    footer: { template: "templates/generic/form-footer.hbs" }
  };

  async _prepareContext(options) {
    return {
      rules: game.settings.get("forja-extras", "restRules"),
      fields: RestRules.schema.fields,
      buttons: [{ type: "submit", icon: "fa-solid fa-floppy-disk", label: "FORJA_EXTRAS.RestConfig.Save" }]
    };
  }

  /** Save the submitted form into the setting */
  static async #onSubmit(event, form, formData) {
    await game.settings.set("forja-extras", "restRules", foundry.utils.expandObject(formData.object));
  }
}
```

```hbs
{{!-- modules/forja-extras/templates/rest-config.hbs --}}
<section class="forja-extras-rest-config">
  {{formGroup fields.healPercent value=rules.healPercent localize=true}}
  {{formGroup fields.removeEffects value=rules.removeEffects localize=true}}
</section>
```

```js
// modules/forja-extras/scripts/settings.js (continued)
import { RestRules } from "./rest-rules.js";
import { RestConfig } from "./rest-config.js";

export function registerRestMenu() {
  game.settings.register("forja-extras", "restRules", {
    scope: "world",
    config: false, // edited through the menu, not listed directly
    type: RestRules,
    default: {}
  });

  game.settings.registerMenu("forja-extras", "restRulesMenu", {
    name: "FORJA_EXTRAS.RestConfig.Name",
    label: "FORJA_EXTRAS.RestConfig.Label", // text on the button
    hint: "FORJA_EXTRAS.RestConfig.Hint",
    icon: "fa-solid fa-bed",
    type: RestConfig,
    restricted: true // GM only
  });
}

// RestRules is not a document data model, so localize its field labels ourselves
Hooks.once("i18nInit", () => foundry.helpers.Localization.localizeDataModel(RestRules));
```

`game.settings.get("forja-extras", "restRules")` now returns a `RestRules` instance, so `rules.healPercent` is always a valid integer between 0 and 100.

## Reacting to changes

- `onChange` in the registration is the simplest option and runs on every client where the value changed.
- The `clientSettingChanged` hook fires for `client` settings.
- World and user settings are `Setting` documents, so `updateSetting` / `createSetting` hooks fire for them as well.

## Keybindings

Keybindings are registered like settings (in `init`), appear in **Configure Controls**, and can be remapped by each user.

```js
// modules/forja-extras/scripts/keybindings.js
export function registerKeybindings() {
  game.keybindings.register("forja-extras", "quickRest", {
    name: "FORJA_EXTRAS.Keybindings.QuickRest.Name",
    hint: "FORJA_EXTRAS.Keybindings.QuickRest.Hint",
    // Default binding: Shift + R. Users can change or add more.
    editable: [{ key: "KeyR", modifiers: ["Shift"] }],
    onDown: (context) => {
      const tokens = canvas.tokens?.controlled ?? [];
      if (!tokens.length) return false; // not handled: let other bindings try
      for (const token of tokens) {
        const actor = token.actor;
        if (actor?.isOwner) actor.update({ "system.hp.value": actor.system.hp.max });
      }
      return true; // handled: stop the event here
    },
    restricted: false, // true = GM only
    precedence: CONST.KEYBINDING_PRECEDENCE.NORMAL
  });
}
```

| Option | Meaning |
| --- | --- |
| `editable` | Default bindings the user may change: `{ key, modifiers }`, where `key` is a `KeyboardEvent.code` (`"KeyR"`, `"Digit1"`, `"F2"`) |
| `uneditable` | Bindings the user cannot remove |
| `onDown` / `onUp` | Handlers; return `true` to mark the event as handled |
| `repeat` | Whether `onDown` fires repeatedly while held |
| `restricted` | Only GMs can use it |
| `precedence` | `CONST.KEYBINDING_PRECEDENCE.PRIORITY`, `NORMAL` or `DEFERRED` — order relative to core bindings |

::: tip
Modifiers are written as `"Shift"`, `"Control"` and `"Alt"`. `"Control"` is automatically treated as ⌘ on macOS.
:::

## Pitfalls

- **Registering outside `init`.** Settings and keybindings registered later will not be in the configuration dialogs.
- **Using `client` for game rules.** Every browser would have its own value; rules must be `world`.
- **Players writing world settings.** `game.settings.set` rejects it; route through a GM.
- **Mutating the returned object.** `game.settings.get` for an `Object`/`DataModel` setting returns data you should treat as read-only; change it with `set`.
- **Unlocalized names.** Use keys in `name`, `hint`, `choices` and menu `label`; Foundry localizes them.
- **Forgetting `default`.** Without it, `get` returns `undefined` until the first save.
