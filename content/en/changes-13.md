# What changed in V13

The developer-facing changes from V12 to V13: the move to ApplicationV2, namespaced classes, the new theme, and token movement.

## At a glance

V13 became stable with build **13.341** on April 27, 2025. The latest V13 build is **13.351** (November 12, 2025). V13 requires Node.js 20 (22 is supported) and ships Electron 33.

| Area | Headline | Impact on your code |
|---|---|---|
| Applications | **All core apps use ApplicationV2**; default actor/item sheets removed | <span class="pill break">breaking</span> for systems without their own sheets |
| Namespaces | Most globals moved to `foundry.*` ES modules | <span class="pill dep">deprecated</span> globals until V15 |
| Theme | **Theme V2** with light/dark and CSS cascade layers | Restyle your sheets |
| Scene controls | `controls` is an object, not an array | <span class="pill break">breaking</span> |
| Tokens | Drag measurement, waypoints, movement actions, movement API | <span class="pill new">new</span> |
| Settings | New `user` scope | <span class="pill new">new</span> |
| jQuery | Deprecation starts; hooks pass `HTMLElement` | Stop using `html.find` |

Legend: <span class="pill break">breaking</span> code stops working · <span class="pill dep">deprecated</span> still works with a warning · <span class="pill rename">renamed</span> same feature, new name · <span class="pill new">new</span> new API

## Migration checklist (V12 → V13)

