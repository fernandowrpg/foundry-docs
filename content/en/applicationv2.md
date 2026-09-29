# ApplicationV2

The window framework behind every Foundry V13+ interface: how to declare an application, render it with Handlebars, react to clicks and submit forms.

::: changed
- Applications can be **popped out** into a separate browser window (`detachWindow()` / `attachWindow()`, `_onDetach` / `_onAttach`).
- New static generator `ApplicationV2.instances()` to iterate open applications.
- Actions support **`auxclick`**, so middle-click can be routed to a handler.
- Window header controls and `ContextMenu` share one entry format (`ContextMenuEntry#icon` accepts class names).
- `options.isFirstRender` is populated automatically, so `_canRender` can tell a first render apart.
- See [the full changelog](#changes-14).
:::

## What it is

`foundry.applications.api.ApplicationV2` is the base class for every window, sheet, dialog and sidebar in Foundry V13 and V14. It replaced the old `Application` (AppV1) class. You almost never extend it alone: you combine it with a rendering mixin, usually `HandlebarsApplicationMixin`, which turns Handlebars templates into DOM.

An application is described by **static configuration** (`DEFAULT_OPTIONS`, `PARTS`, `TABS`) and a small set of **lifecycle methods** you override. Foundry handles the frame, dragging, resizing, minimizing, positioning and re-rendering.

### Differences from AppV1

| AppV1 (`Application`) | AppV2 (`ApplicationV2`) |
|---|---|
| `static get defaultOptions()` + `mergeObject` | `static DEFAULT_OPTIONS = {}` merged automatically along the class chain |
| `getData()` | `async _prepareContext(options)` |
| `activateListeners(html)` with a jQuery object | `data-action` attributes + `_onRender(context, options)` with a plain `HTMLElement` |
| Single `template` | Multiple `PARTS`, each re-renderable on its own |
| `FormApplication#_updateObject` | `form.handler` in `DEFAULT_OPTIONS` |
| `render(true)` | `render({ force: true })` (`render(true)` still works as a shorthand) |

::: warning
`this.element` is an `HTMLElement`, **not** jQuery. `html.find(...)` throws. Use `querySelector`, `querySelectorAll` and `addEventListener`.
:::

## Declare an application

A complete, self-contained example: a small "Forge Tracker" window for the `forja` system.

```js
// systems/forja/module/apps/forge-tracker.mjs
const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

export class ForgeTracker extends HandlebarsApplicationMixin(ApplicationV2) {
  /** Options are merged with those of every parent class. */
  static DEFAULT_OPTIONS = {
    id: "forja-forge-tracker",
    classes: ["forja", "forge-tracker"],
    tag: "form",                       // the outer element is a <form>
    window: {
      title: "FORJA.ForgeTracker.Title",   // localization key, translated automatically
      icon: "fa-solid fa-hammer",
      resizable: true,
      contentTag: "section",
      controls: [
        { icon: "fa-solid fa-rotate", label: "FORJA.ForgeTracker.Reset", action: "reset" }
      ]
    },
    position: { width: 420, height: "auto" },
    actions: {
      addHeat: ForgeTracker.#onAddHeat,
      reset: ForgeTracker.#onReset
    },
    form: {
      handler: ForgeTracker.#onSubmit,
      submitOnChange: true,
      closeOnSubmit: false
    }
  };

  /** Each part is a template rendered into its own element. */
  static PARTS = {
    header: { template: "systems/forja/templates/apps/forge-header.hbs" },
    body: {
      template: "systems/forja/templates/apps/forge-body.hbs",
      scrollable: [""]   // keep the scroll position of the part root between renders
    }
  };

  /** Plain instance state (not saved anywhere). */
  heat = 0;
  label = "";

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    return Object.assign(context, {
      heat: this.heat,
      label: this.label,
      hot: this.heat >= 5
    });
  }

  /** Called once per part; add part-specific data here. */
  async _preparePartContext(partId, context, options) {
    context = await super._preparePartContext(partId, context, options);
    if ( partId === "header" ) context.subtitle = game.i18n.localize("FORJA.ForgeTracker.Subtitle");
    return context;
  }

  static async #onAddHeat(event, target) {
    // `this` is the application instance, `target` is the element with data-action
    this.heat += Number(target.dataset.amount ?? 1);
    this.render({ parts: ["body"] });   // re-render only the body part
  }

  static async #onReset(event, target) {
    this.heat = 0;
    this.render();
  }

  static async #onSubmit(event, form, formData) {
    // formData.object is a flat object keyed by input name
    this.label = formData.object.label ?? "";
  }
}
```

```hbs
{{!-- systems/forja/templates/apps/forge-header.hbs --}}
<header class="forge-header">
  <h2>{{subtitle}}</h2>
</header>
```

```hbs
{{!-- systems/forja/templates/apps/forge-body.hbs --}}
<div class="forge-body {{#if hot}}hot{{/if}}">
  <label>Label <input type="text" name="label" value="{{label}}"></label>
  <p>Heat: <strong>{{heat}}</strong></p>
  <button type="button" data-action="addHeat" data-amount="1">+1</button>
  <button type="button" data-action="addHeat" data-amount="3">+3</button>
</div>
```

Open it from anywhere (a macro, a hook, a button):

```js
import { ForgeTracker } from "./apps/forge-tracker.mjs";

const tracker = new ForgeTracker();
tracker.render({ force: true });
```

::: tip
Every part template must have **exactly one root element**. A part with two top-level elements (or bare text) throws when rendered.
:::

## DEFAULT_OPTIONS in depth

| Key | Purpose |
|---|---|
| `id` | HTML id of the outer element. Use `{id}` inside it to get a unique id per instance (e.g. `"forja-note-{id}"`). |
| `classes` | CSS classes on the outer element. Always include your system/module class so your CSS can be scoped (see [Styling](#styling)). |
| `tag` | Outer element tag. `"form"` is required if you want `form` handling. |
| `window` | `title`, `icon`, `resizable`, `minimizable`, `frame`, `contentTag`, `contentClasses`, `controls` (header menu entries). |
| `position` | Default `width`, `height`, `top`, `left`, `scale`, `zIndex`. |
| `actions` | Map of `data-action` names to handlers. |
| `form` | `handler`, `submitOnChange`, `closeOnSubmit`. |

### Inheritance merge

`DEFAULT_OPTIONS` is **not** replaced by subclasses — Foundry walks the class chain and deep-merges each level. So a subclass only declares what it adds:

```js
export class HotForgeTracker extends ForgeTracker {
  static DEFAULT_OPTIONS = {
    classes: ["hot-variant"],          // arrays like `classes` are combined with the parent's
    position: { width: 520 },          // only width changes; height stays "auto"
    actions: { quench: HotForgeTracker.#onQuench }  // parent actions are still available
  };

  static #onQuench(event, target) {
    this.heat = 0;
    this.render();
  }
}
```

The same merge applies to `PARTS` only if you do it yourself: `PARTS` is a plain static object, so a subclass that declares `PARTS` **replaces** the parent's. Spread the parent's if you want to extend it: `static PARTS = { ...ForgeTracker.PARTS, footer: {...} }`.

## The render lifecycle

`render(options)` runs these steps, in order:

1. `_canRender(options)` — return `false` to cancel the render silently (or throw to cancel with an error).
2. `_prepareContext(options)` — build the shared data object.
3. `_preparePartContext(partId, context, options)` — per part, for each part being rendered.
4. `_preRender(context, options)` — just before HTML replacement.
5. HTML is rendered and inserted; the window is created the first time.
6. `_onFirstRender(context, options)` — **only the first time** the app is rendered. Good for one-time setup (e.g. registering a hook whose id you store).
7. `_onRender(context, options)` — **every render**. Attach non-click listeners here (`change`, `input`, `dragstart`).
8. `_onClose(options)` — when the app closes. Clean up hooks and timers here.

```js
async _onFirstRender(context, options) {
  await super._onFirstRender(context, options);
  // Re-render when any actor changes; remember the id so we can remove it
  this._actorHook = Hooks.on("updateActor", () => this.render());
}

async _onRender(context, options) {
  await super._onRender(context, options);
  const input = this.element.querySelector("input[name=label]");
  input?.addEventListener("input", ev => ev.target.classList.toggle("empty", !ev.target.value));
}

_onClose(options) {
  super._onClose(options);
  Hooks.off("updateActor", this._actorHook);
}

_canRender(options) {
  // Refuse to render for players
  if ( !game.user.isGM ) return false;
}
```

::: v14
In V14, `options.isFirstRender` is set automatically, so `_canRender` can distinguish "open the window" from "refresh an open window":

```js
_canRender(options) {
  // Allow refreshes, but only let a GM open the window for the first time
  if ( options.isFirstRender && !game.user.isGM ) return false;
}
```
:::

::: warning
Listeners added in `_onRender` are added again on every render. Because the part HTML is replaced, the old elements (and their listeners) are discarded, so this is fine for elements *inside* parts. But never add listeners to `this.element` itself or to `document` in `_onRender` — they will pile up. Use `_onFirstRender` for those.
:::

### `render({ force: true })`

`render()` without `force` only re-renders an application that is **already open**. To open a closed app, pass `force: true`. You can also pass `parts: ["body"]` to re-render only some parts, `position` to move it, or `tab` to activate a tab.

## Actions

Any element with `data-action="name"` inside the application calls the handler registered under `actions.name`. Handlers are called with `this` bound to the application, and receive the `PointerEvent` and the element carrying `data-action` (`target`).

Declare them as `static #private` methods: they do not pollute the instance, subclasses cannot call them by accident, and `this` still refers to the instance.

```js
static DEFAULT_OPTIONS = {
  actions: {
    addHeat: ForgeTracker.#onAddHeat,
    // Object form: choose which mouse buttons trigger the action (0 = left, 2 = right)
    inspect: { handler: ForgeTracker.#onInspect, buttons: [0, 2] }
  }
};
```

::: v14
V14 also dispatches actions for `auxclick` events, so the middle mouse button (`1`) can be listed in `buttons`:

```js
inspect: { handler: ForgeTracker.#onInspect, buttons: [0, 1] }
```

Inside the handler, check `event.button` to know which button was used.
:::

::: tip
Use `<button type="button">` for action buttons inside a `<form>`. A plain `<button>` defaults to `type="submit"` and will also submit the form.
:::

## Form handling

With `tag: "form"` and a `form.handler`, Foundry collects every named input into a `FormDataExtended` and calls `handler(event, form, formData)` with `this` bound to the app. `formData.object` is flat (`{ "system.hp.value": 7 }`); use `foundry.utils.expandObject(formData.object)` to get nested data.

- `submitOnChange: true` — submit whenever an input changes (typical for sheets).
- `closeOnSubmit: true` — close after a successful submit (typical for config dialogs).
- `await app.submit()` submits programmatically and returns the handler's return value.

## Tabs

Declare tab groups in `static TABS` and build them with `_prepareTabs(group)`:

```js
static TABS = {
  primary: {
    tabs: [
      { id: "heat", icon: "fa-solid fa-fire" },
      { id: "notes", icon: "fa-solid fa-book" }
    ],
    initial: "heat",
    labelPrefix: "FORJA.ForgeTracker.Tab"   // label = FORJA.ForgeTracker.Tab.heat, etc.
  }
};

static PARTS = {
  tabs: { template: "templates/generic/tab-navigation.hbs" },  // core template
  heat: { template: "systems/forja/templates/apps/forge-heat.hbs" },
  notes: { template: "systems/forja/templates/apps/forge-notes.hbs" }
};

async _prepareContext(options) {
  const context = await super._prepareContext(options);
  context.tabs = this._prepareTabs("primary");
  return context;
}

async _preparePartContext(partId, context, options) {
  context = await super._preparePartContext(partId, context, options);
  if ( partId in context.tabs ) context.tab = context.tabs[partId];
  return context;
}
```

```hbs
{{!-- systems/forja/templates/apps/forge-heat.hbs --}}
<section class="tab {{tab.cssClass}}" data-tab="heat" data-group="primary">
  <p>Heat: {{heat}}</p>
</section>
```

Each tab body needs `class="tab"`, `data-tab` and `data-group`; `tab.cssClass` is `"active"` for the current tab. `changeTab("notes", "primary")` switches tabs from code. The [Sheets](#sheets) page uses the same pattern on a real actor sheet.

## Parts: template, templates, scrollable, root

| Key | Meaning |
|---|---|
| `template` | Path of the part's main template. |
| `templates` | Extra templates (partials) the part uses — they are preloaded before rendering. |
| `scrollable` | CSS selectors (relative to the part root; `""` = the root) whose scroll position is preserved between renders. |
| `root` | `true` if the part template replaces the application's content root instead of being nested inside it. |
| `classes`, `id` | Extra classes / id for the part element. |

## Finding open applications

`foundry.applications.instances` is a `Map` of every rendered AppV2, keyed by id:

```js
const tracker = foundry.applications.instances.get("forja-forge-tracker");
tracker?.bringToFront();
```

::: v14
V14 adds a static generator on each class, yielding the open instances of that class (and its subclasses):

```js
for ( const app of ForgeTracker.instances() ) app.render();
```
:::

## Header controls

`window.controls` adds entries to the window's header menu (the "⋮" button). Each entry has `icon`, `label`, `action` (an action name from `actions`) and optionally `visible`. Other packages can modify the list with the `getHeaderControls{ClassName}` hook:

```js
Hooks.on("getHeaderControlsForgeTracker", (app, controls) => {
  controls.push({ icon: "fa-solid fa-print", label: "Print", action: "print" });
});
```

::: v14
In V14 header controls and `ContextMenu` share one entry format, and `ContextMenuEntry#icon` accepts plain class names (`"fa-solid fa-print"`) instead of only HTML. The `{ icon, label, action, visible }` form above keeps working.
:::

## Pop-out windows

::: v13
V13 applications always live inside the main Foundry browser window.
:::

::: v14
A V14 application can be **detached** into a separate browser window (for example, to put a character sheet on a second monitor). Users do it from the window header; code can call it too:

```js
await tracker.detachWindow();   // move into its own browser window
await tracker.attachWindow();   // bring it back into the main window
```

Override `_onDetach(from, to)` and `_onAttach(from, to)` (both receive the old and new `Document`) if you hold references to the window or document. Core copies stylesheets into the new window for you.

::: warning
In a popped-out app, the global `document` and `window` still point at the **main** window. Use `this.element.ownerDocument` and `this.element.ownerDocument.defaultView` instead, and avoid `instanceof HTMLElement` checks on elements from the other window (each window has its own constructors).
:::
:::

## Pitfalls

- **Forgetting `super`** in `_prepareContext`, `_onRender`, `_onClose`, etc. breaks core behavior (tabs, drag & drop, cleanup).
- **Arrow functions as action handlers** lose `this`. Use `static #onX(event, target)` methods.
- **`render()` does nothing** on a closed app — you need `render({ force: true })`.
- **Declaring `PARTS` in a subclass** replaces the parent's parts; spread them if you want to keep them.
- **Handlers on `document` in `_onRender`** stack up on every render; register them once in `_onFirstRender` and remove them in `_onClose`.
- Unsure whether a hook or method exists in your version? Check https://foundryvtt.com/api/v13/ and https://foundryvtt.com/api/v14/.
