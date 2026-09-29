# Introdução

O que são pacotes do Foundry, como eles carregam, o modelo de documentos em resumo e como usar este guia.

## O que você pode construir

O Foundry Virtual Tabletop é estendido por meio de **pacotes**. Como desenvolvedor, você vai escrever um de dois tipos:

| Pacote | Fica em | O que faz | Por mundo |
|---|---|---|---|
| **Sistema** | `Data/systems/<id>/` | Define as *regras*: o que um Actor ou Item *é*, seus dados, fichas, rolagens, iniciativa de combate. | Exatamente **um** |
| **Módulo** | `Data/modules/<id>/` | Adiciona ou altera comportamento sobre um sistema (ou sobre o core): nova interface, automação, pacotes de conteúdo, macros. | **Zero ou vários** |

Um terceiro tipo de pacote, o **mundo** (world), é a campanha em si (seu banco de dados de atores, cenas, diários…). Você raramente escreve código de mundo; você *testa* em mundos.

::: tip
Se a sua ideia é "um jogo novo com sua própria ficha de personagem", você quer um **sistema**. Se é "fazer o jogo X fazer algo a mais", você quer um **módulo**. Um módulo pode declarar que só funciona com um sistema específico (veja [o manifesto](#manifest)).
:::

### Sistemas e módulos: diferenças técnicas

- O manifesto de um sistema é `system.json`; o de um módulo é `module.json`. A maioria dos campos é compartilhada.
- Só um sistema declara **subtipos de documento** (`documentTypes`, por exemplo Actor `character` / `npc`) e seus data models. Módulos também podem adicionar subtipos, mas eles ganham namespace (`forja-extras.companion`).
- Só um sistema define padrões do mundo inteiro, como distância/unidade do grid, fórmula de iniciativa e atributos das barras do token.
- Todo o resto (hooks, configurações, aplicações, compêndios, sockets) está disponível para ambos.

## Como os pacotes carregam

Quando um usuário entra em um mundo, o cliente inicializa em uma ordem fixa. Conhecê-la diz a você **onde** seu código pode rodar.

1. O **core** carrega (o namespace `foundry`, `CONFIG`, `CONST`, `Hooks`).
2. O **mundo** é lido: qual sistema e quais módulos estão ativos.
3. Os scripts do **sistema** carregam (`esmodules`/`scripts` do `system.json`), depois os scripts de cada **módulo ativo**, em ordem de dependência.
4. Hooks disparam durante a inicialização: `init` → `i18nInit` → `setup` → `ready`.

```js
// Os três hooks que você usa em quase todo pacote
Hooks.once("init", () => {
  // CONFIG, configurações, data models, fichas. game.actors etc. ainda NÃO existem.
  console.log("forja | init");
});

Hooks.once("setup", () => {
  // Localização e configurações prontas; documentos ainda não foram preparados.
});

Hooks.once("ready", () => {
  // Tudo carregado: game.actors, game.user, canvas (se houver cena ativa).
  console.log(`forja | ready, user is ${game.user.name}`);
});
```

::: v14
Na V14 o `ready` dispara **depois** que qualquer animação de transição de cena termina, então código em `ready` pode rodar um pouco mais tarde do que na V13.
:::

::: warning
Registrar data models, fichas ou configurações no `ready` é tarde demais — os documentos já foram preparados. Faça isso no `init`.
:::

## O modelo de documentos em resumo

Quase tudo que é persistente no Foundry é um **Document**: um registro no banco de dados do mundo com schema, permissões e hooks de ciclo de vida (`preCreate`, `updateActor`, …). Documentos são **primários** (guardados em uma coleção do mundo como `game.actors`) ou **embutidos** (guardados dentro de um pai, como Items dentro de um Actor).

| Document | Coleção / pai | Usado para |
|---|---|---|
| `Actor` | `game.actors` | Personagens, PdMs, veículos — qualquer coisa com ficha que age. |
| `Item` | `game.items` ou embutido em `Actor` | Armas, magias, habilidades, inventário. |
| `ActiveEffect` | embutido em `Actor`/`Item` | Modificadores temporários ou permanentes de dados. |
| `ChatMessage` | `game.messages` | Entradas do chat, resultados de rolagens. |
| `Combat` | `game.combats` | Encontros; embute `Combatant`. |
| `Scene` | `game.scenes` | Mapas; embute `Token`, `Tile`, `Wall`, `AmbientLight`, `Region`, … |
| `Token` (`TokenDocument`) | embutido em `Scene` | A presença de um Actor no mapa. |
| `Region` | embutido em `Scene` | Áreas com comportamentos (teleporte, dano, efeitos). |
| `JournalEntry` | `game.journal` | Notas e handouts; embute `JournalEntryPage`. |
| `Macro` | `game.macros` | Scripts da hotbar e macros de chat. |
| `Folder` | `game.folders` | Organização de outros documentos na barra lateral. |
| `Cards` | `game.cards` | Baralhos, mãos e pilhas; embute `Card`. |
| `Playlist` | `game.playlists` | Áudio; embute `PlaylistSound`. |
| `User` | `game.users` | Jogadores e Mestres. |

::: v14
A V14 adiciona **Scene Levels**: uma Scene pode empilhar vários documentos **`Level`** (imagens em elevações diferentes). Além disso:

- **ActiveEffect** também virou documento primário — efeitos podem ficar na barra lateral e em compêndios, não só embutidos.
- O documento `MeasuredTemplate` foi removido; templates agora são **Regions** com formas como cone, linha, anel e emanação.
:::

::: v13
Na V13, `ActiveEffect` está sempre embutido em um Actor ou Item, e templates de área usam o documento separado `MeasuredTemplate`, embutido em uma Scene.
:::

Cada documento tem uma propriedade `system` para os dados do seu pacote, definida por um **data model**. Saiba mais em [Documentos](#documents) e [Modelos de dados](#data-models).

```js
// Lendo documentos pelo console do navegador
const hero = game.actors.getName("Aria");
console.log(hero.type);             // "character"
console.log(hero.system.hp.value);  // dados definidos pelo sistema forja
console.log(hero.items.size);       // Items embutidos
```

## Como ler este guia

### Seletor de versão

Escolha **V13** ou **V14** na barra superior. Textos e códigos que diferem entre versões mudam junto; todo o resto vale para ambas. O padrão é a V14, a versão estável atual.

### Quadros "Mudou no V14"

Com a V14 selecionada, páginas cujo assunto mudou mostram uma caixa **Mudou na V14** perto do topo, com uma lista curta do que mudou. A lista completa fica no [mudanças do V14](#changes-14); se você está vindo da V12, leia também o [mudanças do V13](#changes-13).

### O exemplo contínuo

Todas as páginas se apoiam nos mesmos dois pacotes, para que os exemplos se conectem:

- **`forja`** — um pequeno *sistema* de RPG de fantasia (`systems/forja/...`) com tipos de Actor `character` e `npc`, e tipos de Item `weapon` e `spell`.
- **`forja-extras`** — um *módulo* (`modules/forja-extras/...`) que adiciona ferramentas por cima do `forja`.

::: tip
Os blocos de código são completos: copie-os para o caminho indicado no texto e eles devem funcionar. Identificadores ficam em inglês; comentários e textos de interface são traduzidos.
:::

### Referências da API

Quando precisar da assinatura exata de algo, vá à documentação oficial: [API V13](https://foundryvtt.com/api/v13/) e [API V14](https://foundryvtt.com/api/v14/). Este guia aponta para lá em vez de repetir cada parâmetro.

## Trilha de aprendizado

Siga as páginas mais ou menos nesta ordem:

1. **Primeiros passos** — prepare o [ambiente](#setup), entenda [o manifesto](#manifest), depois construa [seu primeiro módulo](#first-module) e [seu primeiro sistema](#first-system).
2. **Conceitos centrais** — [Ganchos de eventos](#hooks), [Documentos](#documents), [Modelos de dados](#data-models), [Configurações](#settings), [Tradução](#localization).
3. **Entidades** — [Atores](#actor), [Itens](#item), [Efeitos ativos](#active-effect), [Chat e rolagens](#chat-roll), [Combate](#combat), [Cenas e tokens](#scene-token), [Regiões](#regions), [Diário](#journal), [Compêndios](#compendium), [Outros documentos](#other-documents).
4. **Interface** — [Janelas com ApplicationV2](#applicationv2), [Fichas](#sheets), [Diálogos](#dialogs), [Controles da tela de jogo](#canvas-controls), [Estilos](#styling).
5. **Avançado** — [Comunicação entre clientes](#sockets), [Migrações](#migrations), [Empacotamento e publicação](#packaging), [Guia rápido da API](#api-map).
6. **Referência** — [Mudanças no V14](#changes-14), [Mudanças no V13](#changes-13).

::: tip
Sem muito tempo? Faça [Ambiente](#setup) → [Primeiro sistema](#first-system) → [Fichas](#sheets). Isso coloca uma ficha de personagem jogável na tela em uma tarde.
:::
