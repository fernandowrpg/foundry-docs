# Your first system

Build the minimal `forja` system: manifest with document types, data models, an ApplicationV2 actor and item sheet, templates, translations and CSS.

::: changed
- **`template.json` is deprecated.** Declare types in `documentTypes` and define their data with `TypeDataModel` classes — exactly what this page does.
- Manifest: `compatibility.minimum` `"14"` and the optional `"type": "system"`.
- Active Effects store their changes in `effect.system.changes` (with a string `type` instead of a numeric `mode`) — relevant as soon as your system adds effects.
- See [the full changelog](#changes-14).
:::

## What we will build

A tiny fantasy RPG:

- **Actor** types `character` and `npc`, with hit points and three attributes (strength, agility, mind). Characters also have a level.
- **Item** types `weapon` and `spell`, each with a damage formula.
- A character sheet where clicking an attribute rolls `1d20 + attribute`, and clicking an item rolls its damage.

Everything uses the V13+ architecture: data models, `ApplicationV2` sheets and ES modules.

## 1. Folder layout

```bash
Data/systems/forja/
├── system.json
├── module/
│   ├── forja.mjs              # entry point (the only file in esmodules)
│   ├── data/
│   │   ├── actor.mjs          # CharacterData, NpcData
│   │   └── item.mjs           # WeaponData, SpellData
│   └── sheets/
│       ├── actor-sheet.mjs
│       └── item-sheet.mjs
├── templates/
│   ├── actor-sheet.hbs
│   └── item-sheet.hbs
├── lang/
│   ├── en.json
│   └── pt-BR.json
└── styles/
    └── forja.css
```

## 2. The manifest

`documentTypes` tells Foundry which sub-types exist. Without it, the "Create Actor" dialog has nothing to offer. `htmlFields` marks fields that contain rich text so Foundry treats them correctly (enrichment, sanitizing).

::: v13
```json
{
  "id": "forja",
  "title": "Forja RPG",
  "description": "A tiny fantasy RPG used as an example.",
  "version": "0.1.0",
  "compatibility": { "minimum": "13", "verified": "13.351" },
  "esmodules": ["module/forja.mjs"],
  "styles": ["styles/forja.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    },
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] }
    }
  },
  "grid": { "type": 1, "distance": 1.5, "units": "m" },
  "primaryTokenAttribute": "hp",
  "initiative": "1d20 + @attributes.agility.value",
  "flags": {
    "hotReload": { "extensions": ["css", "hbs", "json"], "paths": ["styles", "templates", "lang"] }
  }
}
```

V13 still reads a `template.json` if you ship one, but you do not need it: data models replace it. Skipping it now saves you a migration later.
:::

::: v14
```json
{
  "id": "forja",
  "type": "system",
  "title": "Forja RPG",
  "description": "A tiny fantasy RPG used as an example.",
  "version": "0.1.0",
  "compatibility": { "minimum": "14", "verified": "14.368" },
  "esmodules": ["module/forja.mjs"],
  "styles": ["styles/forja.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    },
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] }
    }
  },
  "grid": { "type": 1, "distance": 1.5, "units": "m" },
  "primaryTokenAttribute": "hp",
  "initiative": "1d20 + @attributes.agility.value",
  "flags": {
    "hotReload": { "extensions": ["css", "hbs", "json"], "paths": ["styles", "templates", "lang"] }
  }
}
```

::: warning
Do not create a `template.json` in V14: it is deprecated. All type data comes from the data models below.
:::
:::

## 3. Data models

A **data model** is a class that describes the `system` object of a document type: field types, defaults, validation. Foundry uses it to clean input (a string `"12"` from a form becomes the number `12`), to fill defaults on creation, and to give you a place for derived values.

`module/data/actor.mjs`:

```js
const { SchemaField, NumberField, HTMLField } = foundry.data.fields;

// Small helper: one attribute = { value }
const attribute = () => new SchemaField({
  value: new NumberField({ required: true, integer: true, min: 0, initial: 1 })
});

// Fields shared by every Forja actor
class ForjaActorData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      hp: new SchemaField({
        value: new NumberField({ required: true, integer: true, min: 0, initial: 10 }),
        max: new NumberField({ required: true, integer: true, min: 0, initial: 10 })
      }),
      attributes: new SchemaField({
        strength: attribute(),
        agility: attribute(),
        mind: attribute()
      }),
      biography: new HTMLField()
    };
  }

  // Derived data: computed every time the document is prepared, never saved
  prepareDerivedData() {
    this.hp.value = Math.min(this.hp.value, this.hp.max);
  }
}

export class CharacterData extends ForjaActorData {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      level: new NumberField({ required: true, integer: true, min: 1, initial: 1 })
    };
  }
}

export class NpcData extends ForjaActorData {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      threat: new NumberField({ required: true, integer: true, min: 0, initial: 1 })
    };
  }
}
```

`module/data/item.mjs`:

```js
const { StringField, NumberField, HTMLField } = foundry.data.fields;

export class WeaponData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      damage: new StringField({ required: true, initial: "1d6" }),
      // Which attribute is added to attack rolls
      attribute: new StringField({ required: true, initial: "strength", choices: ["strength", "agility", "mind"] }),
      description: new HTMLField()
    };
  }
}

export class SpellData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      damage: new StringField({ required: true, initial: "" }),
      cost: new NumberField({ required: true, integer: true, min: 0, initial: 1 }),
      description: new HTMLField()
    };
  }
}
```

More field types and lifecycle methods are in [Data models](#data-models).

## 4. The actor sheet

Sheets are ApplicationV2 classes. `HandlebarsApplicationMixin` adds template rendering through `static PARTS`; `ActorSheetV2` adds document saving, drag & drop and actor-specific actions. Buttons in the template call methods through `data-action="name"` → `DEFAULT_OPTIONS.actions.name`.

`module/sheets/actor-sheet.mjs`:

```js
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2 } = foundry.applications.sheets;
const { TextEditor } = foundry.applications.ux;

export class ForjaActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "actor"],
    position: { width: 560, height: 640 },
    window: { resizable: true },
    form: { submitOnChange: true },   // save every field as soon as it changes
    actions: {
      rollAttribute: ForjaActorSheet.#onRollAttribute,
      rollItem: ForjaActorSheet.#onRollItem,
      createItem: ForjaActorSheet.#onCreateItem,
      editItem: ForjaActorSheet.#onEditItem,
      deleteItem: ForjaActorSheet.#onDeleteItem
    }
  };

  static PARTS = {
    sheet: { template: "systems/forja/templates/actor-sheet.hbs" }
  };

  /** Data available inside the template. */
  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const actor = this.document;
    context.actor = actor;
    context.system = actor.system;
    context.isCharacter = actor.type === "character";
    context.attributes = Object.entries(CONFIG.FORJA.attributes).map(([key, label]) => ({
      key, label, value: actor.system.attributes[key].value
    }));
    context.weapons = actor.items.filter(i => i.type === "weapon");
    context.spells = actor.items.filter(i => i.type === "spell");
    context.enrichedBiography = await TextEditor.implementation.enrichHTML(actor.system.biography, {
      secrets: actor.isOwner, relativeTo: actor
    });
    return context;
  }

  /** Find the embedded Item for a clicked element. */
  #getItem(target) {
    const id = target.closest("[data-item-id]")?.dataset.itemId;
    return this.document.items.get(id);
  }

  // Actions: "this" is the sheet instance
  static async #onRollAttribute(event, target) {
    const key = target.dataset.attribute;
    const roll = await new Roll("1d20 + @attr", { attr: this.document.system.attributes[key].value }).evaluate();
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this.document }),
      flavor: game.i18n.localize(CONFIG.FORJA.attributes[key])
    });
  }

  static async #onRollItem(event, target) {
    const item = this.#getItem(target);
    if (!item?.system.damage) return ui.notifications.warn(game.i18n.localize("FORJA.NoDamage"));
    const roll = await new Roll(item.system.damage).evaluate();
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this.document }),
      flavor: `${game.i18n.localize("FORJA.Damage")}: ${item.name}`
    });
  }

  static async #onCreateItem(event, target) {
    const type = target.dataset.type;
    await this.document.createEmbeddedDocuments("Item", [{
      name: game.i18n.localize(`TYPES.Item.${type}`), type
    }]);
  }

  static #onEditItem(event, target) {
    this.#getItem(target)?.sheet.render({ force: true });
  }

  static async #onDeleteItem(event, target) {
    await this.#getItem(target)?.delete();
  }
}
```

::: tip
`super._prepareContext()` already provides `document`, `source`, `fields`, `editable` and `user`. We add shortcuts (`actor`, `system`) so templates stay short.
:::

### The actor template

`templates/actor-sheet.hbs` — a part template must have **one root element**:

```hbs
<section class="forja-actor">
  <header class="sheet-header">
    <img class="profile" src="{{actor.img}}" alt="{{actor.name}}" data-action="editImage" data-edit="img">
    <div class="identity">
      <input name="name" type="text" value="{{actor.name}}" placeholder="{{localize 'FORJA.Name'}}">
      <label>{{localize "FORJA.HP"}}
        <input name="system.hp.value" type="number" value="{{system.hp.value}}">
        / <input name="system.hp.max" type="number" value="{{system.hp.max}}">
      </label>
      {{#if isCharacter}}
      <label>{{localize "FORJA.Level"}} <input name="system.level" type="number" value="{{system.level}}"></label>
      {{else}}
      <label>{{localize "FORJA.Threat"}} <input name="system.threat" type="number" value="{{system.threat}}"></label>
      {{/if}}
    </div>
  </header>

  <section class="attributes">
    {{#each attributes as |attr|}}
    <div class="attribute">
      <button type="button" data-action="rollAttribute" data-attribute="{{attr.key}}">{{localize attr.label}}</button>
      <input name="system.attributes.{{attr.key}}.value" type="number" value="{{attr.value}}">
    </div>
    {{/each}}
  </section>

  <section class="items">
    <h3>{{localize "TYPES.Item.weapon"}}
      <button type="button" data-action="createItem" data-type="weapon"><i class="fa-solid fa-plus"></i></button>
    </h3>
    <ul>
      {{#each weapons as |item|}}
      <li class="item" data-item-id="{{item.id}}">
        <img src="{{item.img}}" alt="">
        <a data-action="rollItem">{{item.name}}</a>
        <span class="formula">{{item.system.damage}}</span>
        <a data-action="editItem"><i class="fa-solid fa-pen"></i></a>
        <a data-action="deleteItem"><i class="fa-solid fa-trash"></i></a>
      </li>
      {{/each}}
    </ul>

    <h3>{{localize "TYPES.Item.spell"}}
      <button type="button" data-action="createItem" data-type="spell"><i class="fa-solid fa-plus"></i></button>
    </h3>
    <ul>
      {{#each spells as |item|}}
      <li class="item" data-item-id="{{item.id}}">
        <img src="{{item.img}}" alt="">
        <a data-action="rollItem">{{item.name}}</a>
        <span class="formula">{{item.system.cost}} {{localize "FORJA.Mana"}}</span>
        <a data-action="editItem"><i class="fa-solid fa-pen"></i></a>
        <a data-action="deleteItem"><i class="fa-solid fa-trash"></i></a>
      </li>
      {{/each}}
    </ul>
  </section>

  <h3>{{localize "FORJA.Biography"}}</h3>
  <prose-mirror name="system.biography" value="{{system.biography}}" toggled>{{{enrichedBiography}}}</prose-mirror>
</section>
```

Inputs are saved automatically because their `name` matches a document path (`system.hp.value`) and the form has `submitOnChange`.

## 5. The item sheet

`module/sheets/item-sheet.mjs`:

```js
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ItemSheetV2 } = foundry.applications.sheets;
const { TextEditor } = foundry.applications.ux;

export class ForjaItemSheet extends HandlebarsApplicationMixin(ItemSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "item"],
    position: { width: 420, height: 480 },
    window: { resizable: true },
    form: { submitOnChange: true }
  };

  static PARTS = {
    sheet: { template: "systems/forja/templates/item-sheet.hbs" }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const item = this.document;
    context.item = item;
    context.system = item.system;
    context.isWeapon = item.type === "weapon";
    context.attributeChoices = CONFIG.FORJA.attributes;
    context.enrichedDescription = await TextEditor.implementation.enrichHTML(item.system.description, {
      secrets: item.isOwner, relativeTo: item
    });
    return context;
  }
}
```

`templates/item-sheet.hbs`:

```hbs
<section class="forja-item">
  <header class="sheet-header">
    <img class="profile" src="{{item.img}}" alt="{{item.name}}" data-action="editImage" data-edit="img">
    <input name="name" type="text" value="{{item.name}}">
  </header>

  <div class="form-group">
    <label>{{localize "FORJA.Damage"}}</label>
    <input name="system.damage" type="text" value="{{system.damage}}" placeholder="1d6">
  </div>

  {{#if isWeapon}}
  <div class="form-group">
    <label>{{localize "FORJA.Attribute.label"}}</label>
    <select name="system.attribute">
      {{selectOptions attributeChoices selected=system.attribute localize=true}}
    </select>
  </div>
  {{else}}
  <div class="form-group">
    <label>{{localize "FORJA.Cost"}}</label>
    <input name="system.cost" type="number" value="{{system.cost}}">
  </div>
  {{/if}}

  <prose-mirror name="system.description" value="{{system.description}}" toggled>{{{enrichedDescription}}}</prose-mirror>
</section>
```

## 6. The entry point: register everything

`module/forja.mjs` is the only file listed in `esmodules`. It imports the classes and registers them during `init`.

```js
import { CharacterData, NpcData } from "./data/actor.mjs";
import { WeaponData, SpellData } from "./data/item.mjs";
import { ForjaActorSheet } from "./sheets/actor-sheet.mjs";
import { ForjaItemSheet } from "./sheets/item-sheet.mjs";

Hooks.once("init", () => {
  console.log("forja | init");

  // System-wide constants used by sheets and rolls
  CONFIG.FORJA = {
    attributes: {
      strength: "FORJA.Attribute.strength",
      agility: "FORJA.Attribute.agility",
      mind: "FORJA.Attribute.mind"
    }
  };

  // Link each sub-type from documentTypes to its data model
  Object.assign(CONFIG.Actor.dataModels, { character: CharacterData, npc: NpcData });
  Object.assign(CONFIG.Item.dataModels, { weapon: WeaponData, spell: SpellData });

  // Register the sheets (V13+ has no core default actor/item sheets)
  const { DocumentSheetConfig } = foundry.applications.apps;
  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaActorSheet, {
    types: ["character", "npc"], makeDefault: true, label: "FORJA.Sheet.Actor"
  });
  DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
    types: ["weapon", "spell"], makeDefault: true, label: "FORJA.Sheet.Item"
  });
});
```

::: warning
The keys in `CONFIG.Actor.dataModels` must match the keys in `documentTypes` exactly. A type without a data model has an empty `system` object — no errors, just missing fields.
:::

## 7. Translations

`TYPES.<Document>.<type>` is the core convention for type names in dialogs and sheets.

`lang/en.json`:

```json
{
  "TYPES": {
    "Actor": { "character": "Character", "npc": "NPC" },
    "Item": { "weapon": "Weapon", "spell": "Spell" }
  },
  "FORJA": {
    "Name": "Name",
    "HP": "Hit points",
    "Level": "Level",
    "Threat": "Threat",
    "Damage": "Damage",
    "Cost": "Mana cost",
    "Mana": "MP",
    "Biography": "Biography",
    "NoDamage": "This item has no damage formula.",
    "Attribute": { "label": "Attribute", "strength": "Strength", "agility": "Agility", "mind": "Mind" },
    "Sheet": { "Actor": "Forja actor sheet", "Item": "Forja item sheet" }
  }
}
```

`lang/pt-BR.json`:

```json
{
  "TYPES": {
    "Actor": { "character": "Personagem", "npc": "PdM" },
    "Item": { "weapon": "Arma", "spell": "Magia" }
  },
  "FORJA": {
    "Name": "Nome",
    "HP": "Pontos de vida",
    "Level": "Nível",
    "Threat": "Ameaça",
    "Damage": "Dano",
    "Cost": "Custo de mana",
    "Mana": "PM",
    "Biography": "Biografia",
    "NoDamage": "Este item não tem fórmula de dano.",
    "Attribute": { "label": "Atributo", "strength": "Força", "agility": "Agilidade", "mind": "Mente" },
    "Sheet": { "Actor": "Ficha de ator Forja", "Item": "Ficha de item Forja" }
  }
}
```

## 8. Styles

`styles/forja.css` — scope everything under the `forja` class you set in `DEFAULT_OPTIONS.classes`:

```css
.forja.sheet .sheet-header { display: flex; gap: 0.5rem; align-items: center; }
.forja.sheet .sheet-header .profile { width: 80px; height: 80px; object-fit: cover; cursor: pointer; }
.forja.sheet .identity { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.forja.sheet .identity input[type="number"] { width: 4rem; }
.forja.sheet .attributes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin: 0.5rem 0; }
.forja.sheet .attribute { display: flex; flex-direction: column; align-items: center; }
.forja.sheet .items ul { list-style: none; padding: 0; margin: 0; }
.forja.sheet .item { display: flex; align-items: center; gap: 0.5rem; }
.forja.sheet .item img { width: 24px; height: 24px; }
.forja.sheet .item .formula { margin-left: auto; opacity: 0.8; }
.forja.sheet prose-mirror { min-height: 8rem; }
```

## 9. Try it

1. Restart Foundry (new package), create a world with **Forja RPG**, and launch it.
2. In the Actors tab, create a **Character**. Your sheet opens.
3. Change HP and attributes, click **Strength** to roll, add a weapon and click its name to roll damage.
4. Drag the actor onto a scene: the token bar shows HP (`primaryTokenAttribute`).

::: v14
Once you add Active Effects, remember that in V14 their changes live in `effect.system.changes`, each with `{ key, value, type, phase, priority }`, where `type` is a string such as `"add"` or `"override"`. See [Active Effects](#active-effect).
:::

::: v13
Once you add Active Effects, their changes live in `effect.changes`, each with `{ key, value, mode, priority }`, where `mode` is a number from `CONST.ACTIVE_EFFECT_MODES`. See [Active Effects](#active-effect).
:::

## Pitfalls

- **Sheet does not open / "no sheet registered"** — check that `registerSheet` ran in `init` and that its `types` list matches `documentTypes`.
- **Fields do not save** — the input's `name` must be the full path (`system.hp.value`, not `hp.value`), and the value must pass validation (e.g. `min: 0`).
- **Numbers saved as text** — only happens without a data model; `NumberField` casts form strings for you.
- **Template changes don't show** — enable `flags.hotReload` for `hbs` or reload; JavaScript always needs F5.
- **Read-only users can still type** — add `{{#unless editable}}disabled{{/unless}}` to inputs, or see [Sheets](#sheets) for a cleaner approach.

## Next steps

- Grow the data: [Data models](#data-models), [Actor](#actor), [Item](#item).
- Better sheets with tabs and drag & drop: [ApplicationV2](#applicationv2), [Sheets](#sheets).
- Rolls and chat cards: [Chat & Rolls](#chat-roll). Effects: [Active Effects](#active-effect). Combat: [Combat](#combat).
- Keep old worlds working when the schema changes: [Migrations](#migrations).
