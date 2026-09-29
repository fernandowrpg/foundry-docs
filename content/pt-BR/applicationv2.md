# Janelas com ApplicationV2

O framework de janelas por trás de toda interface do Foundry V13+: como declarar uma aplicação, renderizá-la com Handlebars, reagir a cliques e enviar formulários.

::: changed
- Aplicações podem ser **destacadas (pop-out)** para uma janela separada do navegador (`detachWindow()` / `attachWindow()`, `_onDetach` / `_onAttach`).
- Novo gerador estático `ApplicationV2.instances()` para percorrer as aplicações abertas.
- Actions suportam **`auxclick`**, então o clique do botão do meio pode ser direcionado a um handler.
- Os controles do cabeçalho da janela e o `ContextMenu` usam o mesmo formato de entrada (`ContextMenuEntry#icon` aceita nomes de classe).
- `options.isFirstRender` é preenchido automaticamente, então `_canRender` consegue identificar a primeira renderização.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

`foundry.applications.api.ApplicationV2` é a classe base de toda janela, ficha (sheet), diálogo e barra lateral no Foundry V13 e V14. Ela substituiu a antiga classe `Application` (AppV1). Você quase nunca a estende sozinha: ela é combinada com um mixin de renderização, normalmente o `HandlebarsApplicationMixin`, que transforma templates Handlebars em DOM.

Uma aplicação é descrita por **configuração estática** (`DEFAULT_OPTIONS`, `PARTS`, `TABS`) e por um pequeno conjunto de **métodos de ciclo de vida** que você sobrescreve. O Foundry cuida da moldura, de arrastar, redimensionar, minimizar, posicionar e re-renderizar.

### Diferenças em relação ao AppV1

| AppV1 (`Application`) | AppV2 (`ApplicationV2`) |
|---|---|
| `static get defaultOptions()` + `mergeObject` | `static DEFAULT_OPTIONS = {}` mesclado automaticamente pela cadeia de classes |
| `getData()` | `async _prepareContext(options)` |
| `activateListeners(html)` com um objeto jQuery | atributos `data-action` + `_onRender(context, options)` com um `HTMLElement` puro |
| Um único `template` | Várias `PARTS`, cada uma re-renderizável isoladamente |
| `FormApplication#_updateObject` | `form.handler` no `DEFAULT_OPTIONS` |
| `render(true)` | `render({ force: true })` (`render(true)` ainda funciona como atalho) |

::: warning
`this.element` é um `HTMLElement`, **não** jQuery. `html.find(...)` lança erro. Use `querySelector`, `querySelectorAll` e `addEventListener`.
:::

## Declarar uma aplicação

Um exemplo completo e autocontido: uma pequena janela "Rastreador da Forja" para o sistema `forja`.

```js
// systems/forja/module/apps/forge-tracker.mjs
const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

export class ForgeTracker extends HandlebarsApplicationMixin(ApplicationV2) {
  /** As opções são mescladas com as de todas as classes-pai. */
  static DEFAULT_OPTIONS = {
    id: "forja-forge-tracker",
    classes: ["forja", "forge-tracker"],
    tag: "form",                       // o elemento externo é um <form>
    window: {
      title: "FORJA.ForgeTracker.Title",   // chave de localização, traduzida automaticamente
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

  /** Cada parte é um template renderizado em seu próprio elemento. */
  static PARTS = {
    header: { template: "systems/forja/templates/apps/forge-header.hbs" },
    body: {
      template: "systems/forja/templates/apps/forge-body.hbs",
      scrollable: [""]   // mantém a posição de rolagem da raiz da parte entre renderizações
    }
  };

  /** Estado simples da instância (não é salvo em lugar nenhum). */
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

  /** Chamado uma vez por parte; adicione aqui dados específicos da parte. */
  async _preparePartContext(partId, context, options) {
    context = await super._preparePartContext(partId, context, options);
    if ( partId === "header" ) context.subtitle = game.i18n.localize("FORJA.ForgeTracker.Subtitle");
    return context;
  }

  static async #onAddHeat(event, target) {
    // `this` é a instância da aplicação, `target` é o elemento com data-action
    this.heat += Number(target.dataset.amount ?? 1);
    this.render({ parts: ["body"] });   // re-renderiza apenas a parte body
  }

  static async #onReset(event, target) {
    this.heat = 0;
    this.render();
  }

  static async #onSubmit(event, form, formData) {
    // formData.object é um objeto plano indexado pelo name dos inputs
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
  <label>Rótulo <input type="text" name="label" value="{{label}}"></label>
  <p>Calor: <strong>{{heat}}</strong></p>
  <button type="button" data-action="addHeat" data-amount="1">+1</button>
  <button type="button" data-action="addHeat" data-amount="3">+3</button>
</div>
```

