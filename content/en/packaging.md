# Packaging and distribution

Version, build, release and publish your system or module, and support V13 and V14 from one codebase.

::: changed
- The manifest accepts an optional explicit `"type": "system"` or `"type": "module"` field.
- V14 cannot be updated in place from V13, so test on a fresh V14 install.
- World packages can no longer be installed from Setup — ship content as Adventure documents in a compendium.
- See [the full changelog](#changes-14).
:::

## How installation works

When a user pastes a manifest URL (or picks your package from the list), Foundry:

1. Downloads the manifest JSON from `manifest`.
2. Checks `compatibility` against the running core version and `relationships` against installed packages.
3. Downloads the zip from `download` and extracts it into `Data/systems/<id>/` or `Data/modules/<id>/`.
4. Later, "Check for updates" fetches `manifest` again and compares `version` — if it is newer, it downloads the new `download`.

So the two URLs have different jobs:

- `manifest` must always point at the **latest** manifest (so updates are found).
- `download` must point at the zip **for this exact version** (so the manifest and the files match).

## Versioning

Use [semantic versioning](https://semver.org/): `MAJOR.MINOR.PATCH`. Foundry compares versions
with `foundry.utils.isNewerVersion`, which handles dotted numbers. Bump:

- **PATCH** for fixes,
- **MINOR** for features that do not break data,
- **MAJOR** when you drop a core version or need a [world migration](#migrations).

## Manifest fields for distribution

```json
{
  "id": "forja",
  "title": "Forja",
  "version": "2.1.0",
  "compatibility": {
    "minimum": "13",
    "verified": "14.368"
  },
  "url": "https://github.com/forja-rpg/forja",
  "manifest": "https://github.com/forja-rpg/forja/releases/latest/download/system.json",
  "download": "https://github.com/forja-rpg/forja/releases/download/v2.1.0/forja.zip",
  "bugs": "https://github.com/forja-rpg/forja/issues",
  "changelog": "https://github.com/forja-rpg/forja/blob/main/CHANGELOG.md",
  "relationships": {
    "requires": [],
    "recommends": [
      {
        "id": "forja-extras",
        "type": "module",
        "reason": "Extra compendiums and automation"
      }
    ]
  }
}
```

::: v13
V13 does not define the `type` field: the file name (`system.json` / `module.json`) is what
tells Foundry the package kind. While your `minimum` is still 13, the safest choice is to omit it.
:::

::: v14
`"type": "system" | "module"` is optional and makes the package kind explicit (useful for tools
that read the manifest without knowing the file name). Add it once your `minimum` is 14:

```json
{
  "id": "forja",
  "type": "system",
  "compatibility": { "minimum": "14", "verified": "14.368" }
}
```
:::

### Compatibility ranges

| Key | Meaning | Effect |
| --- | --- | --- |
| `minimum` | Oldest core version that can run it | Older cores refuse to install/enable |
| `verified` | Newest version you actually tested | Newer cores show a "not verified" warning |
| `maximum` | Newest version allowed | Newer cores refuse to enable |

Use generation numbers (`"13"`, `"14"`) for broad ranges, full builds (`"14.368"`) for
`verified`. Set `maximum` only if you *know* the next generation breaks you.

### Relationships

`relationships.requires` blocks activation until the dependency is installed and enabled;
`recommends` only suggests; `conflicts` warns. Each entry can carry its own
`compatibility` range, for example `forja-extras` requiring `forja` `>= 2.0.0`:

```json
{
  "relationships": {
    "systems": [
      { "id": "forja", "type": "system", "compatibility": { "minimum": "2.0.0" } }
    ]
  }
}
```

## Zip layout

The zip must contain the package files at the **root** (not inside a `forja/` folder):

```bash
forja.zip
├── system.json
├── forja.mjs
├── module/
├── templates/
├── styles/
├── lang/
│   ├── en.json
│   └── pt-BR.json
└── packs/          # compiled LevelDB compendiums
    └── monsters/
```

Leave out `src/`, `node_modules/`, `.git/` and the YAML/JSON sources of your packs.

## Building compendiums with the fvtt CLI

Keep compendium content as JSON/YAML in git (`src/packs/<name>/`) and compile it into
LevelDB at release time with [`@foundryvtt/foundryvtt-cli`](https://github.com/foundryvtt/foundryvtt-cli):

```bash
npm install --save-dev @foundryvtt/foundryvtt-cli
```

```js
// tools/build-packs.mjs
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { readdir } from "node:fs/promises";

const packs = await readdir("src/packs", { withFileTypes: true });
for (const dir of packs.filter((d) => d.isDirectory())) {
  console.log(`Compiling ${dir.name}`);
  await compilePack(`src/packs/${dir.name}`, `packs/${dir.name}`, { yaml: true, log: true });
}
```

The reverse (`extractPack`) turns an edited LevelDB pack back into YAML so you can commit changes
made inside Foundry.

::: warning
Close Foundry (or at least the world) before compiling into a `packs/` folder it is using —
LevelDB holds a lock on open packs.
:::

## Release workflow with GitHub Actions

Push a tag like `v2.1.0` and the workflow builds packs, writes the version and download URL into
the manifest, zips everything and publishes a GitHub release with **both** `system.json` and
`forja.zip` as assets. Because the release is "latest", `releases/latest/download/system.json`
now serves the new manifest.

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    env:
      FOUNDRY_RELEASE_TOKEN: ${{ secrets.FOUNDRY_RELEASE_TOKEN }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22

      - run: npm ci

      - name: Build compendiums
        run: node tools/build-packs.mjs

      - name: Write version and URLs into the manifest
        run: |
          VERSION="${GITHUB_REF_NAME#v}"
          REPO="https://github.com/${GITHUB_REPOSITORY}"
          jq --arg v "$VERSION" \
             --arg m "$REPO/releases/latest/download/system.json" \
             --arg d "$REPO/releases/download/${GITHUB_REF_NAME}/forja.zip" \
             '.version=$v | .manifest=$m | .download=$d' system.json > tmp.json
          mv tmp.json system.json

      - name: Zip package
        run: zip -r forja.zip system.json forja.mjs module templates styles lang packs assets

      - name: Publish GitHub release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            system.json
            forja.zip
          generate_release_notes: true

      - name: Notify the Foundry package listing
        if: ${{ env.FOUNDRY_RELEASE_TOKEN != '' }}
        run: |
          VERSION="${GITHUB_REF_NAME#v}"
          curl -sSf -X POST https://foundryvtt.com/_api/packages/release_version/ \
            -H "Content-Type: application/json" \
            -H "Authorization: $FOUNDRY_RELEASE_TOKEN" \
            -d "{
              \"id\": \"forja\",
              \"release\": {
                \"version\": \"$VERSION\",
                \"manifest\": \"https://github.com/${GITHUB_REPOSITORY}/releases/download/${GITHUB_REF_NAME}/system.json\",
                \"notes\": \"https://github.com/${GITHUB_REPOSITORY}/releases/tag/${GITHUB_REF_NAME}\",
                \"compatibility\": { \"minimum\": \"13\", \"verified\": \"14.368\" }
              }
            }"
```

For a module, replace `system.json` with `module.json` and `forja` with `forja-extras`.

::: tip
The Package Release API requires a manifest URL for the **specific** release (not `latest`),
as in the last step. Add `"dry-run": true` to the body to test your token first. Sending two
releases within 60 seconds returns `429 Too Many Requests`.
:::

## Publishing on foundryvtt.com

1. Log in at foundryvtt.com and create your package listing from your account's package
   admin ("Submit a package"). The package id must match the manifest `id`.
2. Fill in the title, description, and the **manifest URL** of a release.
3. After approval, every new version is registered either manually in the admin page or
   automatically with the Package Release API token shown there (store it as the
   `FOUNDRY_RELEASE_TOKEN` repository secret).

See the official guides at https://foundryvtt.com/article/package-release-api/ and the
Knowledge Base on package submission.

## Supporting V13 and V14 in one codebase

Many packages keep `minimum: "13"` for a while. Detect features at runtime instead of
maintaining two branches:

```js
// systems/forja/module/compat.mjs
export const compat = {
  /** Core generation number: 13 or 14. */
  get generation() {
    return game.release.generation;
  },

  get isV14() {
    return game.release.generation >= 14;
  },

  /** True when the running build is newer than `build` (e.g. "14.360"). */
  isAfter(build) {
    return foundry.utils.isNewerVersion(game.version, build);
  },

  /** Deep equality that works in both versions. */
  equals(a, b) {
    return (foundry.utils.equals ?? foundry.utils.objectsEqual)(a, b);
  },

  /** localize with data in V14, format in V13. */
  localize(key, data) {
    if (!data) return game.i18n.localize(key);
    return this.isV14 ? game.i18n.localize(key, data) : game.i18n.format(key, data);
  },

  /** Roll-to-chat options. `mode` uses the V14 names: public, gm, blind, self. */
  toMessageOptions(mode) {
    if (this.isV14) return { messageMode: mode };
    const ROLL_MODES = { public: "publicroll", gm: "gmroll", blind: "blindroll", self: "selfroll" };
    return { rollMode: ROLL_MODES[mode] ?? mode };
  },

  /** The raw changes array, wherever this version stores it. */
  effectChanges(effect) {
    return effect.system?.changes ?? effect.changes ?? [];
  }
};
```

```js
import { compat } from "./compat.mjs";

const roll = await new Roll("1d20 + @might", actor.getRollData()).evaluate();
await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) }, compat.toMessageOptions("gm"));
```

Why two checks: `game.release.generation` is a plain number (13 or 14) and is the simplest
way to branch on the major version. `foundry.utils.isNewerVersion(game.version, "14.360")`
compares full builds, which you need when a fix landed in a specific point release.

::: warning
Prefer **feature detection** (`"changes" in effect.system`) over version checks when possible —
it survives future point releases that backport or rename things.
:::

## Testing matrix

Before tagging a release, run the same smoke test on each supported core:

| Check | V13 (13.351) | V14 (14.368) |
| --- | --- | --- |
| Fresh world creation, no console errors | ✔ | ✔ |
| Open every sheet type | ✔ | ✔ |
| Roll to chat in each message/roll mode | ✔ | ✔ |
| Apply and expire an active effect | ✔ | ✔ |
| World migration from the previous release | ✔ | ✔ |
| Compendium import | ✔ | ✔ |
| Module `forja-extras` enabled | ✔ | ✔ |

Keep one Foundry install per generation (separate data paths) so you can switch quickly;
remember that V14 must be a separate install.

## Pitfalls

::: warning
- `manifest` pointing at a specific version — users never see updates.
- `download` pointing at `latest` — an old manifest downloads new files and the versions disagree.
- Zipping the parent folder — the package ends up at `Data/systems/forja/forja/` and is not found.
- Forgetting to bump `version` — "Check for updates" compares versions, not dates.
- Shipping `node_modules` or pack sources — huge downloads, no benefit.
:::
