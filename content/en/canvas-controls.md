# Canvas, Scene Controls and HUD

Add buttons to the scene controls, draw your own canvas layer, extend the Token HUD and react to canvas events.

::: changed
- `SceneControlTool` gains `interaction`, `control` and `creation` properties that describe what a tool does, plus `shapeData` to define Region drawing tools.
- `ui.controls.tool` and `game.activeTool` can be `null` when a control has no tools. Guard against it.
- `PlaceableObject#isInteractable`: locked placeables (except Tokens) are no longer interactable.
- `layerClass` in Canvas Document CONFIG (for example `CONFIG.Token.layerClass`) is deprecated; layer options now live on the `PlaceablesLayer` class.
- New **Placeables Palette** (bulk edit of selected objects) and **Placeables sidebar tab**.
- New visual APIs: `foundry.canvas.vfx` (timeline animations powered by anime.js), `ParticleGenerator`, and `CanvasShakeEffect` (screen shake).
- `PlaceableObject#clear` is deprecated in favor of the protected `_clear`.
- See [the full changelog](#changes-14).
:::

## What it is

The **canvas** is the PIXI.js scene where tokens, walls, lights and regions are drawn. It is split into **layers** (`canvas.tokens`, `canvas.walls`, `canvas.regions`…). The **scene controls** on the left of the screen choose the active layer and tool. Each placeable object (a `Token`, a `Wall`) is the visual side of a document (`TokenDocument`, `WallDocument`).

```text
ui.controls (left toolbar)        canvas
 ├─ tokens  → canvas.tokens   ← Token objects  ↔ TokenDocument
 ├─ walls   → canvas.walls    ← Wall objects   ↔ WallDocument
 └─ forja   → canvas.forja    ← your own layer (optional)
```

## Add a tool to the scene controls

Since V13, `controls` is an **object keyed by name**, and each control's `tools` is an object too. Add or change entries in place.

```js
Hooks.on("getSceneControlButtons", controls => {
  // A button in the existing Token controls
  controls.tokens.tools.forjaRest = {
    name: "forjaRest",
    title: "FORJA.Controls.Rest",           // localized automatically
    icon: "fa-solid fa-campground",
    order: Object.keys(controls.tokens.tools).length,
    button: true,                           // click action, not a mode
    visible: game.user.isGM,
    onChange: (event, active) => game.forja.restParty()
  };

  // A toggle that stays on or off
  controls.tokens.tools.forjaAuras = {
    name: "forjaAuras",
    title: "FORJA.Controls.Auras",
    icon: "fa-solid fa-circle-radiation",
    order: Object.keys(controls.tokens.tools).length,
    toggle: true,
    active: game.settings.get("forja", "showAuras"),
    onChange: (event, active) => game.settings.set("forja", "showAuras", active)
  };
});
```

::: warning
Code written for V12 used `controls.find(c => c.name === "token").tools.push(...)`. That fails in V13 and V14 because `controls` is not an array anymore, and the key is `tokens` (plural).
:::

::: v14
Tools can describe their behavior with the new `interaction`, `control` and `creation` properties, and Region drawing tools can pass `shapeData`. Check the `SceneControlTool` type in the V14 API for the accepted values. Always handle a missing active tool:

```js
const tool = ui.controls.tool;        // can be null in V14
if ( tool?.name === "forjaAuras" ) { /* ... */ }
```
:::

## A custom canvas layer

Use a layer when you need to draw something that is not a document, such as an overlay of auras or a grid heat map.

```js
// systems/forja/module/canvas/aura-layer.mjs
const { InteractionLayer } = foundry.canvas.layers;

export class ForjaAuraLayer extends InteractionLayer {
  static get layerOptions() {
    return foundry.utils.mergeObject(super.layerOptions, { name: "forjaAuras", zIndex: 180 });
  }

  /** Called when the canvas draws this layer. */
  async _draw(options) {
    this.graphics = this.addChild(new PIXI.Graphics());
    this.refreshAuras();
  }

  /** Redraw a circle around every token that has an aura. */
  refreshAuras() {
    const g = this.graphics;
    if ( !g ) return;
    g.clear();
    if ( !game.settings.get("forja", "showAuras") ) return;
    for ( const token of canvas.tokens.placeables ) {
      const radius = token.actor?.system.aura?.radius;       // in grid units
      if ( !radius ) continue;
      const px = radius * canvas.dimensions.distancePixels;
      const { x, y } = token.center;
      g.beginFill(0xee8a4f, 0.12).lineStyle(2, 0xee8a4f, 0.6).drawCircle(x, y, px).endFill();
    }
  }
}
```

```js
Hooks.once("init", () => {
  CONFIG.Canvas.layers.forjaAuras = { layerClass: ForjaAuraLayer, group: "interface" };
});

// Keep it fresh
Hooks.on("refreshToken", () => canvas.forjaAuras?.refreshAuras());
Hooks.on("canvasReady", () => canvas.forjaAuras?.refreshAuras());
```

::: v14
Scenes can have several **Levels**. If your overlay only makes sense on the viewed level, skip tokens that are not on it. See [Scenes and Tokens](#scene-token) for level-aware helpers such as `Scene#getSurfaces`.
:::

## Extend the Token HUD

The Token HUD is the ring of buttons around a selected token. The render hook gives you the HUD application and its `HTMLElement`.

```js
Hooks.on("renderTokenHUD", (hud, html, context) => {
  const token = hud.object;                         // the Token placeable
  if ( !token.actor?.isOwner ) return;
  const button = document.createElement("button");
  button.type = "button";
  button.classList.add("control-icon");
  button.dataset.tooltip = game.i18n.localize("FORJA.HUD.SecondWind");
  button.innerHTML = '<i class="fa-solid fa-heart-pulse"></i>';
  button.addEventListener("click", () => token.actor.secondWind());
  html.querySelector(".col.right")?.append(button);
});
```

## Canvas hooks you will use

| Hook | Arguments | When |
|---|---|---|
| `canvasInit` | `(canvas)` | a scene starts loading |
| `canvasReady` | `(canvas)` | the scene is drawn and interactive |
| `drawToken` / `refreshToken` | `(token, flags)` | a token is drawn or redrawn |
| `controlToken` | `(token, controlled)` | a token is selected or released |
| `hoverToken` | `(token, hovered)` | the mouse enters or leaves a token |
| `targetToken` | `(user, token, targeted)` | a user targets a token |
| `updateToken` | document hook | token data changed (position, elevation…) |

```js
Hooks.on("controlToken", (token, controlled) => {
  if ( controlled ) console.log("forja | selected", token.name, token.document.uuid);
});
```

## Customize movement measurement

V13 introduced drag measurement with waypoints. You can style the ruler by subclassing the token ruler and registering it:

```js
const { TokenRuler } = foundry.canvas.placeables.tokens;

class ForjaTokenRuler extends TokenRuler {
  /** Color each segment by the movement action (walk, fly…). */
  _getSegmentStyle(waypoint) {
    const style = super._getSegmentStyle(waypoint);
    if ( waypoint.action === "fly" ) style.color = 0x80a6e6;
    return style;
  }
}

Hooks.once("init", () => {
  CONFIG.Token.rulerClass = ForjaTokenRuler;
});
```

::: v14
`TokenRuler#_getWaypointStyle` lets you choose waypoint symbols (circle, square, diamond, triangle and hexagon variants). Intermediate waypoints are now included in the rendered path.
:::

For the movement rules themselves (cost, actions, planned movement), see [Scenes and Tokens](#scene-token) and [Regions](#regions).

## Visual effects

::: v13
V13 has no general VFX API. Use `CanvasAnimation` (`foundry.canvas.animation.CanvasAnimation`) to tween properties, or a PIXI container in your own layer.

```js
const { CanvasAnimation } = foundry.canvas.animation;
await CanvasAnimation.animate([{ parent: token.mesh, attribute: "alpha", to: 0.2 }], { duration: 300 });
await CanvasAnimation.animate([{ parent: token.mesh, attribute: "alpha", to: 1 }], { duration: 300 });
```
:::

::: v14
V14 adds three tools for visual feedback:

- **`foundry.canvas.vfx`**: timeline-driven animations on the canvas. The anime.js library it uses is exposed as `globalThis.animejs`.
- **`ParticleGenerator`**: lightweight particles (sparks, dust, embers) with randomized rotation and an `onUpdate` callback.
- **`CanvasShakeEffect`** (`foundry.canvas.animation`): a screen shake for impact moments. It shakes the scene but not the UI or particles.

These APIs are new. Read their pages in the [V14 API](https://foundryvtt.com/api/v14/) for constructor options before building on them, and keep effects optional with a client setting: some players get motion sickness.
:::

## Pitfalls

- **Drawing in `init`**: the canvas does not exist yet. Draw in `canvasReady` or in your layer's `_draw`.
- **Forgetting cleanup**: PIXI objects you add outside a layer survive scene changes. Destroy them in `canvasTearDown`, or keep them inside a layer so the core cleans them up.
- **Using documents for pure visuals**: creating a `Drawing` for every aura writes to the database on every change. Draw in a layer instead.
