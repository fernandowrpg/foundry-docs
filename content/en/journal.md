# Journal Entries and Pages

JournalEntry documents hold pages of text, images, PDFs and video; you can add your own page types, text enrichers and rich-text editing to sheets.

::: changed
- **TinyMCE is gone**: ProseMirror is the only rich-text editor (`foundry.prosemirror.defaultPlugins` → `foundry.applications.ux.ProseMirrorEditor.buildDefaultPlugins()`).
- ProseMirror gains collapsible **details** blocks, **tables**, font size/colour and captions.
- `CONFIG[documentName].embedHandlers` lets you customise how a document type is rendered by `@Embed`.
- `JournalEntrySheet#viewedPageDocuments` exposes the pages currently shown.
- `BaseJournalEntryPage` gets `LOCALIZATION_PREFIXES`, so page field labels are auto-localized.
- See [the full changelog](#changes-14).
:::

## What it is

A **JournalEntry** is a primary document (sidebar, compendiums) that contains embedded
**JournalEntryPage** documents. Each page has a `type`; core provides:

| Type | Key data | Notes |
| --- | --- | --- |
| `text` | `text.content`, `text.format` (`CONST.JOURNAL_ENTRY_PAGE_FORMATS.HTML` or `MARKDOWN`) | the default |
| `image` | `src`, `image.caption` | |
| `pdf` | `src` | rendered with the built-in PDF viewer |
| `video` | `src`, `video.{controls, loop, autoplay, volume, timestamp, width, height}` | also YouTube URLs |

All pages share `name`, `title.{show, level}` (heading shown in the entry and its table of
contents), `sort`, `ownership` and `flags`. Page ownership is checked separately from the
entry, so a GM can hide a single "secret" page from players.

## Create it in code

```js
const entry = await JournalEntry.create({
  name: "Forja: Lore",
  pages: [
    {
      name: "The Iron Kingdom",
      type: "text",
      title: { show: true, level: 1 },
      text: {
        format: CONST.JOURNAL_ENTRY_PAGE_FORMATS.HTML,
        content: "<p>Forged in fire. See @UUID[Actor.abc123def456gh78]{the Smith King}.</p>"
      }
    },
    {
      name: "Map of the Kingdom",
      type: "image",
      src: "systems/forja/assets/maps/kingdom.webp",
      image: { caption: "The known world" }
    }
  ]
});

// Open the entry on a specific page
const page = entry.pages.getName("Map of the Kingdom");
entry.sheet.render({ force: true, pageId: page.id });
```

Add a page to an existing entry with
`entry.createEmbeddedDocuments("JournalEntryPage", [data])`.

## Links and enrichment

Rich text in Foundry is stored as raw HTML and **enriched** at render time. Enrichment turns
text patterns into live HTML:

- `@UUID[Actor.abc123]{Label}` — a content link (drag, click to open). Works with compendium
  UUIDs: `@UUID[Compendium.forja.items.Item.xyz]`.
- `@UUID[.pageId]` — relative link to a sibling page of the same entry.
- `@Embed[JournalEntry.abc.JournalEntryPage.def]` — embeds the page's content inline.
- `[[/r 1d20+3]]` and `[[1d6]]` — roll links and inline rolls.
- `<section class="secret">` — visible only to owners (when `secrets: true`).

In your own sheets **always** enrich before displaying rich text:

```js
// Inside an ApplicationV2 sheet's _prepareContext
const TextEditor = foundry.applications.ux.TextEditor.implementation;
context.enrichedBiography = await TextEditor.enrichHTML(this.document.system.biography, {
  secrets: this.document.isOwner,  // show secret sections to owners only
  rollData: this.document.getRollData(),
  relativeTo: this.document         // resolves relative @UUID links
});
```

```hbs
{{!-- Editable rich-text field --}}
<prose-mirror name="system.biography" value="{{system.biography}}"
              data-document-uuid="{{document.uuid}}" toggled>
  {{{enrichedBiography}}}
</prose-mirror>
```

## Custom enrichers

`CONFIG.TextEditor.enrichers` is an array of `{ pattern, enricher }` objects. `pattern` must be a
global `RegExp`; `enricher(match, options)` is async and returns an `HTMLElement` (or `null` to
leave the text as is).

```js
// modules/forja-extras/scripts/enrichers.mjs
// Syntax: @Check[strength|dc=12]
Hooks.once("init", () => {
  CONFIG.TextEditor.enrichers.push({
    pattern: /@Check\[(\w+)(?:\|dc=(\d+))?\]/gi,
    enricher: async (match, options) => {
      const [, ability, dc] = match;
      const a = document.createElement("a");
      a.classList.add("forja-check");
      a.dataset.ability = ability;
      if (dc) a.dataset.dc = dc;
      const label = game.i18n.localize(`FORJA.Ability.${ability}`);
      a.innerHTML = `<i class="fa-solid fa-dice-d20"></i> ${label}${dc ? ` (DC ${dc})` : ""}`;
      return a;
    }
  });

  // One delegated listener handles every enriched link, wherever it is rendered
  document.body.addEventListener("click", event => {
    const link = event.target.closest("a.forja-check");
    if (!link) return;
    event.preventDefault();
    const actor = canvas.tokens.controlled[0]?.actor ?? game.user.character;
    if (!actor) return ui.notifications.warn("FORJA.NoActor", { localize: true });
    actor.system.rollCheck?.(link.dataset.ability, { dc: Number(link.dataset.dc) || null });
  });
});
```

::: tip
The enricher config also accepts extra keys (such as `id`, `replaceParent` and a render callback) in
recent versions. Check `TextEditorEnricherConfig` in the API for the version you target.
:::

## Define a custom page type (data model)

A module can add a page type, for example an "NPC note" with structured fields. Declare it in
the manifest (module types are namespaced as `forja-extras.npcnote`):

```json
{
  "id": "forja-extras",
  "documentTypes": {
    "JournalEntryPage": {
      "npcnote": { "htmlFields": ["notes"] }
    }
  }
}
```

`htmlFields` tells core which fields contain HTML (for search and enrichment of links).

```js
// modules/forja-extras/scripts/npc-note.mjs
const { fields } = foundry.data;

export class NpcNoteData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA_EXTRAS.NpcNote"];

  static defineSchema() {
    return {
      actor: new fields.DocumentUUIDField({ type: "Actor" }),
      role: new fields.StringField({ required: true, initial: "" }),
      attitude: new fields.StringField({
        required: true, initial: "neutral",
        choices: { friendly: "FORJA_EXTRAS.NpcNote.Friendly", neutral: "FORJA_EXTRAS.NpcNote.Neutral", hostile: "FORJA_EXTRAS.NpcNote.Hostile" }
      }),
      notes: new fields.HTMLField()
    };
  }
}
```

## Sheet

Page sheets have two modes: **view** (inside the journal) and **edit** (its own window). The
Handlebars base class for page sheets is
`foundry.applications.sheets.journal.JournalEntryPageHandlebarsSheet`, with separate `VIEW_PARTS`
and `EDIT_PARTS`.

```js
// modules/forja-extras/scripts/npc-note-sheet.mjs
const Base = foundry.applications.sheets.journal.JournalEntryPageHandlebarsSheet;

export class NpcNoteSheet extends Base {
  static DEFAULT_OPTIONS = { classes: ["forja-extras", "npc-note"] };

  static EDIT_PARTS = {
    header: Base.EDIT_PARTS.header,
    content: { template: "modules/forja-extras/templates/npc-note-edit.hbs" },
    footer: Base.EDIT_PARTS.footer
  };

  static VIEW_PARTS = {
    content: { template: "modules/forja-extras/templates/npc-note-view.hbs" }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const system = this.document.system;
    context.system = system;
    context.fields = system.schema.fields;
    context.linkedActor = system.actor ? await fromUuid(system.actor) : null;
    context.enrichedNotes = await foundry.applications.ux.TextEditor.implementation.enrichHTML(
      system.notes, { secrets: this.document.isOwner, relativeTo: this.document });
    return context;
  }
}
```

```hbs
{{!-- modules/forja-extras/templates/npc-note-edit.hbs --}}
<section class="npc-note-edit">
  {{formGroup fields.actor value=system.actor}}
  {{formGroup fields.role value=system.role localize=true}}
  {{formGroup fields.attitude value=system.attitude localize=true}}
  <prose-mirror name="system.notes" value="{{system.notes}}" toggled>{{{enrichedNotes}}}</prose-mirror>
</section>
```

```hbs
{{!-- modules/forja-extras/templates/npc-note-view.hbs --}}
<article class="npc-note-view attitude-{{system.attitude}}">
  {{#if linkedActor}}<img src="{{linkedActor.img}}" alt="{{linkedActor.name}}">{{/if}}
  <p><strong>{{system.role}}</strong></p>
  <div class="notes">{{{enrichedNotes}}}</div>
</article>
```

## Register it

```js
// modules/forja-extras/scripts/main.mjs
import { NpcNoteData } from "./npc-note.mjs";
import { NpcNoteSheet } from "./npc-note-sheet.mjs";

Hooks.once("init", () => {
  CONFIG.JournalEntryPage.dataModels["forja-extras.npcnote"] = NpcNoteData;
  foundry.applications.apps.DocumentSheetConfig.registerSheet(JournalEntryPage, "forja-extras", NpcNoteSheet, {
    types: ["forja-extras.npcnote"],
    makeDefault: true,
    label: "FORJA_EXTRAS.NpcNote.Sheet"
  });
});
```

Add `"TYPES": { "JournalEntryPage": { "forja-extras.npcnote": "NPC Note" } }` to your language
file so the type shows up nicely in the "create page" dialog.

::: v14
## ProseMirror in V14

With TinyMCE removed, every rich-text field uses ProseMirror. New in V14:

- **Details** (collapsible sections) and **tables** in the editor menu; font size, colour and
  image captions.
- Inline and block content templates in the editor.
- If you extended the editor with plugins, build the defaults with
  `foundry.applications.ux.ProseMirrorEditor.buildDefaultPlugins()` instead of reading
  `foundry.prosemirror.defaultPlugins`.
- `CONFIG[documentName].embedHandlers` customises how a document is embedded by `@Embed`. The
  exact handler signature is in the [V14 API](https://foundryvtt.com/api/v14/).
- `JournalEntrySheet#viewedPageDocuments` returns the pages currently displayed, handy for
  modules that add controls to the visible page.
:::

## Pitfalls

::: warning
- Displaying `system.notes` with `{{{ }}}` **without** enriching shows raw `@UUID[...]` text and,
  worse, reveals secret sections to players.
- Enricher regexes need the `g` flag; without it core throws or matches only once.
- Enrichers run on every client and for every render: keep them fast and don't create documents
  from inside them.
- Page ownership is separate from the entry's: a player may see the entry but not a page.
- A custom page type without a registered sheet falls back to nothing usable: always register one.
:::
