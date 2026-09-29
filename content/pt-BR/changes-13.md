# O que mudou no V13

As mudanças do V12 para o V13 que afetam desenvolvedores: a troca para ApplicationV2, as classes organizadas em espaços de nomes, o novo tema e o movimento de tokens.

## Visão geral

O V13 ficou estável na build **13.341**, em 27 de abril de 2025. A build mais recente do V13 é a **13.351** (12 de novembro de 2025). O V13 exige Node.js 20 (o 22 é suportado) e vem com Electron 33.

| Área | Destaque | Impacto no seu código |
|---|---|---|
| Aplicações | **Todas as aplicações do core usam ApplicationV2**; as fichas padrão de ator/item foram removidas | <span class="pill break">quebra</span> em sistemas sem fichas próprias |
| Namespaces | A maioria dos globais foi para módulos ES `foundry.*` | <span class="pill dep">obsoleto</span> os globais até o V15 |
| Tema | **Theme V2** com claro/escuro e camadas de cascata do CSS | Reestilize suas fichas |
| Controles de cena | `controls` é um objeto, não um array | <span class="pill break">quebra</span> |
| Tokens | Medição ao arrastar, waypoints, ações de movimento, API de movimento | <span class="pill new">novo</span> |
| Configurações | Novo escopo `user` | <span class="pill new">novo</span> |
| jQuery | Começa a obsolescência; os hooks passam `HTMLElement` | Pare de usar `html.find` |

Legenda: <span class="pill break">quebra</span> o código para de funcionar · <span class="pill dep">obsoleto</span> ainda funciona, com aviso · <span class="pill rename">renomeado</span> mesmo recurso, nome novo · <span class="pill new">novo</span> API nova

## Lista de verificação da migração (V12 → V13)

