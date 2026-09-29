# What changed in V14

Every developer-facing change from V13 to V14 that affects modules and systems, grouped by area, with what to do about it.

## At a glance

V14 became stable with build **14.359** on April 1, 2026. The latest build covered here is **14.368** (September 16, 2026). V14 **cannot be updated in place** from V13: users reinstall Foundry and keep their data folder.

| Area | Headline | Impact on your code |
|---|---|---|
| Scenes | **Scene Levels**: one scene stacks several levels at different elevations | Vision, walls, lights and movement are level-aware |
| Active Effects | **Active Effects V2**: `system.changes`, string types, phases, new durations, expiry events | <span class="pill break">breaking</span> for any system that reads or writes effects |
| Templates | `MeasuredTemplate` removed; **Template Regions** replace it | <span class="pill break">breaking</span> for AoE code |
| Chat | **Message Visibility Modes** replace Roll Modes | <span class="pill dep">deprecated</span> until V16 |
| Data | `template.json` enters deprecation; use data models | <span class="pill dep">deprecated</span> |
| UI | Pop-out windows, Placeables Palette, Placeables sidebar tab | <span class="pill new">new</span> |
| Visuals | VFX framework, particles, screen shake, scene transitions | <span class="pill new">new</span> |
| Performance | Core data structures 3%–25% faster on common operations | none |

Legend: <span class="pill break">breaking</span> code stops working · <span class="pill dep">deprecated</span> still works with a warning · <span class="pill rename">renamed</span> same feature, new name · <span class="pill new">new</span> new API

## Migration checklist

Work through this list when you port a package. Each item links to the page that shows the new code.

