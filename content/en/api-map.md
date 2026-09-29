# API cheat sheet

A quick "I want to… → use this" reference for the Foundry APIs you reach for every day, in V13 and V14.

::: changed
- `foundry.utils.objectsEqual` → `foundry.utils.equals`; `game.i18n.localize` now accepts data (plus the `_loc` alias).
- `ActiveEffect#changes` → `effect.system.changes`; `CONFIG.statusEffects` is an object.
- `MeasuredTemplate` removed (use Regions); `rollMode` → `messageMode`; `MESSAGE_PATTERNS` → `CHAT_COMMANDS`.
- `User.queryMany` added. See [the full changelog](#changes-14).
:::

## Namespaces: old globals → V13+ paths

V13 moved most classes into `foundry.*` namespaces. The old globals still work (with a
deprecation warning) until V15, so new code should always use the namespaced path. Document
classes (`Actor`, `Item`, `ChatMessage`, `Roll`…) remain valid globals.

| Old global | Namespaced path (V13 and V14) |
| --- | --- |
| `Application` | `foundry.appv1.api.Application` (legacy — prefer ApplicationV2) |
| `FormApplication` | `foundry.appv1.api.FormApplication` (legacy) |
| `Dialog` | `foundry.appv1.api.Dialog` (legacy — prefer `DialogV2`) |
| `ActorSheet` / `ItemSheet` | `foundry.appv1.sheets.ActorSheet` / `ItemSheet` (legacy) |
| — | `foundry.applications.api.ApplicationV2` |
| — | `foundry.applications.api.HandlebarsApplicationMixin` |
| — | `foundry.applications.api.DialogV2` |
| — | `foundry.applications.api.DocumentSheetV2` |
| — | `foundry.applications.sheets.ActorSheetV2` / `ItemSheetV2` |
| `DocumentSheetConfig` | `foundry.applications.apps.DocumentSheetConfig` |
| `FilePicker` | `foundry.applications.apps.FilePicker` |
| `TextEditor` | `foundry.applications.ux.TextEditor.implementation` |
| `DragDrop` | `foundry.applications.ux.DragDrop` |
| `ContextMenu` | `foundry.applications.ux.ContextMenu` |
| `loadTemplates` / `renderTemplate` | `foundry.applications.handlebars.loadTemplates` / `renderTemplate` |
| `Actors` / `Items` | `foundry.documents.collections.Actors` / `Items` |
| `CompendiumCollection` | `foundry.documents.collections.CompendiumCollection` |
| `ChatLog` | `foundry.applications.sidebar.tabs.ChatLog` |
| `Token` | `foundry.canvas.placeables.Token` |
| `TokenLayer` | `foundry.canvas.layers.TokenLayer` |
| `ClientSettings` | `foundry.helpers.ClientSettings` |

::: tip
Not sure where something lives? In the browser console, type `foundry.` and let autocomplete
guide you, or search the [V13 API](https://foundryvtt.com/api/v13/) /
[V14 API](https://foundryvtt.com/api/v14/). A deprecation warning in the console also prints the new path.
:::

## CONFIG keys you will touch

| I want to… | Key | Example |
| --- | --- | --- |
| Use my own Actor class | `CONFIG.Actor.documentClass` | `CONFIG.Actor.documentClass = ForjaActor` |
| Define actor types' data | `CONFIG.Actor.dataModels` | `CONFIG.Actor.dataModels.character = CharacterData` |
| Choose token bar attributes | `CONFIG.Actor.trackableAttributes` | `{ character: { bar: ["hp"], value: ["might"] } }` |
| Use my own Item class | `CONFIG.Item.documentClass` | `CONFIG.Item.documentClass = ForjaItem` |
| Define item types' data | `CONFIG.Item.dataModels` | `CONFIG.Item.dataModels.weapon = WeaponData` |
| Set the initiative formula | `CONFIG.Combat.initiative` | `{ formula: "1d20 + @might", decimals: 2 }` |
| Register a custom Roll class | `CONFIG.Dice.rolls` | `CONFIG.Dice.rolls.push(ForjaRoll)` |
| Replace status conditions | `CONFIG.statusEffects` | see below |
| Add inline text enrichers | `CONFIG.TextEditor.enrichers` | `push({ pattern, enricher })` |
| Handle user queries | `CONFIG.queries` | `CONFIG.queries["forja.applyDamage"] = fn` |
| Add token movement actions | `CONFIG.Token.movement.actions` | `CONFIG.Token.movement.actions.fly = {...}` |
| Add a Region behavior type | `CONFIG.RegionBehavior.dataModels` | `CONFIG.RegionBehavior.dataModels["forja.trap"] = TrapBehavior` |

```js
// systems/forja/forja.mjs
Hooks.once("init", () => {
  CONFIG.Actor.documentClass = ForjaActor;
  CONFIG.Actor.dataModels = { character: CharacterData, npc: NpcData };
  CONFIG.Actor.trackableAttributes = {
    character: { bar: ["hp"], value: ["might"] },
    npc: { bar: ["hp"], value: [] }
  };
  CONFIG.Item.documentClass = ForjaItem;
  CONFIG.Item.dataModels = { weapon: WeaponData, spell: SpellData };
  CONFIG.Combat.initiative = { formula: "1d20 + @might", decimals: 2 };

  // [[/dano 2d6]] → a clickable damage link
  CONFIG.TextEditor.enrichers.push({
    pattern: /\[\[\/dano (?<formula>[^\]]+)\]\]/gi,
    enricher: async (match) => {
      const a = document.createElement("a");
      a.classList.add("forja-damage");
      a.dataset.formula = match.groups.formula;
      a.textContent = match.groups.formula;
      return a;
    }
  });
});
```

### Status effects

::: v13
`CONFIG.statusEffects` is an **array** of `{ id, name, img }`.

```js
CONFIG.statusEffects = [
  { id: "dead", name: "FORJA.StatusDead", img: "icons/svg/skull.svg" },
  { id: "stunned", name: "FORJA.StatusStunned", img: "icons/svg/daze.svg" }
];
```
:::

::: v14
`CONFIG.statusEffects` is an **object** keyed by id (arrays are still accepted for compatibility).

```js
CONFIG.statusEffects = {
  dead: { id: "dead", name: "FORJA.StatusDead", img: "icons/svg/skull.svg" },
  stunned: { id: "stunned", name: "FORJA.StatusStunned", img: "icons/svg/daze.svg" }
};
```
:::

## game.* objects

| Object | What it is | Typical use |
| --- | --- | --- |
| `game.actors` | World Actors collection | `game.actors.getName("Goblin")` |
| `game.items` | World Items collection | `game.items.filter((i) => i.type === "weapon")` |
| `game.packs` | All compendiums | `game.packs.get("forja.monsters")` |
| `game.settings` | Settings registry | `game.settings.get("forja", "systemMigrationVersion")` |
| `game.i18n` | Localization | `game.i18n.localize("FORJA.Attack")` |
| `game.user` | The current user | `game.user.isGM`, `game.user.isActiveGM`, `game.user.targets` |
| `game.users` | All users | `game.users.activeGM`, `game.users.filter((u) => u.active)` |
| `game.socket` | Socket.io client | `game.socket.emit("system.forja", data)` — see [sockets](#sockets) |
| `game.system` | The active system package | `game.system.id`, `game.system.version` |
| `game.modules` | All installed modules | `game.modules.get("forja-extras")?.active` |
| `game.release` | Core release info | `game.release.generation` (13 or 14), `game.version` |

## foundry.utils helpers

| Helper | What it does |
| --- | --- |
| `mergeObject(original, other, options)` | Deep merge; returns `original` (mutated) unless `{ inplace: false }` |
| `deepClone(obj)` | Deep copy that keeps Dates, Sets and class instances sane |
| `duplicate(obj)` | JSON round-trip copy (loses functions/Dates) — prefer `deepClone` |
| `getProperty(obj, "a.b.c")` | Read a dotted path |
| `setProperty(obj, "a.b.c", v)` | Write a dotted path; returns `true` if changed |
| `expandObject({ "a.b": 1 })` | `{ a: { b: 1 } }` — form data to nested object |
| `flattenObject({ a: { b: 1 } })` | `{ "a.b": 1 }` — nested object to update keys |
| `randomID(length = 16)` | Random document-style id |
| `isNewerVersion(v1, v0)` | `true` if `v1` is newer than `v0` |
| `debounce(fn, ms)` | Delay calls until `ms` of quiet |
| `isEmpty(value)` | `true` for `undefined`, `{}`, `[]` and empty Sets/Maps |

::: v13
- Deep equality: `foundry.utils.objectsEqual(a, b)`.
- `debounce` returns a plain function.
:::

::: v14
- Deep equality: `foundry.utils.equals(a, b)` (replaces `objectsEqual`).
- `debounce(fn, ms).cancel()` cancels a pending call.
- New: `foundry.utils.isPlainObject`, `diffObject(a, b, { bidirectional: true })`, `buildRelativeUuid`.
:::

```js
const { mergeObject, getProperty, expandObject, isNewerVersion } = foundry.utils;

const defaults = { hp: { value: 10, max: 10 }, might: 1 };
const data = mergeObject(defaults, { hp: { value: 4 } }, { inplace: false });
getProperty(data, "hp.value"); // 4
expandObject({ "system.hp.value": 3 }); // { system: { hp: { value: 3 } } }
isNewerVersion("2.1.0", "2.0.9"); // true
```

## V13 → V14: renamed and replaced

| I want to… | V13 | V14 |
| --- | --- | --- |
| Read effect changes | `effect.changes` | `effect.system.changes` |
| Change operation | `mode: CONST.ACTIVE_EFFECT_MODES.ADD` (number) | `type: "add"` (string) |
| Effect duration | `{ rounds, turns, seconds, … }` | `{ value, units, expiry, expired }` |
| Area templates | `MeasuredTemplate` | Scene Regions (cone, line, ring, emanation shapes) |
| Region shape classes | `RegionShape` | `BaseShapeData` |
| Region polygon tree | `foundry.data.regionShapes.RegionPolygonTree` | `foundry.data.PolygonTree` |
| Roll privacy | `roll.toMessage(data, { rollMode })` | `roll.toMessage(data, { messageMode })` |
| Apply a mode to chat data | `ChatMessage.applyRollMode(data, mode)` | `ChatMessage.applyMode(data, mode)` |
| Chat commands | `ChatLog.MESSAGE_PATTERNS` | `ChatLog.CHAT_COMMANDS` |
| Status effect list | array | object keyed by id |
| Delete a key in an update | `"-=key": null` | `foundry.data.operators.ForcedDeletion` |
| Replace a key in an update | `"==key": value` | `foundry.data.operators.ForcedReplacement` |
| Deep equality | `foundry.utils.objectsEqual` | `foundry.utils.equals` |
| Localize with data | `game.i18n.format(key, data)` | `game.i18n.localize(key, data)` / `_loc(key, data)` |
| Query several users | loop `user.query(...)` | `User.queryMany(users, name, data)` |
| Clear a placeable | override `clear()` | override `_clear()` |
| Custom canvas layer | `layerClass` in document CONFIG | deprecated — see API docs |
| Pathfinding options | `ignoreWalls`, `ignoreCost`, `history` | `constrainOptions` |
| Movement animation options | `getAnimationOptions(token)` receives a `Token` | `TokenMovementActionConfig#getAnimationOptions(tokenDocument)` |
| ProseMirror plugins | `foundry.prosemirror.defaultPlugins` | `ProseMirrorEditor.buildDefaultPlugins()` |
| Data schema definition | `template.json` (still works) | `documentTypes` + data models (`template.json` deprecated) |

::: warning
`ChatMessage.applyRollMode` is the V13 name for the static roll-mode helper; confirm it in the
[V13 API](https://foundryvtt.com/api/v13/) before relying on it. For the full migration
checklist see [Migrating your package from V13 to V14](#migrations).
:::

## Pitfalls

::: warning
- Mixing `mergeObject` defaults: it **mutates** the first argument unless `inplace: false`.
- `setProperty` on a Document does not save it — use `doc.update({ "a.b": v })`.
- `game.packs.get` needs the full collection id (`"forja.monsters"`), not just the pack name.
- `game.user.isGM` is true for every GM; use `isActiveGM` when only one client should act.
:::