1. Register your own actor and item sheets. The core no longer registers default sheets, so a system without them shows no sheet at all. [Sheets](#sheets)
2. Port sheets and dialogs from Application (V1) to ApplicationV2. [ApplicationV2](#applicationv2)
3. Replace globals with their `foundry.*` paths to silence deprecation warnings (they are removed in V15). [API map](#api-map)
4. Rewrite `getSceneControlButtons` for the record structure. [Canvas](#canvas-controls)
5. Replace jQuery in render hooks (`html.find`, `html.on`) with DOM APIs.
6. Check chat code: roll modes are only applied in `_preCreate` when `options.rollMode` is set. [Chat and rolls](#chat-roll)
7. Restyle for Theme V2 and test in light and dark. [Styling](#styling)

## Applications and UI

| Change | Type | What to do |
|---|---|---|
| All core applications migrated from AppV1 to ApplicationV2. | <span class="pill break">breaking</span> | Hooks now receive AppV2 instances and `HTMLElement`. |
| Default actor and item sheet registrations removed (no AppV1 fallback). | <span class="pill break">breaking</span> | [Sheets](#sheets) |
| `ApplicationV2#submit` returns the form handler's value. | <span class="pill new">new</span> | |
| `options.window.contentTag` to bind the content element to a form. | <span class="pill new">new</span> | |
| `static TABS` and `_prepareTabs(group)` for tab groups. | <span class="pill new">new</span> | [ApplicationV2](#applicationv2) |
| Hook `getHeaderControls{ApplicationClassName}(app, controls)`. | <span class="pill new">new</span> | |
| `HandlebarsApplicationMixin` parts accept `root: true`. | <span class="pill new">new</span> | |
| `DocumentSheetV2` action `editImage`; `ActorSheetV2` drag-and-drop framework. | <span class="pill new">new</span> | |
| `.theme-dark` / `.theme-light` classes on AppV2; AppV1 gets `.theme-light`. | <span class="pill new">new</span> | [Styling](#styling) |
| CSS cascade layers for all core styles. | <span class="pill break">behavior</span> | |
| `SceneControls#controls` is a record; affects `getSceneControlButtons`. | <span class="pill break">breaking</span> | [Canvas](#canvas-controls) |
| `ClientDocument.createDialog` / `deleteDialog` accept `DatabaseOperation` parameters. | <span class="pill new">new</span> | [Dialogs](#dialogs) |
| `progress` notification type; `Notifications#displayProgressBar` deprecated. | <span class="pill dep">deprecated</span> | |
| `Notifications#notify` accepts a `format` object. | <span class="pill new">new</span> | |
| `HTMLCodeMirrorElement` for JSON/HTML/JavaScript editing. | <span class="pill new">new</span> | |
| `CONFIG.ChatMessage.popoutClass`. | <span class="pill new">new</span> | |
| jQuery deprecation begins. | <span class="pill dep">deprecated</span> | |

## Namespaces

Many classes moved to ES modules under `foundry.<group>`. The old global names still work in V13 and V14 with a deprecation warning and are removed in V15.

| Old global | V13 path |
|---|---|
| `ActorSheet` (V1) | `foundry.appv1.sheets.ActorSheet` (legacy; use `foundry.applications.sheets.ActorSheetV2`) |
| `DocumentSheetConfig` | `foundry.applications.apps.DocumentSheetConfig` |
| `Actors`, `Items` | `foundry.documents.collections.Actors`, `foundry.documents.collections.Items` |
| `loadTemplates`, `renderTemplate` | `foundry.applications.handlebars.loadTemplates`, `…renderTemplate` |
| `TextEditor` | `foundry.applications.ux.TextEditor.implementation` |
| `DragDrop`, `ContextMenu` | `foundry.applications.ux.DragDrop`, `foundry.applications.ux.ContextMenu` |
| `Token`, `Tile`, `Wall`… | `foundry.canvas.placeables.Token`, … |
| `TokenLayer`, `PlaceablesLayer`, `InteractionLayer` | `foundry.canvas.layers.*` |
| `CanvasAnimation`, `Ray`, `MouseInteractionManager` | `foundry.canvas.animation.CanvasAnimation`, `foundry.canvas.geometry.Ray`, `foundry.canvas.interaction.MouseInteractionManager` |

See the full table in the [API map](#api-map). When in doubt, type the class name in the console: the deprecation warning prints the new path.

## Documents and data

| Change | Type | What to do |
|---|---|---|
| New `user` setting scope (per user, synced across devices). | <span class="pill new">new</span> | [Settings](#settings) |
| `Symbol` is no longer allowed as a setting type. | <span class="pill break">breaking</span> | |
| Roll modes are applied in `ChatMessage#_preCreate` only with `options.rollMode`; `ChatMessage.applyRollMode` keeps existing whisper recipients. | <span class="pill break">behavior</span> | [Chat and rolls](#chat-roll) |
| `appendNumber` and `prependAdjective` moved from Token to PrototypeToken. | <span class="pill break">breaking</span> | |
| `DocumentOwnershipField` uses `gmOnly`; new `DocumentAuthorField` for `ChatMessage#author`, `Macro#author`, `Drawing#author`. | <span class="pill break">behavior</span> | |
| `ServerDocument#testUserPermission` overrides removed; use `getUserLevel`. | <span class="pill break">breaking</span> | |
| `NumberField#toInput` no range picker for nullable fields; `step` matches HTML. | <span class="pill break">behavior</span> | |
| `PlaylistSound#channel` initial value is `""`. | <span class="pill break">behavior</span> | |
| `StringField._getChoices` → `StringField._prepareChoiceConfig`. | <span class="pill rename">renamed</span> | |
| `MACRO_SCRIPT` permission restricts creating script macros, not running them. | <span class="pill break">behavior</span> | |
| `prepareData` no longer runs twice for owned item updates. | <span class="pill break">behavior</span> | |
| `foundry.utils.deepFreeze`, `deepSeal`; `User#isActiveGM`; `Users#getDesignatedUser`, `User#isDesignated`. | <span class="pill new">new</span> | [Sockets](#sockets) |
| User queries: `CONFIG.queries` + `User#query`. | <span class="pill new">new</span> | [Sockets](#sockets) |
| `CalendarData#add`; `Combat#_onEnter`, `Combat#_onExit`. | <span class="pill new">new</span> | |
| `Roll#_prepareChatRenderContext` is protected and overridable; `Roll#render` gets the `ChatMessage`. | <span class="pill new">new</span> | [Chat and rolls](#chat-roll) |

## Canvas and tokens

| Change | Type | What to do |
|---|---|---|
| Token drag measurement with waypoints, elevation and movement actions (`CONFIG.Token.movement`). | <span class="pill new">new</span> | [Scenes and Tokens](#scene-token) |
| `TokenDocument#move`, `measureMovementPath`, `getDirectMovementPath`, `stopMovement`, `pauseMovement`, `continueMovement`, `movementHistory`, `clearMovementHistory`. | <span class="pill new">new</span> | |
| `Token#findMovementPath`, `constrainMovementPath`, `_getMovementCostFunction`. | <span class="pill new">new</span> | |
| `TokenDocument#getSnappedPosition`, `getCenterPoint`, `getGridSpacePolygon`, `getOccupiedGridSpaceOffsets`. | <span class="pill new">new</span> | |
| `Token#getSize` → `TokenDocument#getSize`; `Token#testInsideRegion` → `TokenDocument#testInsideRegion`; `Token#segmentizeRegionMovement` → `TokenDocument#segmentizeRegionMovementPath`. | <span class="pill dep">deprecated</span> | |
| `ElevatedPoint` `{ x, y, elevation }`; grid coordinates accept elevation. | <span class="pill new">new</span> | |
| `Token#animate` gets `chain`; `CONFIG.Token.movement.defaultSpeed`. | <span class="pill new">new</span> | |
| Region behavior **Modify Movement Cost**; `RegionDocument#teleportToken`; `CONST.REGION_MOVEMENT_SEGMENTS`. | <span class="pill new">new</span> | [Regions](#regions) |
| `TextureExtractor#extract` returns `{ pixels, width, height, out }`. | <span class="pill break">breaking</span> | |
| Light priority, sound-reactive lights, animated doors, combat turn markers. | <span class="pill new">new</span> | [Combat](#combat) |
| `PlaceableObject.implementation`, `foundry.utils.getPlaceableObjectClass`. | <span class="pill new">new</span> | |
| `FogManager#isPointExplored`; `BasePointSource#testPoint`. | <span class="pill new">new</span> | |

## Sources

- Release notes: [13.332](https://foundryvtt.com/releases/13.332), [13.341 (stable)](https://foundryvtt.com/releases/13.341), [all V13 releases](https://foundryvtt.com/releases/)
- [V13 API documentation](https://foundryvtt.com/api/v13/)
