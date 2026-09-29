# O que mudou no V14

Todas as mudanças do V13 para o V14 que afetam módulos e sistemas, agrupadas por área, com o que fazer em cada caso.

## Visão geral

O V14 ficou estável na build **14.359**, em 1º de abril de 2026. A build mais recente coberta aqui é a **14.368** (16 de setembro de 2026). O V14 **não pode ser atualizado por cima** do V13: o usuário reinstala o Foundry e mantém a pasta de dados.

| Área | Destaque | Impacto no seu código |
|---|---|---|
| Cenas | **Scene Levels**: uma cena empilha vários níveis em elevações diferentes | Visão, paredes, luzes e movimento passam a considerar níveis |
| Active Effects | **Active Effects V2**: `system.changes`, tipos em texto, fases, novas durações, eventos de expiração | <span class="pill break">quebra</span> em todo sistema que lê ou grava efeitos |
| Templates | `MeasuredTemplate` removido; **Template Regions** substituem | <span class="pill break">quebra</span> código de área de efeito |
| Chat | **Modos de visibilidade de mensagem** substituem os Roll Modes | <span class="pill dep">obsoleto</span> até o V16 |
| Dados | `template.json` entra em obsolescência; use data models | <span class="pill dep">obsoleto</span> |
| Interface | Janelas destacáveis, Paleta de Objetos, aba de Objetos | <span class="pill new">novo</span> |
| Visual | Framework de VFX, partículas, tremor de tela, transições de cena | <span class="pill new">novo</span> |
| Desempenho | Estruturas de dados do core de 3% a 25% mais rápidas nas operações comuns | nenhum |

Legenda: <span class="pill break">quebra</span> o código para de funcionar · <span class="pill dep">obsoleto</span> ainda funciona, com aviso · <span class="pill rename">renomeado</span> mesmo recurso, nome novo · <span class="pill new">novo</span> API nova

## Lista de verificação da migração

Siga esta lista ao portar um pacote. Cada item leva à página que mostra o código novo.

