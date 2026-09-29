# Data models

A `TypeDataModel` defines the shape, defaults, validation and derived values of the `system` data for each actor and item type of your system.

::: changed
- `template.json` is **deprecated**: declare types in the manifest `documentTypes` and define them with `TypeDataModel` (or leave them unspecified).
- `SchemaField#extendFields()` and `SchemaField#removeFields()` let packages add or remove fields from an existing schema.
- `DataModel#getFieldForProperty(key)` returns the `DataField` behind a property path.
- New `DataField` option `placeholder`, automatically localized.
- New `TypeDataModel#onEmbed(element)` callback, and new update lifecycle methods `_updateDiff` / `_updateCommit`.
- See [the full changelog](#changes-14).
:::

## What it is

Every `Actor` and `Item` has a `type` (for `forja`: `character`, `npc`, `weapon`) and a `system` object with that type's data. A **TypeDataModel** is a class that describes `system` for one type:

- **Schema** — which fields exist, their types, defaults and limits. Foundry validates every create and update against it, so bad data never reaches the database.
- **Preparation** — methods that compute values not stored in the database (modifiers, totals).
- **Migration** — a hook to convert old stored data into the current shape.
- **Behavior** — any getters or methods you want on `actor.system`.

Because the model is a real class, `actor.system.attributes.strength.mod` can be a computed value and `actor.system.isHeavy` can be a getter.

## Declare the types in the manifest

Types are declared in `system.json` under `documentTypes`. The server cannot run your JavaScript models, so this is also where you tell it which fields contain HTML (to be sanitized) and which contain file paths (with their allowed categories).

```json
{
  "id": "forja",
  "documentTypes": {
    "Actor": {
      "character": {
        "htmlFields": ["biography"],
        "filePathFields": { "crest": ["IMAGE"] }
      },
      "npc": {
        "htmlFields": ["biography"]
      }
    },
    "Item": {
      "weapon": {
        "htmlFields": ["description"],
        "filePathFields": { "sound": ["AUDIO"] }
      }
    }
  }
}
```

::: v13
V13 still accepts a `template.json` file that lists types and their default data. It keeps working, but you should declare types with `documentTypes` and define data with `TypeDataModel`, which is what V14 requires. You can use both during a transition; the data model takes priority for a type that has one.
:::

::: v14
`template.json` is **deprecated** in V14 and logs a warning. Remove it, declare every type in `documentTypes`, and give each type a `TypeDataModel` (a type without one simply has an unvalidated `system` object).
:::

## Define the schema

`defineSchema()` returns an object of `DataField` instances. All field classes live in `foundry.data.fields`. A shared base class avoids repeating fields between `character` and `npc`.

```js
// systems/forja/data/actor-base.mjs
const { SchemaField, NumberField, HTMLField } = foundry.data.fields;

export class ActorBaseData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA.Actor.Base"];

  static defineSchema() {
    return {
      hp: new SchemaField({
        value: new NumberField({ required: true, integer: true, min: 0, initial: 10 }),
        max: new NumberField({ required: true, integer: true, min: 0, initial: 10 })
      }),
      biography: new HTMLField({ required: true, blank: true })
    };
  }
}
```

```js
// systems/forja/data/character.mjs
import { ActorBaseData } from "./actor-base.mjs";

const {
  SchemaField, NumberField, StringField, BooleanField, ArrayField, SetField,
  TypedObjectField, EmbeddedDataField, DocumentUUIDField, FilePathField, ColorField
} = foundry.data.fields;

/** A small reusable model embedded inside the character */
class WalletData extends foundry.abstract.DataModel {
  static defineSchema() {
    return {
      gold: new NumberField({ required: true, integer: true, min: 0, initial: 0 }),
      silver: new NumberField({ required: true, integer: true, min: 0, initial: 0 })
    };
  }
  get totalInSilver() {
    return this.gold * 10 + this.silver;
  }
}

const attribute = () => new SchemaField({
  value: new NumberField({ required: true, integer: true, min: 1, max: 20, initial: 10 })
});

export class CharacterData extends ActorBaseData {
  static LOCALIZATION_PREFIXES = [...super.LOCALIZATION_PREFIXES, "FORJA.Actor.Character"];

  static defineSchema() {
    return {
      ...super.defineSchema(),
      level: new NumberField({ required: true, integer: true, min: 1, max: 10, initial: 1 }),
      attributes: new SchemaField({
        strength: attribute(),
        agility: attribute(),
        mind: attribute()
      }),
      origin: new StringField({
        required: true,
        blank: false,
        initial: "human",
        choices: { human: "FORJA.Origin.Human", dwarf: "FORJA.Origin.Dwarf", elf: "FORJA.Origin.Elf" }
      }),
      inspired: new BooleanField({ initial: false }),
      languages: new SetField(new StringField({ blank: false })),
      skills: new TypedObjectField(new SchemaField({
        rank: new NumberField({ required: true, integer: true, min: 0, max: 5, initial: 0 }),
        trained: new BooleanField()
      })),
      notes: new ArrayField(new SchemaField({
        title: new StringField({ required: true, blank: false }),
        text: new StringField()
      })),
      wallet: new EmbeddedDataField(WalletData),
      patron: new DocumentUUIDField({ type: "Actor" }),
      crest: new FilePathField({ categories: ["IMAGE"] }),
      color: new ColorField({ initial: "#b5651d" })
    };
  }

  prepareDerivedData() {
    // Modifier derived from each attribute, not stored in the database
    for (const attr of Object.values(this.attributes)) {
      attr.mod = Math.floor((attr.value - 10) / 2);
    }
    // Defense is always derived, so it is not part of the schema
    this.defense = 10 + this.attributes.agility.mod;
  }

  getRollData() {
    // Flatten what formulas need: @str, @agi, @mind, @level, @defense
    return {
      level: this.level,
      hp: this.hp,
      attributes: this.attributes,
      defense: this.defense,
      str: this.attributes.strength.mod,
      agi: this.attributes.agility.mod,
      mind: this.attributes.mind.mod
    };
  }
}
```

```js
// systems/forja/data/npc.mjs
import { ActorBaseData } from "./actor-base.mjs";
const { NumberField, ObjectField } = foundry.data.fields;

export class NpcData extends ActorBaseData {
  static LOCALIZATION_PREFIXES = [...super.LOCALIZATION_PREFIXES, "FORJA.Actor.Npc"];

  static defineSchema() {
    return {
      ...super.defineSchema(),
      threat: new NumberField({ required: true, integer: true, min: 0, initial: 1 }),
      // Free-form data, not validated: use sparingly
      extra: new ObjectField()
    };
  }
}
```

```js
// systems/forja/data/weapon.mjs
const { StringField, NumberField, BooleanField, HTMLField, SetField, FilePathField } = foundry.data.fields;

export class WeaponData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA.Item.Weapon"];

  static defineSchema() {
    return {
      description: new HTMLField({ required: true, blank: true }),
      damage: new StringField({ required: true, blank: false, initial: "1d6" }),
      weight: new NumberField({ required: true, min: 0, initial: 1 }),
      equipped: new BooleanField({ initial: false }),
      properties: new SetField(new StringField({
        choices: { light: "FORJA.Weapon.Light", heavy: "FORJA.Weapon.Heavy", thrown: "FORJA.Weapon.Thrown" }
      })),
      sound: new FilePathField({ categories: ["AUDIO"] })
    };
  }

  get isHeavy() {
    return this.properties.has("heavy");
  }
}
```

## Field reference

| Field | Stores | Notes |
| --- | --- | --- |
| `StringField` | string | `blank`, `trim`, `choices` |
| `NumberField` | number | `min`, `max`, `step`, `integer`, `positive`, `choices` |
| `BooleanField` | boolean | defaults to `false` |
| `HTMLField` | HTML string | edited with the rich-text editor; list it in `htmlFields` |
| `SchemaField` | nested object with fixed keys | takes an object of fields |
| `ArrayField` | array | takes the element field: `new ArrayField(new StringField())` |
| `SetField` | `Set` in memory, array in the database | unique values |
| `ObjectField` | any plain object | no validation of contents |
| `TypedObjectField` | object with **arbitrary keys**, each value validated | great for "skills by id" |
| `EmbeddedDataField` | an instance of another `DataModel` | reusable sub-models with methods |
| `DocumentUUIDField` | UUID string | `type` restricts the document type |
| `FilePathField` | file path | `categories`: `IMAGE`, `AUDIO`, `VIDEO`, `TEXT`… |
| `ColorField` | `#rrggbb` string | rendered as a color picker in forms |

### Common options

| Option | Meaning |
| --- | --- |
| `required` | The key must exist (Foundry fills in `initial` if missing) |
| `nullable` | `null` is an accepted value |
| `initial` | Default value (or a function returning one) |
| `min` / `max` / `integer` | Numeric constraints (`NumberField`) |
| `blank` | Whether `""` is valid (`StringField`) |
| `choices` | Allowed values: an array, an object `{ value: labelKey }`, or a function |
| `label` / `hint` | Text for forms; usually supplied by `LOCALIZATION_PREFIXES` instead |

::: v14
**`placeholder`** is a new option shown as the input's placeholder text in generated forms. It is localized automatically, so you can pass a key:

```js
// Placeholder text for an empty field in the form
name: new foundry.data.fields.StringField({ placeholder: "FORJA.Placeholder.Nickname" })
```
:::

## Register the models

```js
// systems/forja/forja.mjs
import { CharacterData } from "./data/character.mjs";
import { NpcData } from "./data/npc.mjs";
import { WeaponData } from "./data/weapon.mjs";

Hooks.once("init", () => {
  CONFIG.Actor.dataModels.character = CharacterData;
  CONFIG.Actor.dataModels.npc = NpcData;
  CONFIG.Item.dataModels.weapon = WeaponData;
});
```

Core localizes models registered in `CONFIG.<Document>.dataModels` automatically. For other models (such as `WalletData` used alone) call `foundry.helpers.Localization.localizeDataModel(Model)` in the `i18nInit` hook.

## Automatic labels with LOCALIZATION_PREFIXES

Instead of writing `label` and `hint` in every field, give the class one or more prefixes. Foundry looks up `<prefix>.FIELDS.<field path>.label` and `.hint`:

```json
{
  "FORJA": {
    "Actor": {
      "Base": {
        "FIELDS": {
          "hp": {
            "label": "Hit Points",
            "value": { "label": "Current" },
            "max": { "label": "Maximum" }
          },
          "biography": { "label": "Biography" }
        }
      },
      "Character": {
        "FIELDS": {
          "level": { "label": "Level", "hint": "From 1 to 10." },
          "attributes": {
            "strength": { "value": { "label": "Strength" } }
          }
        }
      }
    }
  }
}
```

These labels are used by `{{formGroup}}` and `{{formInput}}` in sheets, and by `field.label` in your own code. See [localization](#localization).

## Data preparation

- `prepareBaseData()` runs **before** Active Effects are applied — set up values that effects may modify.
- `prepareDerivedData()` runs **after** embedded items and effects are prepared — compute totals and modifiers.

Both run on every client, every time the document changes. Only assign to `this`; never call `update()` here. The full order with the document methods is on the [documents](#documents) page.

## Roll data

Foundry does not call `system.getRollData()` by itself. Wire it from your actor class so formulas like `1d20 + @str` work:

```js
// systems/forja/documents/actor.mjs
export class ForjaActor extends Actor {
  getRollData() {
    // Use the data model's roll data when it provides one
    return this.system.getRollData?.() ?? super.getRollData();
  }
}
```

## Migrating old data

`static migrateData(source)` receives the **raw** stored data every time a document is loaded or updated, before validation. Convert old shapes and always call `super`.

```js
// systems/forja/data/character.mjs (inside CharacterData)
static migrateData(source) {
  // Old versions stored hit points as a single number named "health"
  if (typeof source.health === "number") {
    source.hp ??= {};
    source.hp.value ??= source.health;
    delete source.health;
  }
  return super.migrateData(source);
}
```

`migrateData` only changes the in-memory copy. To rewrite the database permanently, run a world migration (see [migrations](#migrations)).

## Extending a schema from a module

::: v13
There is no public API to add fields to another package's data model in V13. Modules should store their data in [flags](#documents) instead.
:::

::: v14
`SchemaField#extendFields(fields)` and `SchemaField#removeFields(names)` modify a schema definition. A module can use them in `init` (system scripts load first, so the model is already registered):

```js
// modules/forja-extras/scripts/main.js
Hooks.once("init", () => {
  const CharacterData = CONFIG.Actor.dataModels.character;
  // Adds system.reputation to every forja character
  CharacterData.schema.extendFields({
    reputation: new foundry.data.fields.NumberField({ required: true, integer: true, initial: 0 })
  });
});
```

`getFieldForProperty` finds the field behind a path, which is handy to read labels or choices generically:

```js
const field = actor.system.getFieldForProperty("attributes.strength.value");
console.log(field.label, field.max); // "Strength", 20
```

`onEmbed(element)` is called when the document's HTML embed (`@Embed[...]`) has been added to the DOM — use it to attach listeners to embedded content.
:::

## Pitfalls

- **Missing `...super.defineSchema()`** in a subclass drops all the base fields.
- **Storing derived values.** A `mod` computed in `prepareDerivedData` must not also be a schema field, or it will be overwritten on every update.
- **Using `ObjectField` for everything** throws away validation. Prefer `SchemaField` or `TypedObjectField`.
- **Forgetting `htmlFields`** means HTML content may not be handled correctly by the server.
- **`choices` values are labels.** For `{ human: "FORJA.Origin.Human" }` the stored value is `"human"`, and the label key is localized for display.
- **Registering too late.** Models must be set in `init`, before documents are constructed.
