# Compendium Packs

Compendium packs ship documents with your system or module; you declare them in the manifest, build them from source files with the official CLI and read them with `game.packs`.

::: changed
- **Active Effects** are primary documents in V14 and can be stored in their own compendium packs (`"type": "ActiveEffect"`).
- **World packages can no longer be installed from Setup**: distribute adventures as `Adventure` documents inside a module pack.
- `DocumentCollection#importDocument` now **keeps document IDs** by default.
- Compendium titles are localized in search results.
- See [the full changelog](#changes-14).
:::

## What it is

A **compendium pack** is a database of documents of one type (Actor, Item, JournalEntry, Macro,
RollTable, Scene, Adventure, ...) that lives inside a package, not in a world. Worlds read packs
lazily: only a lightweight **index** is loaded until you ask for full documents.

Packs are stored as **LevelDB** folders (`packs/items/` with `CURRENT`, `LOG`, `*.ldb` files).
LevelDB is binary and locked while Foundry has the pack open, so you **do not commit it by hand**:
you keep JSON/YAML source files in git and compile them with the CLI.

## Declare packs in the manifest

```json
{
  "id": "forja",
  "packs": [
    {
      "name": "items",
      "label": "Forja Items",
      "path": "packs/items",
      "type": "Item",
      "system": "forja",
      "ownership": { "PLAYER": "OBSERVER", "ASSISTANT": "OWNER" },
      "flags": {}
    },
    {
      "name": "rules",
      "label": "Forja Rules",
      "path": "packs/rules",
      "type": "JournalEntry"
    }
  ],
  "packFolders": [
    {
      "name": "Forja",
      "sorting": "m",
      "color": "#7a3b12",
      "packs": ["items", "rules"],
      "folders": []
    }
  ]
}
```

- `name` is the pack id inside the package; the full collection id is `forja.items`.
- `type` is the document name. `system` restricts Actor/Item packs to that system (required in
  modules shipping system-specific content).
- `ownership` sets the default access per role (`NONE`, `LIMITED`, `OBSERVER`, `OWNER`).
- `packFolders` groups packs into sidebar folders (`sorting`: `"a"` alphabetical, `"m"` manual).

## Build packs with the CLI

Install the official CLI (`@foundryvtt/foundryvtt-cli`) as a dev dependency:

```bash
npm install --save-dev @foundryvtt/foundryvtt-cli
npx fvtt configure set dataPath "/path/to/FoundryData"
npx fvtt package workon forja --type System

# LevelDB → one JSON file per document (commit these)
npx fvtt package unpack -n items --outputDirectory src/packs/items

# JSON → LevelDB (run with the world closed)
npx fvtt package pack -n items --inputDirectory src/packs/items --outputDirectory packs
```

Add `--yaml` to both commands to use YAML instead of JSON. For a build script, use the JS API:

```js
// tools/build-packs.mjs  —  run with: node tools/build-packs.mjs
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { readdir } from "node:fs/promises";

const packs = await readdir("src/packs");
for (const pack of packs) {
  console.log(`Packing ${pack}`);
  await compilePack(`src/packs/${pack}`, `packs/${pack}`, { recursive: true, log: true });
}
```

`extractPack(src, dest, options)` is the reverse (options include `yaml`, `folders`,
`expandAdventures`, `omitVolatile`, `transformEntry`).

::: warning
Every source file must contain a stable `_id` (16 characters) and a `_key`
(`"!items!<id>"`, or `"!items.effects!<itemId>.<effectId>"` for embedded documents). Unpacking an
existing pack produces them; when writing files by hand, generate ids once with
`foundry.utils.randomID()` and never change them, or links to the document break.
:::

## Read packs in code

```js
const pack = game.packs.get("forja.items");
console.log(pack.collection, pack.documentName, pack.metadata.label);

// 1. The index: cheap, already cached after the first call
const index = await pack.getIndex({ fields: ["system.price", "system.rarity"] });
const cheap = index.filter(e => e.type === "weapon" && e.system.price < 10);

// 2. One document by id
const sword = await pack.getDocument(cheap[0]._id);

// 3. Many documents, optionally filtered by a query on source data
const weapons = await pack.getDocuments({ type: "weapon" });

// 4. By UUID (works for any pack)
const axe = await fromUuid("Compendium.forja.items.Item.a1b2c3d4e5f6g7h8");
```

`fromUuidSync()` on a compendium UUID returns the **index entry** (not a Document) if the document
isn't loaded yet: check `entry instanceof foundry.abstract.Document` before calling methods.

Use `index` fields for lists and search (e.g. a "choose a weapon" dialog); load full documents only
for the one the user picks. Every field you add to `getIndex({fields})` is kept in memory, so add
only what you display. Systems can add default index fields with `CONFIG.Item.compendiumIndexFields`.

## Import into the world

```js
// Import one document into the Items directory (keeps the same _id)
const item = await game.items.importFromCompendium(pack, sword.id, {}, { keepId: true });

// Import everything into a folder
await pack.importAll({ folderName: "Forja Items", keepId: true });

// Or: give a compendium item to an actor directly
await actor.createEmbeddedDocuments("Item", [sword.toObject()]);
```

`importFromCompendium` records the source in `_stats.compendiumSource`, which you can use to
update world copies from the pack later.

::: v14
In V14 `DocumentCollection#importDocument` keeps the document's id by default, so imported
documents keep their UUID relationships.
:::

## Write to a pack

Packs are locked by default. The GM can unlock them, and code can write to them like a collection:

```js
await pack.configure({ locked: false });
await Item.create({ name: "Ember Blade", type: "weapon" }, { pack: pack.collection });
await sword.update({ "system.price": 12 }); // documents from a pack update in the pack
```

::: tip
Only write to *world* compendiums at runtime. Packs inside your system or module are overwritten
on every update; edit their source files instead.
:::

## Adventures

An **Adventure** document bundles Scenes, Actors, Items, Journals, Tables, Playlists, Macros,
Cards, Combats and Folders into one importable unit. Create one in a pack of type `"Adventure"`
(the Adventure Exporter UI) and users import it with one click, ids preserved.

```js
const adventurePack = game.packs.get("forja-extras.adventures");
const [adventure] = await adventurePack.getDocuments();
adventure.sheet.render(true); // opens the importer
```

::: v14
World packages can no longer be installed from Setup in V14. If you distributed a "starter world",
ship an Adventure in a module instead.

Active Effects are primary documents in V14: declare a pack with `"type": "ActiveEffect"` to
ship conditions and buffs that users drag onto tokens.
:::

## Pitfalls

::: warning
- `fvtt package pack` fails (or corrupts data) while Foundry has the world open: LevelDB is locked.
- A pack `name` must be unique within its package and must not change after release, or all
  `Compendium.forja.<name>...` UUIDs break.
- `pack.index` is empty until `getIndex()` has run once (core calls it on world load, but only
  with default fields).
- Don't loop `await pack.getDocument(id)` for hundreds of ids: use `getDocuments({ _id__in: ids })`.
- Actor/Item packs in a module without `system` show up in every system and may contain invalid data.
:::
