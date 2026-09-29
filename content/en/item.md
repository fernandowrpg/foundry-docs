# Items

Define weapon, spell and gear types, embed them in actors, roll them to chat, accept them by drag & drop, and let them grant Active Effects.

::: changed
- Item effects store their changes in `effect.system.changes`, with a string `type` instead of a numeric `mode`. See [Active Effects](#active-effect).
- `CONFIG.ActiveEffect.legacyTransferral` is **removed**. Transferred effects always stay on the item and apply through `actor.allApplicableEffects()`.
- `template.json` is deprecated: use `documentTypes` + `CONFIG.Item.dataModels`.
- New `TypeDataModel#onEmbed(element)` callback. It is about **HTML embeds** (`@Embed` in journals), *not* about adding an item to an actor. See below.
- See [the full changelog](#changes-14).
:::

## What it is

An **Item** is a thing an actor has or knows: a sword, a spell, a rope, a class feature. Items live in two places:

- as **world items** in the Items sidebar and in compendiums (templates for the GM to hand out);
- as **embedded items** inside an actor (`actor.items`), which are independent copies owned by that actor.

Dragging a world item onto a character sheet *copies* it. Editing the copy never changes the original. This is why embedded items are the right place for per-character state such as quantity, equipped, or charges.

## Define the type (data model)

```json
{
  "documentTypes": {
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] },
      "gear": { "htmlFields": ["description"] }
    }
  }
}
```

```js
// systems/forja/module/data/item.mjs
const { SchemaField, NumberField, StringField, BooleanField, HTMLField } = foundry.data.fields;

class ForjaItemBase extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      description: new HTMLField(),
      weight: new NumberField({ required: true, min: 0, initial: 0 })
    };
  }
}

export class WeaponData extends ForjaItemBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      damage: new StringField({ required: true, initial: "1d6" }),   // roll formula
      ability: new StringField({ required: true, initial: "str", choices: ["str", "agi", "mnd"] }),
      equipped: new BooleanField({ initial: false })
    };
  }

  /** Attack formula built from the chosen ability. */
  get attackFormula() {
    return `1d20 + @${this.ability}`;
  }
}

export class SpellData extends ForjaItemBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      cost: new NumberField({ required: true, integer: true, min: 0, initial: 1 }), // mana
      formula: new StringField({ required: true, blank: true, initial: "" }),
      range: new StringField({ required: true, initial: "touch", choices: ["self", "touch", "near", "far"] })
    };
  }
}

export class GearData extends ForjaItemBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      quantity: new NumberField({ required: true, integer: true, min: 0, initial: 1 }),
      armor: new NumberField({ required: true, integer: true, min: 0, initial: 0 }),
      equipped: new BooleanField({ initial: false })
    };
  }

  prepareDerivedData() {
    this.totalWeight = this.weight * this.quantity;
  }
}
```

## Register it

```js
// systems/forja/forja.mjs
import { WeaponData, SpellData, GearData } from "./module/data/item.mjs";
import { ForjaItem } from "./module/documents/item.mjs";

Hooks.once("init", () => {
  CONFIG.Item.documentClass = ForjaItem;
  Object.assign(CONFIG.Item.dataModels, { weapon: WeaponData, spell: SpellData, gear: GearData });
});
```

### The custom Item class

```js
// systems/forja/module/documents/item.mjs
export class ForjaItem extends Item {
  /** Item formulas can use actor values (@str) and item values (@item.cost). */
  getRollData() {
    const data = { ...(this.actor?.getRollData() ?? {}) };
    data.item = { ...this.system };
    return data;
  }

  /** Post a chat card for this item, with a roll when it has a formula. */
  async roll() {
    const formula = this.type === "weapon" ? this.system.damage : this.system.formula;
    const rolls = [];
    if (formula) {
      const roll = new Roll(formula, this.getRollData());
      await roll.evaluate();
      rolls.push(roll);
    }

    const content = await foundry.applications.handlebars.renderTemplate(
      "systems/forja/templates/chat/item-card.hbs",
      { item: this, rolls }
    );

    const chatData = {
      speaker: ChatMessage.getSpeaker({ actor: this.actor }),
      content,
      rolls,
      flags: { forja: { itemUuid: this.uuid } }   // lets card buttons find the item later
    };
    return ChatMessage.create(chatData);
  }
}
```

```hbs
{{!-- systems/forja/templates/chat/item-card.hbs --}}
<div class="forja item-card">
  <header><img src="{{item.img}}" width="32" height="32"> <h3>{{item.name}}</h3></header>
  <div class="description">{{{item.system.description}}}</div>
  {{#if (eq item.type "weapon")}}
    <button type="button" data-action="attack">Attack</button>
  {{/if}}
</div>
```

Button handling and message visibility (roll modes / message modes) are covered on [Chat & rolls](#chat-roll).

## Create it in code

```js
const actor = game.actors.getName("Aldric");

// Add embedded items (always an array)
const [sword] = await actor.createEmbeddedDocuments("Item", [
  { name: "Longsword", type: "weapon", system: { damage: "1d8 + @str", equipped: true } },
  { name: "Torch", type: "gear", system: { quantity: 3 } }
]);

// Same thing through the class, with a parent
await Item.create({ name: "Firebolt", type: "spell", system: { cost: 2, formula: "2d6" } }, { parent: actor });

// Read
actor.items.getName("Torch");
actor.items.filter(i => i.type === "weapon" && i.system.equipped);

// Update and delete
await sword.update({ "system.equipped": false });
await actor.updateEmbeddedDocuments("Item", [{ _id: sword.id, name: "Notched Longsword" }]);
await actor.deleteEmbeddedDocuments("Item", [sword.id]);

// A world item (sidebar) with no parent
await Item.create({ name: "Healing Potion", type: "gear" });
```

::: tip
Batch your changes. One `createEmbeddedDocuments` call with 10 items is one database round-trip and one re-render. Ten `Item.create` calls are ten of each.
:::

## Sheet/UI

Register an item sheet (the full `ItemSheetV2` walkthrough is on [Sheets](#sheets)):

```js
foundry.applications.apps.DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
  types: ["weapon", "spell", "gear"], makeDefault: true, label: "FORJA.SheetItem"
});
```

### Dropping items onto the actor sheet

`ActorSheetV2` already handles drops. When the drop is an Item, `_onDropItem(event, item)` receives the resolved Item, from the sidebar or from a compendium. If the item already belongs to this actor it is sorted, and otherwise it is created as an embedded copy. Override it to add rules, such as stacking gear:

```js
// systems/forja/module/sheets/character-sheet.mjs
export class ForjaCharacterSheet extends foundry.applications.api.HandlebarsApplicationMixin(
  foundry.applications.sheets.ActorSheetV2
) {
  /** @override */
  async _onDropItem(event, item) {
    if (!this.actor.isOwner) return null;
    // Same actor: let core sort it
    if (item.parent === this.actor) return super._onDropItem(event, item);

    // Stack gear with the same name instead of creating a duplicate
    if (item.type === "gear") {
      const existing = this.actor.items.find(i => i.type === "gear" && i.name === item.name);
      if (existing) {
        return existing.update({ "system.quantity": existing.system.quantity + item.system.quantity });
      }
    }

    // Spells need enough level (example rule)
    if (item.type === "spell" && this.actor.system.level < 2) {
      ui.notifications.warn("Level 2 required to learn spells.");
      return null;
    }

    return super._onDropItem(event, item);
  }
}
```

To create the item yourself, for example to change it first, strip the compendium metadata with `fromCompendium`. It returns plain data without `_id`, folder, sort or ownership:

```js
const data = game.items.fromCompendium(item);    // works for world and compendium items
data.system.quantity = 1;
return this.actor.createEmbeddedDocuments("Item", [data]);
```

## Item-granted effects (transfer)

An Active Effect on an item with `transfer: true` applies to the **owning actor**, for example a ring of strength or armor that raises defense. The effect stays on the item: delete the item and the effect goes with it.

::: v13
```js
await ring.createEmbeddedDocuments("ActiveEffect", [{
  name: "Ring of Strength",
  img: "icons/equipment/finger/ring-band-gold.webp",
  transfer: true,
  changes: [
    { key: "system.abilities.str.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "1" }
  ]
}]);
```

Set `CONFIG.ActiveEffect.legacyTransferral = false` in `init` (the default for new systems). Transferred effects then stay on the item and are applied through `actor.allApplicableEffects()`, instead of being *copied* onto the actor.
:::

::: v14
```js
await ring.createEmbeddedDocuments("ActiveEffect", [{
  name: "Ring of Strength",
  img: "icons/equipment/finger/ring-band-gold.webp",
  transfer: true,
  system: {
    changes: [
      { key: "system.abilities.str.bonus", type: "add", value: "1", phase: "initial" }
    ]
  }
}]);
```

Transferred effects always stay on the item and apply through `actor.allApplicableEffects()` (`legacyTransferral` no longer exists).
:::

Only effects from **equipped** items should apply. Suppress the others in your ActiveEffect class:

```js
export class ForjaActiveEffect extends ActiveEffect {
  get isSuppressed() {
    const item = this.parent;
    if ((item instanceof Item) && ("equipped" in item.system) && !item.system.equipped) return true;
    return super.isSuppressed;
  }
}
// in init: CONFIG.ActiveEffect.documentClass = ForjaActiveEffect;
```

::: v14
### About `TypeDataModel#onEmbed`

V14 added `onEmbed(element)` to `TypeDataModel`. Core calls it when the **embedded HTML** of this document, created by `toEmbed()` for an `@Embed[...]` enricher, has been added to the DOM. Use it to wire listeners on your item's embed card inside a journal page:

```js
export class SpellData extends ForjaItemBase {
  // ...
  onEmbed(element) {
    element.querySelector("[data-action=cast]")?.addEventListener("click", () => this.parent.roll());
  }
}
```

To react when an item is **added to an actor**, use `_preCreate` / `_onCreate` on the data model and check `this.parent.parent` (the actor).
:::

## Common recipes

### React when an item is added to an actor

```js
export class SpellData extends ForjaItemBase {
  async _preCreate(data, options, user) {
    if ((await super._preCreate(data, options, user)) === false) return false;
    const actor = this.parent.parent;           // this.parent is the Item
    if (actor?.type === "npc") this.updateSource({ cost: 0 });   // NPCs cast for free
  }
}
```

### Spend mana when casting

```js
async function castSpell(spell) {
  const actor = spell.actor;
  const mana = actor.system.mana.value;
  if (mana < spell.system.cost) return ui.notifications.warn("Not enough mana.");
  await actor.update({ "system.mana.value": mana - spell.system.cost });
  return spell.roll();
}
```

### Use one consumable

```js
const torch = actor.items.getName("Torch");
if (torch.system.quantity <= 1) await torch.delete();
else await torch.update({ "system.quantity": torch.system.quantity - 1 });
```

## Pitfalls

- **`item.actor` is `null` for world items.** Guard every place that reads actor data (`this.actor?.`).
- **Updating the world item does not update copies.** Embedded items are independent. Use a [migration](#migrations) or re-drop them.
- **`createEmbeddedDocuments` needs an array** and returns an array, even for a single item.
- **Stacking by name** breaks with localized names. For real systems, store a stable identifier such as `system.identifier` or a flag.
- **Transferred effects on unequipped items** apply unless you implement `isSuppressed`.
- **In V13, `legacyTransferral: true`** (the setting kept for old worlds) copies effects onto the actor. The copy then outlives the item. Make sure it is `false`.
