# Ganchos de eventos

Os ganchos de eventos (a API `Hooks`) são o barramento de eventos do Foundry: eventos nomeados nos quais seu código se inscreve para rodar no momento certo da inicialização, reagir a mudanças em documentos e estender a interface de outras aplicações.

::: changed
- O hook `ready` agora dispara **depois** que as transições de cena terminam, então o canvas já está estável quando seu código de `ready` roda.
- Novo hook `planToken`, disparado quando o movimento de um token é planejado.
- Novo hook `preRenderApplication` (e suas variantes por classe, como `preRenderActorSheetV2`), disparado **antes** de uma ApplicationV2 renderizar.
- Os controles de cabeçalho e os menus de contexto passaram a compartilhar a mesma implementação; `getHeaderControls{Classe}` continua funcionando.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é um gancho

O core do Foundry (e qualquer pacote) pode chamar `Hooks.call("algumEvento", ...args)` em um ponto bem definido. Toda função registrada para `"algumEvento"` então roda com esses argumentos. É assim que você adiciona comportamento **sem** editar ou fazer monkey-patch no código do core:

- **Hooks de ciclo de vida** avisam quando o jogo está sendo montado (`init`, `setup`, `ready`).
- **Hooks de documento** avisam que um documento vai mudar ou mudou (`preUpdateActor`, `updateActor`, …).
- **Hooks de renderização** permitem modificar o HTML de uma aplicação depois que ela renderiza (`renderActorSheetV2`, …).
- **Hooks de construção de UI** permitem adicionar botões a menus e barras de ferramentas (`getSceneControlButtons`, `getHeaderControlsApplicationV2`, …).

Hooks são puramente do lado do cliente: cada navegador conectado tem seu próprio registro de `Hooks`, e um handler só roda no navegador que o registrou.

## A API `Hooks`

| Método | O que faz | Retorna |
| --- | --- | --- |
| `Hooks.on(name, fn)` | Registra `fn` para rodar toda vez que o hook disparar | id numérico |
| `Hooks.once(name, fn)` | Registra `fn` para rodar só na próxima vez e depois remove o registro | id numérico |
| `Hooks.off(name, fnOrId)` | Remove o registro pela referência da função ou pelo id retornado por `on` | — |
| `Hooks.call(name, ...args)` | Dispara um hook; para antes se algum handler retornar `false` | `false` se foi interrompido, senão `true` |
| `Hooks.callAll(name, ...args)` | Dispara um hook; todos os handlers rodam, retornos são ignorados | `true` |

```js
// modules/forja-extras/scripts/main.js

// Roda toda vez que qualquer Actor é atualizado
const hookId = Hooks.on("updateActor", (actor, changes, options, userId) => {
  console.log(`forja-extras | ${actor.name} foi atualizado`, changes);
});

// Roda só uma vez, na próxima vez que o hook disparar
Hooks.once("ready", () => {
  console.log("forja-extras | O jogo está pronto");
});

// Pare de escutar depois, usando o id (ou a mesma referência de função)
function stopListening() {
  Hooks.off("updateActor", hookId);
}
```

### `call` ou `callAll`

`Hooks.call` é usado para eventos que podem ser **vetados**: se qualquer handler retornar exatamente `false`, os handlers restantes são pulados e quem chamou recebe `false`. O core usa isso em todo hook `pre*`. `Hooks.callAll` é para notificações — ninguém consegue interrompê-lo.

### Disparando seus próprios ganchos

Seu sistema ou módulo pode expor hooks para que outros pacotes se integrem a ele. Prefixe o nome com o id do seu pacote para evitar colisões.

```js
// systems/forja/scripts/rolls.js
export async function rollAttribute(actor, key) {
  // Deixa outros pacotes cancelarem ou ajustarem a rolagem antes de acontecer
  const rollData = { formula: `1d20 + @attributes.${key}.value`, actor, key };
  const allowed = Hooks.call("forja.preRollAttribute", rollData);
  if (allowed === false) return null;

  const roll = await new Roll(rollData.formula, actor.getRollData()).evaluate();
  await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) });

  // Notificação pura: ninguém pode mais cancelar
  Hooks.callAll("forja.rollAttribute", actor, key, roll);
  return roll;
}
```

