# Fichas de ator e de item

Construa fichas de ator e de item completas e editáveis para o sistema `forja` com `HandlebarsApplicationMixin`, `ActorSheetV2` e `ItemSheetV2`.

::: changed
- Janelas de `DocumentSheet` ganham um botão de **configuração de permissões (ownership)** no cabeçalho.
- Active Effects são documentos primários: podem ser arrastados da barra lateral ou de compêndios para uma ficha (tratado por `_onDropActiveEffect`) ou para um token, aplicando-os ao ator dele.
- Novo `HTMLFormulaInputElement` (`<formula-input>`) para campos de fórmula de dados, com editor de fórmulas embutido.
- O TinyMCE foi removido; `<prose-mirror>` é o único editor de texto rico.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Uma ficha é uma [Janelas com ApplicationV2](#applicationv2) ligada a um documento. `DocumentSheetV2` acrescenta o documento, checagens de permissão (`isEditable`), envio automático do formulário para `document.update()` e uma action `editImage`. `ActorSheetV2` e `ItemSheetV2` acrescentam helpers específicos do documento (`this.actor`, `this.item`, actions de token, drag & drop).

::: warning
Desde o V13 o core não registra mais fichas padrão de ator ou de item. Um sistema que não registra nenhuma ficha deixa seus documentos **sem ficha alguma** — dar duplo clique num ator não faz nada.
:::

Esta página pressupõe os data models de [Modelos de dados](#data-models): um ator `character` com `system.hp.{value,max}`, `system.abilities.{might,agility,wits}.value` e `system.biography` (um `HTMLField`), e itens `weapon` / `gear` com `system.damage` (uma string de fórmula) e `system.quantity`.

## Registrar as fichas

Registre no hook `init`. `types` limita a ficha a certos subtipos; `makeDefault` a torna padrão para esses tipos; `label` aparece no diálogo de configuração de ficha.

```js
// systems/forja/forja.mjs
import { ForjaActorSheet } from "./module/sheets/actor-sheet.mjs";
import { ForjaItemSheet } from "./module/sheets/item-sheet.mjs";

Hooks.once("init", () => {
  const { DocumentSheetConfig } = foundry.applications.apps;

  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaActorSheet, {
    types: ["character"],
    makeDefault: true,
    label: "FORJA.Sheet.Character"
  });

  DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
    types: ["weapon", "gear"],
    makeDefault: true,
    label: "FORJA.Sheet.Item"
  });
});
```

::: tip
Um sistema com vários tipos de ator ou de item (personagem, NPC, veículo, magia…) precisa de uma ficha para cada um. Veja [Tipos de ficha](#sheet-types) para uma ficha por tipo, uma ficha adaptável, fichas alternativas e uma classe base compartilhada.
:::

Para remover uma ficha registrada por outro pacote (por exemplo, um módulo que substitui sua ficha de item), use `unregisterSheet` com o mesmo escopo e a mesma classe:

```js
// modules/forja-extras/main.mjs — substitui a ficha de item do sistema
Hooks.once("init", () => {
  const { DocumentSheetConfig } = foundry.applications.apps;
  const systemSheet = CONFIG.Item.sheetClasses.weapon["forja.ForjaItemSheet"]?.cls;
  if ( systemSheet ) DocumentSheetConfig.unregisterSheet(Item, "forja", systemSheet, { types: ["weapon"] });
});
```

## A classe da ficha de ator

```js
// systems/forja/module/sheets/actor-sheet.mjs
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2 } = foundry.applications.sheets;
const TextEditor = foundry.applications.ux.TextEditor.implementation;

export class ForjaActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  /** O modo de jogo mostra valores; o modo de edição libera os inputs. */
  static MODES = { PLAY: 1, EDIT: 2 };
  _mode = ForjaActorSheet.MODES.PLAY;

  static DEFAULT_OPTIONS = {
    classes: ["forja", "actor-sheet"],
    position: { width: 620, height: 720 },
    window: { resizable: true },
    form: { submitOnChange: true },
    actions: {
      roll: ForjaActorSheet.#onRoll,
      createItem: ForjaActorSheet.#onCreateItem,
      editItem: ForjaActorSheet.#onEditItem,
      deleteItem: ForjaActorSheet.#onDeleteItem,
      toggleEffect: ForjaActorSheet.#onToggleEffect,
      toggleMode: ForjaActorSheet.#onToggleMode
    }
  };

  static PARTS = {
    header: { template: "systems/forja/templates/actor/header.hbs" },
    tabs: { template: "templates/generic/tab-navigation.hbs" },
    abilities: { template: "systems/forja/templates/actor/abilities.hbs" },
    inventory: {
      template: "systems/forja/templates/actor/inventory.hbs",
      templates: ["systems/forja/templates/actor/item-row.hbs"],
      scrollable: [""]
    },
    effects: { template: "systems/forja/templates/actor/effects.hbs" },
    biography: { template: "systems/forja/templates/actor/biography.hbs" }
  };

  static TABS = {
    primary: {
      tabs: [
        { id: "abilities", icon: "fa-solid fa-dumbbell" },
        { id: "inventory", icon: "fa-solid fa-sack" },
        { id: "effects", icon: "fa-solid fa-bolt" },
        { id: "biography", icon: "fa-solid fa-feather" }
      ],
      initial: "abilities",
      labelPrefix: "FORJA.Tab"
    }
  };

  get isEditMode() {
    return this.isEditable && (this._mode === ForjaActorSheet.MODES.EDIT);
  }

  async _prepareContext(options) {
    // o super fornece: document, source, fields, editable, user, rootId
    const context = await super._prepareContext(options);
    const actor = this.actor;

    // Agrupa os itens por tipo, ordenados como na barra lateral
    const itemGroups = {};
    for ( const [type, items] of Object.entries(actor.itemTypes) ) {
      itemGroups[type] = items.toSorted((a, b) => a.sort - b.sort);
    }

    return Object.assign(context, {
      actor,
      system: actor.system,                 // dados preparados (incluem Active Effects)
      systemSource: context.source.system,  // dados brutos armazenados (o que os inputs devem editar)
      systemFields: actor.system.schema.fields,
      isEditMode: this.isEditMode,
      disabled: !this.isEditMode,
      itemGroups,
      effects: actor.effects.contents,
      tabs: this._prepareTabs("primary"),
      enrichedBiography: await TextEditor.enrichHTML(actor.system.biography, {
        secrets: actor.isOwner,
        rollData: actor.getRollData(),
        relativeTo: actor
      })
    });
  }

  async _preparePartContext(partId, context, options) {
    context = await super._preparePartContext(partId, context, options);
    if ( partId in context.tabs ) context.tab = context.tabs[partId];
    return context;
  }

  /** Encontra o Item embutido correspondente ao elemento clicado. */
  _getItem(target) {
    const id = target.closest("[data-item-id]")?.dataset.itemId;
    return this.actor.items.get(id);
  }

  /* ---------- Actions ---------- */

  static async #onRoll(event, target) {
    const ability = target.dataset.ability;
    const roll = new Roll(`1d20 + @abilities.${ability}.value`, this.actor.getRollData());
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this.actor }),
      flavor: game.i18n.localize(`FORJA.Ability.${ability}`)
    });
  }

  static async #onCreateItem(event, target) {
    const type = target.dataset.type;
    await Item.implementation.create({
      name: game.i18n.format("DOCUMENT.New", { type: game.i18n.localize(`TYPES.Item.${type}`) }),
      type
    }, { parent: this.actor });
  }

  static #onEditItem(event, target) {
    this._getItem(target)?.sheet.render({ force: true });
  }

  static async #onDeleteItem(event, target) {
    await this._getItem(target)?.deleteDialog();
  }

  static async #onToggleEffect(event, target) {
    const id = target.closest("[data-effect-id]")?.dataset.effectId;
    const effect = this.actor.effects.get(id);
    await effect?.update({ disabled: !effect.disabled });
  }

  static #onToggleMode(event, target) {
    this._mode = this.isEditMode ? ForjaActorSheet.MODES.PLAY : ForjaActorSheet.MODES.EDIT;
    this.render();
  }

  /* ---------- Drag & drop ---------- */

  /** Aceita apenas os tipos de item que este sistema entende. */
  async _onDropItem(event, item) {
    if ( !["weapon", "gear"].includes(item.type) ) {
      ui.notifications.warn("FORJA.Warn.ItemTypeNotAllowed", { localize: true });
      return null;
    }
    return super._onDropItem(event, item);
  }
}
```

### Por que `system` *e* `systemSource`?

`actor.system` são os dados **preparados**: Active Effects e `prepareDerivedData` já os alteraram. Se um input mostra um valor aumentado por um efeito e a ficha o envia, o bônus é gravado no banco de dados e se acumula para sempre. Inputs devem exibir `systemSource` (o valor armazenado); exibições somente leitura podem mostrar `system`.

## Modelos Handlebars

### Cabeçalho

```hbs
{{!-- systems/forja/templates/actor/header.hbs --}}
<header class="sheet-header">
  <img class="portrait" src="{{actor.img}}" alt="{{actor.name}}"
       data-action="editImage" data-edit="img">
  <div class="identity">
    <input class="name" type="text" name="name" value="{{source.name}}" {{disabled disabled}}>
    <div class="hp">
      {{formInput systemFields.hp.fields.value value=systemSource.hp.value disabled=disabled}}
      <span>/</span>
      {{formInput systemFields.hp.fields.max value=systemSource.hp.max disabled=disabled}}
    </div>
  </div>
  {{#if editable}}
  <button type="button" class="mode-toggle" data-action="toggleMode"
          data-tooltip="FORJA.Sheet.ToggleMode">
    <i class="fa-solid {{#if isEditMode}}fa-lock-open{{else}}fa-lock{{/if}}"></i>
  </button>
  {{/if}}
</header>
```

- `data-action="editImage"` + `data-edit="img"` é a action embutida do `DocumentSheetV2`: abre um FilePicker e atualiza o campo `img`.
- `{{formInput field value=...}}` renderiza o input certo para um `DataField` (número, select, checkbox…) e define o `name` a partir do caminho do campo, então `systemFields.hp.fields.value` vira `name="system.hp.value"`. O formulário então envia `{"system.hp.value": 12}` e a ficha chama `actor.update()` por você.
- `{{disabled disabled}}` é um helper do core que imprime o atributo `disabled` quando verdadeiro.

### Aba de atributos

```hbs
{{!-- systems/forja/templates/actor/abilities.hbs --}}
<section class="tab abilities {{tab.cssClass}}" data-tab="abilities" data-group="primary">
  {{#each systemFields.abilities.fields as |field key|}}
  <div class="ability">
    {{formGroup field.fields.value value=(lookup (lookup @root.systemSource.abilities key) "value")
                localize=true disabled=@root.disabled}}
    <button type="button" data-action="roll" data-ability="{{key}}">
      <i class="fa-solid fa-dice-d20"></i>
    </button>
  </div>
  {{/each}}
</section>
```

`{{formGroup}}` envolve o input com um `<label>` (o `label` do campo, localizado com `localize=true`) e seu `hint`.

### Aba de inventário com um modelo parcial

```hbs
{{!-- systems/forja/templates/actor/inventory.hbs --}}
<section class="tab inventory {{tab.cssClass}}" data-tab="inventory" data-group="primary">
  {{#each itemGroups as |items type|}}
  <h3>
    {{localize (concat "TYPES.Item." type)}}
    {{#if @root.editable}}
    <button type="button" data-action="createItem" data-type="{{type}}">
      <i class="fa-solid fa-plus"></i>
    </button>
    {{/if}}
  </h3>
  <ol class="item-list">
    {{#each items as |item|}}
      {{> "systems/forja/templates/actor/item-row.hbs" item=item editable=@root.editable}}
    {{/each}}
  </ol>
  {{/each}}
</section>
```

```hbs
{{!-- systems/forja/templates/actor/item-row.hbs --}}
<li class="item draggable" data-item-id="{{item.id}}">
  <img src="{{item.img}}" alt="">
  <span class="item-name">{{item.name}}</span>
  {{#if item.system.damage}}<span class="damage">{{item.system.damage}}</span>{{/if}}
  <a data-action="editItem" data-tooltip="DOCUMENT.Update"><i class="fa-solid fa-pen"></i></a>
  {{#if editable}}
  <a data-action="deleteItem" data-tooltip="DOCUMENT.Delete"><i class="fa-solid fa-trash"></i></a>
  {{/if}}
</li>
```

Como `item-row.hbs` está listado em `templates` da parte, ele é pré-carregado e pode ser usado como partial pelo seu caminho.

::: tip
`actor.itemTypes` tem uma chave para **todo** subtipo de item declarado pelo sistema, até os vazios. Por isso o botão de "criar" aparece para cada tipo, mesmo antes de o ator possuir algum item daquele tipo.
:::

### Aba de efeitos

```hbs
{{!-- systems/forja/templates/actor/effects.hbs --}}
<section class="tab effects {{tab.cssClass}}" data-tab="effects" data-group="primary">
  <ol class="effect-list">
    {{#each effects as |effect|}}
    <li class="effect" data-effect-id="{{effect.id}}">
      <img src="{{effect.img}}" alt="">
      <span>{{effect.name}}</span>
      <a data-action="toggleEffect">
        <i class="fa-solid {{#if effect.disabled}}fa-toggle-off{{else}}fa-toggle-on{{/if}}"></i>
      </a>
    </li>
    {{/each}}
  </ol>
</section>
```

### Aba de biografia com ProseMirror

```hbs
{{!-- systems/forja/templates/actor/biography.hbs --}}
<section class="tab biography {{tab.cssClass}}" data-tab="biography" data-group="primary">
  <prose-mirror name="system.biography" value="{{systemSource.biography}}"
                data-document-uuid="{{actor.uuid}}" toggled {{disabled disabled}}>
    {{{enrichedBiography}}}
  </prose-mirror>
</section>
```

O elemento `<prose-mirror>` mostra o HTML enriquecido (o conteúdo interno) até que o usuário o alterne para o modo de edição; aí ele edita o `value` bruto. Ao salvar, ele se comporta como qualquer input com `name` e é enviado junto com o formulário. Sempre passe HTML **enriquecido** como conteúdo: HTML bruto mostraria links `@UUID[...]` e segredos sem processamento.

## A ficha de item

```js
// systems/forja/module/sheets/item-sheet.mjs
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ItemSheetV2 } = foundry.applications.sheets;
const TextEditor = foundry.applications.ux.TextEditor.implementation;

export class ForjaItemSheet extends HandlebarsApplicationMixin(ItemSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "item-sheet"],
    position: { width: 480, height: 520 },
    window: { resizable: true },
    form: { submitOnChange: true }
  };

  static PARTS = {
    header: { template: "systems/forja/templates/item/header.hbs" },
    details: { template: "systems/forja/templates/item/details.hbs", scrollable: [""] }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const item = this.item;
    return Object.assign(context, {
      item,
      system: item.system,
      systemSource: context.source.system,
      systemFields: item.system.schema.fields,
      disabled: !context.editable,
      enrichedDescription: await TextEditor.enrichHTML(item.system.description, {
        secrets: item.isOwner,
        rollData: item.getRollData?.() ?? {},
        relativeTo: item
      })
    });
  }
}
```

```hbs
{{!-- systems/forja/templates/item/header.hbs --}}
<header class="sheet-header">
  <img src="{{item.img}}" alt="" data-action="editImage" data-edit="img">
  <input class="name" type="text" name="name" value="{{source.name}}" {{disabled disabled}}>
</header>
```

::: v13
```hbs
{{!-- systems/forja/templates/item/details.hbs --}}
<section class="details">
  {{#if systemFields.damage}}
    {{formGroup systemFields.damage value=systemSource.damage localize=true}}
  {{/if}}
  {{formGroup systemFields.quantity value=systemSource.quantity localize=true}}
  <prose-mirror name="system.description" value="{{systemSource.description}}"
                data-document-uuid="{{item.uuid}}" toggled>
    {{{enrichedDescription}}}
  </prose-mirror>
</section>
```
:::

::: v14
O V14 adiciona o `HTMLFormulaInputElement` (`<formula-input>`), um input especializado em fórmulas de dados, com um botão que abre o editor de fórmulas e autocompletar. Use-o para `system.damage`:

```hbs
{{!-- systems/forja/templates/item/details.hbs --}}
<section class="details">
  {{#if systemFields.damage}}
  <div class="form-group">
    <label>{{localize "FORJA.Item.Damage"}}</label>
    <formula-input name="system.damage" value="{{systemSource.damage}}"></formula-input>
  </div>
  {{/if}}
  {{formGroup systemFields.quantity value=systemSource.quantity localize=true}}
  <prose-mirror name="system.description" value="{{systemSource.description}}"
                data-document-uuid="{{item.uuid}}" toggled>
    {{{enrichedDescription}}}
  </prose-mirror>
</section>
```

O elemento também aceita um atributo `context`, que seleciona quais entradas de autocompletar se aplicam; veja `HTMLFormulaInputElement` na [API do V14](https://foundryvtt.com/api/v14/).
:::

## Arrastar e soltar

O `ActorSheetV2` já vem com um framework de drag & drop. Os drops são encaminhados por tipo de documento:

| Método | Chamado quando |
|---|---|
| `_onDrop(event)` | Qualquer coisa é solta; despacha para os métodos abaixo. |
| `_onDropItem(event, item)` | Um Item é solto. Cria uma cópia no ator, ou o reordena se ele já pertence a este ator. |
| `_onDropActiveEffect(event, effect)` | Um Active Effect é solto. |
| `_onDropActor(event, actor)` | Um Actor é solto (não faz nada por padrão). |
| `_onDropFolder(event, folder)` | Uma Folder é solta. |
| `_onSortItem(event, item)` | Um item do próprio ator é solto entre seus irmãos. |

Sobrescreva um deles, chame o `super` para o comportamento padrão e retorne `null` para recusar o drop (como no `_onDropItem` acima). `_canDragStart(selector)` e `_canDragDrop(selector)` controlam as permissões; por padrão ambos exigem que a ficha seja editável.

::: tip
Se as linhas do seu template não começam a ser arrastadas, compare seu markup com o que o `_onDragStart` espera na documentação da API da sua versão (as linhas acima usam `class="draggable"` e `data-item-id`), ou sobrescreva `_onDragStart(event)` e chame você mesmo `event.dataTransfer.setData("text/plain", JSON.stringify(item.toDragData()))`.
:::

::: v14
Active Effects são documentos primários no V14: os usuários podem arrastá-los da aba de Efeitos da barra lateral ou de um compêndio para a sua ficha, o que chama `_onDropActiveEffect`, ou para um token no canvas, aplicando-os ao ator daquele token — sem nenhum código na ficha. Veja [Efeitos ativos](#active-effect).
:::

## Modo de edição e modo de visualização

A receita `MODES` acima é um padrão comum:

1. Mantenha um campo `_mode` na instância (não é salvo; volta ao padrão quando a ficha é reaberta).
2. Exponha `isEditMode` e `disabled` no contexto.
3. Passe `disabled=disabled` para todo `{{formInput}}` / `{{formGroup}}` e `{{disabled disabled}}` para inputs escritos à mão.
4. Alterne com uma action e `this.render()`.

`isEditable` já leva as permissões em conta: um jogador olhando o ator de outra pessoa, ou uma entrada de compêndio bloqueado, nunca entra no modo de edição.

## Controles do cabeçalho e permissões

O `ActorSheetV2` fornece actions como `configurePrototypeToken`, `showPortraitArtwork` e `showTokenArtwork`, que aparecem no menu do cabeçalho. Você pode reutilizá-las no seu template (`data-action="showPortraitArtwork"`).

::: v14
O V14 adiciona um botão de **permissões (ownership)** ao cabeçalho das `DocumentSheet`, para que os GMs abram a configuração de permissões diretamente de qualquer ficha. Você o recebe de graça ao estender `ActorSheetV2` / `ItemSheetV2`.
:::

## Armadilhas

- **Nenhuma ficha registrada** → os documentos não podem ser abertos. Registre no `init`, não no `ready`.
- **Editar dados preparados**: inputs ligados a `system` (em vez de `systemSource`) gravam bônus de Active Effects no banco de dados.
- **`name` errado**: `name="hp.value"` não faz nada, silenciosamente; o caminho precisa começar na raiz do documento (`system.hp.value`).
- **HTML sem escape**: use `{{{ }}}` apenas para HTML já enriquecido; todo o resto usa `{{ }}`.
- **Botões sem `type="button"`** enviam o formulário e re-renderizam a ficha a cada clique.
- **Registrar com os `types` errados**: um tipo que não está em `types` cai para outra ficha registrada, ou para nenhuma.