1. Set `compatibility.minimum` / `verified` to `14` in the manifest, and optionally add `"type": "system"` or `"type": "module"`. [Manifest](#manifest)
2. Replace `template.json` with `documentTypes` + `TypeDataModel` classes. [Data models](#data-models)
3. Move effect changes from `effect.changes` to `effect.system.changes`, and `mode` numbers to `type` strings. [Active Effects](#active-effect)
4. Convert effect durations to `{ value, units, expiry }`. [Active Effects](#active-effect)
5. Replace `MeasuredTemplate` code with Regions. [Regions](#regions)
6. Replace `rollMode` with `messageMode`, and `applyRollMode` with `applyMode`. [Chat and rolls](#chat-roll)
7. Replace `-=key` / `==key` update keys with `DataFieldOperator` values. [Documents](#documents)
8. Search your code for the removed and renamed names in the tables below. [Migrations](#migrations)

## Scenes, Levels and the canvas

| Change | Type | What to do |
|---|---|---|
| **Scene Levels**: a Scene holds several `Level`s (background/foreground images at an elevation). `Level` is a global class. | <span class="pill new">new</span> | Make canvas code level-aware. [Scenes and Tokens](#scene-token) |
| `Level#background`, `#foreground`, `#fog` are non-nullable; `Level#edges` holds the level's `CanvasEdges`. | <span class="pill new">new</span> | |
| Edge management moved from `Wall` to `WallDocument`; `WallDocument#isDoor`, `#isOpen`. | <span class="pill rename">moved</span> | Read door state from the document. |
| Line of sight can be satisfied in the viewed level or the token's level. | <span class="pill break">behavior</span> | Retest custom detection modes. |
| `Scene#getSurfaces`, `Scene#testSurfaceCollision` (with `side`, `tMin`, `tMax`), `BaseEffectSource#level`. | <span class="pill new">new</span> | |
| `SceneManager#_determineInitialLevel`; `CONFIG.Canvas.managedScenes` accepts `SceneManager` instances. | <span class="pill new">new</span> | |
| `Scene#activate({ viewOptions, pullUsers })`, `Scene#pullUsers(viewOptions)`; 14 animated scene transitions. | <span class="pill new">new</span> | |
| `ready` hook fires **after** scene transitions finish. | <span class="pill break">behavior</span> | Don't assume the canvas is idle earlier. |
| `layerClass` in Canvas Document CONFIG is deprecated; layer options live on `PlaceablesLayer`. | <span class="pill dep">deprecated</span> | [Canvas](#canvas-controls) |
| `PlaceableObject#clear` → protected `PlaceableObject#_clear`. | <span class="pill dep">deprecated</span> | |
| `PlaceableObject#isInteractable`; locked placeables (except Tokens) are not interactable. | <span class="pill new">new</span> | |
| `SceneControls#tool` and `game.activeTool` can be `null`. | <span class="pill break">behavior</span> | Guard with `?.`. |
| `SceneControlTool` adds `interaction`, `control`, `creation`, `shapeData`. | <span class="pill new">new</span> | [Canvas](#canvas-controls) |
| `ClockwiseSweepPolygonConfig#edgeOptions` → `#edgeTypes`; new `CONST.EDGE_SENSE_TYPES`, `EDGE_RESTRICTION_TYPES`, `EDGE_DIRECTIONS`, `EDGE_DIRECTION_MODES`. | <span class="pill dep">deprecated</span> | |
| `Scene#gridlessGrid`; `BaseGrid#getRectangle`, `#getLine`, `#getEllipse`. | <span class="pill new">new</span> | |
| Tiles: `anchorX` / `anchorY`; the mesh position equals `(x, y)`. `Tile.createPreview` deprecated. | <span class="pill break">behavior</span> | Recheck tile placement math. |
| `foundry.canvas.vfx`, `ParticleGenerator`, `animation.CanvasShakeEffect`, `globalThis.animejs`. | <span class="pill new">new</span> | [Canvas](#canvas-controls) |
| Adaptive and Natural light attenuation techniques. | <span class="pill new">new</span> | |

## Tokens and movement

| Change | Type | What to do |
|---|---|---|
| Planned movement: `token.planMovement(options)`, `TokenDocument#startMovement`, `TokenMovementOptions#planned`, `planToken` hook. | <span class="pill new">new</span> | [Scenes and Tokens](#scene-token) |
| `Scene#moveTokens`, `TokenLayer#placeTokens`, explicit movement IDs. | <span class="pill new">new</span> | |
| `TokenDocument#move` resolves when the whole movement finishes; `TokenMovementData#finished`. | <span class="pill break">behavior</span> | Code awaiting `move` now waits longer. |
| `TokenDocument#depth`, `getMovementOrigin`, `getVisionOrigin`, `getLightOrigin`, `getSoundOrigin`, `getListenerPosition`. | <span class="pill new">new</span> | |
| `TokenFindMovementPathOptions`: `ignoreWalls`, `ignoreCost`, `history` → `constrainOptions`. | <span class="pill dep">deprecated</span> | |
| `TokenMovementActionConfig#getAnimationOptions(token)` now receives a `TokenDocument`. | <span class="pill break">breaking</span> | Update custom movement actions. |
| `TokenDocument#detectionModes` is a `TypedObjectField`. | <span class="pill break">breaking</span> | Access modes by id, not by array index. |
| `TokenDocument#getTestPoints` respects walls and surfaces; `getOccupiedGridSpaceOffsets` too. | <span class="pill break">behavior</span> | |
| Actor `tokenOverrides`: Active Effects can change token vision, light, image, alpha, disposition, size and shape. | <span class="pill new">new</span> | [Actors](#actor) |
| `TokenRuler#_getWaypointStyle`; intermediate waypoints are drawn. | <span class="pill new">new</span> | |
| `ActorDelta` can be `null`; `TokenDocument#_initializeSource` ignores `delta` when `actorLink` is true. | <span class="pill break">behavior</span> | Null-check `token.delta`. |

## Active Effects V2

| Change | Type | What to do |
|---|---|---|
| `ActiveEffect#changes` → `ActiveEffect#system#changes`. | <span class="pill break">breaking</span> | [Active Effects](#active-effect) |
| Change `mode` (number) → `type` (string): `custom`, `multiply`, `add`, `subtract`, `downgrade`, `upgrade`, `override` (`CONST.ACTIVE_EFFECT_CHANGE_TYPES`). | <span class="pill break">breaking</span> | |
| Change `phase`: `initial`, `final` (`CONST.ACTIVE_EFFECT_CHANGE_PHASES`); packages can add phases and apply them with `Actor#applyActiveEffects(phase)`. | <span class="pill new">new</span> | |
| `EffectChangeData#value` is deserialized (JSON value or string). | <span class="pill break">behavior</span> | Don't assume a string. |
| Duration is `{ value, units, expiry, expired }`; units in `CONST.ACTIVE_EFFECT_DURATION_UNITS`. | <span class="pill break">breaking</span> | |
| Expiry events `combatStart`, `roundStart`, `turnStart`, `combatEnd`, `roundEnd`, `turnEnd` (`CONST.ACTIVE_EFFECT_EXPIRY_EVENTS`). | <span class="pill new">new</span> | [Combat](#combat) |
| `ActiveEffect.registry` tracks temporary effects. | <span class="pill new">new</span> | |
| Active Effects are **primary documents**: sidebar, compendiums, drop on a Token to apply. | <span class="pill new">new</span> | |
| `ActiveEffect#origin` is a `DocumentUUIDField`. | <span class="pill break">breaking</span> | Store a UUID only. |
| `CONFIG.ActiveEffect.legacyTransferral` **removed**. | <span class="pill break">breaking</span> | |
| `CONFIG.statusEffects` is an object `{ [id]: config }` (arrays still accepted). | <span class="pill dep">deprecated</span> | |
| "Active Effect" Region behavior applies effects to tokens in a region. | <span class="pill new">new</span> | [Regions](#regions) |

## Regions and templates

| Change | Type | What to do |
|---|---|---|
| `MeasuredTemplate` document type **removed**; its features moved to Regions. | <span class="pill break">breaking</span> | [Regions](#regions) |
| New shapes: line, cone, `RingShapeData`, `EmanationShapeData`, `TokenShapeData`, `GridShapeData`; grid-based mode. | <span class="pill new">new</span> | |
| Regions attach to tokens: `RegionDocument#attachment.token`; `RegionDocument.createTokenEmanation()`. | <span class="pill new">new</span> | |
| `RegionLayer#placeRegion` / `placeRegions` (`attachToToken`, `onChange`, `allowEmpty`); `index`/`count` → `shapeIndex`/`shapeCount`. | <span class="pill new">new</span> | |
| `RegionDocument#teleportTokens`, `#spawnTokens` (`avoidOccupied`, `{ create: false }`). | <span class="pill new">new</span> | |
| Region ownership field and `REGION_CREATE` permission; restriction type and priority. | <span class="pill new">new</span> | |
| Default `visibility` of non-template Regions is `LAYER_UNLOCKED`. | <span class="pill break">behavior</span> | |
| `RegionShape` → `BaseShapeData` mixins; `foundry.data.regionShapes.RegionPolygonTree` → `foundry.data.PolygonTree`. | <span class="pill rename">renamed</span> | |

## Documents and data

| Change | Type | What to do |
|---|---|---|
| `template.json` enters deprecation. | <span class="pill dep">deprecated</span> | [Data models](#data-models) |
| Manifest: optional `"type": "system" \| "module"`. | <span class="pill new">new</span> | [Manifest](#manifest) |
| `updateSource` keys `-=` / `==` → `DataFieldOperator` values. | <span class="pill dep">deprecated</span> | [Documents](#documents) |
| `DataModel#_updateDiff`, `#_updateCommit`; validation moved into `_updateDiff`. | <span class="pill break">behavior</span> | |
| `SchemaField#extendFields`, `#removeFields`; `DataModel#getFieldForProperty`; `DataField#placeholder`. | <span class="pill new">new</span> | |
| `Document.create` uses `this.implementation`; `Document#persisted`; relative UUIDs (`buildRelativeUuid`). | <span class="pill new">new</span> | |
| Document metadata controls whether the base type can be created. | <span class="pill new">new</span> | |
| `TypeDataModel#onEmbed` (HTML embeds). | <span class="pill new">new</span> | |
| `DocumentCollection#importDocument` keeps IDs; batch writes across collections. | <span class="pill new">new</span> | [Compendium](#compendium) |
| `DocumentStatsField#createdTime` / `modifiedTime` are required; `MacroData#author` nullable. | <span class="pill break">behavior</span> | |
| `foundry.utils.equals()` replaces `objectsEqual`; `isPlainObject`; `diffObject(…, { bidirectional })`; `debounce().cancel()`. | <span class="pill rename">renamed</span> | [API map](#api-map) |
| `RegExp.escape` polyfill removed (native is used). | <span class="pill break">breaking</span> | |
| `Collection` uses native iterator helpers. | <span class="pill new">new</span> | |
| `User.queryMany`; query handlers get the sender. | <span class="pill new">new</span> | [Sockets](#sockets) |
| Large batch of V12 deprecations removed. | <span class="pill break">breaking</span> | Fix all V12 deprecation warnings first. |

## Chat, dice and localization

| Change | Type | What to do |
|---|---|---|
| Roll Modes → Message Visibility Modes (`public`, `self`, `gm`, `blind`) plus In-Character mode. | <span class="pill dep">deprecated</span> until V16 | [Chat and rolls](#chat-roll) |
| `ChatMessage.applyRollMode` → `ChatMessage.applyMode`; `toMessage({ rollMode })` → `{ messageMode }`. | <span class="pill rename">renamed</span> | |
| `ChatLog.MESSAGE_PATTERNS` → `ChatLog.CHAT_COMMANDS`. | <span class="pill dep">deprecated</span> until V16 | |
| Booleans in roll data evaluate as `0`/`1`; `Roll.replaceFormulaData` uses custom `toString()`. | <span class="pill break">behavior</span> | |
| `game.i18n.localize(key, data)` merges `format()`; global `_loc`. | <span class="pill new">new</span> | [Localization](#localization) |

## Applications and UI

| Change | Type | What to do |
|---|---|---|
| ApplicationV2 **pop-out windows**; `ApplicationV2.instances` generator. | <span class="pill new">new</span> | [ApplicationV2](#applicationv2) |
| `HeaderControls` and `ContextMenu` unified; `ContextMenuEntry#icon` accepts class names. | <span class="pill break">behavior</span> | |
| `_canRender` receives first-render status; middle-click (`auxclick`) support. | <span class="pill new">new</span> | |
| TinyMCE removed; `foundry.prosemirror.defaultPlugins` → `ProseMirrorEditor.buildDefaultPlugins()`. | <span class="pill break">breaking</span> | [Journal](#journal) |
| ProseMirror: details, tables, font size/color, captions, `inline`/`block` HTML templates. | <span class="pill new">new</span> | |
| `CONFIG[documentName].embedHandlers`. | <span class="pill new">new</span> | |
| `HTMLFormulaInputElement`, `FormulaEditor`, `Autocompletion`. | <span class="pill new">new</span> | [Sheets](#sheets) |
| `parseHTML` returns `null` on failure. | <span class="pill break">behavior</span> | |
| `<code>` inline by default (`block` class for blocks). | <span class="pill break">behavior</span> | [Styling](#styling) |
| `highlightElement(element, options)` helper. | <span class="pill new">new</span> | |
| Font Awesome 7.2. | <span class="pill break">behavior</span> | |

## Packages and permissions

| Change | Type | What to do |
|---|---|---|
| World packages can no longer be installed from Setup; use Adventure documents. | <span class="pill break">breaking</span> | [Packaging](#packaging) |
| CSS hot reload follows `@import`; hot reload render receives the file. | <span class="pill new">new</span> | [Setup](#setup) |
| Adventure imports are recorded in the `core.adventureImports` setting. | <span class="pill new">new</span> | |
| Assistant GMs gain more permissions (not `FILES_UPLOAD`, `MACRO_SCRIPT`, `SETTINGS_MODIFY`). | <span class="pill break">behavior</span> | Recheck `isGM` vs role checks. |

## Sources

- Release notes: [14.349](https://foundryvtt.com/releases/14.349), [14.352](https://foundryvtt.com/releases/14.352), [14.353](https://foundryvtt.com/releases/14.353), [14.354](https://foundryvtt.com/releases/14.354), [14.355](https://foundryvtt.com/releases/14.355), [14.356](https://foundryvtt.com/releases/14.356), [14.357](https://foundryvtt.com/releases/14.357), [14.358](https://foundryvtt.com/releases/14.358), [14.359 (stable)](https://foundryvtt.com/releases/14.359)
- [V14 API documentation](https://foundryvtt.com/api/v14/)
