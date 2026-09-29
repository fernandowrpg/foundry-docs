# Active Effects

Buffs, conditions and item bonuses that change actor data during preparation. This is the entity that changed the most between V13 and V14.

::: changed
- **Changes moved:** `effect.changes` → `effect.system.changes`. The numeric `mode` became a string `type` (`"add"`, `"subtract"`, `"multiply"`, `"override"`, `"upgrade"`, `"downgrade"`, `"custom"`). Core migrates world data. Code and compendium source files must be updated by you.
- **Phases:** every change has a `phase` (`"initial"` or `"final"`, plus phases you register). `Actor#applyActiveEffects(phase)`.
- **Duration:** `{ seconds, rounds, turns, startRound... }` → `{ value, units, expiry, expired }`. Built-in **expiry events** (`combatStart`, `roundStart`, `turnStart`, `combatEnd`, `roundEnd`, `turnEnd`) are tracked by `ActiveEffect.registry`.
- **Primary documents:** effects can live in the sidebar and in compendiums, and can be dropped on a Token to apply to its actor.
- **Token changes:** effects can alter token vision, light, image, alpha, disposition, size and shape.
- `CONFIG.statusEffects` is an **object** keyed by id (arrays still work). `CONFIG.ActiveEffect.legacyTransferral` is **removed**.
- New "Active Effect" **Region behavior** applies effects to tokens that enter a region.
- See [the full changelog](#changes-14).
:::

## What it is

An **Active Effect** is a named bundle of *changes* ("+1 to strength", "defense becomes 18") with optional duration and statuses. Effects are embedded in an **Actor** (they apply to it) or in an **Item** (with `transfer: true` they apply to the item's owner, see [Items](#item)).

The key idea: effects **never write to the database**. During data preparation, Foundry takes the actor's source data, applies each active change in memory, and stores what it changed in `actor.overrides`. Disable or delete the effect and the value snaps back. Where preparation runs effects is described on [Actors](#actor).

## Define the type (data model)

The shape of a *change* is where the versions differ.

::: v13
```js
// A V13 change, stored in effect.changes (array)
{
  key: "system.abilities.str.bonus",       // data path on the actor
  mode: CONST.ACTIVE_EFFECT_MODES.ADD,      // number, see table
  value: "2",                               // always a string
  priority: null                            // null → mode * 10
}
```

| `CONST.ACTIVE_EFFECT_MODES` | Value | Effect |
|---|---|---|
| `CUSTOM` | 0 | Your code decides, through the `applyActiveEffect` hook |
| `MULTIPLY` | 1 | `current * value` |
| `ADD` | 2 | `current + value` (use `-2` to subtract; for arrays, pushes) |
| `DOWNGRADE` | 3 | `min(current, value)` |
| `UPGRADE` | 4 | `max(current, value)` |
| `OVERRIDE` | 5 | replaces with `value` |

Duration (all optional): `{ startTime, seconds, combat, rounds, turns, startRound, startTurn }`.
:::

::: v14
```js
// A V14 change, stored in effect.system.changes (array)
{
  key: "system.abilities.str.bonus",       // data path on the target
  type: "add",                              // string, see table
  value: 2,                                 // deserialized: JSON if it parses, otherwise a string
  phase: "initial",                         // "initial" | "final" | a registered phase
  priority: null                            // null → default priority of the type
}
```

| `type` | Default priority (`CONST.ACTIVE_EFFECT_CHANGE_TYPES`) | Effect |
|---|---|---|
| `custom` | 0 | Your code decides, through the `applyActiveEffect` hook |
| `multiply` | 10 | `current * value` |
| `add` | 20 | `current + value` |
| `subtract` | 20 | `current - value` |
| `downgrade` | 30 | `min(current, value)` |
| `upgrade` | 40 | `max(current, value)` |
| `override` | 50 | replaces with `value` |

Phases (`CONST.ACTIVE_EFFECT_CHANGE_PHASES`): each phase is its own priority group. Every `initial` change runs before any `final` change, whatever the priorities. `final` changes run after derived data, so they can target derived values.

Duration: `{ value, units, expiry, expired }`. `units` is one of `CONST.ACTIVE_EFFECT_DURATION_UNITS` (`years`, `months`, `days`, `hours`, `minutes`, `seconds`, `rounds`, `turns`). `expiry` is an event id or `null`. The effect expires when **both** the duration has run out **and** the expiry event has happened. With `value: null` and `expiry: null` the effect lasts forever.
:::

### A custom effect type

Effects have a `type` and a `system` field, like actors and items. Declare a type in the manifest to store extra data, such as the number of stacks:

```json
{ "documentTypes": { "ActiveEffect": { "buff": {} } } }
```

::: v13
```js
// systems/forja/module/data/effect.mjs
const { NumberField, BooleanField } = foundry.data.fields;

export class BuffData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      stacks: new NumberField({ required: true, integer: true, min: 1, initial: 1 }),
      dispellable: new BooleanField({ initial: true })
    };
  }
}
```
:::

::: v14
In V14 the effect data model **owns the changes**. Extend `foundry.data.ActiveEffectTypeDataModel` and keep its schema. You may redefine `changes`, but it must keep `type`, `phase` and `priority`.

```js
// systems/forja/module/data/effect.mjs
const { NumberField, BooleanField } = foundry.data.fields;

export class BuffData extends foundry.data.ActiveEffectTypeDataModel {
  static defineSchema() {
    return {
      ...super.defineSchema(),               // keeps `changes`
      stacks: new NumberField({ required: true, integer: true, min: 1, initial: 1 }),
      dispellable: new BooleanField({ initial: true })
    };
  }
}
```
:::

## Register it

```js
// systems/forja/forja.mjs
import { BuffData } from "./module/data/effect.mjs";
import { ForjaActiveEffect } from "./module/documents/effect.mjs";

Hooks.once("init", () => {
  CONFIG.ActiveEffect.documentClass = ForjaActiveEffect;   // see "Items" for isSuppressed
  CONFIG.ActiveEffect.dataModels.buff = BuffData;
});
```

::: v13
```js
Hooks.once("init", () => {
  // New systems: keep transferred effects on their item
  CONFIG.ActiveEffect.legacyTransferral = false;

  // Status effects: an ARRAY of { id, name, img, ...effect data }
  CONFIG.statusEffects = [
    ...CONFIG.statusEffects.filter(s => ["dead", "prone", "blind"].includes(s.id)),
    {
      id: "stunned",
      name: "FORJA.Status.Stunned",
      img: "systems/forja/icons/stunned.svg",
      changes: [{ key: "system.defense.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "-2" }]
    }
  ];
});
```
:::

::: v14
```js
Hooks.once("init", () => {
  // Status effects: an OBJECT keyed by id (arrays are still accepted)
  const keep = ["dead", "prone", "blind"];
  for (const id of Object.keys(CONFIG.statusEffects)) if (!keep.includes(id)) delete CONFIG.statusEffects[id];
  CONFIG.statusEffects.stunned = {
    id: "stunned",
    name: "FORJA.Status.Stunned",
    img: "systems/forja/icons/stunned.svg",
    system: { changes: [{ key: "system.defense.bonus", type: "subtract", value: 2, phase: "initial" }] }
  };

  // Optional: a custom phase and a custom expiry event
  CONFIG.ActiveEffect.phases["forja-armor"] = { label: "FORJA.Phase.Armor", hint: "FORJA.Phase.ArmorHint" };
  CONFIG.ActiveEffect.expiryEvents["forja.rest"] = "FORJA.Expiry.Rest";
});
```
:::

## Create it in code

A 3-round blessing on an actor, plus a permanent status-based condition:

::: v13
```js
const actor = game.actors.getName("Aldric");

await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Blessing",
  img: "icons/magic/holy/prayer-hands-glowing-yellow.webp",
  type: "buff",
  system: { stacks: 1 },
  origin: someSpell.uuid,                   // where it came from (optional)
  duration: { rounds: 3 },                  // start round/turn filled in during combat
  statuses: ["blessed"],
  changes: [
    { key: "system.abilities.str.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "1" },
    { key: "system.defense.bonus", mode: CONST.ACTIVE_EFFECT_MODES.UPGRADE, value: "2" }
  ]
}]);

// Toggle a configured status effect (creates or deletes the effect)
await actor.toggleStatusEffect("stunned");
await actor.toggleStatusEffect("dead", { active: true, overlay: true });
actor.statuses.has("stunned");            // Set of active status ids
```

::: warning
V13 **does not remove expired effects** by itself. `duration.remaining` counts down, but deletion is up to your system or a module. See "Expire effects" below.
:::
:::

::: v14
```js
const actor = game.actors.getName("Aldric");

await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Blessing",
  img: "icons/magic/holy/prayer-hands-glowing-yellow.webp",
  type: "buff",
  origin: someSpell.uuid,                   // DocumentUUIDField
  duration: { value: 3, units: "rounds", expiry: "turnEnd" },
  statuses: ["blessed"],
  system: {
    stacks: 1,
    changes: [
      { key: "system.abilities.str.bonus", type: "add", value: 1, phase: "initial" },
      // "final" runs after prepareDerivedData, so it can target the derived total
      { key: "system.defense.value", type: "upgrade", value: 14, phase: "final" }
    ]
  }
}]);

// "Until the end of combat", whatever the number of rounds
await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Rage", duration: { value: null, units: "rounds", expiry: "combatEnd" },
  system: { changes: [{ key: "system.abilities.str.bonus", type: "add", value: 2, phase: "initial" }] }
}]);

// Status effects
await actor.toggleStatusEffect("stunned");
const data = await ActiveEffect.fromStatusEffect("stunned");  // an ActiveEffect you can customize
actor.statuses.has("stunned");

// A primary (sidebar) effect: no parent. GMs can drag it onto a token.
await ActiveEffect.create({ name: "Poisoned", img: "icons/svg/poison.svg" });
```

When an effect expires, `ActiveEffect.registry` acts according to `CONFIG.ActiveEffect.expiryAction` (`"update"`, `"delete"` or `null`).
:::

### Custom change logic

With `CUSTOM` / `"custom"`, core does nothing and fires the `applyActiveEffect` hook (same signature in both versions). Put what to write into the `changes` accumulator. This example adds a formula evaluated against the actor's roll data:

::: v13
```js
Hooks.on("applyActiveEffect", (actor, change, current, delta, changes) => {
  if (!change.key.startsWith("system.") || !String(change.value).startsWith("formula:")) return;
  const formula = Roll.replaceFormulaData(change.value.slice(8), actor.getRollData());
  changes[change.key] = Number(current) + Roll.safeEval(formula);
});
// Change: { key: "system.hp.max", mode: CONST.ACTIVE_EFFECT_MODES.CUSTOM, value: "formula:@lvl * 2" }
```
:::

::: v14
```js
Hooks.on("applyActiveEffect", (actor, change, current, delta, changes) => {
  if (!change.key.startsWith("system.") || !String(change.value).startsWith("formula:")) return;
  const formula = Roll.replaceFormulaData(change.value.slice(8), actor.getRollData());
  changes[change.key] = Number(current) + Roll.safeEval(formula);
});
// Change: { key: "system.hp.max", type: "custom", value: "formula:@lvl * 2", phase: "initial" }
```

::: tip
V14 already resolves `@` expressions in string values through `ActiveEffect#getReplacementData`. Before you write custom code, try a plain `add` change with value `"@lvl"`. Custom change types can also be registered in `CONFIG.ActiveEffect.changeTypes`. See the [API](https://foundryvtt.com/api/v14/) for the `ActiveEffectChangeTypeConfig` shape.
:::
:::

::: v14
### Migrating V13-shaped data to V14

Core migrates world and compendium documents when they load. Your **own** code and JSON sources, such as the `changes` arrays in pack source files, generators and macros, still need the new shape. Use this helper:

```js
const MODE_TO_TYPE = { 0: "custom", 1: "multiply", 2: "add", 3: "downgrade", 4: "upgrade", 5: "override" };
const DURATION_UNITS = ["seconds", "turns", "rounds"];   // V13 fields, checked in this order

/** Convert V13 ActiveEffect source data to the V14 shape. Returns a new object. */
export function effectToV14(data) {
  const out = foundry.utils.deepClone(data);
  const changes = out.changes ?? [];
  delete out.changes;
  out.system ??= {};
  out.system.changes = changes.map(c => ({
    key: c.key,
    type: MODE_TO_TYPE[c.mode] ?? "add",
    value: c.value,
    phase: "initial",                          // V13 behaviour = before derived data
    priority: c.priority ?? null
  }));

  const d = out.duration ?? {};
  const unit = DURATION_UNITS.find(u => Number.isFinite(d[u]) && d[u] > 0);
  out.duration = unit ? { value: d[unit], units: unit, expiry: null } : { value: null, units: "seconds", expiry: null };
  return out;
}

// Supporting both versions from one module:
const effectData = game.release.generation >= 14 ? effectToV14(v13Data) : v13Data;
```
:::

## Sheet/UI

Core ships an `ActiveEffectConfig` sheet (`effect.sheet.render(true)`). Your actor sheet usually lists effects with toggle and delete buttons:

```hbs
<ul class="effects">
  {{#each effects as |effect|}}
  <li data-effect-id="{{effect.id}}" data-parent-uuid="{{effect.parent.uuid}}" class="{{#if effect.disabled}}disabled{{/if}}">
    <img src="{{effect.img}}" width="24" height="24"> {{effect.name}}
    <a data-action="toggleEffect"><i class="fa-solid fa-power-off"></i></a>
    <a data-action="editEffect"><i class="fa-solid fa-pen"></i></a>
  </li>
  {{/each}}
</ul>
```

```js
// In your ActorSheetV2 subclass
static DEFAULT_OPTIONS = {
  actions: {
    async toggleEffect(event, target) {
      const effect = await ForjaCharacterSheet.#getEffect(target);
      return effect?.update({ disabled: !effect.disabled });
    },
    async editEffect(event, target) {
      (await ForjaCharacterSheet.#getEffect(target))?.sheet.render(true);
    }
  }
};

static async #getEffect(target) {
  const { effectId, parentUuid } = target.closest("[data-effect-id]").dataset;
  const parent = await fromUuid(parentUuid);            // the actor, or an item for transferred effects
  return parent?.effects.get(effectId);
}

async _prepareContext(options) {
  const context = await super._prepareContext(options);
  context.effects = [...this.actor.allApplicableEffects()];   // includes item effects
  return context;
}
```

## Common recipes

### Expire effects

::: v13
Remove effects whose duration ran out whenever the combat advances. Only the GM runs this:

```js
Hooks.on("updateCombat", async (combat, changes) => {
  if (!game.user.isActiveGM || !("turn" in changes || "round" in changes)) return;
  for (const combatant of combat.combatants) {
    const actor = combatant.actor;
    const expired = actor?.temporaryEffects.filter(e => e.duration.remaining <= 0) ?? [];
    for (const effect of expired) await effect.delete();
  }
});
```
:::

::: v14
Core does this for you. For your custom `forja.rest` event, you trigger the expiry yourself:

```js
async function shortRest(actor) {
  const ids = actor.effects.filter(e => e.duration.expiry === "forja.rest").map(e => e.id);
  await actor.deleteEmbeddedDocuments("ActiveEffect", ids);
}
```
:::

### Read the final value and who changed it

```js
actor.system.abilities.str.bonus;                       // after effects
actor.overrides;                                        // { "system.abilities.str.bonus": 1, ... }
[...actor.allApplicableEffects()].filter(e => e.active); // effects currently applying
```

::: v14
### Effects from regions and drops

Add an **Active Effect** behavior to a Scene Region to apply chosen effects to tokens that enter it, for example a poison cloud or a blessed zone. GMs can also drag a sidebar or compendium effect onto a Token. Both work with no code. To post-process them, use `preCreateActiveEffect` / `createActiveEffect` hooks.
:::

## Pitfalls

- **Targeting derived values.** Effects in V13, and the `initial` phase in V14, run *before* `prepareDerivedData`. Target a stored field such as `bonus`, or use the `final` phase in V14.
- **Key typos fail silently.** A wrong `key` just does nothing. Check `actor.overrides`.
- **V13 values are strings.** `"2"` is cast using the target field's type. For arrays and objects, the value must be valid JSON.
- **Transferred effects** apply from the item. Don't look for them in `actor.effects`. Use `allApplicableEffects()`.
- **Mixing shapes:** V14 code that writes `changes` at the top level, or `mode`, produces effects with no changes. Use `effectToV14()` above.
- **Expiring on every client.** In V13, delete expired effects on the active GM only, or each connected client will try to.