```js
// modules/forja-extras/scripts/main.js
Hooks.on("forja.preRollAttribute", (rollData) => {
  // Adiciona um bônus fixo de +1 a toda rolagem de Força
  if (rollData.key === "strength") rollData.formula += " + 1";
});
```

::: tip
Os handlers são chamados de forma síncrona. Se um handler for `async`, o Foundry **não** espera por ele, e uma Promise retornada não é `false` — então um handler `pre*` assíncrono nunca consegue cancelar uma operação.
:::

## Ordem do ciclo de vida

Quando um cliente carrega um mundo, estes hooks disparam nesta ordem, exatamente uma vez cada:

| Hook | Quando | O que está disponível | Uso típico |
| --- | --- | --- | --- |
| `init` | Logo após as classes do core carregarem, antes de qualquer preparação | `CONFIG`, `game.settings`, `game.keybindings`, `Hooks` | Registrar data models, classes de documento, fichas, configurações, atalhos, helpers do Handlebars |
| `i18nInit` | As traduções foram carregadas | `game.i18n` totalmente utilizável | Localizar strings estáticas, `localizeDataModel` para models próprios |
| `setup` | Os documentos estão prestes a ser criados a partir dos dados do mundo | Valores das configurações, `game.i18n` | Ajustes finais em `CONFIG` que dependem de configurações |
| `ready` | Tudo foi inicializado e o canvas foi desenhado | `game.actors`, `game.user`, `canvas`, `game.ready === true` | Migrações, sockets, UI que precisa de documentos |

::: v13
Na V13, `ready` dispara assim que o jogo termina de inicializar e a primeira cena é desenhada.
:::

::: v14
Na V14, `ready` dispara **depois que qualquer animação de transição de cena termina**. Se você iniciar algo visual no `ready` (uma notificação, um pan), isso não vai mais se sobrepor à transição.
:::

```js
// systems/forja/forja.mjs
import { CharacterData } from "./data/character.mjs";
import { ForjaActor } from "./documents/actor.mjs";

Hooks.once("init", () => {
  console.log("forja | Inicializando");
  CONFIG.Actor.documentClass = ForjaActor;
  CONFIG.Actor.dataModels.character = CharacterData;
});

Hooks.once("i18nInit", () => {
  // Traduções prontas: seguro localizar strings uma única vez
  CONFIG.forja = { sizes: { small: game.i18n.localize("FORJA.Size.Small") } };
});

Hooks.once("setup", () => {
  console.log("forja | Setup: as configurações já podem ser lidas");
});

Hooks.once("ready", () => {
  // Os documentos existem, o usuário é conhecido
  if (game.user.isGM) console.log(`forja | ${game.actors.size} atores neste mundo`);
});
```

::: warning
Registre data models, classes de documento e configurações no `init`. Quando chega o `ready`, os documentos do mundo já foram construídos com o que estava configurado antes, e mudanças em `CONFIG.Actor.dataModels` não se aplicam a eles.
:::

## Ganchos de documento

Toda criação, atualização e exclusão de um documento dispara um par de hooks, nomeados pelo tipo do documento (`Actor`, `Item`, `ChatMessage`, `Token`, …):

| Hook | Argumentos | Roda em | Pode cancelar? |
| --- | --- | --- | --- |
| `preCreate{Doc}` | `(document, data, options, userId)` | Só no cliente que pediu a mudança | Sim, retorne `false` |
| `create{Doc}` | `(document, options, userId)` | Em todo cliente conectado | Não |
| `preUpdate{Doc}` | `(document, changes, options, userId)` | Só no cliente que pediu | Sim, retorne `false` |
| `update{Doc}` | `(document, changes, options, userId)` | Em todo cliente conectado | Não |
| `preDelete{Doc}` | `(document, options, userId)` | Só no cliente que pediu | Sim, retorne `false` |
| `delete{Doc}` | `(document, options, userId)` | Em todo cliente conectado | Não |