1. Registre suas próprias fichas de ator e de item. O core não registra mais fichas padrão, então um sistema sem elas não mostra ficha nenhuma. [Fichas](#sheets)
2. Porte fichas e diálogos de Application (V1) para ApplicationV2. [Janelas com ApplicationV2](#applicationv2)
3. Troque os globais pelos caminhos `foundry.*` para calar os avisos de obsolescência (eles saem no V15). [Guia rápido da API](#api-map)
4. Reescreva o `getSceneControlButtons` para a estrutura de objeto. [Tela de jogo](#canvas-controls)
5. Troque o jQuery dos hooks de renderização (`html.find`, `html.on`) pelas APIs do DOM.
6. Revise o código de chat: os roll modes só são aplicados no `_preCreate` quando `options.rollMode` é informado. [Chat e rolagens](#chat-roll)
7. Reestilize para o Theme V2 e teste no claro e no escuro. [Estilos](#styling)

## Aplicações e interface

| Mudança | Tipo | O que fazer |
|---|---|---|
| Todas as aplicações do core migraram de AppV1 para ApplicationV2. | <span class="pill break">quebra</span> | Os hooks agora recebem instâncias AppV2 e `HTMLElement`. |
| Registros das fichas padrão de ator e item removidos (sem fallback AppV1). | <span class="pill break">quebra</span> | [Fichas](#sheets) |
| `ApplicationV2#submit` devolve o valor do handler do formulário. | <span class="pill new">novo</span> | |
| `options.window.contentTag` para ligar o elemento de conteúdo a um formulário. | <span class="pill new">novo</span> | |
| `static TABS` e `_prepareTabs(group)` para grupos de abas. | <span class="pill new">novo</span> | [Janelas com ApplicationV2](#applicationv2) |
| Hook `getHeaderControls{NomeDaClasse}(app, controls)`. | <span class="pill new">novo</span> | |
| As parts do `HandlebarsApplicationMixin` aceitam `root: true`. | <span class="pill new">novo</span> | |
| Ação `editImage` no `DocumentSheetV2`; framework de arrastar e soltar no `ActorSheetV2`. | <span class="pill new">novo</span> | |
| Classes `.theme-dark` / `.theme-light` na AppV2; a AppV1 recebe `.theme-light`. | <span class="pill new">novo</span> | [Estilos](#styling) |
| Camadas de cascata do CSS em todos os estilos do core. | <span class="pill break">comportamento</span> | |
| `SceneControls#controls` é um objeto; afeta o `getSceneControlButtons`. | <span class="pill break">quebra</span> | [Tela de jogo](#canvas-controls) |
| `ClientDocument.createDialog` / `deleteDialog` aceitam parâmetros de `DatabaseOperation`. | <span class="pill new">novo</span> | [Diálogos](#dialogs) |
| Tipo de notificação `progress`; `Notifications#displayProgressBar` obsoleto. | <span class="pill dep">obsoleto</span> | |
| `Notifications#notify` aceita um objeto `format`. | <span class="pill new">novo</span> | |
| `HTMLCodeMirrorElement` para editar JSON/HTML/JavaScript. | <span class="pill new">novo</span> | |
| `CONFIG.ChatMessage.popoutClass`. | <span class="pill new">novo</span> | |
| Começa a obsolescência do jQuery. | <span class="pill dep">obsoleto</span> | |

## Espaços de nomes

Muitas classes foram para módulos ES em `foundry.<grupo>`. Os nomes globais antigos ainda funcionam no V13 e no V14, com aviso de obsolescência, e saem no V15.

| Global antigo | Caminho no V13 |
|---|---|
| `ActorSheet` (V1) | `foundry.appv1.sheets.ActorSheet` (legado; use `foundry.applications.sheets.ActorSheetV2`) |
| `DocumentSheetConfig` | `foundry.applications.apps.DocumentSheetConfig` |
| `Actors`, `Items` | `foundry.documents.collections.Actors`, `foundry.documents.collections.Items` |
| `loadTemplates`, `renderTemplate` | `foundry.applications.handlebars.loadTemplates`, `…renderTemplate` |
| `TextEditor` | `foundry.applications.ux.TextEditor.implementation` |
| `DragDrop`, `ContextMenu` | `foundry.applications.ux.DragDrop`, `foundry.applications.ux.ContextMenu` |
| `Token`, `Tile`, `Wall`… | `foundry.canvas.placeables.Token`, … |
| `TokenLayer`, `PlaceablesLayer`, `InteractionLayer` | `foundry.canvas.layers.*` |
| `CanvasAnimation`, `Ray`, `MouseInteractionManager` | `foundry.canvas.animation.CanvasAnimation`, `foundry.canvas.geometry.Ray`, `foundry.canvas.interaction.MouseInteractionManager` |

Veja a tabela completa no [Guia rápido da API](#api-map). Na dúvida, digite o nome da classe no console: o aviso de obsolescência mostra o caminho novo.

## Documentos e dados

| Mudança | Tipo | O que fazer |
|---|---|---|
| Novo escopo de configuração `user` (por usuário, sincronizado entre dispositivos). | <span class="pill new">novo</span> | [Configurações](#settings) |
| `Symbol` não é mais aceito como tipo de configuração. | <span class="pill break">quebra</span> | |
| Os roll modes só são aplicados em `ChatMessage#_preCreate` com `options.rollMode`; `ChatMessage.applyRollMode` mantém os destinatários de whisper que já existem. | <span class="pill break">comportamento</span> | [Chat e rolagens](#chat-roll) |
| `appendNumber` e `prependAdjective` passaram de Token para PrototypeToken. | <span class="pill break">quebra</span> | |
| `DocumentOwnershipField` usa `gmOnly`; novo `DocumentAuthorField` para `ChatMessage#author`, `Macro#author`, `Drawing#author`. | <span class="pill break">comportamento</span> | |
| Sobrescritas de `ServerDocument#testUserPermission` removidas; use `getUserLevel`. | <span class="pill break">quebra</span> | |
| `NumberField#toInput` sem seletor de intervalo para campos que aceitam null; `step` segue o HTML. | <span class="pill break">comportamento</span> | |
| O valor inicial de `PlaylistSound#channel` é `""`. | <span class="pill break">comportamento</span> | |
| `StringField._getChoices` → `StringField._prepareChoiceConfig`. | <span class="pill rename">renomeado</span> | |
| A permissão `MACRO_SCRIPT` limita criar macros de script, não executá-las. | <span class="pill break">comportamento</span> | |
| `prepareData` não roda mais duas vezes em updates de itens de um ator. | <span class="pill break">comportamento</span> | |
| `foundry.utils.deepFreeze`, `deepSeal`; `User#isActiveGM`; `Users#getDesignatedUser`, `User#isDesignated`. | <span class="pill new">novo</span> | [Comunicação entre clientes](#sockets) |
| Queries de usuário: `CONFIG.queries` + `User#query`. | <span class="pill new">novo</span> | [Comunicação entre clientes](#sockets) |
| `CalendarData#add`; `Combat#_onEnter`, `Combat#_onExit`. | <span class="pill new">novo</span> | |
| `Roll#_prepareChatRenderContext` é protegido e pode ser sobrescrito; `Roll#render` recebe a `ChatMessage`. | <span class="pill new">novo</span> | [Chat e rolagens](#chat-roll) |

## Tela de jogo e tokens

| Mudança | Tipo | O que fazer |
|---|---|---|
| Medição ao arrastar tokens com waypoints, elevação e ações de movimento (`CONFIG.Token.movement`). | <span class="pill new">novo</span> | [Cenas e tokens](#scene-token) |
| `TokenDocument#move`, `measureMovementPath`, `getDirectMovementPath`, `stopMovement`, `pauseMovement`, `continueMovement`, `movementHistory`, `clearMovementHistory`. | <span class="pill new">novo</span> | |
| `Token#findMovementPath`, `constrainMovementPath`, `_getMovementCostFunction`. | <span class="pill new">novo</span> | |
| `TokenDocument#getSnappedPosition`, `getCenterPoint`, `getGridSpacePolygon`, `getOccupiedGridSpaceOffsets`. | <span class="pill new">novo</span> | |
| `Token#getSize` → `TokenDocument#getSize`; `Token#testInsideRegion` → `TokenDocument#testInsideRegion`; `Token#segmentizeRegionMovement` → `TokenDocument#segmentizeRegionMovementPath`. | <span class="pill dep">obsoleto</span> | |
| `ElevatedPoint` `{ x, y, elevation }`; as coordenadas do grid aceitam elevação. | <span class="pill new">novo</span> | |
| `Token#animate` ganha `chain`; `CONFIG.Token.movement.defaultSpeed`. | <span class="pill new">novo</span> | |
| Comportamento de Region **Modify Movement Cost**; `RegionDocument#teleportToken`; `CONST.REGION_MOVEMENT_SEGMENTS`. | <span class="pill new">novo</span> | [Regiões](#regions) |
| `TextureExtractor#extract` devolve `{ pixels, width, height, out }`. | <span class="pill break">quebra</span> | |
| Prioridade de luz, luzes que reagem ao som, portas animadas, marcadores de turno de combate. | <span class="pill new">novo</span> | [Combate](#combat) |
| `PlaceableObject.implementation`, `foundry.utils.getPlaceableObjectClass`. | <span class="pill new">novo</span> | |
| `FogManager#isPointExplored`; `BasePointSource#testPoint`. | <span class="pill new">novo</span> | |

## Fontes

- Notas de versão: [13.332](https://foundryvtt.com/releases/13.332), [13.341 (estável)](https://foundryvtt.com/releases/13.341), [todas as versões V13](https://foundryvtt.com/releases/)
- [Documentação da API do V13](https://foundryvtt.com/api/v13/)
