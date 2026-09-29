# Outros documentos

Guias curtos sobre macros, pastas, cartas, listas de reprodução, usuários e configurações, mais um exemplo completo de "pilha de itens" feito com marcadores (`flags`).

::: changed
- Novo documento `Level` embutido nas Scenes (veja [Níveis de cena](#scene-token--niveis-de-cena)).
- `MeasuredTemplate` foi removido; as áreas de efeito são [Regiões de área de efeito](#regions).
- Active Effects são documentos primários (barra lateral, compêndios); veja [Efeitos ativos](#active-effect).
- `MacroData#author` aceita null; os assistentes de mestre ganham mais permissões (menos `FILES_UPLOAD`, `MACRO_SCRIPT`, `SETTINGS_MODIFY`).
- `User.queryMany()` consulta vários usuários de uma vez; os handlers recebem o id de quem enviou.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Além de Actors, Items e Scenes, o Foundry tem vários tipos de documento menores. Todos têm a
mesma API ([Documentos](#documents)): `create`, `update`, `delete`, flags, ownership e hooks.
Esta página mostra para que serve cada um e as chamadas que você realmente vai usar.

| Documento | Coleção | Uso típico em módulos |
| --- | --- | --- |
| `Macro` | `game.macros` | atalhos na hotbar para itens e habilidades |
| `Folder` | `game.folders` | organizar o conteúdo gerado |
| `Cards` / `Card` | `game.cards` | baralhos, mãos, pilhas |
| `Playlist` / `PlaylistSound` | `game.playlists` | música e ambientação |
| `User` | `game.users` | permissões, dados por jogador, "quem executa" |
| `Setting` | `game.settings.storage` | o valor guardado de uma [configuração](#settings) |

## Macros (`Macro`)

Uma Macro é um comando `"script"` (JavaScript) ou `"chat"` (texto enviado como mensagem de chat).

```js
const macro = await Macro.create({
  name: "Forja: Descansar",
  type: "script",
  img: "icons/svg/sleep.svg",
  command: `
    // 'actor' e 'token' são fornecidos pelo core (token selecionado ou personagem atribuído)
    if (!actor) return ui.notifications.warn("Selecione um token primeiro.");
    await actor.update({ "system.hp.value": actor.system.hp.max });
    ChatMessage.create({ speaker: ChatMessage.getSpeaker({ actor }), content: "Descansa." });
  `
});

// Executa pelo código; chaves extras viram variáveis dentro do script
await macro.execute({ reason: "camp" });
```

Macros de script rodam como uma função assíncrona com `speaker`, `actor`, `token`, `character`, `event`
e as chaves do seu `scope` disponíveis. Criar macros de script exige a permissão `MACRO_SCRIPT`
(no V13+ ela limita só a criação, não a execução).

### Macros de item na barra de atalhos

O hook `hotbarDrop` dispara quando algo é solto na hotbar. Ele precisa devolver `false`
**de forma síncrona** para impedir o comportamento padrão, então comece o trabalho assíncrono sem esperá-lo.

```js
// systems/forja/module/macros.mjs
Hooks.on("hotbarDrop", (bar, data, slot) => {
  if (data.type !== "Item") return;          // deixa o core tratar os outros tipos
  createItemMacro(data, slot);               // sem await de propósito
  return false;
});

async function createItemMacro(data, slot) {
  const item = await fromUuid(data.uuid);
  if (!item?.parent) return ui.notifications.warn("FORJA.Macro.OwnedOnly", { localize: true });
  const command = `game.forja.rollItemMacro(${JSON.stringify(item.name)});`;
  let macro = game.macros.find(m => (m.command === command) && m.isAuthor);
  macro ??= await Macro.create({
    name: item.name, type: "script", img: item.img, command,
    flags: { forja: { itemMacro: true } }
  });
  await game.user.assignHotbarMacro(macro, slot);
}

// Exposto no init: game.forja = { rollItemMacro }
export function rollItemMacro(itemName) {
  const speaker = ChatMessage.getSpeaker();
  const actor = game.actors.tokens[speaker.token] ?? game.actors.get(speaker.actor);
  const item = actor?.items.getName(itemName);
  if (!item) return ui.notifications.warn(game.i18n.format("FORJA.Macro.NoItem", { name: itemName }));
  return item.roll();
}
```

Guardar o **nome** do item (não o id) faz a macro funcionar para qualquer ator que tenha um item com
esse nome, que é o que os jogadores costumam esperar.

## Pastas (`Folder`)

Pastas são documentos com um `type` (o nome do documento que elas guardam), uma pasta-pai `folder` opcional,
`color` e `sorting` (`"a"` alfabético, `"m"` manual).

```js
const root = await Folder.create({ name: "Forja", type: "Item", color: "#7a3b12", sorting: "a" });
const weapons = await Folder.create({ name: "Armas", type: "Item", folder: root.id });
await Item.create({ name: "Lâmina de Brasa", type: "weapon", folder: weapons.id });

console.log(weapons.contents);   // documentos direto na pasta
console.log(root.children);      // nós da árvore de subpastas
```

O aninhamento é limitado a `CONST.FOLDER_MAX_DEPTH` níveis. Também existem pastas dentro dos compêndios.

## Cartas (`Cards`)

Um documento `Cards` é um **baralho** (deck), uma **mão** (hand) ou uma **pilha** (pile), conforme o `type`; os documentos `Card` embutidos
têm `faces` (cada uma `{ name, text, img }`), um verso `back` e `face` (índice da face visível, ou
`null` para virada para baixo).

```js
const deck = await Cards.create({
  name: "Baralho do Destino do Forja",
  type: "deck",
  cards: [1, 2, 3, 4, 5].map(n => ({
    name: `Destino ${n}`,
    type: "base",
    value: n,
    faces: [{ name: `Destino ${n}`, img: `systems/forja/assets/cards/fate-${n}.webp` }],
    back: { img: "systems/forja/assets/cards/back.webp" },
    face: null
  }))
});
const hand = await Cards.create({ name: "Mão da Aria", type: "hand" });

await deck.shuffle();
await deck.deal([hand], 2);               // duas cartas do baralho para a mão
await hand.pass(deck, [hand.cards.contents[0].id]); // devolve uma
await deck.recall();                      // devolve ao baralho todas as cartas distribuídas
```

## Listas de reprodução (`Playlist` e `PlaylistSound`)

```js
const playlist = await Playlist.create({
  name: "Batalha do Forja",
  mode: CONST.PLAYLIST_MODES.SEQUENTIAL,
  sounds: [
    { name: "Tambores", path: "modules/forja-extras/audio/drums.ogg", volume: 0.5, repeat: true }
  ]
});
await playlist.playAll();
await playlist.stopAll();

// Efeito sonoro único para todos (o segundo argumento transmite para todos)
foundry.audio.AudioHelper.play({ src: "modules/forja-extras/audio/clang.ogg", volume: 0.8, loop: false }, true);
```

Tocar uma playlist é um update de documento (`playing: true`), então só quem pode atualizar a
playlist (normalmente o mestre) consegue iniciá-la. `AudioHelper.play` com transmissão é o jeito de os jogadores
dispararem efeitos curtos.

## Usuários (`User`)

`game.user` é o usuário atual; `game.users` tem todo mundo, conectado ou não.

```js
game.user.isGM;                  // mestre ou assistente de mestre
game.user.role;                  // valor de CONST.USER_ROLES
game.user.character;             // Actor atribuído, ou null
game.user.hasPermission("FILES_UPLOAD");
game.users.activeGM;             // o mestre ativo que está conectado (ou null)
game.users.filter(u => u.active && !u.isGM);  // jogadores conectados
```

Muitos hooks rodam em todos os clientes. Para exatamente um cliente agir (criar um documento, aplicar dano),
escolha um usuário "designado":

```js
Hooks.on("combatTurnChange", (combat, prior, current) => {
  // V13+: true só no cliente do mestre ativo
  if (!game.user.isActiveGM) return;
  // ...faz o trabalho uma vez
});
```

`game.users.getDesignatedUser(filter)` (V13+) escolhe um usuário de forma determinística entre os que atendem
a um filtro; `user.isDesignated` confere isso. Use quando pode não haver mestre on-line.

Dados por usuário vão em flags do usuário (`game.user.setFlag("forja-extras", "favoriteDice", "d20")`) ou
em uma [configuração](#settings) com escopo `user` (V13+).

::: v14
`User.queryMany()` envia uma [consulta](#sockets) a vários usuários e junta as respostas; os handlers
de query agora também recebem o id de quem enviou.
:::

## Configurações (`Setting`)

Cada valor de configuração guardado é um documento `Setting` (configurações de mundo no banco de dados, de cliente
no `localStorage`). Normalmente você usa `game.settings.get/set` ([Configurações](#settings)), mas o
documento é útil para hooks:

```js
Hooks.on("updateSetting", (setting, changes) => {
  if (setting.key !== "forja.difficulty") return;
  console.log("A dificuldade agora é", game.settings.get("forja", "difficulty"));
});
```

::: v14
## Níveis (`Level`)

`Level` é um documento novo embutido em `Scene` (`scene.levels`) que descreve uma fatia de elevação
de uma cena com vários níveis, com fundo, frente e névoa próprios. Veja
[Níveis de cena](#scene-token--niveis-de-cena).

## `MeasuredTemplate` (removido)

O documento `MeasuredTemplate`, `CONFIG.MeasuredTemplate` e `canvas.templates` não existem mais.
As áreas de efeito são Regions com formas de template; veja [Regiões e áreas de efeito](#regions).
:::

## Receita: pilhas de itens com marcadores (`flags`)

Um padrão completo e compacto: qualquer ator marcado como "pilha" aceita itens soltos no token dele, e
os jogadores podem pegar itens dela mesmo sem serem donos da pilha. O problema de permissão é resolvido
com uma **query** executada pelo mestre.

```js
// modules/forja-extras/scripts/piles.mjs
const MODULE = "forja-extras";

/** Este ator é uma pilha? */
const isPile = actor => !!actor?.getFlag(MODULE, "pile");

Hooks.once("init", () => {
  // Roda no cliente do mestre; os jogadores chamam com user.query()
  CONFIG.queries[`${MODULE}.transferItem`] = async ({ itemUuid, targetUuid }) => {
    const item = await fromUuid(itemUuid);
    const target = await fromUuid(targetUuid);
    if (!item?.parent || !target) return false;
    const data = item.toObject();
    delete data._id;
    await target.createEmbeddedDocuments("Item", [data]);
    await item.delete();
    return true;
  };
});

/** Move um item entre dois atores, passando pelo mestre se necessário */
export async function transferItem(item, targetActor) {
  const payload = { itemUuid: item.uuid, targetUuid: targetActor.uuid };
  if (item.parent.isOwner && targetActor.isOwner) {
    return CONFIG.queries[`${MODULE}.transferItem`](payload);
  }
  const gm = game.users.activeGM;
  if (!gm) return ui.notifications.warn(game.i18n.localize("FORJA_EXTRAS.Pile.NoGM"));
  return gm.query(`${MODULE}.transferItem`, payload, { timeout: 10_000 });
}

// Solta um item de uma ficha em um token de pilha
Hooks.on("dropCanvasData", (canvas, data) => {
  if (data.type !== "Item") return;
  const token = canvas.tokens.placeables.find(t => t.bounds.contains(data.x, data.y));
  if (!isPile(token?.actor)) return;
  fromUuid(data.uuid).then(item => {
    if (item?.parent && item.parent !== token.actor) transferItem(item, token.actor);
  });
  return false; // não deixa o core criar um item novo do mundo no canvas
});

// Transforma o ator do token selecionado em uma pilha (rode como mestre)
export async function makePile(actor) {
  await actor.setFlag(MODULE, "pile", true);
  await actor.update({ "ownership.default": CONST.DOCUMENT_OWNERSHIP_LEVELS.LIMITED });
}
```

Para os jogadores *pegarem* itens, chame `transferItem(item, game.user.character)` a partir de um botão na
ficha da pilha ou de um diálogo que liste `pileActor.items`.

## Armadilhas

::: warning
- `hotbarDrop` e `dropCanvasData` precisam devolver `false` de forma síncrona; um handler `async` devolve
  uma Promise, que o core não trata como `false`.
- `game.users.activeGM` é `null` quando nenhum mestre está conectado; sempre trate esse caso.
- Os comandos das macros são código guardado no mundo: nunca monte-os concatenando entrada do usuário
  sem escapar (use `JSON.stringify` como acima).
- Iniciar uma playlist pelo cliente de um jogador falha em silêncio sem permissão para atualizá-la.
- Os handlers de `CONFIG.queries` (V13+) precisam ser registrados em todos os clientes (no `init`), porque qualquer
  cliente pode ser o que responde.
:::
