# Documents

Documents are the persistent records of a world — actors, items, scenes, chat messages and more — and this page shows how they are structured, created, found, changed and extended.

::: changed
- `Document.create()` now builds `this.implementation`, so calling `Actor.create()` on a base class still produces your configured subclass.
- New `Document#persisted` property to tell whether an instance is backed by the database.
- Relative UUIDs got first-class helpers (`foundry.utils.buildRelativeUuid`, `DocumentUUIDField#relative`).
- The special update keys `-=key` and `==key` are **deprecated** in favor of `DataFieldOperator` values (`foundry.data.operators.ForcedDeletion`, `ForcedReplacement`).
- Document metadata can control whether the "base" type may be created or offered in create dialogs.
- `DocumentCollection#importDocument` keeps the original IDs; `foundry.utils.equals()` replaces `objectsEqual`.
- See [the full changelog](#changes-14).
:::

## What it is

A Document is a data model that is saved to the database and synchronized to every connected client. Each Document type exists in two layers:

| Layer | Example | Where it runs | Responsibility |
| --- | --- | --- | --- |
| Base (common) | `foundry.documents.BaseActor` | Server **and** client | Schema, validation, permissions metadata |
| Client | `Actor` (a `ClientDocument`) | Browser only | Data preparation, sheets, rolls, UI helpers, hooks |

You never subclass the base class. You extend the **client** class (`Actor`, `Item`, …) and tell Foundry to use your subclass. The type-specific data under `system` is defined by a [data model](#data-models).

Documents are either **primary** (live in a world collection: `Actor`, `Item`, `Scene`, `JournalEntry`, `ChatMessage`, …) or **embedded** (live inside a parent: an `Item` inside an `Actor`, a `Token` inside a `Scene`, an `ActiveEffect` inside an `Actor` or `Item`).

## World collections

Primary documents are stored in collections on `game`. They are `Map`-like and indexed by id.

```js
// Collections: game.actors, game.items, game.scenes, game.journal,
// game.messages, game.users, game.folders, game.tables, game.macros ...
const hero = game.actors.getName("Aria");
const byId = game.actors.get("q8sLhg0GqL5bRw2x");
const characters = game.actors.filter((a) => a.type === "character");
const allItems = game.items.contents; // plain Array

// Embedded documents live in collections on the parent
const sword = hero.items.getName("Longsword");
const effects = hero.effects.contents;
```

## UUIDs

Every document has a globally unique `uuid` string that encodes where it lives:

| Document | UUID format |
| --- | --- |
| World actor | `Actor.q8sLhg0GqL5bRw2x` |
| Item owned by an actor | `Actor.q8sLhg0GqL5bRw2x.Item.a1b2c3d4e5f6g7h8` |
| Token in a scene | `Scene.xyz123abc456def7.Token.tok123abc456def7` |
| Compendium entry | `Compendium.forja.monsters.Actor.m0nst3r1d0000000` |

```js
// Asynchronous: works for anything, including compendium documents not yet loaded
const actor = await fromUuid("Actor.q8sLhg0GqL5bRw2x");

// Synchronous: only returns documents already in memory
// (for an unloaded compendium entry it may return an index entry instead of a Document)
const item = fromUuidSync("Actor.q8sLhg0GqL5bRw2x.Item.a1b2c3d4e5f6g7h8");
```

UUIDs are what you store when one document needs to point to another (for example in a `DocumentUUIDField`), and what `@UUID[...]` links in text use.

::: v14
V14 adds helpers for **relative** UUIDs — short references resolved against another document (for example an item referencing a sibling item in the same actor). See `foundry.utils.buildRelativeUuid` and the `relative` option of `DocumentUUIDField` in the [V14 API](https://foundryvtt.com/api/v14/). `fromUuid(uuid, { relative: doc })` resolves them.
:::

## Create, read, update, delete

All database operations are **asynchronous** and return Promises. Use the batch (`*Documents`) variants when changing many documents: one round-trip, one set of hooks per document.

```js
// CREATE
const actor = await Actor.create({ name: "Aria", type: "character" });
const [goblin, orc] = await Actor.createDocuments([
  { name: "Goblin", type: "npc" },
  { name: "Orc", type: "npc" }
]);

// UPDATE — dot notation targets nested fields
await actor.update({ "system.hp.value": 8, name: "Aria the Bold" });
await Actor.updateDocuments([
  { _id: goblin.id, "system.hp.value": 3 },
  { _id: orc.id, "system.hp.value": 5 }
]);

// DELETE
await orc.delete();
await Actor.deleteDocuments([goblin.id]);
```

### Embedded documents

Embedded documents are changed through their parent:

```js
// Give Aria two weapons
const created = await actor.createEmbeddedDocuments("Item", [
  { name: "Longsword", type: "weapon", system: { damage: "1d8" } },
  { name: "Dagger", type: "weapon", system: { damage: "1d4" } }
]);

// Equivalent for a single one: Item.create(data, { parent: actor })
await Item.create({ name: "Shield", type: "weapon" }, { parent: actor });

await actor.updateEmbeddedDocuments("Item", [{ _id: created[0].id, "system.damage": "1d10" }]);
await actor.deleteEmbeddedDocuments("Item", [created[1].id]);
```

### Removing or replacing keys

Normally `update` **merges** objects. To delete a key or replace a whole object, you need a special instruction:

::: v13
Use the special key prefixes `-=` (delete) and `==` (replace):

```js
// Delete the key "oldBonus" from system.bonuses
await actor.update({ "system.bonuses.-=oldBonus": null });
// Replace system.bonuses entirely instead of merging
await actor.update({ "system.==bonuses": { melee: 1 } });
```
:::

::: v14
The `-=` / `==` prefixes still work but are **deprecated**. Use `DataFieldOperator` values from `foundry.data.operators`:

```js
const { ForcedDeletion, ForcedReplacement } = foundry.data.operators;
// Delete the key "oldBonus" from system.bonuses
await actor.update({ "system.bonuses.oldBonus": ForcedDeletion.create() });
// Replace system.bonuses entirely instead of merging
await actor.update({ "system.bonuses": ForcedReplacement.create({ melee: 1 }) });
```

Check the [`DataFieldOperator` API](https://foundryvtt.com/api/v14/classes/foundry.data.operators.DataFieldOperator.html) for the exact semantics of each operator.
:::

## updateSource vs update

| | `document.update(changes)` | `document.updateSource(changes)` |
| --- | --- | --- |
| Saves to database | Yes | **No** — only changes the local in-memory source |
| Broadcast to other clients | Yes | No |
| Fires hooks | `preUpdate*` / `update*` | None |
| Returns | Promise | Synchronous diff object |
| Use for | Real changes | Adjusting data **before** it is saved, e.g. in `_preCreate` / `preCreate*` |

```js
// Build a temporary actor, tweak it, then save it
const draft = new Actor.implementation({ name: "Draft", type: "npc" });
draft.updateSource({ "system.hp.max": 12 });
await Actor.create(draft.toObject());
```

## Flags

Flags are a free-form storage area on every document, namespaced by package id. They are the right place for **module** data on documents you don't own the schema of.

```js
// Stored at actor.flags["forja-extras"].rests
await actor.setFlag("forja-extras", "rests", 3);
const rests = actor.getFlag("forja-extras", "rests"); // 3
await actor.unsetFlag("forja-extras", "rests");
```

::: warning
The scope (first argument) must be `"world"`, `"core"`, or the id of an **active** package, otherwise `setFlag` throws. Systems should prefer fields in their own data model over flags — flags have no validation.
:::

## Ownership and permissions

Each document has an `ownership` object mapping user ids (and `"default"`) to a level from `CONST.DOCUMENT_OWNERSHIP_LEVELS`: `NONE` (0), `LIMITED` (1), `OBSERVER` (2), `OWNER` (3), plus `INHERIT` (-1) for embedded/folder cases.

```js
const { OWNER, OBSERVER } = CONST.DOCUMENT_OWNERSHIP_LEVELS;

actor.isOwner;                              // current user is at least OWNER (GMs always are)
actor.testUserPermission(game.user, "OBSERVER"); // at least OBSERVER?
actor.testUserPermission(someUser, OWNER, { exact: true }); // exactly OWNER?
actor.canUserModify(game.user, "update");   // may this user update it?

// Let every player observe the actor
await actor.update({ "ownership.default": OBSERVER });
```

Check permissions **before** calling `update` in UI code, and show a friendly message instead of letting the server reject the request.

## Extending document classes

Subclass the client class and register it in `init`. `CONFIG.Actor.documentClass` is what `Actor.implementation` returns, so every actor in the world will use your class.

```js
// systems/forja/documents/actor.mjs
export class ForjaActor extends Actor {
  /** Convenience getter used by sheets and rolls */
  get isDefeated() {
    return this.system.hp?.value <= 0;
  }

  getRollData() {
    // Expose system data (and anything else) to roll formulas as @...
    return { ...super.getRollData(), level: this.system.level ?? 1 };
  }
}
```

```js
// systems/forja/forja.mjs
import { ForjaActor } from "./documents/actor.mjs";

Hooks.once("init", () => {
  CONFIG.Actor.documentClass = ForjaActor;
});
```

::: v13
Always create documents through the configured class: `Actor.implementation.create(...)` or `getDocumentClass("Actor").create(...)`. Calling `new Actor(...)` directly builds the core class, not yours.
:::

::: v14
`Document.create()` now uses `this.implementation` internally, so `Actor.create(...)` returns a `ForjaActor` even when called on the base class. For `new`, still use `new Actor.implementation(...)`.
:::

### Document lifecycle overrides

Instead of listening to hooks for your *own* documents, override the protected lifecycle methods. Always call `super`.

| Method | Runs on | Purpose |
| --- | --- | --- |
| `async _preCreate(data, options, user)` | Requesting client | Adjust data with `this.updateSource()`, or return `false` to cancel |
| `_onCreate(data, options, userId)` | All clients | React after creation |
| `async _preUpdate(changes, options, user)` | Requesting client | Modify `changes` or return `false` |
| `_onUpdate(changes, options, userId)` | All clients | React after update |
| `async _preDelete(options, user)` | Requesting client | Return `false` to cancel |
| `_onDelete(options, userId)` | All clients | Clean up |

```js
// systems/forja/documents/actor.mjs (continued)
export class ForjaActor extends Actor {
  async _preCreate(data, options, user) {
    const allowed = await super._preCreate(data, options, user);
    if (allowed === false) return false;
    // Characters are linked to their tokens by default
    if (this.type === "character") {
      this.updateSource({ "prototypeToken.actorLink": true });
    }
  }

  _onUpdate(changes, options, userId) {
    super._onUpdate(changes, options, userId);
    // Runs on every client: only UI feedback here, no database writes
    if (foundry.utils.hasProperty(changes, "system.hp.value") && this.isDefeated) {
      ui.notifications.info(`${this.name} is down!`);
    }
  }
}
```

## Data preparation order

Every time a document is initialized or updated, `prepareData()` runs on every client. For an `Actor` with a `TypeDataModel` the order is:

1. `system.prepareBaseData()` — data model: values that depend only on stored data
2. `actor.prepareBaseData()` — document-level base values
3. `actor.prepareEmbeddedDocuments()` — prepares items and effects; **Active Effects are applied here**
4. `system.prepareDerivedData()` — data model: totals, modifiers (effects are already applied)
5. `actor.prepareDerivedData()` — document-level derived values

```js
// systems/forja/documents/actor.mjs (continued)
prepareDerivedData() {
  super.prepareDerivedData();
  // Items are prepared already, so their data can be summed here
  this.system.encumbrance = this.items.reduce((sum, i) => sum + (i.system.weight ?? 0), 0);
}
```

::: warning
Never call `update()` from inside `prepareData` methods — it runs on every client on every change and will loop. Derived values live in memory only.
:::

## Other V14 changes

::: v14
- **`Document#persisted`** tells whether an instance is backed by a database record — useful to distinguish temporary/ephemeral documents from saved ones.
- **Base type creation**: document metadata can hide or forbid the `"base"` type in create dialogs, so systems that only use their own subtypes no longer show a useless "Base" option.
- **`DocumentCollection#importDocument`** keeps the source document's `_id`, so importing from a compendium preserves IDs (and UUID-based references keep working).
- **`foundry.utils.equals(a, b)`** replaces `foundry.utils.objectsEqual` for deep equality.
:::

::: v13
For deep comparisons use `foundry.utils.objectsEqual(a, b)`. When importing from a compendium, pass `{ keepId: true }` to `importFromCompendium` if you need the original id.
:::

## Pitfalls

- **Forgetting `await`.** `actor.update()` returns before the change is saved; read the new value after awaiting.
- **Updating inside a loop.** Use `updateDocuments` / `updateEmbeddedDocuments` with an array instead of N separate `update` calls.
- **Writing in `_onUpdate` or `update*` hooks** without checking `userId === game.user.id` duplicates writes across clients.
- **Mutating `document.system` directly** (`actor.system.hp.value = 3`) changes only local memory — nothing is saved.
- **Token actors.** An unlinked token has its own synthetic actor; `token.actor` is not `game.actors.get(token.actorId)`.
- **Invalid flag scopes** throw; use your package id.
