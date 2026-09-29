# Data migrations

Keep old worlds working when your data shape changes, and move your package from V13 to V14.

::: changed
- `ActiveEffect#changes` moved to `effect.system.changes`; the numeric `mode` became a string `type`.
- Effect `duration` is now `{ value, units, expiry, expired }`.
- `template.json` is deprecated; use `documentTypes` in the manifest plus data models.
- `MeasuredTemplate` is gone (absorbed into Regions); `-=` / `==` update keys are deprecated.
- V12 deprecations were removed. See [the full changelog](#changes-14).
:::

## Two layers of migration

Foundry gives you two complementary tools, and a mature system uses both:

| Layer | Where | When it runs | Persists? |
| --- | --- | --- | --- |
| `static migrateData(source)` | Your `TypeDataModel` | Every time a document is constructed (load, import, compendium) | No — only in memory until the document is saved |
| World migration script | `ready` hook, GM only | Once per system version bump | Yes — writes to the database |

`migrateData` is the safety net: it makes old data readable **everywhere**, including
compendiums and imported JSON. The world script is the cleanup: it writes the new shape to
disk so `migrateData` eventually has nothing to do, and so queries on raw data (like
`pack.getIndex({ fields })`) see the new shape.

## Per-document: migrateData

Suppose version 1.x stored hit points as a number `system.hp`, and 2.0 uses `{ value, max }`.

```js
// systems/forja/module/data/character.mjs
const { HTMLField, NumberField, SchemaField } = foundry.data.fields;

export class CharacterData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      hp: new SchemaField({
        value: new NumberField({ integer: true, min: 0, initial: 10 }),
        max: new NumberField({ integer: true, min: 0, initial: 10 })
      }),
      might: new NumberField({ integer: true, min: 0, initial: 1 }),
      notes: new HTMLField()
    };
  }

  static migrateData(source) {
    // 1.x: hp was a plain number
    if (typeof source.hp === "number") {
      source.hp = { value: source.hp, max: source.hp };
    }
    // 1.x: "vigor" was renamed to "might"
    if ("vigor" in source && !("might" in source)) {
      source.might = source.vigor;
      delete source.vigor;
    }
    return super.migrateData(source);
  }
}
```

Rules for `migrateData`:

- It receives **source** data (plain object), possibly partial (updates run through it too). Check that a key exists before touching it.
- Mutate and return `source`; always call `super.migrateData(source)`.
- Keep it idempotent: running it twice must be harmless.
- Never read other documents or `game` state here — it may run before the world is ready.

## Keep old code working: shimData

If other modules read `actor.system.vigor`, renaming the field breaks them. `shimData`
lets you add a deprecated accessor on the prepared data:

```js
static shimData(data, options) {
  data = super.shimData(data, options);
  if (!Object.hasOwn(data, "vigor")) {
    Object.defineProperty(data, "vigor", {
      get() {
        foundry.utils.logCompatibilityWarning(
          "system.vigor is deprecated, use system.might",
          { since: "Forja 2.0", until: "Forja 3.0" }
        );
        return this.might;
      },
      configurable: true,
      enumerable: false
    });
  }
  return data;
}
```

Announce a removal version and delete the shim when you get there.

## World migration script

```js
// systems/forja/module/migration.mjs
export const MIGRATION_VERSION = "2.0.0";

export function registerMigrationSetting() {
  game.settings.register("forja", "systemMigrationVersion", {
    scope: "world",
    config: false,
    type: String,
    default: ""
  });
}

export async function migrateWorldIfNeeded() {
  if (!game.user.isActiveGM) return;
  const current = game.settings.get("forja", "systemMigrationVersion");
  // A brand-new world has nothing to migrate.
  if (!current && !game.actors.size && !game.items.size) {
    return game.settings.set("forja", "systemMigrationVersion", game.system.version);
  }
  if (current && !foundry.utils.isNewerVersion(MIGRATION_VERSION, current)) return;
  await migrateWorld();
  await game.settings.set("forja", "systemMigrationVersion", game.system.version);
}

/**
 * Return an update object for one Actor's source data, or null.
 * `source` comes from toObject(), so migrateData has ALREADY run on it:
 * changes handled there only need to be written back (see `persist`).
 */
function migrateActorData(source, persist = false) {
  const update = {};
  // Persist in-memory fixes from migrateData (hp number → { value, max }).
  if (persist) update["system.hp"] = source.system.hp;
  // Things migrateData cannot do: move a legacy flag into the schema.
  const notes = source.flags?.forja?.legacyNotes;
  if (notes !== undefined) {
    update["system.notes"] = notes;
    update["flags.forja.-=legacyNotes"] = null;
  }
  const items = (source.items ?? []).map((i) => {
    const u = migrateItemData(i);
    return u ? { _id: i._id, ...u } : null;
  }).filter(Boolean);
  if (items.length) update.items = items;
  return foundry.utils.isEmpty(update) ? null : update;
}

function migrateItemData(source) {
  const update = {};
  if (source.flags?.forja?.weight !== undefined) {
    update["system.weight"] = source.flags.forja.weight;
    update["flags.forja.-=weight"] = null;
  }
  return foundry.utils.isEmpty(update) ? null : update;
}

async function updateInBatches(cls, updates, options = {}, size = 100) {
  // diff: false sends the values even if they equal the (already migrated) in-memory data.
  for (let i = 0; i < updates.length; i += size) {
    await cls.updateDocuments(updates.slice(i, i + size), { diff: false, ...options });
  }
}

export async function migrateWorld() {
  const steps = 4;
  const bar = ui.notifications.info("Forja: migrating world data…", { progress: true, permanent: true });
  const report = (step, message) => bar.update({ pct: step / steps, message });

  // 1. World actors (and their embedded items)
  const actorUpdates = game.actors.map((a) => {
    const u = migrateActorData(a.toObject(), true);
    return u ? { _id: a.id, ...u } : null;
  }).filter(Boolean);
  await updateInBatches(Actor, actorUpdates);
  report(1, "Actors migrated");

  // 2. World items
  const itemUpdates = game.items.map((i) => {
    const u = migrateItemData(i.toObject());
    return u ? { _id: i.id, ...u } : null;
  }).filter(Boolean);
  await updateInBatches(Item, itemUpdates);
  report(2, "Items migrated");

  // 3. Unlinked token actors in scenes (their data lives in the token's ActorDelta)
  for (const scene of game.scenes) {
    for (const token of scene.tokens) {
      if (token.actorLink || !token.actor) continue;
      const u = migrateActorData(token.actor.toObject());
      if (u) await token.actor.update(u, { diff: false });
    }
  }
  report(3, "Scenes migrated");

  // 4. Compendium packs owned by the world or this system
  for (const pack of game.packs) {
    if (!["Actor", "Item"].includes(pack.documentName)) continue;
    if (pack.metadata.packageType === "module") continue; // modules migrate their own packs
    const wasLocked = pack.locked;
    await pack.configure({ locked: false });
    const docs = await pack.getDocuments();
    const fn = pack.documentName === "Actor" ? (src) => migrateActorData(src, true) : migrateItemData;
    const updates = docs.map((d) => {
      const u = fn(d.toObject());
      return u ? { _id: d.id, ...u } : null;
    }).filter(Boolean);
    await updateInBatches(pack.documentClass, updates, { pack: pack.collection });
    await pack.configure({ locked: wasLocked });
  }
  report(4, "Compendiums migrated");
  bar.update({ pct: 1, message: "Forja: migration complete" });
  setTimeout(() => ui.notifications.remove(bar), 3000);
}
```

```js
// systems/forja/forja.mjs
import { registerMigrationSetting, migrateWorldIfNeeded } from "./module/migration.mjs";

Hooks.once("init", registerMigrationSetting);
Hooks.once("ready", migrateWorldIfNeeded);
```

Why these choices:

- **`isActiveGM`** — only one client may write, otherwise two GMs race each other.
- **`toObject()`** — returns source data that has *already* passed through `migrateData`, so you cannot detect the old shape there. Instead, write the migrated values back with `diff: false` (otherwise Foundry sees "no change" and sends nothing), and use the script for what `migrateData` cannot do, such as moving flags into the schema.
- **Token actors** — for unlinked tokens only the delta is stored; we skip the forced `hp` write there so we do not copy the base actor's values into every delta.
- **Batches** — a single `updateDocuments` with thousands of entries can time out the socket.
- **System-owned packs only** — modules should migrate their own compendiums.

::: warning
Tell GMs to **back up the world** before updating. Migrations cannot be undone.
:::

::: tip
The `progress: true` notification (V13+) replaces the deprecated
`SceneNavigation.displayProgressBar`. Call `update({ pct, message })` on the returned object.
:::

## Migrating your package from V13 to V14

### Checklist

- [ ] Manifest `compatibility`: `{ "minimum": "13", "verified": "14" }` if you support both, or `"minimum": "14"` if you drop V13. Optionally add `"type": "system"` / `"module"`.
- [ ] Replace `template.json` with `documentTypes` in `system.json` and `CONFIG.<Doc>.dataModels`.
- [ ] Active Effects: `changes` → `system.changes`, `mode` (number) → `type` (string). See the code below.
- [ ] Effect duration: read `{ value, units, expiry, expired }`; units come from `CONST.ACTIVE_EFFECT_DURATION_UNITS`.
- [ ] Remove any use of `CONFIG.ActiveEffect.legacyTransferral`.
- [ ] `MeasuredTemplate` → Scene Regions (cone, line, ring, emanation shapes; `RegionLayer#placeRegion`).
- [ ] `Roll#toMessage(data, { rollMode })` → `{ messageMode }`; use `ChatMessage.applyMode(chatData, mode)`.
- [ ] `ChatLog.MESSAGE_PATTERNS` → `ChatLog.CHAT_COMMANDS`.
- [ ] `CONFIG.statusEffects` is an object keyed by id (arrays still accepted).
- [ ] `"-=key": null` / `"==key": value` → `foundry.data.operators.ForcedDeletion` / `ForcedReplacement`.
- [ ] Remove code that relied on V12 deprecations — they are gone in V14.
- [ ] `RegionShape` → `BaseShapeData`; `foundry.data.regionShapes.RegionPolygonTree` → `foundry.data.PolygonTree`.
- [ ] Override `PlaceableObject#_clear` instead of `clear`.
- [ ] Stop setting `layerClass` in canvas document CONFIG.
- [ ] `Token#findMovementPath` options `ignoreWalls` / `ignoreCost` / `history` → `constrainOptions`.
- [ ] `foundry.utils.objectsEqual` → `foundry.utils.equals`.
- [ ] `game.i18n.format(key, data)` → `game.i18n.localize(key, data)` (or `_loc(key, data)`).
- [ ] Test on a **fresh V14 install** — V14 cannot update in place from V13.

### Active Effect changes: V13 vs V14

::: v13
```js
// V13 effect source
const effectData = {
  name: "Bless",
  changes: [
    { key: "system.attack.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "2", priority: 20 }
  ],
  duration: { rounds: 10 }
};
```
:::

::: v14
```js
// V14 effect source
const effectData = {
  name: "Bless",
  system: {
    changes: [
      { key: "system.attack.bonus", type: "add", value: 2, phase: "initial", priority: 20 }
    ]
  },
  duration: { value: 10, units: "rounds", expiry: "turnEnd" }
};
```
:::

Core migrates effect data it stores itself, but your **code** and any effect data you build
at runtime (or keep in `flags`, macros, JSON imports) must be updated. A helper that reads
both shapes lets one codebase run on both versions:

```js
// systems/forja/module/compat/effects.mjs
const MODE_TO_TYPE = { 0: "custom", 1: "multiply", 2: "add", 3: "downgrade", 4: "upgrade", 5: "override" };

/** Return change entries in the V14 shape, whatever the running version. */
export function getEffectChanges(effect) {
  const raw = effect.system?.changes ?? effect.changes ?? [];
  return raw.map((c) => ({
    key: c.key,
    value: c.value,
    type: c.type ?? MODE_TO_TYPE[c.mode] ?? "custom",
    priority: c.priority ?? null
  }));
}

/** Convert legacy effect source data (e.g. from flags or JSON) to the V14 shape. */
export function migrateEffectSource(source) {
  if (!Array.isArray(source.changes)) return source;
  source.system ??= {};
  source.system.changes = source.changes.map((c) => ({
    key: c.key,
    value: c.value,
    type: MODE_TO_TYPE[c.mode] ?? "custom",
    phase: "initial",
    priority: c.priority ?? undefined
  }));
  delete source.changes;
  return source;
}
```

::: warning
The mapping above follows the V13 `CONST.ACTIVE_EFFECT_MODES` numbers
(CUSTOM 0, MULTIPLY 1, ADD 2, DOWNGRADE 3, UPGRADE 4, OVERRIDE 5). V14 has `subtract` too,
which has no V13 equivalent. Verify against `CONST.ACTIVE_EFFECT_CHANGE_TYPES` in the
[V14 API](https://foundryvtt.com/api/v14/).
:::

### Deletion operators

::: v13
```js
await actor.update({ "system.-=obsoleteField": null });
```
:::

::: v14
```js
const { ForcedDeletion } = foundry.data.operators;
await actor.update({ "system.obsoleteField": ForcedDeletion.create() });
```
The `-=` syntax still works with a deprecation warning. Check the exact operator usage for your
build in the [V14 API](https://foundryvtt.com/api/v14/modules/foundry.data.operators.html).
:::

## Pitfalls

::: warning
- Running the world migration on every client — guard with `game.user.isActiveGM`.
- Setting `systemMigrationVersion` **before** the migration finishes — a crash halfway leaves the world marked as migrated.
- Non-idempotent `migrateData` (for example, multiplying a value) — it runs on every load.
- Forgetting unlinked tokens and compendiums — they hold their own copies of actor data.
- Reading `game` or other documents in `migrateData` — it runs during construction, often before `ready`.
:::
