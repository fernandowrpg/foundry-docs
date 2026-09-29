# Styling, Templates and Themes

Load your CSS, scope it so it does not leak, support light and dark themes, and organize Handlebars templates, partials and helpers.

::: changed
- `<code>` is now styled **inline** by default. Add the `block` class (`<code class="block">`) for a block of code.
- CSS hot reload follows `@import`, so you can split styles into several files and still get live reload.
- Applications can be **popped out** into a separate browser window. Keep all styling in your stylesheets instead of injecting `<style>` tags from JavaScript, so the styles are available in that window too.
- Font Awesome was updated to 7.2.
- See [the full changelog](#changes-14).
:::

## Load your stylesheets

List them in the manifest. Paths are relative to the package folder.

```json
{
  "styles": ["styles/forja.css"]
}
```

For more than a couple of files, keep one entry file and import the rest:

```css
/* styles/forja.css */
@import url("./variables.css");
@import url("./sheets.css");
@import url("./chat.css");
```

::: tip
Enable hot reload for CSS and templates while developing (see [Development setup](#setup)). Style changes then appear without reloading the world.
:::

## Scope every rule

Foundry, the system and all modules share one page. Unscoped selectors such as `h2 {}` or `.header {}` change other packages. Put your package id on your applications and prefix every rule with it.

```js
// In your ApplicationV2 / sheet
static DEFAULT_OPTIONS = { classes: ["forja", "sheet", "actor"] };
```

```css
/* Good: only affects Forja sheets */
.forja.sheet .attributes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }

/* Bad: changes every application in the world */
.window-content h2 { color: red; }
```

## CSS cascade layers (V13+)

Since V13 the core puts its own styles in **CSS cascade layers** (`@layer`). Two rules follow from how layers work:

1. Styles **outside** any layer beat styles inside a layer, regardless of selector specificity. Your plain package CSS overrides core styles without `!important` or long selectors.
2. If you want other modules to be able to override *your* styles easily, put your CSS in a layer of your own.

```css
/* Everything in this file can be overridden by unlayered CSS from other modules */
@layer forja {
  .forja.sheet .resource { border: 1px solid var(--forja-line); border-radius: 6px; }
}
```

Open the browser devtools and look at the **Layers** view of the Styles panel to see the core layer names in your version.

## Light and dark themes

V13 introduced Theme V2: the interface follows the operating system's light or dark preference, and users can override it. The core adds `.theme-dark` or `.theme-light` to the page and to applications. Define your colors as custom properties and switch them per theme instead of writing every rule twice.

```css
.forja {
  --forja-ink: #1f2530;
  --forja-paper: #f6f1e7;
  --forja-line: #c9bfae;
  --forja-accent: #9c3d17;
}
.theme-dark .forja,
.forja.theme-dark {
  --forja-ink: #e7e3dc;
  --forja-paper: #1d2129;
  --forja-line: #3a404c;
  --forja-accent: #f08a57;
}

.forja.sheet .window-content { background: var(--forja-paper); color: var(--forja-ink); }
.forja .roll-button { background: var(--forja-accent); color: var(--forja-paper); }
```

::: tip
The core defines many custom properties of its own (text colors, borders, fonts). Inspect `body` in the devtools and reuse them where it makes sense, so your sheets match the rest of the UI in both themes.
:::

You can force a theme on one application with the class:

```js
static DEFAULT_OPTIONS = { classes: ["forja", "sheet", "theme-light"] };  // always light, like parchment
```

## Templates and partials

Handlebars templates (`.hbs`) are fetched and compiled once. Preload partials in `init`, so they are available by name in other templates.

```js
Hooks.once("init", async () => {
  await foundry.applications.handlebars.loadTemplates([
    "systems/forja/templates/parts/resource-bar.hbs",
    "systems/forja/templates/parts/item-row.hbs"
  ]);
});
```

```hbs
{{!-- Use a partial by its path, passing data --}}
{{> "systems/forja/templates/parts/resource-bar.hbs" label="FORJA.HP" value=system.hp.value max=system.hp.max}}

{{!-- systems/forja/templates/parts/resource-bar.hbs --}}
<div class="forja resource-bar">
  <span class="label">{{localize label}}</span>
  <meter min="0" max="{{max}}" value="{{value}}"></meter>
  <span class="value">{{value}} / {{max}}</span>
</div>
```

Templates listed in an application's `PARTS` are loaded automatically; you only need `loadTemplates` for partials and for templates you render yourself with `renderTemplate`.

## Handlebars helpers

The core ships useful helpers: `localize`, `formGroup`, `formInput`, `selectOptions`, `editor`, `numberFormat`, `eq`, `ne`, `gt`, `and`, `or`, `not`, `ifThen`, `concat`. Register your own in `init`:

```js
Hooks.once("init", () => {
  // {{forjaSigned 3}} → "+3"
  Handlebars.registerHelper("forjaSigned", n => (Number(n) >= 0 ? `+${n}` : `${n}`));

  // {{#forjaTimes 3}}<i class="pip"></i>{{/forjaTimes}}
  Handlebars.registerHelper("forjaTimes", function(n, options) {
    let out = "";
    for ( let i = 0; i < n; i++ ) out += options.fn({ index: i });
    return out;
  });
});
```

::: warning
Prefix helper names with your package id. Helpers are global, and a module that registers `signed` can silently replace yours.
:::

## Icons

Foundry includes Font Awesome. Use the `fa-solid` / `fa-regular` classes:

```hbs
<button type="button" data-action="rollAttack"><i class="fa-solid fa-dice-d20"></i> {{localize "FORJA.Attack"}}</button>
```

::: v14
Font Awesome was updated to 7.2. Most icon names are unchanged, but check any icons you use that were renamed between major versions of Font Awesome.
:::

## Code snippets inside your UI

::: v13
Use `<code>` for short identifiers and `<pre><code>` for multi-line code, so the result looks the same everywhere.
:::

::: v14
`<code>` is inline by default. For a block, add the class:

```html
<p>Use <code>@UUID[...]</code> to link documents.</p>
<code class="block">Hooks.once("ready", () => console.log("forja ready"));</code>
```
:::

## Pop-out windows

::: v14
Dialogs and other ApplicationV2 windows can be popped out into their own browser window. That window is a separate `document`:

- Keep all CSS in your manifest stylesheets. Styles that you add at runtime with `document.head.append(style)` only exist in the main window.
- Use `this.element` (and elements inside it) instead of global `document.querySelector` in your application code.
- Tooltips and context menus work in the pop-out because the core activates them per window.
:::

## Pitfalls

- **`!important` everywhere**: with cascade layers you rarely need it. Remove it and check that the rule is outside any layer.
- **Fixed pixel sizes**: sheets are resizable and users change the UI scale. Prefer `rem`, `%`, grid and flex.
- **Colors that only work on one theme**: test every sheet in both the light and dark themes before release.
