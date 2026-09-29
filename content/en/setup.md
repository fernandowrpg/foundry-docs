# Development setup

Install Foundry for development, link your repository into the user data folder, and turn on hot reload and debugging tools.

::: changed
- V14 **cannot be upgraded in place** from V13: do a fresh install (you can point it at a copy of your data folder).
- CSS **hot reload now follows `@import`** — split stylesheets reload without a full refresh.
- Hot-reload render hooks receive information about the changed file.
- See [the full changelog](#changes-14).
:::

## Install Foundry for development

You need a license key and the download from your account page on foundryvtt.com. Two builds matter for developers:

- **Desktop app** (Windows/macOS/Linux) — an Electron app. Easiest to start with.
- **Node.js build** — a zip you run with `node`. Best for a dev server you restart often or run headless.

::: v13
V13 ships with **Electron 33** in the desktop app. The Node.js build requires **Node 20** (Node 22 is also supported).

```bash
# Node.js build, V13 (use Node 20 or 22)
node --version
cd ~/foundry/v13
node main.js --dataPath=$HOME/foundrydata-v13
```
:::

::: v14
V14 is a **fresh install**: the V13 app cannot update itself to V14. Install V14 into a new folder and use a **separate data folder** (or a copy of your V13 one) — worlds migrated by V14 cannot go back to V13.

```bash
# Node.js build, V14 — separate install folder and data folder
node --version
cd ~/foundry/v14
node main.js --dataPath=$HOME/foundrydata-v14
```
:::

::: tip
Keep one install and one data folder **per major version**. You will want to test your package on V13 and V14 side by side, and a migrated world is a one-way trip.
:::

::: warning
Check the Node version requirement in the release notes of the exact build you download. Running an unsupported Node version usually fails at startup with a syntax or native-module error.
:::

## The user data folder

The `--dataPath` (or the path chosen in the desktop app's settings) contains:

```bash
foundrydata/
├── Config/           # options.json (port, dataPath, etc.), license
├── Data/             # everything served to clients
│   ├── modules/      # one folder per module:  Data/modules/forja-extras/
│   ├── systems/      # one folder per system:  Data/systems/forja/
│   └── worlds/       # one folder per world:   Data/worlds/forja-dev/
└── Logs/             # server logs — check here when a package fails to load
```

Files under `Data/` are served by URL relative to that folder: `Data/systems/forja/templates/actor.hbs` becomes `systems/forja/templates/actor.hbs` in your code.

::: warning
The folder name **must equal the package `id`** in the manifest. `Data/modules/forja_extras/` with `"id": "forja-extras"` will not load.
:::

## Link your repository

Keep your git repository somewhere else (e.g. `~/dev/forja`) and **symlink** it into the data folder. You edit and commit in one place, and can link the same repo into the V13 and V14 data folders.

```bash
# Linux / macOS
ln -s ~/dev/forja        ~/foundrydata-v14/Data/systems/forja
ln -s ~/dev/forja-extras ~/foundrydata-v14/Data/modules/forja-extras
```

```bash
# Windows (Command Prompt as administrator, or with Developer Mode on)
mklink /D "%LOCALAPPDATA%\FoundryVTT\Data\systems\forja" "C:\dev\forja"
mklink /D "%LOCALAPPDATA%\FoundryVTT\Data\modules\forja-extras" "C:\dev\forja-extras"
```

Restart Foundry (or return to Setup) after creating a link: packages are discovered when the server starts or when the Setup screen refreshes.

## Create a dev world

1. On the Setup screen, open **Game Worlds → Create World**.
2. Give it an id like `forja-dev` and choose your system (`forja`).
3. Launch it, log in as **Gamemaster**, and enable your modules under **Game Settings → Manage Modules**.

::: tip
Create a second world with only your module and a popular system to catch accidental dependencies. Keep a "clean" world with no other modules for bug reports — it rules out conflicts.
:::

## Editor setup (VS Code)

Foundry's client code ships with the app as readable JavaScript modules with JSDoc. Pointing your editor at it gives autocompletion for `foundry.*` without extra packages.

```json
{
  "compilerOptions": {
    "module": "ES2022",
    "target": "ES2022",
    "checkJs": false,
    "baseUrl": "."
  },
  "include": [
    "module/**/*.mjs",
    "scripts/**/*.mjs",
    "../../foundry/v14/resources/app/client/**/*.mjs",
    "../../foundry/v14/resources/app/common/**/*.mjs"
  ]
}
```

Save this as `jsconfig.json` in your repo root and adjust the paths to where your Foundry install lives (the `client` and `common` folders are inside the install's `resources/app/` or at its root, depending on the build).

::: tip
Community TypeScript definitions exist (`@league-of-foundry-developers/foundry-vtt-types`), but they may lag behind the latest major version. Check their README for V13/V14 support before relying on them.
:::

## Hot reload

Without hot reload, every CSS, template or translation change needs an F5. Declare which files the server should watch in your manifest under `flags.hotReload`:

```json
{
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "html", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```

- `extensions` — file types that trigger a reload.
- `paths` — folders (relative to the package root) to watch.
- **CSS** is swapped live, **templates** are re-fetched and open applications re-render, **lang** files are re-merged.
- JavaScript is **not** hot-reloaded — reload the page (F5) after changing `.mjs` files.

::: v14
In V14 hot reload also follows CSS **`@import`**: if `styles/forja.css` imports `styles/actor.css`, editing `actor.css` reloads it too. The hot-reload render also receives the changed file's context, so applications can decide whether they need to re-render.
:::

::: v13
In V13 only the files listed directly in `styles` are hot-swapped. If you split CSS with `@import`, changes to imported files may need a page reload.
:::

::: warning
Hot reload only works when the server can see file changes. Some symlinked folders on network drives or WSL mounts do not emit change events — edit files on the same filesystem that Foundry runs on.
:::

## Browser devtools

Open the developer tools with **F12** (desktop app or browser). You can also connect a normal browser to `http://localhost:30000` — Chrome/Firefox devtools are more comfortable than Electron's.

- **Console** — run any API call: `game.actors.contents`, `canvas.tokens.controlled`, `CONFIG.Actor.dataModels`.
- **Sources** — your files appear under `systems/forja/…`; set breakpoints in `.mjs` files.
- **Network** — check for `404` on templates or language files.

### Log every hook

Foundry can print every hook call with its arguments. This is the fastest way to discover *which* hook to use:

```js
// In the browser console
CONFIG.debug.hooks = true;
// Now open a sheet, move a token, send a chat message... and watch the log.
// Turn it off again:
CONFIG.debug.hooks = false;
```

::: tip
Right-click an element and choose **Inspect** to find the application class and `data-action` attributes; then search the API docs for that class.
:::

### Handy console snippets

```js
// The document behind the first open sheet
foundry.applications.instances.values().next().value?.document;

// Your package's manifest, as loaded
game.system.id;                    // "forja"
game.modules.get("forja-extras");  // Module object, .active tells if enabled
```

## Git tips

- Commit the package folder itself (manifest at the repo root), so the repo can be symlinked directly.
- Add a `.gitignore` for build output and compiled packs if you generate them:

```bash
node_modules/
dist/
*.zip
# LevelDB compendium files change on every open; commit their source instead
packs/*/LOCK
packs/*/LOG*
```

- Use **tags** that match `version` in the manifest (`v0.1.0`). Release tooling and update checks rely on the version string. See [Packaging & release](#packaging).
- Test on **both** V13 and V14 before tagging if your `compatibility` range covers both.

## Next steps

Continue with [the manifest](#manifest), then build [your first module](#first-module).
