# Scenes and Tokens

How Scene documents describe a map, how TokenDocuments and Token placeables relate, and how to create and move tokens from code.

::: changed
- **Scene Levels**: a Scene can stack several `Level` documents (each with its own background, foreground, fog and elevation range). Tokens belong to a level (`TokenDocument#level`).
- **Planned movement**: `Token#planMovement()`, `Scene#moveTokens()` and `TokenLayer#placeTokens()` are new.
- `TokenDocument#move()` now resolves when the movement is **finished**, not when the first update is written.
- New origin helpers: `getMovementOrigin`, `getVisionOrigin`, `getLightOrigin`, `getSoundOrigin`; tokens have a `depth`.
- `Scene#activate({ viewOptions, pullUsers })`, scene transitions, `CanvasShakeEffect` and `ParticleGenerator` (VFX).
- `TokenFindMovementPathOptions` `ignoreWalls/ignoreCost/history` deprecated in favour of `constrainOptions`.
- See [the full changelog](#changes-14).
:::

## What it is

A **Scene** is a document that describes one map: its size, grid, background image, lighting and
all the objects placed on it. Those objects are *embedded documents* of the Scene: `Token`,
`Tile`, `Wall`, `AmbientLight`, `AmbientSound`, `Note`, `Drawing`, `Region` (and in V13
`MeasuredTemplate`).

For every embedded document there are **two** objects you will meet:

| Object | Class | Lives in | Used for |
| --- | --- | --- | --- |
| `TokenDocument` | `foundry.documents.TokenDocument` | the database, on every client | data: position, image, actor link, movement |
| `Token` (placeable) | `foundry.canvas.placeables.Token` | the canvas, only for the *viewed* scene | drawing, mouse interaction, animation |

Get from one to the other with `tokenDoc.object` (may be `null` when the scene is not viewed) and
`token.document`. The rule of thumb: **read and write data through the document; use the placeable
only for visual things.** Updates on the document replicate to all clients; changes you make to the
placeable are local and are lost on the next redraw.

```js
// Useful entry points
game.scenes.active;          // the Scene players are pulled to
game.scenes.viewed;          // the Scene this client is looking at (same as canvas.scene)
canvas.tokens.controlled;    // Token placeables the user has selected
canvas.tokens.placeables;    // all Token placeables on the viewed scene
actor.getActiveTokens();     // placeables for this actor on the viewed scene
canvas.scene.tokens;         // EmbeddedCollection of TokenDocuments
```

## Scene data: grid, background and dimensions

The important Scene fields are `width`, `height`, `padding`, `grid` (`type`, `size`, `distance`,
`units`), `background` (`src`, ...), `initial` (starting view) and `tokenVision`.
Derived pixel geometry lives in `scene.dimensions`, which is computed during data preparation.

```js
// Create a Scene from code
const scene = await Scene.create({
  name: "Forja Arena",
  width: 3000,
  height: 2000,
  padding: 0.1,
  grid: { type: CONST.GRID_TYPES.SQUARE, size: 100, distance: 1.5, units: "m" },
  background: { src: "systems/forja/assets/maps/arena.webp" },
  tokenVision: true
});

const d = scene.dimensions;
console.log(d.sceneRect);      // Rectangle of the playable area (without padding)
console.log(d.size, d.distance, d.distancePixels); // grid size in px, units per grid, px per unit
```

`scene.view()` shows the scene on *this* client only. `scene.activate()` (GM) marks it active and
pulls every player to it.

::: v14
In V14 `Scene#activate` accepts options: `pullUsers` and `viewOptions` (the same options as
`Scene#view`), which is also where the new scene transitions are configured. The `ready` hook fires
only **after** the initial scene transition finishes.

```js
// Activate without pulling users that are viewing other scenes
await scene.activate({ pullUsers: false });
```

A Scene can now hold several **Levels** (embedded `Level` documents in `scene.levels`). Each level
has a `name`, an `elevation` range, its own `background`, `foreground` and `fog` settings, and
`visibility`. Scene-level properties such as `background` are mapped to the child level, so simple
single-level scenes keep working. See [Levels](#scene-token--scene-levels) below.
:::

## Prototype tokens

Every Actor has a `prototypeToken` (a `PrototypeToken` data model, not a document). It is the
template used when the actor is placed on a scene. Systems usually set sensible defaults in
`Actor#_preCreate`:

```js
// systems/forja/module/documents/actor.mjs
export class ForjaActor extends Actor {
  async _preCreate(data, options, user) {
    if ((await super._preCreate(data, options, user)) === false) return false;
    // Player characters: linked token, friendly, vision on
    if (this.type === "character") {
      this.updateSource({
        prototypeToken: {
          actorLink: true,
          disposition: CONST.TOKEN_DISPOSITIONS.FRIENDLY,
          sight: { enabled: true }
        }
      });
    }
  }
}
```

`actorLink: true` means the token and the world actor share the same data (player characters).
`actorLink: false` makes each token an independent copy whose differences are stored in an
`ActorDelta` (monsters: ten goblins, ten HP bars).

## Create a token in code

Never build token data by hand from the actor: `actor.getTokenDocument()` merges the prototype,
resolves wildcard images and links the actor for you.

```js
/**
 * Place an actor's token centred on a grid space of the viewed scene.
 * @param {Actor} actor
 * @param {{x:number, y:number}} point   A point in canvas pixels
 */
async function placeActor(actor, point) {
  const scene = canvas.scene;
  // Snap to the grid so the token lands on a space
  const snapped = scene.grid.getSnappedPoint(point, { mode: CONST.GRID_SNAPPING_MODES.TOP_LEFT_CORNER });
  const tokenDoc = await actor.getTokenDocument({ x: snapped.x, y: snapped.y, hidden: false });
  // Either of these two lines works
  const [created] = await scene.createEmbeddedDocuments("Token", [tokenDoc.toObject()]);
  // const created = await TokenDocument.implementation.create(tokenDoc, { parent: scene });
  return created;
}
```

::: v14
V14 also offers an interactive placement flow, the same one used when dragging actors: the user
sees a preview, can rotate it with the mouse wheel, and confirms with a click.

```js
const tokenDoc = await actor.getTokenDocument();
// Resolves with the created TokenDocuments (empty/null if the user cancels)
const placed = await canvas.tokens.placeTokens([tokenDoc.toObject()], { allowRotation: true });
```
:::

## Movement

::: v13
V13 introduced a full movement API. Moving a token is no longer "update `x` and `y`": a move is a
list of **waypoints**, each with a **movement action** (walk, fly, swim, ...), measured with the
grid and terrain costs, stored in `movementHistory` and announced by hooks.
:::

::: v14
V14 keeps the V13 movement API and adds **planned movement** and multi-token moves (below).
:::

### Move with waypoints

```js
const tokenDoc = canvas.tokens.controlled[0]?.document;
if (tokenDoc) {
  // Walk two spaces right, then fly one space up
  const size = canvas.grid.size;
  await tokenDoc.move([
    { x: tokenDoc.x + 2 * size, y: tokenDoc.y, action: "walk" },
    { x: tokenDoc.x + 2 * size, y: tokenDoc.y - size, action: "fly", elevation: 5 }
  ], { showRuler: true });
}
```

Options include `method` (`"api"`, `"dragging"`, `"keyboard"`, ...), `autoRotate`, `showRuler`
and `constrainOptions` (for wall/cost constraints). `move()` returns a `Promise<boolean>`: `false`
if a hook or the permission check cancelled it.

::: v14
In V14 the promise resolves when the movement has **finished** (including animation and any pauses),
so you can safely `await` it before the next step. In V13 it resolves once the move is submitted.
:::

### Measure a path and read history

```js
// Distance and cost of a hypothetical path (no movement happens)
const result = tokenDoc.measureMovementPath([
  { x: tokenDoc.x, y: tokenDoc.y, elevation: tokenDoc.elevation },
  { x: tokenDoc.x + 500, y: tokenDoc.y, elevation: tokenDoc.elevation }
]);
console.log(result.distance, result.cost, result.spaces);

// What the token did so far (e.g. this combat turn)
console.log(tokenDoc.movementHistory);
```

### Hooks: validate or react to movement

```js
// Cancel a single move that costs more than the actor's speed (a Forja rule)
Hooks.on("preMoveToken", (tokenDoc, movement, operation) => {
  const speed = tokenDoc.actor?.system.speed ?? 6;
  if (movement.passed.cost + movement.pending.cost > speed) {
    ui.notifications.warn(game.i18n.localize("FORJA.Movement.TooFar"));
    return false;
  }
});

Hooks.on("moveToken", (tokenDoc, movement, operation, user) => {
  console.log(`${tokenDoc.name} moved ${movement.passed.distance} ${canvas.scene.grid.units}`);
});
```

### Custom movement actions

Movement actions live in `CONFIG.Token.movement.actions`. Add your own in `init`:

```js
Hooks.once("init", () => {
  CONFIG.Token.movement.actions.glide = {
    // Start from "walk" so every key core expects has a value
    ...CONFIG.Token.movement.actions.walk,
    label: "FORJA.Movement.Glide",
    icon: "fa-solid fa-feather",
    order: 25,
    // Only actors with the "glide" trait can select it
    canSelect: (token) => !!token.actor?.system.traits?.glide
  };
});
```

::: tip
Other keys of the action config (cost functions, terrain, animation) are documented in the API
under `TokenMovementActionConfig`. Check the version you target before relying on them.
:::

### Custom Token class and ruler

For visual changes (a health ring, a custom ruler label), subclass the placeable and register it:

```js
class ForjaToken extends foundry.canvas.placeables.Token {
  /** Tint a resource bar red when it is empty */
  _drawBar(number, bar, data) {
    super._drawBar(number, bar, data);
    bar.tint = data.value <= 0 ? 0xff3333 : 0xffffff;
  }
}

class ForjaTokenRuler extends foundry.canvas.placeables.tokens.TokenRuler {
  /** Our own label template, copied from the core one and extended */
  static WAYPOINT_LABEL_TEMPLATE = "systems/forja/templates/hud/waypoint-label.hbs";

  /** Add the movement cost to the waypoint label */
  _getWaypointLabelContext(waypoint, state) {
    const context = super._getWaypointLabelContext(waypoint, state);
    // The context feeds the label template; inspect it in the console to see its keys
    if (context) context.forjaCost = waypoint.measurement?.cost;
    return context;
  }
}

Hooks.once("init", () => {
  CONFIG.Token.objectClass = ForjaToken;
  CONFIG.Token.rulerClass = ForjaTokenRuler;
});
```

::: v14
### Planned movement and multi-token moves

V14 lets a user *plan* a move (the ruler stays on screen until confirmed) and lets code move many
tokens in one operation:

```js
// Let the user plan a path for the controlled token (resolves null if cancelled)
const token = canvas.tokens.controlled[0];
const plan = await token?.planMovement();
if (plan) console.log(plan.origin, plan.destination, plan.waypoints);

// Move several tokens together; keys are token ids
const size = canvas.grid.size;
const instructions = {};
for (const t of canvas.tokens.controlled) {
  instructions[t.id] = { waypoints: [{ x: t.document.x + size, y: t.document.y }] };
}
const results = await canvas.scene.moveTokens(instructions);
```

The `planToken` hook fires when a user plans movement. The exact shape of
`TokenMovementInstruction` is documented in the [V14 API](https://foundryvtt.com/api/v14/).

Collision and vision now use the token's *origin points*: `getMovementOrigin()`,
`getVisionOrigin()`, `getLightOrigin()`, `getSoundOrigin()`. Override them on a `TokenDocument`
subclass if your system uses non-standard token geometry.

:::

::: v14
## Scene Levels

A level is a slice of the scene between two elevations (ground floor, balcony, cellar). Each
`TokenDocument` has a `level` field with the id of the level it stands on; vision, lighting and
fog are computed per level, and walls/surfaces between levels block sight.

```js
// List the levels of the viewed scene
for (const level of canvas.scene.levels) {
  console.log(level.index, level.name, level.elevation, level.isView);
}

// Tokens on a given level
const cellar = canvas.scene.levels.getName("Cellar");
const tokensInCellar = canvas.scene.tokens.filter(t => t.level === cellar?.id);
```

`Scene#getSurfaces()` returns the surfaces (floors/ceilings) of the scene filtered by type
(`"move"`, `"sight"`, `"light"`, `"sound"`, `"darkness"`) and level; `Scene#testSurfaceCollision()`
tests whether a line between two elevated points crosses one. Use the **Change Level** region
behavior (see [Regions](#regions)) for stairs.

## Visual effects: screen shake and particles

```js
// Shake the canvas for 1.5 seconds (e.g. an earthquake spell)
const shake = new foundry.canvas.animation.CanvasShakeEffect({
  duration: 1500,
  maxDisplacement: 15,
  smoothness: 0.5
});
await shake.play();
```

`CanvasShakeEffect` is local to the client that runs it: broadcast it with a
[socket](#sockets) if every player should feel it. `ParticleGenerator` (in `foundry.canvas.vfx`)
emits particle effects; see the V14 API for its options.
:::

## Common recipes

```js
// Pan to and select an actor's token
const token = actor.getActiveTokens()[0];
if (token) {
  await canvas.animatePan({ x: token.center.x, y: token.center.y, scale: 1.5 });
  token.control({ releaseOthers: true });
}

// Rename every token of a scene linked to a given actor
const updates = canvas.scene.tokens
  .filter(t => t.actorId === actor.id)
  .map(t => ({ _id: t.id, name: actor.name }));
await canvas.scene.updateEmbeddedDocuments("Token", updates);
```

## Pitfalls

::: warning
- `tokenDoc.object` is `null` when its scene is not the viewed one. Always guard.
- `token.actor` for an unlinked token is a *synthetic* actor. Updating it writes to the token's
  `ActorDelta`, not to the world actor.
- Updating `x`/`y` directly still works but bypasses waypoints and the movement action; prefer
  `TokenDocument#move` so rulers, hooks and history stay correct.
- Hooks like `moveToken` run on every client. Only one client (for example
  `game.users.activeGM?.isSelf`) should create documents in response.
- Custom placeable classes must call `super` in every override: the core rendering pipeline depends
  on it.
:::
