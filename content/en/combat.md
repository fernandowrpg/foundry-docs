# Combat and Initiative

Configure the initiative formula, extend the Combat and Combatant classes, run code at the start or end of a turn, and create encounters from code.

::: changed
- Active Effects can now **expire on combat events** (`combatStart`, `roundStart`, `turnStart`, `combatEnd`, `roundEnd`, `turnEnd`) and measure duration in `rounds` or `turns` with the new `{ value, units, expiry }` shape. Many systems can delete their own "remove effect at end of turn" code. See [Active Effects](#active-effect).
- `ActiveEffect.registry` tracks temporary effects and their expiry, so the combat tracker and token icons agree on what is still active.
- See [the full changelog](#changes-14).
:::

## What it is

A **Combat** is a world document for one encounter. It owns embedded **Combatant** documents, one per participant, each pointing to a token (and through it to an actor). The combat stores `round`, `turn` and whether it has `started`; combatants store `initiative`, `defeated` and `hidden`.

The **Combat Tracker** in the sidebar is only the UI. Everything it does (rolling initiative, next turn) is a method on the documents, so you can call the same methods from code.

```text
Combat (round 2, turn 1)
 ├─ Combatant  Aria    initiative 18  → Token → Actor (character)
 ├─ Combatant  Goblin  initiative 12  → Token → Actor (npc)   ← current turn
 └─ Combatant  Wolf    initiative  7
```

## Set the initiative formula

The simplest option is the system manifest:

```json
{ "initiative": "1d20 + @abilities.agi.mod" }
```

Setting it in code gives you more control, such as tie-breaking decimals:

```js
Hooks.once("init", () => {
  CONFIG.Combat.initiative = {
    formula: "1d20 + @abilities.agi.mod",
    decimals: 2          // used to break ties, shown as 15.03
  };
});
```

`@...` references are resolved from `actor.getRollData()`.

## A custom formula per combatant

When the formula depends on the actor (for example NPCs roll `1d10`), override the Combatant class.

```js
// systems/forja/module/documents/combatant.mjs
export class ForjaCombatant extends Combatant {
  /** Return the initiative formula for this combatant. */
  _getInitiativeFormula() {
    if ( this.actor?.type === "npc" ) return "1d10 + @level";
    return super._getInitiativeFormula();   // CONFIG.Combat.initiative.formula
  }
}
```

```js
Hooks.once("init", () => {
  CONFIG.Combatant.documentClass = ForjaCombatant;
});
```

## A custom Combat class

Override `Combat` to change turn order or to run rules when turns and rounds change.

```js
// systems/forja/module/documents/combat.mjs
export class ForjaCombat extends Combat {
  /** Highest initiative first; ties go to characters over NPCs. */
  _sortCombatants(a, b) {
    const diff = (b.initiative ?? -Infinity) - (a.initiative ?? -Infinity);
    if ( diff ) return diff;
    return (a.actor?.type === "character" ? -1 : 1);
  }

  /** Runs once, on the active GM's client, when a combatant's turn starts. */
  async _onStartTurn(combatant, context) {
    await super._onStartTurn(combatant, context);
    const actor = combatant.actor;
    if ( !actor ) return;
    // Regenerate 1 stamina at the start of each turn
    const stamina = actor.system.stamina;
    if ( stamina && stamina.value < stamina.max ) {
      await actor.update({ "system.stamina.value": stamina.value + 1 });
    }
  }

  /** Runs on the active GM's client when a round ends. */
  async _onEndRound(context) {
    await super._onEndRound(context);
    ChatMessage.create({ content: `<p>${game.i18n.localize("FORJA.Combat.RoundEnd")}</p>` });
  }
}
```

```js
Hooks.once("init", () => {
  CONFIG.Combat.documentClass = ForjaCombat;
});
```

::: tip
`_onStartTurn`, `_onEndTurn`, `_onStartRound` and `_onEndRound` run **only on one client** (the active GM), which is exactly what you want for database updates. Hooks such as `combatTurn` run on **every** client, so use them for UI, not for updates.
:::

## Combat hooks

| Hook | Arguments | Runs on | Use it for |
|---|---|---|---|
| `combatStart` | `(combat, updateData)` | client that started | announce the fight |
| `combatRound` | `(combat, updateData, options)` | client that advanced | round banners |
| `combatTurn` | `(combat, updateData, options)` | client that advanced | UI feedback |
| `combatTurnChange` | `(combat, prior, current)` | every client | react to the new active turn |
| `preUpdateCombat` / `updateCombat` | document hooks | see [Hooks](#hooks) | low-level control |
| `deleteCombat` | `(combat, options, userId)` | every client | clean up |

```js
Hooks.on("combatTurnChange", (combat, prior, current) => {
  const combatant = combat.combatant;           // the one whose turn it is now
  if ( combatant?.isOwner ) ui.notifications.info(game.i18n.format("FORJA.Combat.YourTurn", { name: combatant.name }));
});
```

## Create an encounter from code

```js
// Put the selected tokens into a new, active combat on the current scene
const tokens = canvas.tokens.controlled.map(t => t.document);
const combat = await Combat.implementation.create({ scene: canvas.scene.id, active: true });
await TokenDocument.implementation.createCombatants(tokens, { combat });

await combat.rollAll();          // roll for everybody without initiative
await combat.startCombat();      // round 1, turn 0
```

Other useful methods:

```js
await combat.rollNPC();                          // only non-player combatants
await combat.rollInitiative([combatantId], { formula: "1d20 + 5" });
await combat.nextTurn();
await combat.previousTurn();
await combat.nextRound();
await combat.endCombat();                        // asks for confirmation, then deletes

// From an actor: add its tokens to the combat and roll
await actor.rollInitiative({ createCombatants: true, rerollInitiative: false });
```

## Combatant data (optional)

Systems can give combatants their own data model, for example to track actions left this round.

```json
{ "documentTypes": { "Combatant": { "base": {} } } }
```

```js
class ForjaCombatantData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    const { NumberField } = foundry.data.fields;
    return { actionsLeft: new NumberField({ required: true, integer: true, min: 0, initial: 2 }) };
  }
}

Hooks.once("init", () => {
  CONFIG.Combatant.dataModels.base = ForjaCombatantData;
});
```

## Turn markers

V13 added **combat turn markers**: an animated texture under the token whose turn it is. Users configure them in the Combat Tracker settings. A system can supply a default image through `CONFIG.Combat` (check `CONFIG.Combat.fallbackTurnMarker` in the API docs for your version).

## Effects that last "until the end of your next turn"

::: v13
V13 has no built-in expiry events. Store the duration in rounds/turns and remove effects yourself, usually in `_onStartTurn`:

```js
async _onStartTurn(combatant, context) {
  await super._onStartTurn(combatant, context);
  const expired = combatant.actor?.effects.filter(e => e.duration.remaining !== null && e.duration.remaining <= 0) ?? [];
  if ( expired.length ) await combatant.actor.deleteEmbeddedDocuments("ActiveEffect", expired.map(e => e.id));
}
```
:::

::: v14
Declare it on the effect and let the core handle it:

```js
await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Parry",
  img: "icons/skills/melee/weapons-crossed-swords-yellow.webp",
  duration: { value: 1, units: "turns", expiry: "turnEnd" },   // ends at the end of the next turn
  system: { changes: [{ key: "system.defense", type: "add", value: "2" }] }
}]);
```

Expiry events come from `CONST.ACTIVE_EFFECT_EXPIRY_EVENTS`. Systems and modules can define more events, but then they must handle them.
:::

## Customize the tracker UI

The tracker is an ApplicationV2 in V13 and V14. To add a small element to each row, use its render hook with the `HTMLElement` it passes:

```js
Hooks.on("renderCombatTracker", (app, html, context) => {
  for ( const li of html.querySelectorAll("[data-combatant-id]") ) {
    const combatant = app.viewed?.combatants.get(li.dataset.combatantId);
    const left = combatant?.system?.actionsLeft;
    if ( left === undefined ) continue;
    li.querySelector(".token-name")?.insertAdjacentHTML("beforeend", `<span class="forja-actions">${left}⚔</span>`);
  }
});
```

For deeper changes, subclass the tracker and set `CONFIG.ui.combat` to your class in `init`.

## Pitfalls

- **Updating documents in `combatTurn`**: every client runs it, so you get one update per connected user. Use `_onStartTurn` or check `game.user.isActiveGM`.
- **Combatants without tokens**: combatants can exist without a token (or with a deleted one). Always use `combatant.actor?.`.
- **Tie-breakers**: without `decimals`, ties keep insertion order, which players read as random.
