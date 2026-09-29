# Sheet types

Give every document type in your system the right sheet: one sheet per type, one sheet that adapts to the type, alternative sheets the user can pick, and a shared base class so you don't repeat code.

::: changed
- The sheet registration API (`DocumentSheetConfig.registerSheet`) is the **same** in V13 and V14. Code on this page works in both unless a block says otherwise.
- Sheets can be **popped out** into their own browser window, and `DocumentSheet` headers get an **ownership** button.
- Active Effects are primary documents, so effect **types** can have their own sheets too (see "Sheets for other documents").
- A document class can declare in its metadata whether its `base` type may be created, which hides `base` from the "Create" dialog.
- See [the full changelog](#changes-14).
:::

## Types and sheets are two different things

A **type** is data: `character`, `npc`, `weapon`, `spell`. You declare it in the manifest and give it a data model ([Data models](#data-models)). A **sheet** is the window that shows and edits one document. Foundry connects them through a registry:

```text
system.json                 CONFIG.Actor.dataModels        CONFIG.Actor.sheetClasses
documentTypes.Actor   →     character → CharacterData  →   character → { "forja.ForjaCharacterSheet": {...default: true},
  character                 npc       → NpcData                          "forja.ForjaCompactSheet":   {...} }
  npc                                                      npc       → { "forja.ForjaNpcSheet":       {...default: true} }
```

Each registered sheet gets an id `<scope>.<ClassName>` (for example `forja.ForjaNpcSheet`). The scope is the first argument of `registerSheet`; use your package id.

::: warning
Since V13 the core registers **no** default actor or item sheet. Every type you declare needs at least one registered sheet, or double-clicking that document does nothing. Registering without `types` applies the sheet to **all** types of that document.
:::

## How Foundry picks the sheet

When a document opens, Foundry looks for its sheet in this order:

1. **The sheet chosen for this document**, stored in `flags.core.sheetClass` (set in the "Configure Sheet" dialog in the sheet header, or by code).
2. **The default the GM chose for the type**, in the same dialog (saved in the world setting `core.sheetClasses`).
3. **The sheet registered with `makeDefault: true`** for that type.
4. The first sheet registered for that type.

This is why users can switch sheets without touching your code, and why renaming a sheet class breaks their saved choice: the id stored in the flag no longer exists, and Foundry falls back to the default.

## Checklist for adding a new type

1. Declare it in the manifest under `documentTypes`.
2. Write its data model and register it in `CONFIG.<Document>.dataModels`.
3. Add its name in the language files under `TYPES.<Document>.<type>`.
4. Register a sheet for it (one of the patterns below).
5. Create its templates.

```json
{
  "documentTypes": {
    "Actor": { "character": {}, "npc": {}, "vehicle": {} },
    "Item":  { "weapon": {}, "gear": {}, "spell": { "htmlFields": ["description"] } }
  }
}
```

```json
{
  "TYPES": {
    "Actor": { "character": "Character", "npc": "NPC", "vehicle": "Vehicle" },
    "Item":  { "weapon": "Weapon", "gear": "Gear", "spell": "Spell" }
  },
  "FORJA": {
    "Sheet": {
      "Character": "Forja character sheet",
      "Npc": "Forja NPC sheet",
      "Vehicle": "Forja vehicle sheet",
      "Compact": "Forja compact sheet",
      "Item": "Forja item sheet",
      "Spell": "Forja spell sheet"
    }
  }
}
```

## Pattern 1: a shared base class

Most sheets share the same options, actions and context (the document, the `system` data, the fields, enriched HTML). Put that in a base class and keep only the differences in each sheet.

```js
// systems/forja/module/sheets/base-actor-sheet.mjs
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2 } = foundry.applications.sheets;
const TextEditor = foundry.applications.ux.TextEditor.implementation;

export class ForjaBaseActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "actor-sheet"],
    position: { width: 620, height: 720 },
    window: { resizable: true },
    form: { submitOnChange: true },
    actions: {
      roll: ForjaBaseActorSheet.#onRoll,
      editItem: ForjaBaseActorSheet.#onEditItem,
      deleteItem: ForjaBaseActorSheet.#onDeleteItem
    }
  };

  /** Parts every actor sheet has. Subclasses spread these into their own PARTS. */
  static BASE_PARTS = {
    header: { template: "systems/forja/templates/actor/header.hbs" },
    tabs: { template: "templates/generic/tab-navigation.hbs" }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const actor = this.actor;
    return Object.assign(context, {
      actor,
      system: actor.system,
      systemSource: context.source.system,
      systemFields: actor.system.schema.fields,
      itemGroups: actor.itemTypes,
      enrichedBiography: await TextEditor.enrichHTML(actor.system.biography ?? "", {
        secrets: actor.isOwner, rollData: actor.getRollData(), relativeTo: actor
      })
    });
  }

  async _preparePartContext(partId, context, options) {
    context = await super._preparePartContext(partId, context, options);
    if ( context.tabs && (partId in context.tabs) ) context.tab = context.tabs[partId];
    return context;
  }

  _getItem(target) {
    return this.actor.items.get(target.closest("[data-item-id]")?.dataset.itemId);
  }

  static async #onRoll(event, target) {
    const roll = new Roll(`1d20 + @abilities.${target.dataset.ability}.value`, this.actor.getRollData());
    await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor: this.actor }) });
  }

  static #onEditItem(event, target) { this._getItem(target)?.sheet.render({ force: true }); }

  static async #onDeleteItem(event, target) { await this._getItem(target)?.deleteDialog(); }
}
```

What subclasses inherit and what they don't:

| Static property | Inherited how |
|---|---|
| `DEFAULT_OPTIONS` | **Merged** with the parent's. A subclass only lists what changes (extra classes, a new action, a different width). |
| `PARTS` | **Replaced**. A subclass that defines `PARTS` must list every part it wants, so spread the parent's parts explicitly. |
| `TABS` | **Replaced**, like `PARTS`. |
| Instance methods (`_prepareContext`…) | Normal JavaScript inheritance: call `super` first. |

::: tip
Private static handlers (`static #onRoll`) can only be referenced inside the class that declares them. Register them in that class's `DEFAULT_OPTIONS.actions`; subclasses get them through the merge.
:::

## Pattern 2: one sheet per type

Use this when types look very different, such as a full character sheet versus a one-page NPC stat block. Each type gets its own class and templates.

```js
// systems/forja/module/sheets/character-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

export class ForjaCharacterSheet extends ForjaBaseActorSheet {
  static DEFAULT_OPTIONS = { classes: ["character"] };   // merged: forja actor-sheet character

  static PARTS = {
    ...ForjaBaseActorSheet.BASE_PARTS,
    abilities: { template: "systems/forja/templates/actor/abilities.hbs" },
    inventory: { template: "systems/forja/templates/actor/inventory.hbs", scrollable: [""] },
    biography: { template: "systems/forja/templates/actor/biography.hbs" }
  };

  static TABS = {
    primary: {
      tabs: [{ id: "abilities" }, { id: "inventory" }, { id: "biography" }],
      initial: "abilities",
      labelPrefix: "FORJA.Tab"
    }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    context.tabs = this._prepareTabs("primary");
    return context;
  }
}
```

```js
// systems/forja/module/sheets/npc-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

export class ForjaNpcSheet extends ForjaBaseActorSheet {
  static DEFAULT_OPTIONS = {
    classes: ["npc"],
    position: { width: 460, height: 560 }                // smaller window
  };

  /** A single scrolling stat block: no tabs. */
  static PARTS = {
    header: ForjaBaseActorSheet.BASE_PARTS.header,
    statblock: { template: "systems/forja/templates/actor/npc-statblock.hbs", scrollable: [""] }
  };
}
```

```js
// systems/forja/forja.mjs
import { ForjaCharacterSheet } from "./module/sheets/character-sheet.mjs";
import { ForjaNpcSheet } from "./module/sheets/npc-sheet.mjs";

Hooks.once("init", () => {
  const { DocumentSheetConfig } = foundry.applications.apps;

  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaCharacterSheet, {
    types: ["character"], makeDefault: true, label: "FORJA.Sheet.Character"
  });
  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaNpcSheet, {
    types: ["npc"], makeDefault: true, label: "FORJA.Sheet.Npc"
  });
});
```

## Pattern 3: one sheet that adapts to the type

Use this when types share most of the layout and differ in a few sections, such as `character` and `vehicle` both having an inventory, but only characters having abilities. Declare every part once, then choose which ones to render for the current document.

```js
// systems/forja/module/sheets/adaptive-actor-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

/** Which parts and tabs each type shows. */
const LAYOUT = {
  character: ["abilities", "inventory", "biography"],
  vehicle:   ["crew", "inventory"]
};

export class ForjaAdaptiveSheet extends ForjaBaseActorSheet {
  static PARTS = {
    ...ForjaBaseActorSheet.BASE_PARTS,
    abilities: { template: "systems/forja/templates/actor/abilities.hbs" },
    crew:      { template: "systems/forja/templates/actor/crew.hbs" },
    inventory: { template: "systems/forja/templates/actor/inventory.hbs", scrollable: [""] },
    biography: { template: "systems/forja/templates/actor/biography.hbs" }
  };

  static TABS = {
    primary: {
      tabs: [{ id: "abilities" }, { id: "crew" }, { id: "inventory" }, { id: "biography" }],
      initial: "inventory",
      labelPrefix: "FORJA.Tab"
    }
  };

  /** Render only the parts that belong to this document's type. */
  _configureRenderOptions(options) {
    super._configureRenderOptions(options);
    const wanted = LAYOUT[this.document.type] ?? [];
    options.parts = ["header", "tabs", ...wanted].filter(p => !options.parts || options.parts.includes(p));
  }

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    // Keep only the tabs of this type
    const wanted = LAYOUT[this.document.type] ?? [];
    const tabs = this._prepareTabs("primary");
    context.tabs = Object.fromEntries(Object.entries(tabs).filter(([id]) => wanted.includes(id)));
    return context;
  }
}
```

```js
DocumentSheetConfig.registerSheet(Actor, "forja", ForjaAdaptiveSheet, {
  types: ["character", "vehicle"], makeDefault: true, label: "FORJA.Sheet.Character"
});
```

::: warning
If the initial tab (`initial`) is not in the list of a type, the sheet opens with no active tab. Pick an `initial` tab that every type has, as above (`inventory`), or set `this.tabGroups.primary` in `_prepareContext` before calling `_prepareTabs`.
:::

The template of a shared part can still branch on the type:

```hbs
{{!-- systems/forja/templates/actor/inventory.hbs --}}
<section class="tab inventory {{tab.cssClass}}" data-tab="inventory" data-group="primary">
  {{#if (eq actor.type "vehicle")}}
    <p class="capacity">{{localize "FORJA.Vehicle.Cargo"}}: {{system.cargo.value}} / {{system.cargo.max}}</p>
  {{/if}}
  {{#each itemGroups.gear as |item|}}
    <div class="item-row" data-item-id="{{item.id}}">{{item.name}}
      <a data-action="editItem"><i class="fa-solid fa-pen"></i></a>
    </div>
  {{/each}}
</section>
```

### Which pattern should I use?

| Situation | Pattern |
|---|---|
| Types share most fields and layout | One adaptive sheet (Pattern 3) |
| Types look completely different | One sheet per type (Pattern 2) |
| Several sheets repeat options and actions | Shared base class (Pattern 1), always |
| Users want a different look for the same type | Alternative sheets (next section) |

## Alternative sheets for the same type

Register a second sheet for the same type **without** `makeDefault`. It appears in the "Configure Sheet" dialog, where a user can choose it for one actor, and the GM can make it the default for the type.

```js
// systems/forja/module/sheets/compact-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

export class ForjaCompactSheet extends ForjaBaseActorSheet {
  static DEFAULT_OPTIONS = { classes: ["compact"], position: { width: 360, height: 480 } };
  static PARTS = {
    header: ForjaBaseActorSheet.BASE_PARTS.header,
    summary: { template: "systems/forja/templates/actor/compact.hbs" }
  };
}
```

```js
DocumentSheetConfig.registerSheet(Actor, "forja", ForjaCompactSheet, {
  types: ["character", "npc"],
  label: "FORJA.Sheet.Compact"          // not the default: users opt in
});
```

`registerSheet` also accepts `canBeDefault: false` (users can pick it per document, but it can never become the type default) and `canConfigure: false` (hides the sheet configuration option). Check `DocumentSheetConfig.registerSheet` in the API for the full option list of your version.

### Choose a sheet from code

```js
// Open this actor with the compact sheet from now on
await actor.setFlag("core", "sheetClass", "forja.ForjaCompactSheet");

// Back to the type default
await actor.unsetFlag("core", "sheetClass");

// Which sheets exist for a type?
console.log(Object.keys(CONFIG.Actor.sheetClasses.character));
// ["forja.ForjaCharacterSheet", "forja.ForjaCompactSheet"]
```

Core closes the open sheet and uses the new class the next time the document opens.

### A limited view for other players

Players with only **Limited** permission on an actor should see a short description, not the full sheet. You don't need a separate registered sheet for this: switch parts in the same sheet.

```js
_configureRenderOptions(options) {
  super._configureRenderOptions(options);
  if ( this.document.limited ) options.parts = ["header", "limited"];   // name, image, public biography
}
```

Add a `limited` entry to `PARTS` with its template, and make sure `_prepareContext` does not expose secret data (enrich the biography with `secrets: false` for limited viewers).

## Item sheets per type

Items follow the same rules. A common setup is a generic item sheet plus a special one for spells:

```js
// systems/forja/module/sheets/spell-sheet.mjs
import { ForjaItemSheet } from "./item-sheet.mjs";

export class ForjaSpellSheet extends ForjaItemSheet {
  static DEFAULT_OPTIONS = { classes: ["spell"] };
  static PARTS = {
    header: ForjaItemSheet.PARTS.header,
    casting: { template: "systems/forja/templates/item/spell-casting.hbs" },
    details: ForjaItemSheet.PARTS.details
  };
}
```

```js
DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
  types: ["weapon", "gear"], makeDefault: true, label: "FORJA.Sheet.Item"
});
DocumentSheetConfig.registerSheet(Item, "forja", ForjaSpellSheet, {
  types: ["spell"], makeDefault: true, label: "FORJA.Sheet.Spell"
});
```

## Sheets for other documents

The same registration works for any document type that has sheets. Extend the matching base class:

| Document | Base class to extend |
|---|---|
| Actor | `foundry.applications.sheets.ActorSheetV2` |
| Item | `foundry.applications.sheets.ItemSheetV2` |
| ActiveEffect | `foundry.applications.sheets.ActiveEffectConfig` |
| JournalEntryPage | `foundry.applications.sheets.journal.JournalEntryPageHandlebarsSheet` (see [Journal](#journal)) |
| Any other document | `foundry.applications.api.DocumentSheetV2` |

Region behaviors don't need a sheet: their configuration window is generated from the data model ([Regions](#regions)).

```js
// A sheet for the "buff" Active Effect type
class ForjaBuffConfig extends foundry.applications.sheets.ActiveEffectConfig {
  static DEFAULT_OPTIONS = { classes: ["forja", "buff-config"] };
}

DocumentSheetConfig.registerSheet(ActiveEffect, "forja", ForjaBuffConfig, {
  types: ["buff"], makeDefault: true, label: "FORJA.Sheet.Buff"
});
```

::: v14
Active Effects are primary documents in V14: they appear in the sidebar and in compendiums and open with the sheet registered for their type, just like actors and items. The effect `system` data model owns the `changes`, so a custom effect sheet should keep the core "Changes" part. See [Active Effects](#active-effect).
:::

## Hide the `base` type

::: v13
When a document supports types, the "Create" dialog lists every registered type. Documents created with no type get `base`, which only makes sense if you declared and registered it. Declare only the types you really support and register a sheet for each.
:::

::: v14
Each document class can now say in its metadata whether its `base` type may be created and offered in creation dialogs. If your system has no `base` actor, hide it so users can't create one by accident. Check the `metadata` entry of the document class in the [V14 API](https://foundryvtt.com/api/v14/) for the exact key before relying on it.
:::

## Pitfalls

- **A type without a sheet**: opening the document does nothing. Register a sheet for every declared type.
- **Forgetting `types`**: the sheet is registered for all types, including ones added later by modules.
- **Two sheets with `makeDefault: true` for the same type**: the last one registered wins. Keep one default per type.
- **Renaming a sheet class**: the id `forja.ClassName` changes and users lose their saved choice. Keep class names stable once released.
- **Expecting `PARTS` to merge**: only `DEFAULT_OPTIONS` merges. Spread the parent's parts explicitly.
- **Registering in `ready`**: sheets must be registered in `init`, before any document opens.