Abra de qualquer lugar (uma macro, um hook, um botão):

```js
import { ForgeTracker } from "./apps/forge-tracker.mjs";

const tracker = new ForgeTracker();
tracker.render({ force: true });
```

::: tip
Todo template de parte precisa ter **exatamente um elemento raiz**. Uma parte com dois elementos de nível superior (ou texto solto) lança erro ao renderizar.
:::

## `DEFAULT_OPTIONS` em detalhes

| Chave | Finalidade |
|---|---|
| `id` | id HTML do elemento externo. Use `{id}` dentro dele para ter um id único por instância (ex.: `"forja-note-{id}"`). |
| `classes` | Classes CSS do elemento externo. Sempre inclua a classe do seu sistema/módulo para poder escopar o CSS (veja [Estilos](#styling)). |
| `tag` | Tag do elemento externo. `"form"` é obrigatório se você quiser tratamento de `form`. |
| `window` | `title`, `icon`, `resizable`, `minimizable`, `frame`, `contentTag`, `contentClasses`, `controls` (entradas do menu do cabeçalho). |
| `position` | `width`, `height`, `top`, `left`, `scale`, `zIndex` padrão. |
| `actions` | Mapa de nomes de `data-action` para handlers. |
| `form` | `handler`, `submitOnChange`, `closeOnSubmit`. |

### Mesclagem por herança

O `DEFAULT_OPTIONS` **não** é substituído pelas subclasses — o Foundry percorre a cadeia de classes e faz um deep-merge de cada nível. Assim, a subclasse declara apenas o que acrescenta:

```js
export class HotForgeTracker extends ForgeTracker {
  static DEFAULT_OPTIONS = {
    classes: ["hot-variant"],          // arrays como `classes` são combinados com os do pai
    position: { width: 520 },          // só a largura muda; a altura continua "auto"
    actions: { quench: HotForgeTracker.#onQuench }  // as actions do pai continuam disponíveis
  };

  static #onQuench(event, target) {
    this.heat = 0;
    this.render();
  }
}
```

A mesma mesclagem só vale para `PARTS` se você mesmo fizer: `PARTS` é um objeto estático simples, então uma subclasse que declara `PARTS` **substitui** as do pai. Espalhe as do pai se quiser estendê-las: `static PARTS = { ...ForgeTracker.PARTS, footer: {...} }`.

## O ciclo de vida da renderização

`render(options)` executa estes passos, nesta ordem:

1. `_canRender(options)` — retorne `false` para cancelar a renderização silenciosamente (ou lance um erro para cancelar com erro).
2. `_prepareContext(options)` — monta o objeto de dados compartilhado.
3. `_preparePartContext(partId, context, options)` — por parte, para cada parte sendo renderizada.
4. `_preRender(context, options)` — logo antes da substituição do HTML.
5. O HTML é renderizado e inserido; a janela é criada na primeira vez.
6. `_onFirstRender(context, options)` — **somente na primeira** renderização. Bom para configurações únicas (ex.: registrar um hook e guardar seu id).
7. `_onRender(context, options)` — **a cada renderização**. Adicione aqui listeners que não sejam de clique (`change`, `input`, `dragstart`).
8. `_onClose(options)` — quando a aplicação fecha. Limpe hooks e timers aqui.

```js
async _onFirstRender(context, options) {
  await super._onFirstRender(context, options);
  // Re-renderiza quando qualquer ator mudar; guarda o id para poder remover depois
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
  // Recusa renderizar para jogadores
  if ( !game.user.isGM ) return false;
}
```

::: v14
No V14, `options.isFirstRender` é definido automaticamente, então `_canRender` consegue distinguir "abrir a janela" de "atualizar uma janela aberta":

```js
_canRender(options) {
  // Permite atualizações, mas só deixa um GM abrir a janela pela primeira vez
  if ( options.isFirstRender && !game.user.isGM ) return false;
}
```
:::

::: warning
Listeners adicionados em `_onRender` são adicionados de novo a cada renderização. Como o HTML das partes é substituído, os elementos antigos (e seus listeners) são descartados, então isso é seguro para elementos *dentro* das partes. Mas nunca adicione listeners ao próprio `this.element` ou ao `document` em `_onRender` — eles vão se acumular. Use `_onFirstRender` para esses casos.
:::

### `render({ force: true })`

`render()` sem `force` só re-renderiza uma aplicação que **já está aberta**. Para abrir uma aplicação fechada, passe `force: true`. Você também pode passar `parts: ["body"]` para re-renderizar só algumas partes, `position` para movê-la ou `tab` para ativar uma aba.

## Ações

Qualquer elemento com `data-action="nome"` dentro da aplicação chama o handler registrado em `actions.nome`. Os handlers são chamados com `this` ligado à aplicação e recebem o `PointerEvent` e o elemento que carrega o `data-action` (`target`).

Declare-os como métodos `static #privados`: eles não poluem a instância, subclasses não os chamam por acidente e `this` continua apontando para a instância.

```js
static DEFAULT_OPTIONS = {
  actions: {
    addHeat: ForgeTracker.#onAddHeat,
    // Forma de objeto: escolha quais botões do mouse disparam a action (0 = esquerdo, 2 = direito)
    inspect: { handler: ForgeTracker.#onInspect, buttons: [0, 2] }
  }
};
```

::: v14
O V14 também dispara actions em eventos `auxclick`, então o botão do meio do mouse (`1`) pode ser listado em `buttons`:

```js
inspect: { handler: ForgeTracker.#onInspect, buttons: [0, 1] }
```

Dentro do handler, verifique `event.button` para saber qual botão foi usado.
:::

::: tip
Use `<button type="button">` para botões de action dentro de um `<form>`. Um `<button>` simples tem `type="submit"` por padrão e também envia o formulário.
:::

## Tratamento de formulários

Com `tag: "form"` e um `form.handler`, o Foundry coleta todo input com `name` em um `FormDataExtended` e chama `handler(event, form, formData)` com `this` ligado à aplicação. `formData.object` é plano (`{ "system.hp.value": 7 }`); use `foundry.utils.expandObject(formData.object)` para obter dados aninhados.

- `submitOnChange: true` — envia sempre que um input muda (típico de fichas).
- `closeOnSubmit: true` — fecha após um envio bem-sucedido (típico de diálogos de configuração).
- `await app.submit()` envia programaticamente e retorna o valor de retorno do handler.

## Abas

Declare grupos de abas em `static TABS` e monte-os com `_prepareTabs(group)`:

```js
static TABS = {
  primary: {
    tabs: [
      { id: "heat", icon: "fa-solid fa-fire" },
      { id: "notes", icon: "fa-solid fa-book" }
    ],
    initial: "heat",
    labelPrefix: "FORJA.ForgeTracker.Tab"   // rótulo = FORJA.ForgeTracker.Tab.heat, etc.
  }
};

static PARTS = {
  tabs: { template: "templates/generic/tab-navigation.hbs" },  // template do core
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
  <p>Calor: {{heat}}</p>
</section>
```

O corpo de cada aba precisa de `class="tab"`, `data-tab` e `data-group`; `tab.cssClass` vale `"active"` para a aba atual. `changeTab("notes", "primary")` troca de aba via código. A página [Fichas](#sheets) usa o mesmo padrão em uma ficha de ator real.

## Partes: opções `template`, `templates`, `scrollable` e `root`

| Chave | Significado |
|---|---|
| `template` | Caminho do template principal da parte. |
| `templates` | Templates extras (partials) usados pela parte — são pré-carregados antes da renderização. |
| `scrollable` | Seletores CSS (relativos à raiz da parte; `""` = a raiz) cuja posição de rolagem é preservada entre renderizações. |
| `root` | `true` se o template da parte substitui a raiz de conteúdo da aplicação em vez de ficar aninhado dentro dela. |
| `classes`, `id` | Classes / id extras para o elemento da parte. |

## Encontrando aplicações abertas

`foundry.applications.instances` é um `Map` com todo AppV2 renderizado, indexado por id:

```js
const tracker = foundry.applications.instances.get("forja-forge-tracker");
tracker?.bringToFront();
```

::: v14
O V14 adiciona um gerador estático em cada classe, que produz as instâncias abertas daquela classe (e de suas subclasses):

```js
for ( const app of ForgeTracker.instances() ) app.render();
```
:::

## Controles do cabeçalho

`window.controls` adiciona entradas ao menu do cabeçalho da janela (o botão "⋮"). Cada entrada tem `icon`, `label`, `action` (um nome de action de `actions`) e, opcionalmente, `visible`. Outros pacotes podem modificar a lista com o hook `getHeaderControls{NomeDaClasse}`:

```js
Hooks.on("getHeaderControlsForgeTracker", (app, controls) => {
  controls.push({ icon: "fa-solid fa-print", label: "Imprimir", action: "print" });
});
```

::: v14
No V14, os controles do cabeçalho e o `ContextMenu` compartilham o mesmo formato de entrada, e `ContextMenuEntry#icon` aceita nomes de classe simples (`"fa-solid fa-print"`) em vez de apenas HTML. A forma `{ icon, label, action, visible }` acima continua funcionando.
:::

## Janelas destacadas

::: v13
No V13, as aplicações sempre vivem dentro da janela principal do Foundry no navegador.
:::

::: v14
Uma aplicação V14 pode ser **destacada** para uma janela separada do navegador (por exemplo, para colocar uma ficha de personagem em um segundo monitor). O usuário faz isso pelo cabeçalho da janela; o código também pode fazer:

```js
await tracker.detachWindow();   // move para uma janela própria do navegador
await tracker.attachWindow();   // traz de volta para a janela principal
```

Sobrescreva `_onDetach(from, to)` e `_onAttach(from, to)` (ambos recebem o `Document` antigo e o novo) se você guarda referências à janela ou ao documento. O core copia as folhas de estilo para a nova janela por você.

::: warning
Em uma aplicação destacada, os globais `document` e `window` continuam apontando para a janela **principal**. Use `this.element.ownerDocument` e `this.element.ownerDocument.defaultView`, e evite checagens `instanceof HTMLElement` em elementos da outra janela (cada janela tem seus próprios construtores).
:::
:::

## Armadilhas

- **Esquecer o `super`** em `_prepareContext`, `_onRender`, `_onClose` etc. quebra comportamentos do core (abas, drag & drop, limpeza).
- **Arrow functions como handlers de action** perdem o `this`. Use métodos `static #onX(event, target)`.
- **`render()` não faz nada** em uma aplicação fechada — você precisa de `render({ force: true })`.
- **Declarar `PARTS` numa subclasse** substitui as partes do pai; espalhe-as se quiser mantê-las.
- **Handlers no `document` dentro de `_onRender`** se acumulam a cada renderização; registre-os uma vez em `_onFirstRender` e remova-os em `_onClose`.
- Não sabe se um hook ou método existe na sua versão? Consulte https://foundryvtt.com/api/v13/ e https://foundryvtt.com/api/v14/.
