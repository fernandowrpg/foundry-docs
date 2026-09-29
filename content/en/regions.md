# Regions and Templates

Scene Regions are shaped areas that react to tokens through Region Behaviors; in V14 they also replace Measured Templates for areas of effect.

::: changed
- **MeasuredTemplate is removed.** Areas of effect are now **Template Regions**: regions with the new shapes `line`, `cone`, `ring`, `emanation`, `token` and `grid`.
- Regions can be **attached to a token** (`RegionDocument#attachment.token`) and follow it; `RegionDocument.createTokenEmanation()` builds one.
- `RegionLayer#placeRegion()` / `#placeRegions()` for interactive placement (`attachToToken`, `onChange`, `allowEmpty`, ...).
- New behaviors: **Active Effect** (applies effects to tokens inside) and **Change Level**.
- `RegionDocument#teleportTokens()` and `#spawnTokens()`; regions have an `ownership` field and a new `REGION_CREATE` permission.
- `RegionShape` deprecated in favour of `BaseShapeData` subclasses.
- See [the full changelog](#changes-14).
:::

## What it is

A **Region** (`RegionDocument`, embedded in a Scene) is a set of shapes plus an elevation range.
On its own it does nothing. You attach **Region Behaviors** (`RegionBehavior` documents, embedded
in the Region) that listen to **events** such as a token entering, a combat turn starting inside
the area, or the behavior being activated.

Typical uses: traps, difficult terrain, stairs/teleporters, zones of darkness, "pause the game when
someone opens this door", and (V14) spell areas.

## Shapes and events

The basic region shapes are `rectangle`, `circle`, `ellipse` and `polygon` (V14 adds the template
shapes below), and any shape can be a `hole`. Regions have `elevation: { bottom, top }` (`null` means infinite).

```js
// A trap covering 3x3 grid spaces, starting at pixel (500, 500)
const size = canvas.grid.size;
const [region] = await canvas.scene.createEmbeddedDocuments("Region", [{
  name: "Spike pit",
  color: "#aa3322",
  shapes: [{ type: "rectangle", x: 500, y: 500, width: 3 * size, height: 3 * size, rotation: 0, hole: false }],
  elevation: { bottom: null, top: 0 },
  visibility: CONST.REGION_VISIBILITY.GAMEMASTER
}]);
```

The events a behavior can subscribe to are in `CONST.REGION_EVENTS`:

| Key | Value | Fires when |
| --- | --- | --- |
| `TOKEN_ENTER` / `TOKEN_EXIT` | `tokenEnter` / `tokenExit` | a token enters/leaves (after the update) |
| `TOKEN_MOVE_IN` / `TOKEN_MOVE_OUT` / `TOKEN_MOVE_WITHIN` | `tokenMoveIn` ... | a movement segment crosses/stays in the region |
| `TOKEN_ANIMATE_IN` / `TOKEN_ANIMATE_OUT` | `tokenAnimateIn` ... | the token's *animation* crosses the boundary |
| `TOKEN_TURN_START` / `TOKEN_TURN_END` | `tokenTurnStart` ... | a combatant inside starts/ends its turn |
| `TOKEN_ROUND_START` / `TOKEN_ROUND_END` | `tokenRoundStart` ... | a combat round starts/ends with the token inside |
| `REGION_BOUNDARY` | `regionBoundary` | the region's shape or elevation changed |
| `BEHAVIOR_ACTIVATED` / `BEHAVIOR_DEACTIVATED` | `behaviorActivated` ... | the behavior was enabled/disabled or created/deleted |
| `BEHAVIOR_VIEWED` / `BEHAVIOR_UNVIEWED` | `behaviorViewed` ... | the scene started/stopped being viewed |

## Built-in behaviors

Core ships behaviors you can configure without code: **Adjust Darkness Level**, **Display Scrolling
Text**, **Execute Macro**, **Execute Script**, **Pause Game**, **Suppress Weather**, **Teleport
Token**, **Toggle Behavior** and **Modify Movement Cost** (V13+, per movement action difficulty).

::: v14
V14 adds **Change Level** (stairs, ladders and lifts between [Scene Levels](#scene-token--scene-levels))
and **Active Effect**, which applies Active Effects to tokens while they are inside the region.
:::

## Define a custom behavior type (data model)

A behavior type is a `TypeDataModel` subclass of `foundry.data.regionBehaviors.RegionBehaviorType`.
Two ways to handle events:

- `static events = { [eventName]: handler }` — events the type **always** handles.
- An `events` field in the schema (built with `this._createEventsField()`) — events the **user**
  picks in the config sheet; these are dispatched to `_handleRegionEvent(event)`.

```js
// modules/forja-extras/scripts/trap-behavior.mjs
const { fields } = foundry.data;

export class TrapBehaviorType extends foundry.data.regionBehaviors.RegionBehaviorType {
  static LOCALIZATION_PREFIXES = ["FORJA_EXTRAS.Trap"];

  static defineSchema() {
    return {
      // Let the GM choose which events spring the trap; default: entering
      events: this._createEventsField({
        events: [
          CONST.REGION_EVENTS.TOKEN_ENTER,
          CONST.REGION_EVENTS.TOKEN_TURN_START
        ],
        initial: [CONST.REGION_EVENTS.TOKEN_ENTER]
      }),
      damage: new fields.StringField({ required: true, blank: false, initial: "2d6" }),
      once: new fields.BooleanField({ initial: true })
    };
  }

  /** @override */
  async _handleRegionEvent(event) {
    // Behaviors run on EVERY client. Let only the active GM act: the GM can update the
    // actor AND the behavior, which the moving player may not own
    if (!game.users.activeGM?.isSelf) return;
    const token = event.data.token;
    const actor = token?.actor;
    if (!actor) return;

    const roll = await new Roll(this.damage).evaluate();
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ token }),
      flavor: game.i18n.format("FORJA_EXTRAS.Trap.Triggered", { name: token.name })
    });
    const hp = actor.system.hp;
    await actor.update({ "system.hp.value": Math.max(hp.value - roll.total, 0) });

    // Disable the behavior after the first trigger
    if (this.once) await this.parent.update({ disabled: true });
  }
}
```

`this.parent` is the `RegionBehavior` document and `this.region` the `RegionDocument`.
`event` has `name`, `data`, `region` and `user`; for token events `event.data.token` is the
`TokenDocument` (movement events also carry `event.data.movement`).

## Register it

Declare the sub-type in the manifest, then connect the data model in `init`. Module sub-types are
namespaced with the module id, so the type key is `forja-extras.trap`.

```json
{
  "id": "forja-extras",
  "documentTypes": {
    "RegionBehavior": {
      "trap": {}
    }
  }
}
```

```js
// modules/forja-extras/scripts/main.mjs
import { TrapBehaviorType } from "./trap-behavior.mjs";

Hooks.once("init", () => {
  CONFIG.RegionBehavior.dataModels["forja-extras.trap"] = TrapBehaviorType;
  CONFIG.RegionBehavior.typeIcons["forja-extras.trap"] = "fa-solid fa-burst";
});
```

```json
{
  "TYPES": { "RegionBehavior": { "forja-extras.trap": "Trap" } },
  "FORJA_EXTRAS": {
    "Trap": {
      "FIELDS": {
        "damage": { "label": "Damage", "hint": "Roll formula applied to the token." },
        "once": { "label": "Single use" }
      },
      "Triggered": "{name} springs a trap!"
    }
  }
}
```

The config sheet for the behavior is generated automatically from the schema.

## Create it in code

```js
await region.createEmbeddedDocuments("RegionBehavior", [{
  name: "Spikes",
  type: "forja-extras.trap",
  system: { damage: "3d6", once: false }
}]);
```

## Areas of effect

::: v13
### MeasuredTemplate (V13)

In V13 spell areas are `MeasuredTemplate` documents embedded in the Scene. `t` is one of
`CONST.MEASURED_TEMPLATE_TYPES`: `"circle"`, `"cone"`, `"rect"`, `"ray"`. `distance` is in scene
units, `direction` and `angle` in degrees. Default cone angle and ray width live in
`CONFIG.MeasuredTemplate.defaults`.

```js
/** Create a 6 m cone in front of the caster's token */
async function castCone(token) {
  const [template] = await canvas.scene.createEmbeddedDocuments("MeasuredTemplate", [{
    t: CONST.MEASURED_TEMPLATE_TYPES.CONE,
    x: token.center.x,
    y: token.center.y,
    distance: 6,
    angle: 60,
    direction: token.document.rotation + 90,
    fillColor: game.user.color.css,
    flags: { forja: { spell: "fire-breath" } }
  }]);
  return template;
}

// Which tokens are inside? Test token centres against the template shape
function tokensInTemplate(templateDoc) {
  const t = templateDoc.object;
  return canvas.tokens.placeables.filter(tok =>
    t.shape.contains(tok.center.x - templateDoc.x, tok.center.y - templateDoc.y));
}
```
:::

::: v14
### Template Regions (V14)

The `MeasuredTemplate` document no longer exists. An area of effect is a Region using the
template shapes (`circle`, `cone`, `line`, `ring`, `emanation`, `token`, `grid`). Because it is a
region, it can carry behaviors: the **Active Effect** behavior applies a condition to everything
inside, and `region.tokens` tells you who is in the area.

The easiest and most robust way is interactive placement: the user positions the shape and core
handles snapping, rotation and preview.

```js
/** Let the user place a fire cone; the region is created on confirm */
async function castCone(token) {
  const region = await canvas.regions.placeRegion({
    name: "Fire breath",
    color: game.user.color.css,
    shapes: [{ type: "cone" }],
    flags: { forja: { spell: "fire-breath" } }
  }, {
    attachToToken: false,
    onChange: (data) => { /* live preview: react to shape changes */ }
  });
  if (!region) return null;           // cancelled
  return [...region.tokens];          // TokenDocuments inside the area
}
```

::: warning
The field names of each shape (radius, angle, width, ...) are defined by its `BaseShapeData`
subclass (for example `foundry.data.ConeShapeData`). Check the V14 API before writing shape data by
hand; when in doubt, let `placeRegion` fill them.
:::

An **emanation** that follows a token (auras) is created with `RegionDocument.createTokenEmanation()`
or by setting `attachment.token` to the token id; the region then moves with the token.

`RegionDocument#teleportTokens(tokens, options)` moves tokens into a region (options
`placement: "center" | "relative" | "random"`, `avoidOccupied`, `snap`, `level`), and
`RegionDocument#spawnTokens(tokenData, options)` creates them there (`create: false` returns
ephemeral, unsaved documents).

Players need the new `REGION_CREATE` permission to create regions, and the region's `ownership`
controls who can edit it.
:::

::: v14
## Migrating an AoE template to a region

1. Replace `createEmbeddedDocuments("MeasuredTemplate", ...)` with `canvas.regions.placeRegion()`
   (interactive) or `createEmbeddedDocuments("Region", ...)` (fixed data).
2. Move `t`/`distance`/`direction`/`angle` into a single entry in `shapes`, using the V14 shape types.
3. Replace your "who is in the template" math with `region.tokens` or
   `tokenDoc.testInsideRegion(region)`.
4. Replace hooks on `createMeasuredTemplate` with `createRegion` (check your flag, e.g.
   `region.getFlag("forja", "spell")`).
5. Replace ongoing effects implemented by hand with an **Active Effect** behavior.
6. Remove every reference to `CONFIG.MeasuredTemplate`, `canvas.templates` and the
   `MeasuredTemplate` class. Test the migration of old worlds that still contain templates in a
   copy of the world before release.
:::

## Common recipes

```js
// Is a token inside a region right now?
const inside = tokenDoc.testInsideRegion(region);

// All regions containing a token
console.log([...tokenDoc.regions].map(r => r.name));

// Teleport a token into a destination region
await destination.teleportToken(tokenDoc);
```

## Pitfalls

::: warning
- Region events are dispatched on **every** client. Guard with `game.users.activeGM?.isSelf`
  (GM does the work) or `event.user.isSelf` (the user who caused the event does it), or your trap
  fires once per connected player.
- A player cannot update documents they don't own: if a behavior must update the region, actor or
  scene on a player's move, route the change to the GM via a [query or socket](#sockets).
- `TOKEN_ENTER` fires after the token's update is saved. If you need to react *during* the
  movement (for example to stop the token at the edge with `tokenDoc.stopMovement()`), use the
  `TOKEN_MOVE_IN` family instead.
- Forgetting `documentTypes` in the manifest means `type: "forja-extras.trap"` is rejected as invalid.
:::
