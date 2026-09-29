# Actor and item sheets

Build complete, editable actor and item sheets for the `forja` system with `HandlebarsApplicationMixin`, `ActorSheetV2` and `ItemSheetV2`.

::: changed
- `DocumentSheet` windows get an **ownership configuration** button in the header.
- Active Effects are primary documents: they can be dragged from the sidebar or compendiums onto a sheet (handled by `_onDropActiveEffect`) or onto a token to apply them to its actor.
- New `HTMLFormulaInputElement` (`<formula-input>`) for dice-formula fields, with a built-in formula editor.
- TinyMCE is gone; `<prose-mirror>` is the only rich-text editor.
- See [the full changelog](#changes-14).
:::

## What it is

A sheet is an [ApplicationV2](#applicationv2) bound to one document. `DocumentSheetV2` adds the document, permission checks (`isEditable`), automatic form submission into `document.update()`, and an `editImage` action. `ActorSheetV2` and `ItemSheetV2` add document-specific helpers (`this.actor`, `this.item`, token actions, drag & drop).

::: warning
Since V13 core no longer registers default actor or item sheets. A system that registers no sheet leaves its documents **with no sheet at all** — double-clicking an actor does nothing.
:::

This page assumes the data models from [Data models](#data-models): a `character` actor with `system.hp.{value,max}`, `system.abilities.{might,agility,wits}.value` and `system.biography` (an `HTMLField`), and `weapon` / `gear` items with `system.damage` (a formula string) and `system.quantity`.

## Register the sheets

Register in the `init` hook. `types` limits the sheet to certain subtypes; `makeDefault` makes it the default for those types; `label` is shown in the sheet configuration dialog.

```js
// systems/forja/forja.mjs
import { ForjaActorSheet } from "./module/sheets/actor-sheet.mjs";
import { ForjaItemSheet } from "./module/sheets/item-sheet.mjs";

Hooks.once("init", () => {
  const { DocumentSheetConfig } = foundry.applications.apps;

  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaActorSheet, {
    types: ["character"],
    makeDefault: true,
    label: "FORJA.Sheet.Character"
  });

  DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
    types: ["weapon", "gear"],
    makeDefault: true,
    label: "FORJA.Sheet.Item"
  });
});
```

::: tip
A system with several actor or item types (character, NPC, vehicle, spell…) needs a sheet for each one. See [Sheet types](#sheet-types) for one sheet per type, one adaptive sheet, alternative sheets and a shared base class.
:::

To remove a sheet registered by someone else (for example, a module replacing your item sheet), use `unregisterSheet` with the same scope and class:

```js
// modules/forja-extras/main.mjs — replace the system's item sheet
Hooks.once("init", () => {
  const { DocumentSheetConfig } = foundry.applications.apps;
  const systemSheet = CONFIG.Item.sheetClasses.weapon["forja.ForjaItemSheet"]?.cls;
  if ( systemSheet ) DocumentSheetConfig.unregisterSheet(Item, "forja", systemSheet, { types: ["weapon"] });
});
```

## The actor sheet class

```js
// systems/forja/module/sheets/actor-sheet.mjs
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2 } = foundry.applications.sheets;
const TextEditor = foundry.applications.ux.TextEditor.implementation;

export class ForjaActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  /** Play mode shows values; edit mode unlocks the inputs. */
  static MODES = { PLAY: 1, EDIT: 2 };
  _mode = ForjaActorSheet.MODES.PLAY;

  static DEFAULT_OPTIONS = {
    classes: ["forja", "actor-sheet"],
    position: { width: 620, height: 720 },
    window: { resizable: true },
    form: { submitOnChange: true },
    actions: {
      roll: ForjaActorSheet.#onRoll,
      createItem: ForjaActorSheet.#onCreateItem,
      editItem: ForjaActorSheet.#onEditItem,
      deleteItem: ForjaActorSheet.#onDeleteItem,
      toggleEffect: ForjaActorSheet.#onToggleEffect,
      toggleMode: ForjaActorSheet.#onToggleMode
    }
  };

  static PARTS = {
    header: { template: "systems/forja/templates/actor/header.hbs" },
    tabs: { template: "templates/generic/tab-navigation.hbs" },
    abilities: { template: "systems/forja/templates/actor/abilities.hbs" },
    inventory: {
      template: "systems/forja/templates/actor/inventory.hbs",
      templates: ["systems/forja/templates/actor/item-row.hbs"],
      scrollable: [""]
    },
    effects: { template: "systems/forja/templates/actor/effects.hbs" },
    biography: { template: "systems/forja/templates/actor/biography.hbs" }
  };

  static TABS = {
    primary: {
      tabs: [
        { id: "abilities", icon: "fa-solid fa-dumbbell" },
        { id: "inventory", icon: "fa-solid fa-sack" },
        { id: "effects", icon: "fa-solid fa-bolt" },
        { id: "biography", icon: "fa-solid fa-feather" }
      ],
      initial: "abilities",
      labelPrefix: "FORJA.Tab"
    }
  };

  get isEditMode() {
    return this.isEditable && (this._mode === ForjaActorSheet.MODES.EDIT);
  }

  async _prepareContext(options) {
    // super gives: document, source, fields, editable, user, rootId
    const context = await super._prepareContext(options);
    const actor = this.actor;

    // Group items by type, sorted like the sidebar
    const itemGroups = {};
    for ( const [type, items] of Object.entries(actor.itemTypes) ) {
      itemGroups[type] = items.toSorted((a, b) => a.sort - b.sort);
    }

    return Object.assign(context, {
      actor,
      system: actor.system,                 // prepared data (includes Active Effects)
      systemSource: context.source.system,  // raw stored data (what inputs should edit)
      systemFields: actor.system.schema.fields,
      isEditMode: this.isEditMode,
      disabled: !this.isEditMode,
      itemGroups,
      effects: actor.effects.contents,
      tabs: this._prepareTabs("primary"),
      enrichedBiography: await TextEditor.enrichHTML(actor.system.biography, {
        secrets: actor.isOwner,
        rollData: actor.getRollData(),
        relativeTo: actor
      })
    });
  }

  async _preparePartContext(partId, context, options) {
    context = await super._preparePartContext(partId, context, options);
    if ( partId in context.tabs ) context.tab = context.tabs[partId];
    return context;
  }

  /** Find the embedded Item for a clicked element. */
  _getItem(target) {
    const id = target.closest("[data-item-id]")?.dataset.itemId;
    return this.actor.items.get(id);
  }

  /* ---------- Actions ---------- */

  static async #onRoll(event, target) {
    const ability = target.dataset.ability;
    const roll = new Roll(`1d20 + @abilities.${ability}.value`, this.actor.getRollData());
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this.actor }),
      flavor: game.i18n.localize(`FORJA.Ability.${ability}`)
    });
  }

  static async #onCreateItem(event, target) {
    const type = target.dataset.type;
    await Item.implementation.create({
      name: game.i18n.format("DOCUMENT.New", { type: game.i18n.localize(`TYPES.Item.${type}`) }),
      type
    }, { parent: this.actor });
  }

  static #onEditItem(event, target) {
    this._getItem(target)?.sheet.render({ force: true });
  }

  static async #onDeleteItem(event, target) {
    await this._getItem(target)?.deleteDialog();
  }

  static async #onToggleEffect(event, target) {
    const id = target.closest("[data-effect-id]")?.dataset.effectId;
    const effect = this.actor.effects.get(id);
    await effect?.update({ disabled: !effect.disabled });
  }

  static #onToggleMode(event, target) {
    this._mode = this.isEditMode ? ForjaActorSheet.MODES.PLAY : ForjaActorSheet.MODES.EDIT;
    this.render();
  }

  /* ---------- Drag & drop ---------- */

  /** Only accept item types this system understands. */
  async _onDropItem(event, item) {
    if ( !["weapon", "gear"].includes(item.type) ) {
      ui.notifications.warn("FORJA.Warn.ItemTypeNotAllowed", { localize: true });
      return null;
    }
    return super._onDropItem(event, item);
  }
}
```

### Why `system` *and* `systemSource`?

`actor.system` is the **prepared** data: Active Effects and `prepareDerivedData` have already changed it. If an input shows a value boosted by an effect and the sheet submits it, the boost gets written to the database and stacks forever. Inputs should display `systemSource` (the stored value); read-only displays can show `system`.

## Templates

### Header

```hbs
{{!-- systems/forja/templates/actor/header.hbs --}}
<header class="sheet-header">
  <img class="portrait" src="{{actor.img}}" alt="{{actor.name}}"
       data-action="editImage" data-edit="img">
  <div class="identity">
    <input class="name" type="text" name="name" value="{{source.name}}" {{disabled disabled}}>
    <div class="hp">
      {{formInput systemFields.hp.fields.value value=systemSource.hp.value disabled=disabled}}
      <span>/</span>
      {{formInput systemFields.hp.fields.max value=systemSource.hp.max disabled=disabled}}
    </div>
  </div>
  {{#if editable}}
  <button type="button" class="mode-toggle" data-action="toggleMode"
          data-tooltip="FORJA.Sheet.ToggleMode">
    <i class="fa-solid {{#if isEditMode}}fa-lock-open{{else}}fa-lock{{/if}}"></i>
  </button>
  {{/if}}
</header>
```

- `data-action="editImage"` + `data-edit="img"` is the built-in `DocumentSheetV2` action: it opens a FilePicker and updates the `img` field.
- `{{formInput field value=...}}` renders the right input for a `DataField` (number, select, checkbox…) and sets `name` from the field path, so `systemFields.hp.fields.value` becomes `name="system.hp.value"`. The form then submits `{"system.hp.value": 12}` and the sheet calls `actor.update()` for you.
- `{{disabled disabled}}` is a core helper that prints the `disabled` attribute when true.

### Abilities tab

```hbs
{{!-- systems/forja/templates/actor/abilities.hbs --}}
<section class="tab abilities {{tab.cssClass}}" data-tab="abilities" data-group="primary">
  {{#each systemFields.abilities.fields as |field key|}}
  <div class="ability">
    {{formGroup field.fields.value value=(lookup (lookup @root.systemSource.abilities key) "value")
                localize=true disabled=@root.disabled}}
    <button type="button" data-action="roll" data-ability="{{key}}">
      <i class="fa-solid fa-dice-d20"></i>
    </button>
  </div>
  {{/each}}
</section>
```

`{{formGroup}}` wraps the input with a `<label>` (the field's `label`, localized with `localize=true`) and its `hint`.

### Inventory tab with a partial

```hbs
{{!-- systems/forja/templates/actor/inventory.hbs --}}
<section class="tab inventory {{tab.cssClass}}" data-tab="inventory" data-group="primary">
  {{#each itemGroups as |items type|}}
  <h3>
    {{localize (concat "TYPES.Item." type)}}
    {{#if @root.editable}}
    <button type="button" data-action="createItem" data-type="{{type}}">
      <i class="fa-solid fa-plus"></i>
    </button>
    {{/if}}
  </h3>
  <ol class="item-list">
    {{#each items as |item|}}
      {{> "systems/forja/templates/actor/item-row.hbs" item=item editable=@root.editable}}
    {{/each}}
  </ol>
  {{/each}}
</section>
```

```hbs
{{!-- systems/forja/templates/actor/item-row.hbs --}}
<li class="item draggable" data-item-id="{{item.id}}">
  <img src="{{item.img}}" alt="">
  <span class="item-name">{{item.name}}</span>
  {{#if item.system.damage}}<span class="damage">{{item.system.damage}}</span>{{/if}}
  <a data-action="editItem" data-tooltip="DOCUMENT.Update"><i class="fa-solid fa-pen"></i></a>
  {{#if editable}}
  <a data-action="deleteItem" data-tooltip="DOCUMENT.Delete"><i class="fa-solid fa-trash"></i></a>
  {{/if}}
</li>
```

Because `item-row.hbs` is listed in the part's `templates`, it is preloaded and can be used as a partial by its path.

::: tip
`actor.itemTypes` has a key for **every** item subtype declared by the system, even the empty ones. That is why the "create" button appears for each type, even before the actor owns any item of that type.
:::

### Effects tab

```hbs
{{!-- systems/forja/templates/actor/effects.hbs --}}
<section class="tab effects {{tab.cssClass}}" data-tab="effects" data-group="primary">
  <ol class="effect-list">
    {{#each effects as |effect|}}
    <li class="effect" data-effect-id="{{effect.id}}">
      <img src="{{effect.img}}" alt="">
      <span>{{effect.name}}</span>
      <a data-action="toggleEffect">
        <i class="fa-solid {{#if effect.disabled}}fa-toggle-off{{else}}fa-toggle-on{{/if}}"></i>
      </a>
    </li>
    {{/each}}
  </ol>
</section>
```

### Biography tab with ProseMirror

```hbs
{{!-- systems/forja/templates/actor/biography.hbs --}}
<section class="tab biography {{tab.cssClass}}" data-tab="biography" data-group="primary">
  <prose-mirror name="system.biography" value="{{systemSource.biography}}"
                data-document-uuid="{{actor.uuid}}" toggled {{disabled disabled}}>
    {{{enrichedBiography}}}
  </prose-mirror>
</section>
```

The `<prose-mirror>` element shows the enriched HTML (inner content) until the user toggles it into edit mode, then edits the raw `value`. On save it behaves like any named input and is submitted with the form. Always pass **enriched** HTML as content: raw HTML would show `@UUID[...]` links and secrets unprocessed.

## The item sheet

```js
// systems/forja/module/sheets/item-sheet.mjs
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ItemSheetV2 } = foundry.applications.sheets;
const TextEditor = foundry.applications.ux.TextEditor.implementation;

export class ForjaItemSheet extends HandlebarsApplicationMixin(ItemSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "item-sheet"],
    position: { width: 480, height: 520 },
    window: { resizable: true },
    form: { submitOnChange: true }
  };

  static PARTS = {
    header: { template: "systems/forja/templates/item/header.hbs" },
    details: { template: "systems/forja/templates/item/details.hbs", scrollable: [""] }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const item = this.item;
    return Object.assign(context, {
      item,
      system: item.system,
      systemSource: context.source.system,
      systemFields: item.system.schema.fields,
      disabled: !context.editable,
      enrichedDescription: await TextEditor.enrichHTML(item.system.description, {
        secrets: item.isOwner,
        rollData: item.getRollData?.() ?? {},
        relativeTo: item
      })
    });
  }
}
```

```hbs
{{!-- systems/forja/templates/item/header.hbs --}}
<header class="sheet-header">
  <img src="{{item.img}}" alt="" data-action="editImage" data-edit="img">
  <input class="name" type="text" name="name" value="{{source.name}}" {{disabled disabled}}>
</header>
```

::: v13
```hbs
{{!-- systems/forja/templates/item/details.hbs --}}
<section class="details">
  {{#if systemFields.damage}}
    {{formGroup systemFields.damage value=systemSource.damage localize=true}}
  {{/if}}
  {{formGroup systemFields.quantity value=systemSource.quantity localize=true}}
  <prose-mirror name="system.description" value="{{systemSource.description}}"
                data-document-uuid="{{item.uuid}}" toggled>
    {{{enrichedDescription}}}
  </prose-mirror>
</section>
```
:::

::: v14
V14 adds `HTMLFormulaInputElement` (`<formula-input>`), an input specialised for dice formulas with a button that opens the formula editor and autocompletion. Use it for `system.damage`:

```hbs
{{!-- systems/forja/templates/item/details.hbs --}}
<section class="details">
  {{#if systemFields.damage}}
  <div class="form-group">
    <label>{{localize "FORJA.Item.Damage"}}</label>
    <formula-input name="system.damage" value="{{systemSource.damage}}"></formula-input>
  </div>
  {{/if}}
  {{formGroup systemFields.quantity value=systemSource.quantity localize=true}}
  <prose-mirror name="system.description" value="{{systemSource.description}}"
                data-document-uuid="{{item.uuid}}" toggled>
    {{{enrichedDescription}}}
  </prose-mirror>
</section>
```

The element also accepts a `context` attribute that selects which autocompletion entries apply; see `HTMLFormulaInputElement` in the [V14 API](https://foundryvtt.com/api/v14/).
:::

## Drag & drop

`ActorSheetV2` ships a drag & drop framework. Drops are routed by document type:

| Method | Called when |
|---|---|
| `_onDrop(event)` | Anything is dropped; dispatches to the methods below. |
| `_onDropItem(event, item)` | An Item is dropped. Creates a copy on the actor, or sorts it if it already belongs to this actor. |
| `_onDropActiveEffect(event, effect)` | An Active Effect is dropped. |
| `_onDropActor(event, actor)` | An Actor is dropped (no-op by default). |
| `_onDropFolder(event, folder)` | A Folder is dropped. |
| `_onSortItem(event, item)` | An owned item is dropped among its siblings. |

Override one, call `super` for the default behavior, and return `null` to refuse the drop (as in `_onDropItem` above). `_canDragStart(selector)` and `_canDragDrop(selector)` control permissions; by default both require the sheet to be editable.

::: tip
If rows in your template don't start dragging, compare your markup with what `_onDragStart` expects in the API docs for your version (the rows above use `class="draggable"` and `data-item-id`), or override `_onDragStart(event)` and call `event.dataTransfer.setData("text/plain", JSON.stringify(item.toDragData()))` yourself.
:::

::: v14
Active Effects are primary documents in V14: users can drag them from the Effects sidebar or a compendium onto your sheet, which calls `_onDropActiveEffect`, or onto a token on the canvas to apply them to that token's actor — no sheet code needed. See [Active Effects](#active-effect).
:::

## Editable vs. view mode

The `MODES` recipe above is a common pattern:

1. Keep a `_mode` field on the instance (not saved; resets when the sheet is reopened).
2. Expose `isEditMode` and `disabled` in the context.
3. Pass `disabled=disabled` to every `{{formInput}}` / `{{formGroup}}` and `{{disabled disabled}}` to raw inputs.
4. Toggle with an action and `this.render()`.

`isEditable` already accounts for permissions: a player looking at someone else's actor, or at a locked compendium entry, never gets edit mode.

## Header controls and ownership

`ActorSheetV2` provides actions such as `configurePrototypeToken`, `showPortraitArtwork` and `showTokenArtwork`, which appear in the header menu. You can reuse them in your template (`data-action="showPortraitArtwork"`).

::: v14
V14 adds an **ownership** button to `DocumentSheet` headers, so GMs can open the ownership configuration directly from any sheet. You get it for free by extending `ActorSheetV2` / `ItemSheetV2`.
:::

## Pitfalls

- **No sheet registered** → documents cannot be opened. Register in `init`, not `ready`.
- **Editing prepared data**: inputs bound to `system` (instead of `systemSource`) write Active Effect bonuses into the database.
- **`name` mismatch**: `name="hp.value"` silently does nothing; the path must start at the document root (`system.hp.value`).
- **Unescaped HTML**: use `{{{ }}}` only for already-enriched HTML; everything else uses `{{ }}`.
- **Buttons without `type="button"`** submit the form and re-render the sheet on every click.
- **Registering with the wrong `types`**: a type not listed in `types` falls back to another registered sheet, or none.
