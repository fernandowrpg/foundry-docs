# Introduction

What Foundry packages are, how they load, the Document model at a glance, and how to use this guide.

## What you can build

Foundry Virtual Tabletop is extended through **packages**. As a developer you will write one of two kinds:

| Package | Lives in | What it does | Per world |
|---|---|---|---|
| **System** | `Data/systems/<id>/` | Defines the *rules*: what an Actor or Item *is*, their data, sheets, rolls, combat initiative. | Exactly **one** |
| **Module** | `Data/modules/<id>/` | Adds or changes behavior on top of a system (or of core): new UI, automation, content packs, macros. | **Zero or many** |

A third package type, the **world**, is the actual campaign (its database of actors, scenes, journals…). You rarely write world code; you *test* in worlds.

::: tip
If your idea is "a new game with its own character sheet", you want a **system**. If it is "make game X do something extra", you want a **module**. A module can declare that it only works with a specific system (see [the manifest](#manifest)).
:::

### Systems vs modules: technical differences

- A system's manifest is `system.json`; a module's is `module.json`. Most fields are shared.
- Only a system declares **document sub-types** (`documentTypes`, e.g. Actor `character` / `npc`) and their data models. Modules can add sub-types too, but they are namespaced (`forja-extras.companion`).
- Only a system sets world-wide defaults such as grid distance/units, initiative formula and token bar attributes.
- Everything else (hooks, settings, applications, compendium packs, sockets) is available to both.

## How packages load

When a user joins a world, the client boots in a fixed order. Knowing it tells you **where** your code may run.

1. **Core** loads (the `foundry` namespace, `CONFIG`, `CONST`, `Hooks`).
2. The **world** is read: which system and which modules are active.
3. The **system** scripts load (`esmodules`/`scripts` from `system.json`), then each **active module**'s scripts, in dependency order.
4. Hooks fire during boot: `init` → `i18nInit` → `setup` → `ready`.

```js
// The three hooks you use in almost every package
Hooks.once("init", () => {
  // CONFIG, settings, data models, sheets. game.actors etc. do NOT exist yet.
  console.log("forja | init");
});

Hooks.once("setup", () => {
  // Localization and settings are ready; documents are not yet prepared.
});

Hooks.once("ready", () => {
  // Everything is loaded: game.actors, game.user, canvas (if a scene is active).
  console.log(`forja | ready, user is ${game.user.name}`);
});
```

::: v14
In V14 `ready` fires **after** any scene transition animation has finished, so code in `ready` may run slightly later than in V13.
:::

::: warning
Registering data models, sheets or settings in `ready` is too late — documents have already been prepared. Do it in `init`.
:::

## The Document model at a glance

Almost everything persistent in Foundry is a **Document**: a record in the world database with a schema, permissions and lifecycle hooks (`preCreate`, `updateActor`, …). Documents are either **primary** (stored in a world collection such as `game.actors`) or **embedded** (stored inside a parent, like Items inside an Actor).

| Document | Collection / parent | Used for |
|---|---|---|
| `Actor` | `game.actors` | Characters, NPCs, vehicles — anything with a sheet that acts. |
| `Item` | `game.items` or embedded in `Actor` | Weapons, spells, features, inventory. |
| `ActiveEffect` | embedded in `Actor`/`Item` | Temporary or permanent modifiers to data. |
| `ChatMessage` | `game.messages` | Chat log entries, roll results. |
| `Combat` | `game.combats` | Encounters; embeds `Combatant`. |
| `Scene` | `game.scenes` | Maps; embeds `Token`, `Tile`, `Wall`, `AmbientLight`, `Region`, … |
| `Token` (`TokenDocument`) | embedded in `Scene` | An Actor's presence on a map. |
| `Region` | embedded in `Scene` | Areas with behaviors (teleport, damage, effects). |
| `JournalEntry` | `game.journal` | Notes and handouts; embeds `JournalEntryPage`. |
| `Macro` | `game.macros` | Hotbar scripts and chat macros. |
| `Folder` | `game.folders` | Sidebar organization of other documents. |
| `Cards` | `game.cards` | Decks, hands and piles; embeds `Card`. |
| `Playlist` | `game.playlists` | Audio; embeds `PlaylistSound`. |
| `User` | `game.users` | Players and GMs. |

::: v14
V14 adds **Scene Levels**: a Scene can stack several **`Level`** documents (images at different elevations). Also:

- **ActiveEffect** became a primary document too — effects can live in the sidebar and in compendiums, not only embedded.
- The `MeasuredTemplate` document was removed; templates are now **Regions** with shapes like cone, line, ring and emanation.
:::

::: v13
In V13, `ActiveEffect` is always embedded in an Actor or Item, and area templates use the separate `MeasuredTemplate` document embedded in a Scene.
:::

Each document has a `system` property for your package's own data, defined by a **data model**. Learn more in [Documents](#documents) and [Data models](#data-models).

```js
// Reading documents from the browser console
const hero = game.actors.getName("Aria");
console.log(hero.type);             // "character"
console.log(hero.system.hp.value);  // data defined by the forja system
console.log(hero.items.size);       // embedded Items
```

## How to read this guide

### Version switcher

Pick **V13** or **V14** in the top bar. Text and code that differ between versions change with it; everything else applies to both. The default is V14, the current stable release.

### "Changed in V14" boxes

When V14 is selected, pages whose topic changed show a **Changed in V14** box near the top with a short list of what moved. The full list lives in the [V14 changelog](#changes-14); if you are upgrading from V12, also read the [V13 changelog](#changes-13).

### The running example

Every page builds on the same two packages so examples connect:

- **`forja`** — a tiny fantasy RPG *system* (`systems/forja/...`) with Actor types `character` and `npc`, and Item types `weapon` and `spell`.
- **`forja-extras`** — a *module* (`modules/forja-extras/...`) that adds tools on top of `forja`.

::: tip
Code blocks are complete: copy them into the path given in the text and they should run. Identifiers stay in English; comments and UI strings are translated.
:::

### API references

When you need the exact signature of something, go to the official API docs: [V13 API](https://foundryvtt.com/api/v13/) and [V14 API](https://foundryvtt.com/api/v14/). This guide links to them rather than repeating every parameter.

## Learning path

Follow the pages roughly in this order:

1. **Getting started** — [Setup](#setup) your dev environment, learn [the manifest](#manifest), then build [your first module](#first-module) and [your first system](#first-system).
2. **Core concepts** — [Hooks](#hooks), [Documents](#documents), [Data models](#data-models), [Settings](#settings), [Localization](#localization).
3. **Entities** — [Actor](#actor), [Item](#item), [Active Effects](#active-effect), [Chat & Rolls](#chat-roll), [Combat](#combat), [Scenes & Tokens](#scene-token), [Regions](#regions), [Journal](#journal), [Compendiums](#compendium), [Other documents](#other-documents).
4. **UI** — [ApplicationV2](#applicationv2), [Sheets](#sheets), [Dialogs](#dialogs), [Canvas controls](#canvas-controls), [Styling](#styling).
5. **Advanced** — [Sockets](#sockets), [Migrations](#migrations), [Packaging & release](#packaging), [API map](#api-map).
6. **Reference** — [Changes in V14](#changes-14), [Changes in V13](#changes-13).

::: tip
Short on time? Do [Setup](#setup) → [First system](#first-system) → [Sheets](#sheets). That gets a playable character sheet on screen in an afternoon.
:::
