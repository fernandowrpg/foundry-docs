# Documentos

Documentos são os registros persistentes de um mundo — atores, itens, cenas, mensagens de chat e mais — e esta página mostra como eles são estruturados, criados, encontrados, alterados e estendidos.

::: changed
- `Document.create()` agora constrói `this.implementation`, então chamar `Actor.create()` na classe base ainda produz a sua subclasse configurada.
- Nova propriedade `Document#persisted` para saber se uma instância está gravada no banco de dados.
- UUIDs relativos ganharam helpers de primeira classe (`foundry.utils.buildRelativeUuid`, `DocumentUUIDField#relative`).
- As chaves especiais de update `-=chave` e `==chave` estão **depreciadas** em favor de valores `DataFieldOperator` (`foundry.data.operators.ForcedDeletion`, `ForcedReplacement`).
- Os metadados do documento podem controlar se o tipo "base" pode ser criado ou oferecido nos diálogos de criação.
- `DocumentCollection#importDocument` mantém os IDs originais; `foundry.utils.equals()` substitui `objectsEqual`.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Um Document é um data model que é salvo no banco de dados e sincronizado com todos os clientes conectados. Cada tipo de Document existe em duas camadas:

| Camada | Exemplo | Onde roda | Responsabilidade |
| --- | --- | --- | --- |
| Base (comum) | `foundry.documents.BaseActor` | Servidor **e** cliente | Schema, validação, metadados de permissão |
| Cliente | `Actor` (um `ClientDocument`) | Só no navegador | Preparação de dados, fichas, rolagens, helpers de UI, hooks |

