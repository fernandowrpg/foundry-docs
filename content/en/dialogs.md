# Dialogs and notifications

Ask the user a question with `DialogV2`, get a value back with `await`, and give feedback with `ui.notifications`.

::: changed
- `DialogV2` is an `ApplicationV2`, so in V14 a dialog can be **popped out** into a separate browser window like any other app (see [ApplicationV2](#applicationv2)).
- `game.i18n.localize()` accepts format data in V14, and `_loc(key, data)` is a global alias — handy for dialog titles and button labels.
- See [the full changelog](#changes-14).
:::

## What it is

`foundry.applications.api.DialogV2` is the V13+ replacement for the old `Dialog` class. It is a small [ApplicationV2](#applicationv2) whose content is wrapped in a `<form>` and whose buttons are declared as data. Its static helpers return a **Promise**, so the usual flow is:

```js
const answer = await DialogV2.something({ ... });
if ( answer === null ) return; // the user closed the dialog
```

| Static helper | Buttons | Resolves to |
|---|---|---|
| `DialogV2.confirm(config)` | Yes / No | `true`, `false` (or a callback's return value) |
| `DialogV2.prompt(config)` | One "OK" button | the button's `action`, or its callback's return value |
| `DialogV2.input(config)` | One "OK" button | the form data as a plain object, or the callback's return value |
| `DialogV2.wait(config)` | Any buttons you declare | the clicked button's `action`, or its callback's return value |
| `DialogV2.query(user, type, config)` | Same as `type` | the other user's answer (see below) |

If the user closes the dialog without choosing, the Promise resolves to `null`, or **rejects** if you passed `rejectClose: true`.

## Confirm

```js
const { DialogV2 } = foundry.applications.api;

const ok = await DialogV2.confirm({
  window: { title: "FORJA.Dialog.RestTitle", icon: "fa-solid fa-campground" },
  content: `<p>${game.i18n.localize("FORJA.Dialog.RestBody")}</p>`,
  modal: true,          // block the rest of the UI while open
  rejectClose: false    // closing the window resolves to null instead of throwing
});

if ( ok ) {
  // Restore HP to max
  await actor.update({ "system.hp.value": actor.system.hp.max });
}
```

Customize the buttons with `yes` and `no` (same shape as any button, see below):

```js
await DialogV2.confirm({
  content: "<p>Break the weapon?</p>",
  yes: { label: "Break it", icon: "fa-solid fa-hammer" },
  no: { label: "Keep it", default: true }
});
```

## Button configuration

| Key | Meaning |
|---|---|
| `action` | Identifier of the button; returned if there is no callback. |
| `label` | Text (localization keys are translated). |
| `icon` | Font Awesome classes. |
| `default` | `true` for the button triggered by Enter. |
| `callback` | `(event, button, dialog) => value`. Its return value (awaited if async) becomes the Promise's result. |

`button` is the clicked `<button>` element. Because the dialog content lives inside a `<form>`, `button.form` gives you that form and `button.form.elements` every named input.

## Prompt: read one value

```js
const bonus = await DialogV2.prompt({
  window: { title: "FORJA.Dialog.BonusTitle" },
  content: `<input type="number" name="bonus" value="0" autofocus>`,
  ok: {
    label: "FORJA.Roll",
    icon: "fa-solid fa-dice-d20",
    // Return the number instead of the button's action
    callback: (event, button, dialog) => button.form.elements.bonus.valueAsNumber
  },
  rejectClose: false
});

if ( bonus !== null ) {
  const roll = await new Roll(`1d20 + ${bonus}`).evaluate();
  await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) });
}
```

## Input: read a whole form

`DialogV2.input` returns every named field as an object, already typed (numbers for `type="number"`, booleans for checkboxes):

```js
const data = await DialogV2.input({
  window: { title: "FORJA.Dialog.NewNpcTitle" },
  content: `
    <div class="form-group">
      <label>Name</label>
      <input type="text" name="name" required>
    </div>
    <div class="form-group">
      <label>Level</label>
      <input type="number" name="level" value="1" min="1">
    </div>
    <div class="form-group">
      <label>Elite</label>
      <input type="checkbox" name="elite">
    </div>`,
  ok: { label: "FORJA.Create" }
});
// data → { name: "Goblin", level: 3, elite: true }   (or null if closed)

if ( data ) {
  await Actor.implementation.create({ name: data.name, type: "character" });
}
```

For forms built with `wait`, the same conversion is available with `new foundry.applications.ux.FormDataExtended(button.form).object`.

## Wait: several choices

```js
const stance = await DialogV2.wait({
  window: { title: "FORJA.Dialog.StanceTitle" },
  content: "<p>Choose your stance for this round.</p>",
  buttons: [
    { action: "attack", label: "Attack", icon: "fa-solid fa-khanda", default: true },
    { action: "defend", label: "Defend", icon: "fa-solid fa-shield" },
    {
      action: "flee",
      label: "Flee",
      icon: "fa-solid fa-person-running",
      // A callback can do work and return any value
      callback: async (event, button, dialog) => {
        await actor.setFlag("forja", "fled", true);
        return "fled";
      }
    }
  ],
  rejectClose: false
});
// stance → "attack" | "defend" | "fled" | null
```

## Custom content from a template

Long content belongs in a Handlebars file. Render it first, then pass the HTML string as `content`:

```hbs
{{!-- systems/forja/templates/dialogs/attack.hbs --}}
<div class="form-group">
  <label>{{localize "FORJA.Weapon"}}</label>
  <select name="weaponId">
    {{selectOptions weapons valueAttr="id" labelAttr="name"}}
  </select>
</div>
<div class="form-group">
  <label>{{localize "FORJA.Bonus"}}</label>
  <input type="number" name="bonus" value="0">
</div>
```

```js
const { DialogV2 } = foundry.applications.api;
const { renderTemplate } = foundry.applications.handlebars;

export async function attackDialog(actor) {
  const weapons = actor.itemTypes.weapon;
  if ( !weapons.length ) return ui.notifications.warn("FORJA.Warn.NoWeapons", { localize: true });

  const content = await renderTemplate("systems/forja/templates/dialogs/attack.hbs", { weapons });

  const result = await DialogV2.wait({
    window: { title: "FORJA.Dialog.AttackTitle" },
    classes: ["forja"],           // scope your CSS
    content,
    buttons: [{
      action: "roll",
      label: "FORJA.Roll",
      default: true,
      callback: (event, button) => {
        const { weaponId, bonus } = button.form.elements;
        return { weapon: actor.items.get(weaponId.value), bonus: bonus.valueAsNumber };
      }
    }],
    // Runs after the dialog renders: add listeners or tweak the DOM
    render: (event, dialog) => {
      dialog.element.querySelector("select[name=weaponId]")?.focus();
    },
    rejectClose: false
  });

  if ( !result ) return;
  const roll = await new Roll(`${result.weapon.system.damage} + ${result.bonus}`).evaluate();
  return roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }), flavor: result.weapon.name });
}
```

::: tip
Remaining options (`classes`, `position`, `window`, `modal`…) are normal [ApplicationV2 options](#applicationv2), so you can size a dialog with `position: { width: 400 }`.
:::

## Asking another user

`DialogV2.query(user, type, config)` shows a dialog on **another** user's client and resolves to their answer. `type` is `"confirm"`, `"prompt"`, `"input"` or `"wait"`, and `config` is what you would pass to that helper.

```js
// GM asks the actor's owner whether they accept a deal
const player = game.users.find(u => u.active && !u.isGM && actor.testUserPermission(u, "OWNER"));
if ( player ) {
  const accepted = await DialogV2.query(player, "confirm", {
    window: { title: "Deal" },
    content: "<p>The merchant offers 50 gold for your sword. Accept?</p>"
  });
}
```

The target user must be connected. It is built on the user query system (`user.query`), described in [Sockets](#sockets).

## Document create and delete dialogs

Every client document has ready-made dialogs, so you rarely need to build these yourself:

```js
// Pick a name and type, create an Item on the actor
const item = await Item.implementation.createDialog({}, { parent: actor }, {
  types: ["weapon", "gear"]    // restrict the type list
});

// Confirm and delete
await item?.deleteDialog();
```

Both resolve to `null` (or `undefined`) if the user cancels.

## Notifications

`ui.notifications` shows toasts at the top of the screen.

```js
ui.notifications.info("Your weapon was sharpened.");
ui.notifications.success("FORJA.Notify.Saved", { localize: true });
ui.notifications.warn("FORJA.Notify.LowHp", { localize: true, format: { name: actor.name } });
ui.notifications.error("Something went wrong.", { permanent: true }); // stays until clicked
```

- `localize: true` treats the message as a key; `format` fills `{placeholders}`.
- `permanent: true` keeps it until dismissed.
- Use them for **feedback**, not for errors the developer needs: pair errors with `console.error` or throw.

### Progress notifications

V13 added a `progress` notification that replaces the deprecated `SceneNavigation.displayProgressBar`:

```js
const docs = game.actors.contents;
const bar = ui.notifications.info("Migrating actors…", { progress: true });

for ( const [i, actor] of docs.entries() ) {
  await migrateActor(actor);          // your own function
  bar.update({ pct: (i + 1) / docs.length, message: `Migrating ${actor.name}` });
}
// Once pct reaches 1 the bar is full and the notification is removed like any other
```

## Pop-out dialogs

::: v13
In V13 dialogs always render inside the main window.
:::

::: v14
In V14 a user can pop a dialog out into its own browser window. Your callbacks keep working, but inside a `render` callback use `dialog.element.ownerDocument` instead of the global `document` if you need to query or create elements.
:::

## Pitfalls

- **Forgetting `await`**: `DialogV2.confirm()` returns a Promise, which is always truthy — `if (DialogV2.confirm(...))` always passes.
- **Not handling `null`**: users close dialogs with Escape or the × button. Check for `null`, or pass `rejectClose: true` and `try/catch`.
- **Duplicate `name` attributes** in content: `button.form.elements.x` becomes a `RadioNodeList` instead of an element.
- **Unescaped user input** in `content`: escape names you interpolate (`Handlebars.escapeExpression(actor.name)`) or render a template, which escapes by default.
- The old `Dialog` class (AppV1) is deprecated; don't start new code with it.
