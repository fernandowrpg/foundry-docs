# Authoring guide — Foundry Builder's Guide

This project is a bilingual (English + Brazilian Portuguese), version-aware documentation
site for building **modules and systems** for Foundry Virtual Tabletop **V13** and **V14**.
It is built to be localized: every string lives in a locale file, and adding a language means
adding one folder + one JSON file (see README.md).

## Files

```
content/nav.json            navigation: sections, page ids, versions, locales
content/<locale>/<page>.md  one Markdown file per page per locale (locale = en | pt-BR)
i18n/<locale>.json          UI strings (menus, buttons, labels)
build.py                    bundles everything into docs/index.html (GitHub Pages)
template.html               page shell (CSS + JS renderer)
```

## Page file rules

1. The FIRST line is `# Page title` (used in the sidebar and search).
2. The second paragraph is a one-sentence summary (shown under the title). Put it right after the H1.
3. Use `##` for sections and `###` for sub-sections (they build the "On this page" list).
4. Internal links: `[text](#page-id)` or `[text](#page-id--anchor)`. Page ids are listed in nav.json.
5. Code fences must declare a language: `js`, `json`, `hbs` (Handlebars), `css`, `html`, `bash`.
   Translate **code comments** and example UI strings into the page's locale; keep identifiers in English.
6. Same structure in `en` and `pt-BR`: identical headings order, identical code (only comments differ).

## Version blocks (the core feature)

The reader picks V13 or V14 in the top bar. Content that differs goes in fenced blocks:

```
::: v13
Only shown when the reader has V13 selected.
:::

::: v14
Only shown for V14.
:::
```

Everything outside a version block is shared by both versions. Keep shared text shared —
only wrap what actually differs. Blocks can contain code fences, lists, callouts.

### Callouts

```
::: tip
Helpful advice.
:::

::: warning
Things that break or bite.
:::

::: changed
What changed in this topic between V13 and V14. Rendered as a "Changed in V14" box
ONLY when V14 is selected. Every page whose topic changed in V14 MUST have one near the top,
with a short bullet list and a link to [the full changelog](#changes-14).
:::
```

Callouts may be nested inside version blocks (e.g. a `warning` inside `v13`).
Do not nest version blocks inside each other. Close every block with `:::` alone on a line.

## Style

- Audience: JavaScript developers new to Foundry. Explain *why*, then show complete, runnable code.
- Every entity page follows: **What it is → Define the type (data model) → Register it → Create it in code → Sheet/UI → Common recipes → Pitfalls**.
- Use the example system id `forja` (a tiny fantasy RPG) and module id `forja-extras` everywhere, so examples connect across pages.
- File paths: `systems/forja/...`, `modules/forja-extras/...`.
- Portuguese: natural Brazilian Portuguese, "você". **Titles, headings and page summaries are fully in
  Portuguese** (Atores, Itens, Efeitos ativos, Modelos de dados, Ganchos de eventos, Tela de jogo,
  Compêndios, Marcadores). English only appears as code: class and API names in backticks
  (`ActorSheetV2`, `flags`, `MeasuredTemplate`). Accepted loanwords: token, chat, HUD, CSS, JSON, macro.
- Never invent API. If unsure a name exists, say so and point to the API docs:
  https://foundryvtt.com/api/v13/ and https://foundryvtt.com/api/v14/