Você nunca estende a classe base. Você estende a classe **cliente** (`Actor`, `Item`, …) e diz ao Foundry para usar a sua subclasse. Os dados específicos de cada tipo, dentro de `system`, são definidos por um [modelo de dados](#data-models).

Documentos são **primários** (vivem em uma coleção do mundo: `Actor`, `Item`, `Scene`, `JournalEntry`, `ChatMessage`, …) ou **embutidos** (vivem dentro de um pai: um `Item` dentro de um `Actor`, um `Token` dentro de uma `Scene`, um `ActiveEffect` dentro de um `Actor` ou `Item`).

## Coleções do mundo

Documentos primários ficam em coleções em `game`. Elas se comportam como `Map` e são indexadas por id.

```js
// Coleções: game.actors, game.items, game.scenes, game.journal,
// game.messages, game.users, game.folders, game.tables, game.macros ...
const hero = game.actors.getName("Aria");
const byId = game.actors.get("q8sLhg0GqL5bRw2x");
const characters = game.actors.filter((a) => a.type === "character");
const allItems = game.items.contents; // Array comum

// Documentos embutidos ficam em coleções no pai
const sword = hero.items.getName("Longsword");
const effects = hero.effects.contents;
```

## UUIDs

Todo documento tem uma string `uuid` globalmente única que codifica onde ele vive:

| Documento | Formato do UUID |
| --- | --- |
| Ator do mundo | `Actor.q8sLhg0GqL5bRw2x` |
| Item pertencente a um ator | `Actor.q8sLhg0GqL5bRw2x.Item.a1b2c3d4e5f6g7h8` |
| Token em uma cena | `Scene.xyz123abc456def7.Token.tok123abc456def7` |
| Entrada de compêndio | `Compendium.forja.monsters.Actor.m0nst3r1d0000000` |

```js
// Assíncrono: funciona para qualquer coisa, inclusive documentos de compêndio ainda não carregados
const actor = await fromUuid("Actor.q8sLhg0GqL5bRw2x");

// Síncrono: só retorna documentos que já estão em memória
// (para uma entrada de compêndio não carregada pode retornar uma entrada do índice em vez de um Document)
const item = fromUuidSync("Actor.q8sLhg0GqL5bRw2x.Item.a1b2c3d4e5f6g7h8");
```

UUIDs são o que você guarda quando um documento precisa apontar para outro (por exemplo em um `DocumentUUIDField`), e o que os links `@UUID[...]` em textos usam.

::: v14
A V14 adiciona helpers para UUIDs **relativos** — referências curtas resolvidas em relação a outro documento (por exemplo, um item que referencia um item irmão no mesmo ator). Veja `foundry.utils.buildRelativeUuid` e a opção `relative` de `DocumentUUIDField` na [API V14](https://foundryvtt.com/api/v14/). `fromUuid(uuid, { relative: doc })` resolve essas referências.
:::

## Criar, ler, atualizar, excluir

Todas as operações de banco de dados são **assíncronas** e retornam Promises. Use as variantes em lote (`*Documents`) ao alterar muitos documentos: uma única ida ao servidor, um conjunto de hooks por documento.

```js
// CRIAR
const actor = await Actor.create({ name: "Aria", type: "character" });
const [goblin, orc] = await Actor.createDocuments([
  { name: "Goblin", type: "npc" },
  { name: "Orc", type: "npc" }
]);

// ATUALIZAR — a notação com pontos acessa campos aninhados
await actor.update({ "system.hp.value": 8, name: "Aria the Bold" });
await Actor.updateDocuments([
  { _id: goblin.id, "system.hp.value": 3 },
  { _id: orc.id, "system.hp.value": 5 }
]);

// EXCLUIR
await orc.delete();
await Actor.deleteDocuments([goblin.id]);
```

### Documentos embutidos

Documentos embutidos são alterados através do pai:

```js
// Dá duas armas para a Aria
const created = await actor.createEmbeddedDocuments("Item", [
  { name: "Longsword", type: "weapon", system: { damage: "1d8" } },
  { name: "Dagger", type: "weapon", system: { damage: "1d4" } }
]);

// Equivalente para um só: Item.create(data, { parent: actor })
await Item.create({ name: "Shield", type: "weapon" }, { parent: actor });

await actor.updateEmbeddedDocuments("Item", [{ _id: created[0].id, "system.damage": "1d10" }]);
await actor.deleteEmbeddedDocuments("Item", [created[1].id]);
```

### Removendo ou substituindo chaves

Normalmente o `update` **mescla** objetos. Para excluir uma chave ou substituir um objeto inteiro, você precisa de uma instrução especial:

::: v13
Use os prefixos especiais de chave `-=` (excluir) e `==` (substituir):

```js
// Exclui a chave "oldBonus" de system.bonuses
await actor.update({ "system.bonuses.-=oldBonus": null });
// Substitui system.bonuses inteiro em vez de mesclar
await actor.update({ "system.==bonuses": { melee: 1 } });
```
:::

::: v14
Os prefixos `-=` / `==` ainda funcionam, mas estão **depreciados**. Use valores `DataFieldOperator` de `foundry.data.operators`:

```js
const { ForcedDeletion, ForcedReplacement } = foundry.data.operators;
// Exclui a chave "oldBonus" de system.bonuses
await actor.update({ "system.bonuses.oldBonus": ForcedDeletion.create() });
// Substitui system.bonuses inteiro em vez de mesclar
await actor.update({ "system.bonuses": ForcedReplacement.create({ melee: 1 }) });
```

Consulte a [API de `DataFieldOperator`](https://foundryvtt.com/api/v14/classes/foundry.data.operators.DataFieldOperator.html) para a semântica exata de cada operador.
:::

## `updateSource` ou `update`

| | `document.update(changes)` | `document.updateSource(changes)` |
| --- | --- | --- |
| Salva no banco de dados | Sim | **Não** — só altera a fonte local em memória |
| Transmite para outros clientes | Sim | Não |
| Dispara hooks | `preUpdate*` / `update*` | Nenhum |
| Retorna | Promise | Objeto de diferenças, síncrono |
| Use para | Mudanças reais | Ajustar dados **antes** de salvar, ex.: em `_preCreate` / `preCreate*` |

```js
// Monta um ator temporário, ajusta e depois salva
const draft = new Actor.implementation({ name: "Draft", type: "npc" });
draft.updateSource({ "system.hp.max": 12 });
await Actor.create(draft.toObject());
```

## Marcadores: o campo `flags`

Flags são uma área de armazenamento livre em todo documento, separada por id de pacote. São o lugar certo para dados de **módulo** em documentos cujo schema não é seu.

```js
// Guardado em actor.flags["forja-extras"].rests
await actor.setFlag("forja-extras", "rests", 3);
const rests = actor.getFlag("forja-extras", "rests"); // 3
await actor.unsetFlag("forja-extras", "rests");
```

::: warning
O escopo (primeiro argumento) precisa ser `"world"`, `"core"` ou o id de um pacote **ativo**; caso contrário `setFlag` lança um erro. Sistemas devem preferir campos no próprio data model em vez de flags — flags não têm validação.
:::

## Propriedade e permissões

Cada documento tem um objeto `ownership` que mapeia ids de usuário (e `"default"`) para um nível de `CONST.DOCUMENT_OWNERSHIP_LEVELS`: `NONE` (0), `LIMITED` (1), `OBSERVER` (2), `OWNER` (3), além de `INHERIT` (-1) para casos de embutidos/pastas.

```js
const { OWNER, OBSERVER } = CONST.DOCUMENT_OWNERSHIP_LEVELS;

actor.isOwner;                              // usuário atual é pelo menos OWNER (GMs sempre são)
actor.testUserPermission(game.user, "OBSERVER"); // pelo menos OBSERVER?
actor.testUserPermission(someUser, OWNER, { exact: true }); // exatamente OWNER?
actor.canUserModify(game.user, "update");   // este usuário pode atualizá-lo?

// Deixa todos os jogadores observarem o ator
await actor.update({ "ownership.default": OBSERVER });
```

Verifique as permissões **antes** de chamar `update` em código de UI e mostre uma mensagem amigável, em vez de deixar o servidor rejeitar o pedido.

## Estendendo classes de documento

Estenda a classe cliente e registre-a no `init`. `CONFIG.Actor.documentClass` é o que `Actor.implementation` retorna, então todo ator do mundo vai usar a sua classe.

```js
// systems/forja/documents/actor.mjs
export class ForjaActor extends Actor {
  /** Getter de conveniência usado por fichas e rolagens */
  get isDefeated() {
    return this.system.hp?.value <= 0;
  }

  getRollData() {
    // Expõe os dados de system (e o que mais quiser) às fórmulas de rolagem como @...
    return { ...super.getRollData(), level: this.system.level ?? 1 };
  }
}
```

```js
// systems/forja/forja.mjs
import { ForjaActor } from "./documents/actor.mjs";

Hooks.once("init", () => {
  CONFIG.Actor.documentClass = ForjaActor;
});
```

::: v13
Sempre crie documentos pela classe configurada: `Actor.implementation.create(...)` ou `getDocumentClass("Actor").create(...)`. Chamar `new Actor(...)` diretamente constrói a classe do core, não a sua.
:::

::: v14
`Document.create()` agora usa `this.implementation` internamente, então `Actor.create(...)` retorna um `ForjaActor` mesmo quando chamado na classe base. Para `new`, continue usando `new Actor.implementation(...)`.
:::

### Sobrescritas do ciclo de vida do documento

Em vez de escutar hooks para os *seus próprios* documentos, sobrescreva os métodos protegidos do ciclo de vida. Sempre chame `super`.

| Método | Roda em | Finalidade |
| --- | --- | --- |
| `async _preCreate(data, options, user)` | Cliente que pediu | Ajustar dados com `this.updateSource()` ou retornar `false` para cancelar |
| `_onCreate(data, options, userId)` | Todos os clientes | Reagir após a criação |
| `async _preUpdate(changes, options, user)` | Cliente que pediu | Modificar `changes` ou retornar `false` |
| `_onUpdate(changes, options, userId)` | Todos os clientes | Reagir após a atualização |
| `async _preDelete(options, user)` | Cliente que pediu | Retornar `false` para cancelar |
| `_onDelete(options, userId)` | Todos os clientes | Limpeza |

```js
// systems/forja/documents/actor.mjs (continuação)
export class ForjaActor extends Actor {
  async _preCreate(data, options, user) {
    const allowed = await super._preCreate(data, options, user);
    if (allowed === false) return false;
    // Personagens ficam vinculados aos seus tokens por padrão
    if (this.type === "character") {
      this.updateSource({ "prototypeToken.actorLink": true });
    }
  }

  _onUpdate(changes, options, userId) {
    super._onUpdate(changes, options, userId);
    // Roda em todo cliente: só feedback de UI aqui, nada de gravar no banco
    if (foundry.utils.hasProperty(changes, "system.hp.value") && this.isDefeated) {
      ui.notifications.info(`${this.name} caiu!`);
    }
  }
}
```

## Ordem de preparação dos dados

Sempre que um documento é inicializado ou atualizado, `prepareData()` roda em todo cliente. Para um `Actor` com um `TypeDataModel` a ordem é:

1. `system.prepareBaseData()` — data model: valores que dependem só dos dados salvos
2. `actor.prepareBaseData()` — valores base no nível do documento
3. `actor.prepareEmbeddedDocuments()` — prepara itens e efeitos; **os Active Effects são aplicados aqui**
4. `system.prepareDerivedData()` — data model: totais, modificadores (efeitos já aplicados)
5. `actor.prepareDerivedData()` — valores derivados no nível do documento

```js
// systems/forja/documents/actor.mjs (continuação)
prepareDerivedData() {
  super.prepareDerivedData();
  // Os itens já foram preparados, então os dados deles podem ser somados aqui
  this.system.encumbrance = this.items.reduce((sum, i) => sum + (i.system.weight ?? 0), 0);
}
```

::: warning
Nunca chame `update()` dentro dos métodos de `prepareData` — eles rodam em todo cliente a cada mudança e vão entrar em loop. Valores derivados vivem só na memória.
:::

## Outras mudanças do V14

::: v14
- **`Document#persisted`** indica se uma instância está gravada no banco de dados — útil para distinguir documentos temporários/efêmeros dos salvos.
- **Criação do tipo base**: os metadados do documento podem esconder ou proibir o tipo `"base"` nos diálogos de criação, então sistemas que só usam seus próprios subtipos não mostram mais uma opção "Base" inútil.
- **`DocumentCollection#importDocument`** mantém o `_id` do documento de origem, então importar de um compêndio preserva os IDs (e referências baseadas em UUID continuam funcionando).
- **`foundry.utils.equals(a, b)`** substitui `foundry.utils.objectsEqual` para igualdade profunda.
:::

::: v13
Para comparações profundas use `foundry.utils.objectsEqual(a, b)`. Ao importar de um compêndio, passe `{ keepId: true }` para `importFromCompendium` se você precisar do id original.
:::

## Armadilhas

- **Esquecer o `await`.** `actor.update()` retorna antes de a mudança ser salva; leia o valor novo depois do await.
- **Atualizar dentro de um loop.** Use `updateDocuments` / `updateEmbeddedDocuments` com um array em vez de N chamadas separadas de `update`.
- **Gravar em `_onUpdate` ou em hooks `update*`** sem checar `userId === game.user.id` duplica gravações entre clientes.
- **Alterar `document.system` diretamente** (`actor.system.hp.value = 3`) muda só a memória local — nada é salvo.
- **Atores de token.** Um token não vinculado tem seu próprio ator sintético; `token.actor` não é `game.actors.get(token.actorId)`.
- **Escopos de flag inválidos** lançam erro; use o id do seu pacote.
