# Localization

Ship every string in language files, translate data model labels automatically, and make your package easy for the community to translate.

::: changed
- `game.i18n.localize(key, data)` now also does what `format()` did: pass an object and `{placeholders}` are filled in. `format()` still works.
- New global shortcut `_loc(key, data)` for `game.i18n.localize`.
- `LOCALIZATION_PREFIXES` were added to more core models (`BaseDrawing`, `BaseJournalEntryPage`).
- `DataField#placeholder` is a new field option and is localized automatically, like `label` and `hint`.
- Compendium titles are localized in search results.
- See [the full changelog](#changes-14).
:::

## How localization works

Foundry loads one JSON dictionary per language. At startup it merges the dictionaries of the core, the system and every active module for the language the user picked, then falls back to English for missing keys. Your code never contains visible text; it contains **keys**.

```text
lang/en.json      →  "FORJA.Sheet.Attributes": "Attributes"
lang/pt-BR.json   →  "FORJA.Sheet.Attributes": "Atributos"
code / template   →  game.i18n.localize("FORJA.Sheet.Attributes")
```

## Declare the languages in the manifest

```json
{
  "languages": [
    { "lang": "en",    "name": "English",              "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)",   "path": "lang/pt-BR.json" }
  ]
}
```

- `lang` is the language code the user selects in **Configure Settings → Language**. Use `pt-BR` for Brazilian Portuguese.
- A module can ship translations *for another package*. Add `"system": "forja"` (or `"module": "some-module"`) to the entry, and the file is only loaded when that package is active. This is how community translation modules work.

## Write the language file

Keys can be flat (`"FORJA.Sheet.Attributes"`) or nested objects. Nested is easier to maintain; Foundry flattens it on load.

```json
{
  "FORJA": {
    "Sheet": {
      "Attributes": "Attributes",
      "Inventory": "Inventory"
    },
    "Roll": {
      "Attack": "{name} attacks with {weapon}!",
      "Success": "Success",
      "Failure": "Failure"
    },
    "Settings": {
      "Difficulty": { "Name": "Default difficulty", "Hint": "Target number used when none is given." }
    }
  }
}
```

::: tip
Prefix every key with your package id in upper case (`FORJA.`, `FORJAEXTRAS.`). Keys share one global dictionary, so a bare `"Attack"` can collide with the core or another module.
:::

## Use keys in JavaScript

::: v13
```js
// Simple text
game.i18n.localize("FORJA.Sheet.Attributes");            // "Attributes"

// Text with placeholders: use format()
game.i18n.format("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });

// Check before using an optional key
if ( game.i18n.has("FORJA.Tips.Rare") ) ui.notifications.info("FORJA.Tips.Rare", { localize: true });
```
:::

::: v14
```js
// Simple text
game.i18n.localize("FORJA.Sheet.Attributes");            // "Attributes"

// localize() now accepts data and fills {placeholders}
game.i18n.localize("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });

// Global shortcut, handy in long UI code
_loc("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });

// format() keeps working, so code shared with V13 does not break
game.i18n.format("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });
```
:::

`game.i18n.lang` holds the active language code, which is useful for `Intl` formatting:

```js
const fmt = new Intl.NumberFormat(game.i18n.lang, { maximumFractionDigits: 1 });
fmt.format(1234.5); // "1,234.5" in en, "1.234,5" in pt-BR
```

## Use keys in Handlebars templates

```hbs
<h2>{{localize "FORJA.Sheet.Attributes"}}</h2>

{{!-- Placeholders are passed as named arguments --}}
<p>{{localize "FORJA.Roll.Attack" name=actor.name weapon=item.name}}</p>

{{!-- Data model fields: labels come from the schema (see below) --}}
{{formGroup fields.hp.fields.value value=system.hp.value localize=true}}
```

## Localize data model labels automatically

Instead of hardcoding `label:` in each field, declare `LOCALIZATION_PREFIXES` on the model. Foundry then looks up `<prefix>.FIELDS.<path>.label` and `.hint` for every field, and `formGroup` / `formInput` show them.

```js
export class CharacterData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA.Actor.Character"];

  static defineSchema() {
    const { SchemaField, NumberField } = foundry.data.fields;
    return {
      hp: new SchemaField({
        value: new NumberField({ required: true, integer: true, min: 0, initial: 10 }),
        max:   new NumberField({ required: true, integer: true, min: 0, initial: 10 })
      })
    };
  }
}
```

```json
{
  "FORJA": {
    "Actor": {
      "Character": {
        "FIELDS": {
          "hp": {
            "label": "Hit points",
            "value": { "label": "Current", "hint": "Damage lowers this value." },
            "max":   { "label": "Maximum" }
          }
        }
      }
    }
  }
}
```

The core localizes the models registered in `CONFIG.<Document>.dataModels` during startup. For a model you build yourself (for example a settings object), call the helper once in `i18nInit`:

```js
Hooks.once("i18nInit", () => {
  foundry.helpers.Localization.localizeDataModel(MySettingsModel);
});
```

::: warning
Check the exact namespace of `Localization` in the API docs for your version before relying on it. Older code uses the global `Localization.localizeDataModel`.
:::

::: v14
Fields also accept a `placeholder` option. It is localized like `label` and `hint` (`<prefix>.FIELDS.<path>.placeholder`) and is shown inside empty inputs.
:::

## Localize document type names

The type selector in "Create Actor" shows `TYPES.<Document>.<type>`:

```json
{
  "TYPES": {
    "Actor": { "character": "Character", "npc": "Non-player character" },
    "Item":  { "weapon": "Weapon", "spell": "Spell", "gear": "Gear" }
  }
}
```

## Settings, notifications and dialogs

Most core APIs take a key and localize it for you:

```js
game.settings.register("forja", "difficulty", {
  name: "FORJA.Settings.Difficulty.Name",   // localized automatically
  hint: "FORJA.Settings.Difficulty.Hint",
  scope: "world", config: true, type: Number, default: 10
});

ui.notifications.warn("FORJA.Warn.NoTarget", { localize: true });
```

## Timing: when is the dictionary ready?

| Hook | `game.i18n` usable? |
|---|---|
| `init` | No. Only register things; store **keys**, not translated text. |
| `i18nInit` | Yes. Translate anything you need to prepare once. |
| `setup`, `ready` | Yes. |

::: warning
Calling `localize` in `init` returns the key itself. A common bug is translating `CONFIG` choices in `init`: store the keys and translate when rendering, or translate in `i18nInit`.
:::

## Compendium content

Pack documents are stored in one language. Two common strategies:

1. **One pack per language**, each declared with its own `label` key in the manifest.
2. **Translation modules** (such as Babele) that map document names and descriptions at load time. Keep stable `_id`s and names in English to make this easy.

::: v14
Compendium titles are now localized in search results, so give every pack a translatable `label` key.
:::

## Checklist: a translation-ready package

- [ ] No visible text in `.mjs` or `.hbs` files: only keys.
- [ ] All keys start with your package id.
- [ ] `en.json` is complete; other languages may be partial (English is the fallback).
- [ ] Placeholders use names (`{weapon}`), never string concatenation, because word order changes between languages.
- [ ] Data models use `LOCALIZATION_PREFIXES` instead of hardcoded labels.
- [ ] Numbers and dates use `Intl` with `game.i18n.lang`.
- [ ] The README tells translators which file to copy and how to send it back.

## Pitfalls

- **Missing key shows the key itself.** If you see `FORJA.Sheet.Attributes` on screen, the key is misspelled or the language file failed to parse. Check the console for JSON errors.
- **Duplicate keys in nested JSON** silently overwrite each other. Validate files with a JSON linter in CI.
- **pt vs pt-BR.** The user's language must match `lang` exactly. Ship `pt-BR` if your audience is Brazilian.