**Por que a divisão?** Os hooks `pre*` rodam *antes* de o pedido ir ao servidor, então só o cliente que pediu a mudança sabe dela. Você pode inspecionar ou modificar os dados pendentes (no `preCreate` use `document.updateSource(...)`; no `preUpdate` altere `changes`) ou retornar `false` para cancelar. Os hooks posteriores rodam depois que o servidor confirmou e transmitiu a mudança, então todo cliente os executa.

```js
// modules/forja-extras/scripts/document-hooks.js

// Dá um ícone padrão a armas novas e bloqueia a criação de uma arma sem nome
Hooks.on("preCreateItem", (item, data, options, userId) => {
  if (item.type !== "weapon") return;
  if (!data.name?.trim()) {
    ui.notifications.warn("forja-extras | Armas precisam de um nome.");
    return false; // cancela a criação
  }
  if (!data.img) item.updateSource({ img: "icons/weapons/swords/sword-guard-steel.webp" });
});

// Impede que o PV fique abaixo de zero
Hooks.on("preUpdateActor", (actor, changes, options, userId) => {
  const hp = foundry.utils.getProperty(changes, "system.hp.value");
  if (hp !== undefined && hp < 0) foundry.utils.setProperty(changes, "system.hp.value", 0);
});

// Reage depois da mudança: roda em TODO cliente
Hooks.on("updateActor", async (actor, changes, options, userId) => {
  // Só o usuário que fez a mudança deve criar documentos em sequência
  if (userId !== game.user.id) return;
  if (foundry.utils.getProperty(changes, "system.hp.value") === 0) {
    await ChatMessage.create({ content: `${actor.name} caiu!` });
  }
});
```

