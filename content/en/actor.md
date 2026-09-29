# Actors

Define character and NPC types with data models, give them a custom document class with derived data and rolls, and create, update and token-link them from code.

::: changed
- Active Effects apply in **phases** (`"initial"`, `"final"`, plus your own): `Actor#applyActiveEffects(phase)` now takes a phase argument.
- Effects can now change the actor's **Tokens** (vision, light, image, alpha, disposition, size, shape). The Actor collects these changes in `Actor#tokenActiveEffectChanges`; the token applies them with `TokenDocument#applyActiveEffects(phase)`.
- `template.json` is deprecated: declare types with `documentTypes` in `system.json` plus `CONFIG.Actor.dataModels`.
- `TokenDocument#delta` (the `ActorDelta` of an unlinked token) **can be `null`**. Check it before you read from it.
- See [the full changelog](#changes-14).
:::

## What it is

An **Actor** is anything that acts in the world: player characters, NPCs, monsters, vehicles, traps. Each actor has:

- a `type` (for example `character` or `npc`), which chooses its data model and its sheet;
- a `system` object holding your game's data (HP, abilities, level...);
- embedded **Items** (`actor.items`) and **Active Effects** (`actor.effects`);
- a `prototypeToken`, the template used every time the actor is placed on a scene.

Foundry stores and syncs the *source* data. On every client it then runs a **preparation** pipeline that computes derived values such as modifiers and totals, and applies effects. Most system code lives in that pipeline. This page builds the `forja` actor step by step. For the general document concepts, see [Documents](#documents) and [Data models](#data-models).

## Define the type (data model)

Declare the types in the manifest first. Foundry only accepts types that are listed here.

```json
{
  "id": "forja",
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    }
  }
}
```

Then write one `TypeDataModel` per type. A shared base class keeps the common fields in one place.

```js
// systems/forja/module/data/actor.mjs
const { SchemaField, NumberField, StringField, HTMLField } = foundry.data.fields;

/** A {value, max} pair, used for HP and mana. */
function resourceField(initial) {
  return new SchemaField({
    value: new NumberField({ required: true, integer: true, min: 0, initial }),
    max: new NumberField({ required: true, integer: true, min: 0, initial })
  });
}

function abilityField() {
  return new SchemaField({
    value: new NumberField({ required: true, integer: true, min: 1, max: 20, initial: 10 })
  });
}

export class ForjaActorBase extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      hp: resourceField(10),
      abilities: new SchemaField({
        str: abilityField(),
        agi: abilityField(),
        mnd: abilityField()
      }),
      // "bonus" is stored and can be changed by effects; "value" is derived
      defense: new SchemaField({
        bonus: new NumberField({ required: true, integer: true, initial: 0 })
      }),
      biography: new HTMLField()
    };
  }

  /** Runs BEFORE Active Effects: initialize values that effects will add to. */
  prepareBaseData() {
    for (const ability of Object.values(this.abilities)) ability.bonus = 0;
  }

  /** Runs AFTER Active Effects: compute everything derived. */
  prepareDerivedData() {
    for (const ability of Object.values(this.abilities)) {
      ability.mod = Math.floor((ability.value - 10) / 2) + ability.bonus;
    }
    this.defense.value = 10 + this.abilities.agi.mod + this.defense.bonus;
    this.hp.value = Math.min(this.hp.value, this.hp.max);
  }
}

export class CharacterData extends ForjaActorBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      level: new NumberField({ required: true, integer: true, min: 1, initial: 1 }),
      mana: resourceField(5)
    };
  }
}

export class NpcData extends ForjaActorBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      threat: new StringField({ required: true, initial: "minion", choices: ["minion", "elite", "boss"] })
    };
  }
}
```

::: tip
Keep derived values such as `mod` and `defense.value` **out of the schema**. Anything in the schema is saved to the database. A derived value saved there goes stale and gets in the way of effects.
:::

## Register it

Everything is registered in the `init` hook, before any document is prepared.

```js
// systems/forja/forja.mjs
import { CharacterData, NpcData } from "./module/data/actor.mjs";
import { ForjaActor } from "./module/documents/actor.mjs";

Hooks.once("init", () => {
  CONFIG.Actor.documentClass = ForjaActor;
  CONFIG.Actor.dataModels.character = CharacterData;
  CONFIG.Actor.dataModels.npc = NpcData;

  // Attributes offered as token bars (paths are relative to `system`)
  CONFIG.Actor.trackableAttributes = {
    character: { bar: ["hp", "mana"], value: ["level", "defense.bonus"] },
    npc: { bar: ["hp"], value: ["defense.bonus"] }
  };
});
```

`trackableAttributes` controls what appears in the "Bar 1 / Bar 2" dropdowns of the token config. A `bar` entry must point at an object with `value` and `max`. Without this setting, Foundry guesses from the schema, and the guess often includes fields you don't want.

### The custom Actor class

The data model handles data that belongs to a single type. The **document class** holds logic shared by every actor and anything that needs the whole document: its items, its tokens, chat output.

```js
// systems/forja/module/documents/actor.mjs
export class ForjaActor extends Actor {
  /** Default token settings, applied once when the actor is created. */
  async _preCreate(data, options, user) {
    if ((await super._preCreate(data, options, user)) === false) return false;
    const isCharacter = this.type === "character";
    this.updateSource({
      prototypeToken: {
        actorLink: isCharacter,           // PCs share one sheet across all tokens
        disposition: isCharacter
          ? CONST.TOKEN_DISPOSITIONS.FRIENDLY
          : CONST.TOKEN_DISPOSITIONS.HOSTILE,
        sight: { enabled: isCharacter },
        bar1: { attribute: "hp" },
        displayBars: CONST.TOKEN_DISPLAY_MODES.OWNER_HOVER
      }
    });
  }

  /** Cross-document derived data: runs after the system model's prepareDerivedData. */
  prepareDerivedData() {
    super.prepareDerivedData();
    // Example: add the armor bonus from equipped gear
    const armor = this.items.filter(i => i.type === "gear" && i.system.equipped);
    this.system.defense.value += armor.reduce((sum, i) => sum + (i.system.armor ?? 0), 0);
  }

  /** Short names for formulas: "1d20 + @str" instead of "@abilities.str.mod". */
  getRollData() {
    const data = { ...super.getRollData() };  // copy! super returns this.system itself
    for (const [key, ability] of Object.entries(this.system.abilities)) data[key] = ability.mod;
    data.lvl = this.system.level ?? 0;
    return data;
  }
}
```

The roll method depends on the version, because V14 renamed roll modes to message modes:

::: v13
```js
  /** Roll an ability test and post it to chat. */
  async rollAbility(key) {
    const roll = new Roll(`1d20 + @${key}`, this.getRollData());
    await roll.evaluate();
    return roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this }),
      flavor: `Ability test: ${key.toUpperCase()}`
    }, { rollMode: game.settings.get("core", "rollMode") });
  }
```
:::

::: v14
```js
  /** Roll an ability test and post it to chat. */
  async rollAbility(key, { messageMode } = {}) {
    const roll = new Roll(`1d20 + @${key}`, this.getRollData());
    await roll.evaluate();
    // Pass messageMode ("public" | "self" | "gm" | "blind") only when the caller chose one
    return roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this }),
      flavor: `Ability test: ${key.toUpperCase()}`
    }, messageMode ? { messageMode } : {});
  }
```
:::

The order in which the steps of `prepareData()` run is what matters in practice:

::: v13
1. `system.prepareBaseData()`, then `Actor#prepareBaseData()`
2. `prepareEmbeddedDocuments()`: items are prepared, then `applyActiveEffects()` runs
3. `system.prepareDerivedData()`, then `Actor#prepareDerivedData()`

Effects change *source-like* values (`system.defense.bonus`). Step 3 then derives totals from them. An effect that targets `system.defense.value` has no effect, because step 3 overwrites it.
:::

::: v14
1. `system.prepareBaseData()`, then `Actor#prepareBaseData()`
2. `prepareEmbeddedDocuments()`: items are prepared, then `applyActiveEffects("initial")` runs
3. `system.prepareDerivedData()`, then `Actor#prepareDerivedData()`
4. Changes in the `"final"` phase run **after** derived data, so they *can* target derived values such as `system.defense.value`.

You can register your own phases in `CONFIG.ActiveEffect.phases` and apply them where you want with `this.applyActiveEffects("your-phase")`. See [Active Effects](#active-effect).
:::

## Create it in code

```js
// Create an actor with starting items in a single database operation
const hero = await Actor.create({
  name: "Aldric",
  type: "character",
  img: "systems/forja/assets/aldric.webp",
  system: { abilities: { str: { value: 14 } }, hp: { value: 12, max: 12 } },
  items: [
    { name: "Longsword", type: "weapon", system: { damage: "1d8 + @str" } },
    { name: "Rope (15 m)", type: "gear" }
  ]
});

// Update: use dot-notation paths into `system`
await hero.update({ "system.hp.value": hero.system.hp.value - 3 });

// Several actors at once
await Actor.createDocuments([
  { name: "Goblin", type: "npc" },
  { name: "Goblin Boss", type: "npc", system: { threat: "boss" } }
]);
```

::: warning
Never assign directly, as in `actor.system.hp.value = 5`. That changes only the prepared copy on *your* client, and the next preparation overwrites it. Always go through `update()`.
:::

### Linked vs. unlinked tokens

- **Linked** (`actorLink: true`): every token points at the same world actor. Damaging the token damages the actor. Use this for PCs.
- **Unlinked**: every token has a **synthetic actor**, which is the world actor plus a per-token `ActorDelta` that stores only the differences. Five goblins from one actor each keep their own HP.

```js
// token is a TokenDocument (for example canvas.tokens.controlled[0].document)
const actor = token.actor;           // synthetic actor for unlinked tokens
await actor.update({ "system.hp.value": 0 }); // writes into the token's ActorDelta

// All tokens of a world actor on the current scene
const tokens = hero.getActiveTokens(); // Token placeables
```

::: v14
```js
// V14: the delta can be null. Guard before reading it directly.
if (!token.actorLink && token.delta) {
  console.log("Overridden fields:", token.delta.toObject());
}
```
:::

::: tip
Write through `token.actor` and let Foundry decide where the data goes. Code that edits `token.delta` directly is fragile.
:::

## Sheet/UI

Foundry has no default actor sheet since V13, so you must register one. The complete `ActorSheetV2` example, with tabs, drag & drop and editors, is on [Sheets](#sheets). Here is the minimal registration:

```js
Hooks.once("init", () => {
  foundry.applications.apps.DocumentSheetConfig.registerSheet(Actor, "forja", ForjaCharacterSheet, {
    types: ["character"], makeDefault: true, label: "FORJA.SheetCharacter"
  });
});
```

A button in the sheet template calls your roll method through an action:

```hbs
<button type="button" data-action="rollAbility" data-ability="str">STR {{system.abilities.str.mod}}</button>
```

```js
static DEFAULT_OPTIONS = {
  actions: {
    rollAbility(event, target) { return this.document.rollAbility(target.dataset.ability); }
  }
};
```

## Common recipes

### Heal to full on a macro

```js
for (const token of canvas.tokens.controlled) {
  const { max } = token.actor.system.hp;
  await token.actor.update({ "system.hp.value": max });
}
```

### React to HP reaching 0

```js
Hooks.on("updateActor", (actor, changes, options, userId) => {
  if (game.user.id !== userId) return;                // run once, on the client that made the change
  const hp = foundry.utils.getProperty(changes, "system.hp.value");
  if (hp === 0) actor.toggleStatusEffect("dead", { active: true, overlay: true });
});
```

### Group items by type for a sheet

```js
const { weapon = [], spell = [], gear = [] } = actor.itemTypes;
```

::: v14
### Effects that change the token

In V14 an Active Effect can change token properties such as vision, light, image, alpha, disposition, size and shape. This lets a torch give light or a disguise swap the token image. The actor collects those changes by phase, and each dependent token applies them to its own `overrides`:

```js
// Inspect what effects are doing to tokens (debugging)
console.log(actor.tokenActiveEffectChanges);   // { initial: [...], final: [...] }
for (const t of actor.getDependentTokens()) console.log(t.name, t.overrides);
```

The Active Effect config offers the token fields directly. To see the exact change `key` it writes, create one in the UI and inspect `effect.system.changes`. Don't hard-code a guessed key.
:::

## Pitfalls

- **Types missing from `documentTypes`** make creation fail validation. The type must be declared in the manifest *and* have a data model.
- **Returning `this.system` from `getRollData()` and mutating it** corrupts prepared data. Copy it first.
- **Heavy work in `prepareDerivedData`**, such as fetching compendiums or `await`: preparation is synchronous and runs often, on every client.
- **Calling `update()` inside `prepareData`** creates an infinite loop, because each update triggers another preparation.
- **Hooks on every client**: `updateActor` fires everywhere. Guard with `userId === game.user.id` or `game.users.activeGM?.isSelf` so the update runs only once.
- **Unlinked tokens**: `game.actors.get(id)` returns the *world* actor, not the goblin you hit. Use `token.actor`.
