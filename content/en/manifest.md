# The package manifest

Every field of `module.json` and `system.json`, what it does, and complete examples for V13 and V14.

::: changed
- `compatibility.minimum` should be `"14"` for packages that use V14-only API.
- New optional top-level **`"type": "system" | "module"`** field makes the package type explicit.
- **`template.json` is deprecated**: declare sub-types in `documentTypes` and define their data with `TypeDataModel` classes in `CONFIG.<Document>.dataModels`.
- See [the full changelog](#changes-14).
:::

## What the manifest is for

The manifest is a JSON file at the package root. Foundry reads it to **discover** the package on the Setup screen, **check compatibility** with the running core version, **resolve dependencies**, and know which **files to load** into the client. It is also what the installer downloads to check for updates.

- A module uses `module.json` → `Data/modules/<id>/module.json`
- A system uses `system.json` → `Data/systems/<id>/system.json`

::: warning
JSON has no comments and no trailing commas. A single syntax error hides the package from the Setup screen — check `Logs/` or run the file through a JSON validator.
:::

## Shared fields

### Identity

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Lower-case, hyphens, no spaces. Must equal the folder name. Never change it after release — worlds and flags reference it. |
| `title` | yes | Human-readable name shown in the UI. |
| `description` | yes | Shown on Setup and in the module list; HTML allowed. |
| `version` | yes | Any string, but use semantic versioning (`"1.2.0"`). Updates are detected by comparing it. |
| `authors` | no | Array of `{ name, email?, url?, discord? }`. |

### Compatibility

```json
"compatibility": {
  "minimum": "13",
  "verified": "13.351",
  "maximum": "13"
}
```

- `minimum` — oldest core version the package can run on. Below it, the package cannot be enabled.
- `verified` — newest version you actually tested. Newer versions show a warning, but still run.
- `maximum` — hard ceiling. Leave it out unless you *know* a newer major version breaks you.

::: tip
Use a major number (`"13"`) to mean "any 13.x build" and a full build (`"13.351"`) for `verified`.
:::

### Code, styles and translations

| Field | Notes |
|---|---|
| `esmodules` | Array of JavaScript **ES modules** to load (`import`/`export` supported). Use this. |
| `scripts` | Array of classic scripts (no `import`). Only for legacy code. |
| `styles` | Array of CSS files added to every page of the game. |
| `languages` | Array of `{ lang, name, path }`, e.g. `{ "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }`. |

::: tip
Load **one** entry file in `esmodules` and `import` the rest from it. Load order between multiple entries is harder to reason about.
:::

### Compendium packs

```json
"packs": [
  {
    "name": "weapons",
    "label": "Forja: Weapons",
    "path": "packs/weapons",
    "type": "Item",
    "system": "forja",
    "ownership": { "PLAYER": "OBSERVER", "ASSISTANT": "OWNER" }
  }
],
"packFolders": [
  { "name": "Forja", "sorting": "m", "color": "#6b3b1f", "packs": ["weapons"], "folders": [] }
]
```

`type` is the document type the pack holds (`Actor`, `Item`, `JournalEntry`, `Scene`, `Adventure`…). `system` restricts a module's pack to worlds of that system. `packFolders` groups packs in the Compendium sidebar. More in [Compendiums](#compendium).

### Relationships

```json
"relationships": {
  "systems":    [{ "id": "forja", "type": "system", "compatibility": { "minimum": "0.1.0" } }],
  "requires":   [{ "id": "lib-wrapper", "type": "module" }],
  "recommends": [{ "id": "dice-so-nice", "type": "module", "reason": "3D dice for Forja rolls" }],
  "conflicts":  [{ "id": "old-forja-helper", "type": "module", "reason": "Replaced by this module" }]
}
```

- `systems` — (modules) the systems this module supports. With an entry here, the module can only be enabled in worlds of those systems.
- `requires` — must be installed and active; Foundry offers to install/enable them.
- `recommends` — suggested, not enforced.
- `conflicts` — warns the user when both are active.

Each entry can have `manifest` (URL to install it) and `compatibility` for version ranges.

### Networking and distribution

| Field | Notes |
|---|---|
| `socket` | `true` gives the package a socket channel `module.<id>` / `system.<id>`. See [Sockets](#sockets). |
| `url` | Project homepage or repository. |
| `manifest` | Stable URL to the **latest** manifest. Foundry fetches it to check for updates. |
| `download` | URL of the zip **for this version**. |
| `license`, `readme`, `bugs`, `changelog` | Paths or URLs shown in package details. |
| `media` | Array of `{ type, url, thumbnail?, caption? }` for screenshots, videos, covers. |
| `flags` | Free-form object for your own data and dev tools, e.g. `flags.hotReload` (see [Setup](#setup--hot-reload)). |

## System-only fields

| Field | Notes |
|---|---|
| `documentTypes` | Sub-types per document: `{ "Actor": { "character": {}, "npc": {} } }`. Each type can list `htmlFields` (fields that hold rich text, for enrichment/security) and `filePathFields`. |
| `grid` | Default grid for new scenes: `{ "type": 1, "distance": 1.5, "units": "m" }` (`type` 1 = square). |
| `primaryTokenAttribute` | Path inside `system` shown as the token's first bar, e.g. `"hp"`. |
| `secondaryTokenAttribute` | Second bar, e.g. `"mana"`. |
| `initiative` | Default initiative formula, e.g. `"1d20 + @attributes.agility.value"`. |
| `background` | Image path shown behind the system on the Setup screen. |

::: tip
`primaryTokenAttribute` points at an object with `value` and `max` (like `system.hp`) so the bar knows its range.
:::

## Complete examples

### module.json

::: v13
```json
{
  "id": "forja-extras",
  "title": "Forja Extras",
  "description": "Quality-of-life tools for the Forja system.",
  "version": "0.1.0",
  "authors": [{ "name": "Your Name", "url": "https://github.com/you" }],
  "compatibility": { "minimum": "13", "verified": "13.351", "maximum": "13" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "relationships": {
    "systems": [{ "id": "forja", "type": "system" }]
  },
  "socket": true,
  "url": "https://github.com/you/forja-extras",
  "manifest": "https://github.com/you/forja-extras/releases/latest/download/module.json",
  "download": "https://github.com/you/forja-extras/releases/download/v0.1.0/forja-extras.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```
:::

::: v14
```json
{
  "id": "forja-extras",
  "type": "module",
  "title": "Forja Extras",
  "description": "Quality-of-life tools for the Forja system.",
  "version": "0.1.0",
  "authors": [{ "name": "Your Name", "url": "https://github.com/you" }],
  "compatibility": { "minimum": "14", "verified": "14.368", "maximum": "14" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "relationships": {
    "systems": [{ "id": "forja", "type": "system" }]
  },
  "socket": true,
  "url": "https://github.com/you/forja-extras",
  "manifest": "https://github.com/you/forja-extras/releases/latest/download/module.json",
  "download": "https://github.com/you/forja-extras/releases/download/v0.1.0/forja-extras.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```
:::

### system.json

::: v13
```json
{
  "id": "forja",
  "title": "Forja RPG",
  "description": "A tiny fantasy RPG used as an example.",
  "version": "0.1.0",
  "authors": [{ "name": "Your Name" }],
  "compatibility": { "minimum": "13", "verified": "13.351", "maximum": "13" },
  "esmodules": ["module/forja.mjs"],
  "styles": ["styles/forja.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    },
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] }
    }
  },
  "grid": { "type": 1, "distance": 1.5, "units": "m" },
  "primaryTokenAttribute": "hp",
  "initiative": "1d20 + @attributes.agility.value",
  "background": "systems/forja/assets/background.webp",
  "socket": true,
  "url": "https://github.com/you/forja",
  "manifest": "https://github.com/you/forja/releases/latest/download/system.json",
  "download": "https://github.com/you/forja/releases/download/v0.1.0/forja.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```

V13 still accepts a `template.json` file next to `system.json` to describe default data per type. It works, but new systems should define data with `TypeDataModel` instead — it is what V14 expects.
:::

::: v14
```json
{
  "id": "forja",
  "type": "system",
  "title": "Forja RPG",
  "description": "A tiny fantasy RPG used as an example.",
  "version": "0.1.0",
  "authors": [{ "name": "Your Name" }],
  "compatibility": { "minimum": "14", "verified": "14.368", "maximum": "14" },
  "esmodules": ["module/forja.mjs"],
  "styles": ["styles/forja.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    },
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] }
    }
  },
  "grid": { "type": 1, "distance": 1.5, "units": "m" },
  "primaryTokenAttribute": "hp",
  "initiative": "1d20 + @attributes.agility.value",
  "background": "systems/forja/assets/background.webp",
  "socket": true,
  "url": "https://github.com/you/forja",
  "manifest": "https://github.com/you/forja/releases/latest/download/system.json",
  "download": "https://github.com/you/forja/releases/download/v0.1.0/forja.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```

::: warning
`template.json` is **deprecated** in V14. Declare every sub-type in `documentTypes` and register a `TypeDataModel` for it in `CONFIG.Actor.dataModels` / `CONFIG.Item.dataModels` (see [First system](#first-system) and [Data models](#data-models)).
:::
:::

## Supporting both V13 and V14

One manifest can cover both majors: `"minimum": "13", "verified": "14.368"`, no `maximum`. Then you must only use API that exists in V13 *or* guard V14 code:

```js
// Branch on the running core generation
if (game.release.generation >= 14) {
  // V14-only API here
} else {
  // V13 fallback
}
```

::: warning
The `"type"` field is new in V14. It is optional, so leave it out of a manifest that must also load in V13.
:::

## Pitfalls

- **`id` ≠ folder name** → package does not appear.
- **Wrong path case** (`Scripts/main.mjs` vs `scripts/main.mjs`) works on Windows and breaks on Linux servers.
- **`manifest` pointing at a specific version** → users never see updates. It must always serve the newest manifest.
- **Forgetting `documentTypes`** → your types don't show in the "Create Actor" dialog.
- **Changing `version` without updating `download`** → users install the old zip.