1. Defina `compatibility.minimum` / `verified` como `14` no manifesto e, se quiser, adicione `"type": "system"` ou `"type": "module"`. [Manifesto](#manifest)
2. Troque o `template.json` por `documentTypes` + classes `TypeDataModel`. [Modelos de dados](#data-models)
3. Mova as mudanças dos efeitos de `effect.changes` para `effect.system.changes`, e os números de `mode` para textos em `type`. [Efeitos ativos](#active-effect)
4. Converta as durações dos efeitos para `{ value, units, expiry }`. [Efeitos ativos](#active-effect)
5. Troque o código de `MeasuredTemplate` por Regions. [Regiões](#regions)
6. Troque `rollMode` por `messageMode`, e `applyRollMode` por `applyMode`. [Chat e rolagens](#chat-roll)
7. Troque as chaves de update `-=chave` / `==chave` por valores `DataFieldOperator`. [Documentos](#documents)
8. Procure no seu código os nomes removidos e renomeados das tabelas abaixo. [Migrações](#migrations)

## Cenas, níveis e tela de jogo

| Mudança | Tipo | O que fazer |
|---|---|---|
| **Scene Levels**: uma cena guarda vários `Level`s (imagens de fundo/frente em uma elevação). `Level` é uma classe global. | <span class="pill new">novo</span> | Deixe o código de canvas ciente dos níveis. [Cenas e tokens](#scene-token) |
| `Level#background`, `#foreground`, `#fog` não aceitam mais null; `Level#edges` guarda os `CanvasEdges` do nível. | <span class="pill new">novo</span> | |
| A gestão de arestas passou de `Wall` para `WallDocument`; `WallDocument#isDoor`, `#isOpen`. | <span class="pill rename">movido</span> | Leia o estado da porta no documento. |
| A linha de visão pode ser satisfeita no nível visualizado ou no nível do token. | <span class="pill break">comportamento</span> | Teste de novo os modos de detecção próprios. |
| `Scene#getSurfaces`, `Scene#testSurfaceCollision` (com `side`, `tMin`, `tMax`), `BaseEffectSource#level`. | <span class="pill new">novo</span> | |
| `SceneManager#_determineInitialLevel`; `CONFIG.Canvas.managedScenes` aceita instâncias de `SceneManager`. | <span class="pill new">novo</span> | |
| `Scene#activate({ viewOptions, pullUsers })`, `Scene#pullUsers(viewOptions)`; 14 transições de cena animadas. | <span class="pill new">novo</span> | |
| O hook `ready` dispara **depois** que as transições de cena terminam. | <span class="pill break">comportamento</span> | Não suponha que o canvas está parado antes disso. |
| `layerClass` no CONFIG dos documentos de canvas está obsoleto; as opções da camada ficam em `PlaceablesLayer`. | <span class="pill dep">obsoleto</span> | [Tela de jogo](#canvas-controls) |
| `PlaceableObject#clear` → `PlaceableObject#_clear` (protegido). | <span class="pill dep">obsoleto</span> | |
| `PlaceableObject#isInteractable`; objetos travados (menos Tokens) não são interativos. | <span class="pill new">novo</span> | |
| `SceneControls#tool` e `game.activeTool` podem ser `null`. | <span class="pill break">comportamento</span> | Proteja com `?.`. |
| `SceneControlTool` ganha `interaction`, `control`, `creation`, `shapeData`. | <span class="pill new">novo</span> | [Tela de jogo](#canvas-controls) |
| `ClockwiseSweepPolygonConfig#edgeOptions` → `#edgeTypes`; novos `CONST.EDGE_SENSE_TYPES`, `EDGE_RESTRICTION_TYPES`, `EDGE_DIRECTIONS`, `EDGE_DIRECTION_MODES`. | <span class="pill dep">obsoleto</span> | |
| `Scene#gridlessGrid`; `BaseGrid#getRectangle`, `#getLine`, `#getEllipse`. | <span class="pill new">novo</span> | |
| Tiles: `anchorX` / `anchorY`; a posição da malha é igual a `(x, y)`. `Tile.createPreview` obsoleto. | <span class="pill break">comportamento</span> | Revise os cálculos de posição de tiles. |
| `foundry.canvas.vfx`, `ParticleGenerator`, `animation.CanvasShakeEffect`, `globalThis.animejs`. | <span class="pill new">novo</span> | [Tela de jogo](#canvas-controls) |
| Técnicas de atenuação de luz Adaptive e Natural. | <span class="pill new">novo</span> | |

## Tokens e movimento

| Mudança | Tipo | O que fazer |
|---|---|---|
| Movimento planejado: `token.planMovement(options)`, `TokenDocument#startMovement`, `TokenMovementOptions#planned`, hook `planToken`. | <span class="pill new">novo</span> | [Cenas e tokens](#scene-token) |
| `Scene#moveTokens`, `TokenLayer#placeTokens`, IDs de movimento explícitos. | <span class="pill new">novo</span> | |
| `TokenDocument#move` só resolve quando o movimento inteiro termina; `TokenMovementData#finished`. | <span class="pill break">comportamento</span> | Código que espera o `move` agora espera mais. |
| `TokenDocument#depth`, `getMovementOrigin`, `getVisionOrigin`, `getLightOrigin`, `getSoundOrigin`, `getListenerPosition`. | <span class="pill new">novo</span> | |
| `TokenFindMovementPathOptions`: `ignoreWalls`, `ignoreCost`, `history` → `constrainOptions`. | <span class="pill dep">obsoleto</span> | |
| `TokenMovementActionConfig#getAnimationOptions(token)` agora recebe um `TokenDocument`. | <span class="pill break">quebra</span> | Atualize as ações de movimento próprias. |
| `TokenDocument#detectionModes` é um `TypedObjectField`. | <span class="pill break">quebra</span> | Acesse os modos pelo id, não pelo índice. |
| `TokenDocument#getTestPoints` respeita paredes e superfícies; `getOccupiedGridSpaceOffsets` também. | <span class="pill break">comportamento</span> | |
| `tokenOverrides` no Actor: Active Effects podem mudar visão, luz, imagem, alpha, disposição, tamanho e forma do token. | <span class="pill new">novo</span> | [Atores](#actor) |
| `TokenRuler#_getWaypointStyle`; waypoints intermediários são desenhados. | <span class="pill new">novo</span> | |
| `ActorDelta` pode ser `null`; `TokenDocument#_initializeSource` ignora `delta` quando `actorLink` é true. | <span class="pill break">comportamento</span> | Confira `token.delta` antes de usar. |

## Efeitos ativos V2

| Mudança | Tipo | O que fazer |
|---|---|---|
| `ActiveEffect#changes` → `ActiveEffect#system#changes`. | <span class="pill break">quebra</span> | [Efeitos ativos](#active-effect) |
| `mode` (número) da mudança → `type` (texto): `custom`, `multiply`, `add`, `subtract`, `downgrade`, `upgrade`, `override` (`CONST.ACTIVE_EFFECT_CHANGE_TYPES`). | <span class="pill break">quebra</span> | |
| `phase` da mudança: `initial`, `final` (`CONST.ACTIVE_EFFECT_CHANGE_PHASES`); pacotes podem criar fases e aplicá-las com `Actor#applyActiveEffects(phase)`. | <span class="pill new">novo</span> | |
| `EffectChangeData#value` é desserializado (valor JSON ou texto). | <span class="pill break">comportamento</span> | Não suponha que é texto. |
| A duração é `{ value, units, expiry, expired }`; unidades em `CONST.ACTIVE_EFFECT_DURATION_UNITS`. | <span class="pill break">quebra</span> | |
| Eventos de expiração `combatStart`, `roundStart`, `turnStart`, `combatEnd`, `roundEnd`, `turnEnd` (`CONST.ACTIVE_EFFECT_EXPIRY_EVENTS`). | <span class="pill new">novo</span> | [Combate](#combat) |
| `ActiveEffect.registry` acompanha os efeitos temporários. | <span class="pill new">novo</span> | |
| Active Effects são **documentos primários**: barra lateral, compêndios, soltar em um Token para aplicar. | <span class="pill new">novo</span> | |
| `ActiveEffect#origin` é um `DocumentUUIDField`. | <span class="pill break">quebra</span> | Guarde só um UUID. |
| `CONFIG.ActiveEffect.legacyTransferral` **removido**. | <span class="pill break">quebra</span> | |
| `CONFIG.statusEffects` é um objeto `{ [id]: config }` (arrays ainda são aceitos). | <span class="pill dep">obsoleto</span> | |
| O comportamento de Region "Active Effect" aplica efeitos aos tokens dentro da região. | <span class="pill new">novo</span> | [Regiões](#regions) |

## Regiões e áreas de efeito

| Mudança | Tipo | O que fazer |
|---|---|---|
| Tipo de documento `MeasuredTemplate` **removido**; os recursos foram para as Regions. | <span class="pill break">quebra</span> | [Regiões](#regions) |
| Novas formas: linha, cone, `RingShapeData`, `EmanationShapeData`, `TokenShapeData`, `GridShapeData`; modo baseado no grid. | <span class="pill new">novo</span> | |
| Regiões presas a tokens: `RegionDocument#attachment.token`; `RegionDocument.createTokenEmanation()`. | <span class="pill new">novo</span> | |
| `RegionLayer#placeRegion` / `placeRegions` (`attachToToken`, `onChange`, `allowEmpty`); `index`/`count` → `shapeIndex`/`shapeCount`. | <span class="pill new">novo</span> | |
| `RegionDocument#teleportTokens`, `#spawnTokens` (`avoidOccupied`, `{ create: false }`). | <span class="pill new">novo</span> | |
| Campo de ownership nas Regions e permissão `REGION_CREATE`; tipo e prioridade de restrição. | <span class="pill new">novo</span> | |
| A `visibility` padrão de Regions que não são template é `LAYER_UNLOCKED`. | <span class="pill break">comportamento</span> | |
| `RegionShape` → mixins de `BaseShapeData`; `foundry.data.regionShapes.RegionPolygonTree` → `foundry.data.PolygonTree`. | <span class="pill rename">renomeado</span> | |

## Documentos e dados

| Mudança | Tipo | O que fazer |
|---|---|---|
| `template.json` entra em obsolescência. | <span class="pill dep">obsoleto</span> | [Modelos de dados](#data-models) |
| Manifesto: `"type": "system" \| "module"` opcional. | <span class="pill new">novo</span> | [Manifesto](#manifest) |
| Chaves `-=` / `==` do `updateSource` → valores `DataFieldOperator`. | <span class="pill dep">obsoleto</span> | [Documentos](#documents) |
| `DataModel#_updateDiff`, `#_updateCommit`; a validação foi para dentro do `_updateDiff`. | <span class="pill break">comportamento</span> | |
| `SchemaField#extendFields`, `#removeFields`; `DataModel#getFieldForProperty`; `DataField#placeholder`. | <span class="pill new">novo</span> | |
| `Document.create` usa `this.implementation`; `Document#persisted`; UUIDs relativos (`buildRelativeUuid`). | <span class="pill new">novo</span> | |
| Os metadados do documento controlam se o tipo base pode ser criado. | <span class="pill new">novo</span> | |
| `TypeDataModel#onEmbed` (embeds em HTML). | <span class="pill new">novo</span> | |
| `DocumentCollection#importDocument` mantém os IDs; gravações em lote entre coleções. | <span class="pill new">novo</span> | [Compêndios](#compendium) |
| `DocumentStatsField#createdTime` / `modifiedTime` são obrigatórios; `MacroData#author` aceita null. | <span class="pill break">comportamento</span> | |
| `foundry.utils.equals()` substitui `objectsEqual`; `isPlainObject`; `diffObject(…, { bidirectional })`; `debounce().cancel()`. | <span class="pill rename">renomeado</span> | [Guia rápido da API](#api-map) |
| Polyfill de `RegExp.escape` removido (usa o nativo). | <span class="pill break">quebra</span> | |
| `Collection` usa os iterator helpers nativos. | <span class="pill new">novo</span> | |
| `User.queryMany`; os handlers de query recebem quem enviou. | <span class="pill new">novo</span> | [Comunicação entre clientes](#sockets) |
| Um lote grande de obsolescências do V12 foi removido. | <span class="pill break">quebra</span> | Corrija antes todos os avisos de obsolescência do V12. |

## Chat, dados e localização

| Mudança | Tipo | O que fazer |
|---|---|---|
| Roll Modes → Message Visibility Modes (`public`, `self`, `gm`, `blind`) mais o modo In-Character. | <span class="pill dep">obsoleto</span> até o V16 | [Chat e rolagens](#chat-roll) |
| `ChatMessage.applyRollMode` → `ChatMessage.applyMode`; `toMessage({ rollMode })` → `{ messageMode }`. | <span class="pill rename">renomeado</span> | |
| `ChatLog.MESSAGE_PATTERNS` → `ChatLog.CHAT_COMMANDS`. | <span class="pill dep">obsoleto</span> até o V16 | |
| Booleanos nos dados de rolagem viram `0`/`1`; `Roll.replaceFormulaData` usa o `toString()` próprio do objeto. | <span class="pill break">comportamento</span> | |
| `game.i18n.localize(key, data)` incorpora o `format()`; atalho global `_loc`. | <span class="pill new">novo</span> | [Tradução](#localization) |

## Aplicações e interface

| Mudança | Tipo | O que fazer |
|---|---|---|
| **Janelas destacáveis** da ApplicationV2; gerador `ApplicationV2.instances`. | <span class="pill new">novo</span> | [Janelas com ApplicationV2](#applicationv2) |
| `HeaderControls` e `ContextMenu` unificados; `ContextMenuEntry#icon` aceita nomes de classe. | <span class="pill break">comportamento</span> | |
| `_canRender` recebe se é a primeira renderização; suporte a clique do meio (`auxclick`). | <span class="pill new">novo</span> | |
| TinyMCE removido; `foundry.prosemirror.defaultPlugins` → `ProseMirrorEditor.buildDefaultPlugins()`. | <span class="pill break">quebra</span> | [Diários](#journal) |
| ProseMirror: details, tabelas, tamanho/cor de fonte, legendas, templates HTML `inline`/`block`. | <span class="pill new">novo</span> | |
| `CONFIG[documentName].embedHandlers`. | <span class="pill new">novo</span> | |
| `HTMLFormulaInputElement`, `FormulaEditor`, `Autocompletion`. | <span class="pill new">novo</span> | [Fichas](#sheets) |
| `parseHTML` devolve `null` em caso de falha. | <span class="pill break">comportamento</span> | |
| `<code>` inline por padrão (classe `block` para blocos). | <span class="pill break">comportamento</span> | [Estilos](#styling) |
| Helper `highlightElement(element, options)`. | <span class="pill new">novo</span> | |
| Font Awesome 7.2. | <span class="pill break">comportamento</span> | |

## Pacotes e permissões

| Mudança | Tipo | O que fazer |
|---|---|---|
| Pacotes de mundo não podem mais ser instalados pelo Setup; use documentos Adventure. | <span class="pill break">quebra</span> | [Publicação](#packaging) |
| O hot reload de CSS segue `@import`; a renderização do hot reload recebe o arquivo. | <span class="pill new">novo</span> | [Ambiente](#setup) |
| As importações de Adventure ficam registradas na configuração `core.adventureImports`. | <span class="pill new">novo</span> | |
| Assistentes de mestre ganham mais permissões (menos `FILES_UPLOAD`, `MACRO_SCRIPT`, `SETTINGS_MODIFY`). | <span class="pill break">comportamento</span> | Revise checagens de `isGM` e de papel. |

## Fontes

- Notas de versão: [14.349](https://foundryvtt.com/releases/14.349), [14.352](https://foundryvtt.com/releases/14.352), [14.353](https://foundryvtt.com/releases/14.353), [14.354](https://foundryvtt.com/releases/14.354), [14.355](https://foundryvtt.com/releases/14.355), [14.356](https://foundryvtt.com/releases/14.356), [14.357](https://foundryvtt.com/releases/14.357), [14.358](https://foundryvtt.com/releases/14.358), [14.359 (estável)](https://foundryvtt.com/releases/14.359)
- [Documentação da API do V14](https://foundryvtt.com/api/v14/)