::: warning
Como os hooks `create*`, `update*` e `delete*` rodam em todo cliente, gravar no banco de dados dentro deles sem uma proteção faz **cada cliente conectado** executar a gravação. Sempre filtre com `userId === game.user.id` (ou use um GM designado, veja [comunicação entre clientes](#sockets)).
:::

Também existem versões genéricas que disparam para qualquer tipo de documento: `preCreateDocument`, `createDocument`, `preUpdateDocument`, `updateDocument`, `preDeleteDocument`, `deleteDocument`. Para lógica dentro do seu próprio sistema, prefira sobrescrever `_preCreate` / `_onUpdate` na sua classe de documento (veja [documentos](#documents)).

## Ganchos de renderização da ApplicationV2

Toda ApplicationV2 dispara `render{NomeDaClasse}` depois de renderizar, **e um hook para cada classe pai** na cadeia de herança. Uma classe de ficha (sheet) `ForjaCharacterSheet extends ActorSheetV2` dispara `renderForjaCharacterSheet`, `renderActorSheetV2`, `renderDocumentSheetV2`, `renderApplicationV2`, nessa ordem.

Assinatura: `(application, element, context, options)`. `element` é um **`HTMLElement`** comum, não um objeto jQuery.

```js
// modules/forja-extras/scripts/sheet-button.js
Hooks.on("renderActorSheetV2", (app, element, context, options) => {
  const actor = app.document;
  if (actor.type !== "character") return;

  // Evita adicionar o botão duas vezes quando só algumas partes re-renderizam
  if (element.querySelector(".forja-extras-rest")) return;

  const button = document.createElement("button");
  button.type = "button";
  button.classList.add("forja-extras-rest");
  button.innerHTML = `<i class="fa-solid fa-bed"></i> Descansar`;
  button.addEventListener("click", () => actor.update({ "system.hp.value": actor.system.hp.max }));

  element.querySelector(".window-content")?.prepend(button);
});
```

::: v13
Aplicações legadas (AppV1) disparam hooks no estilo `renderApplicationV1` e ainda passam um objeto jQuery. Todas as aplicações do core na V13 são ApplicationV2, então escreva seus handlers para `HTMLElement`. Se precisar suportar os dois, normalize com `const el = html instanceof HTMLElement ? html : html[0];`.
:::

::: v14
A V14 adiciona `preRenderApplication` (e o `preRender{NomeDaClasse}` por classe, ex.: `preRenderActorSheetV2`), chamado **antes** da renderização com `(application, context, options)`. Use-o para adicionar ao `context` dados que seu hook de render ou template espera.

```js
// modules/forja-extras/scripts/sheet-context.js
Hooks.on("preRenderActorSheetV2", (app, context, options) => {
  // Valor extra para exibir na ficha
  context.forjaExtras = { restCount: app.document.getFlag("forja-extras", "rests") ?? 0 };
});
```
:::

## `getSceneControlButtons`

Chamado quando os controles de cena da esquerda são montados. Desde a V13, `controls` é um **record** (um objeto indexado pelo nome do controle), não um array, e o `tools` de cada controle também é um record.

```js
// modules/forja-extras/scripts/controls.js
Hooks.on("getSceneControlButtons", (controls) => {
  const tokens = controls.tokens;
  if (!tokens) return;

  tokens.tools.forjaRest = {
    name: "forjaRest",
    title: "FORJA_EXTRAS.Controls.Rest", // localizado automaticamente
    icon: "fa-solid fa-campground",
    order: Object.keys(tokens.tools).length,
    button: true,
    visible: game.user.isGM,
    onChange: (event, active) => {
      ui.notifications.info("O grupo faz um descanso curto.");
    }
  };
});
```

::: warning
Código escrito para a V12 que faz `controls.find(c => c.name === "token")` ou `controls.push(...)` quebra: não existe mais array, e a chave do grupo de tokens é `tokens`.
:::

## `getHeaderControls{Classe}`

Janelas ApplicationV2 têm um menu "…" no cabeçalho. Antes de ele ser exibido, `getHeaderControls{NomeDaClasse}` dispara para a classe e para cada classe pai, com `(application, controls)`, onde `controls` é um **array** de entradas `{ icon, label, action, visible?, ownership?, onClick? }`.

```js
// modules/forja-extras/scripts/header.js
Hooks.on("getHeaderControlsActorSheetV2", (app, controls) => {
  controls.push({
    icon: "fa-solid fa-share-nodes",
    label: "FORJA_EXTRAS.Header.Share", // localizado automaticamente
    action: "forjaExtrasShare",
    visible: () => game.user.isGM,
    onClick: () => ChatMessage.create({ content: `@UUID[${app.document.uuid}]` })
  });
});
```

## Ganchos novos no V14

::: v13
Os hooks abaixo não existem na V13. Para movimento de token use `preMoveToken` / `moveToken`; para lógica antes da renderização, sobrescreva `_prepareContext` na sua própria aplicação.
:::

::: v14
| Hook | Argumentos | Dispara quando |
| --- | --- | --- |
| `planToken` | `(tokenDocument)` | O movimento de um token é planejado (prévia ao arrastar / caminho planejado) |
| `preRenderApplication` / `preRender{Classe}` | `(application, context, options)` | Antes de uma ApplicationV2 renderizar |

```js
// modules/forja-extras/scripts/movement.js
Hooks.on("planToken", (tokenDocument) => {
  console.log(`forja-extras | Movimento planejado para ${tokenDocument.name}`);
});
```
:::

## Depurando ganchos

Ative o log de hooks no console do navegador (F12) para ver o nome e os argumentos de cada hook conforme ele dispara:

```js
CONFIG.debug.hooks = true;
```

Esse é o jeito mais rápido de descobrir qual hook usar: abra a ficha, mova o token ou clique no botão que você quer estender e leia o log. Volte para `false` quando terminar — é muito verboso.

## Armadilhas

- **Handlers de `init` registrados tarde demais.** Um `Hooks.once("init", ...)` dentro de um handler de `ready` nunca roda. Registre hooks de ciclo de vida no nível superior do seu script de entrada.
- **Handlers `pre*` assíncronos não cancelam.** Retorne `false` de forma síncrona.
- **Efeitos colaterais duplicados.** Hooks posteriores rodam em todo cliente; proteja com `userId === game.user.id`.
- **Usar jQuery em elementos de AppV2.** `element.find(...)` não é uma função; use `querySelector`.
- **Duplicação ao re-renderizar.** Hooks de render disparam a cada renderização; verifique se o elemento que você injetou já existe.
- **Erros de digitação no nome do hook falham em silêncio.** `Hooks.on("updateactor", …)` simplesmente nunca dispara. Use `CONFIG.debug.hooks` para conferir os nomes.
