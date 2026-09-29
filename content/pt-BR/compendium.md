# Compêndios

Os compêndios levam documentos junto com o seu sistema ou módulo; você os declara no manifesto, monta-os a partir de arquivos-fonte com a ferramenta oficial de linha de comando e lê com `game.packs`.

::: changed
- **Active Effects** são documentos primários no V14 e podem ficar em compêndios próprios (`"type": "ActiveEffect"`).
- **Pacotes de mundo não podem mais ser instalados pelo Setup**: distribua aventuras como documentos `Adventure` dentro de um pack de módulo.
- `DocumentCollection#importDocument` agora **mantém os IDs dos documentos** por padrão.
- Os títulos dos compêndios são traduzidos nos resultados de busca.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Um **compêndio** (pack) é um banco de documentos de um único tipo (Actor, Item, JournalEntry, Macro,
RollTable, Scene, Adventure, ...) que fica dentro de um pacote, não em um mundo. Os mundos leem os packs
sob demanda: só um **índice** leve é carregado até você pedir os documentos completos.

Os packs são guardados como pastas **LevelDB** (`packs/items/` com arquivos `CURRENT`, `LOG`, `*.ldb`).
O LevelDB é binário e fica travado enquanto o Foundry está com o pack aberto, então você **não faz commit dele na mão**:
você mantém arquivos-fonte JSON/YAML no git e os compila com a CLI.

## Declare os compêndios no manifesto

```json
{
  "id": "forja",
  "packs": [
    {
      "name": "items",
      "label": "Itens do Forja",
      "path": "packs/items",
      "type": "Item",
      "system": "forja",
      "ownership": { "PLAYER": "OBSERVER", "ASSISTANT": "OWNER" },
      "flags": {}
    },
    {
      "name": "rules",
      "label": "Regras do Forja",
      "path": "packs/rules",
      "type": "JournalEntry"
    }
  ],
  "packFolders": [
    {
      "name": "Forja",
      "sorting": "m",
      "color": "#7a3b12",
      "packs": ["items", "rules"],
      "folders": []
    }
  ]
}
```

- `name` é o id do pack dentro do pacote; o id completo da coleção é `forja.items`.
- `type` é o nome do documento. `system` restringe packs de Actor/Item a esse sistema (obrigatório em
  módulos que trazem conteúdo específico de um sistema).
- `ownership` define o acesso padrão por papel (`NONE`, `LIMITED`, `OBSERVER`, `OWNER`).
- `packFolders` agrupa os packs em pastas na barra lateral (`sorting`: `"a"` alfabético, `"m"` manual).

## Monte os compêndios pela linha de comando

Instale a CLI oficial (`@foundryvtt/foundryvtt-cli`) como dependência de desenvolvimento:

```bash
npm install --save-dev @foundryvtt/foundryvtt-cli
npx fvtt configure set dataPath "/caminho/para/FoundryData"
npx fvtt package workon forja --type System

# LevelDB → um arquivo JSON por documento (faça commit destes)
npx fvtt package unpack -n items --outputDirectory src/packs/items

# JSON → LevelDB (rode com o mundo fechado)
npx fvtt package pack -n items --inputDirectory src/packs/items --outputDirectory packs
```

Acrescente `--yaml` aos dois comandos para usar YAML em vez de JSON. Para um script de build, use a API em JS:

```js
// tools/build-packs.mjs  —  rode com: node tools/build-packs.mjs
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { readdir } from "node:fs/promises";

const packs = await readdir("src/packs");
for (const pack of packs) {
  console.log(`Empacotando ${pack}`);
  await compilePack(`src/packs/${pack}`, `packs/${pack}`, { recursive: true, log: true });
}
```

`extractPack(src, dest, options)` faz o caminho inverso (as opções incluem `yaml`, `folders`,
`expandAdventures`, `omitVolatile`, `transformEntry`).

::: warning
Todo arquivo-fonte precisa ter um `_id` estável (16 caracteres) e uma `_key`
(`"!items!<id>"`, ou `"!items.effects!<itemId>.<effectId>"` para documentos embutidos). Desempacotar um
pack existente já gera esses campos; ao escrever arquivos na mão, gere os ids uma vez com
`foundry.utils.randomID()` e nunca os mude, senão os links para o documento quebram.
:::

## Leia os compêndios pelo código

```js
const pack = game.packs.get("forja.items");
console.log(pack.collection, pack.documentName, pack.metadata.label);

// 1. O índice: barato, fica em cache depois da primeira chamada
const index = await pack.getIndex({ fields: ["system.price", "system.rarity"] });
const cheap = index.filter(e => e.type === "weapon" && e.system.price < 10);

// 2. Um documento pelo id
const sword = await pack.getDocument(cheap[0]._id);

// 3. Vários documentos, com filtro opcional sobre os dados-fonte
const weapons = await pack.getDocuments({ type: "weapon" });

// 4. Pelo UUID (funciona com qualquer pack)
const axe = await fromUuid("Compendium.forja.items.Item.a1b2c3d4e5f6g7h8");
```

`fromUuidSync()` com um UUID de compêndio devolve a **entrada do índice** (não um Document) se o documento
ainda não foi carregado: confira `entry instanceof foundry.abstract.Document` antes de chamar métodos.

Use os campos do `index` para listas e buscas (por exemplo, um diálogo "escolha uma arma"); carregue os documentos completos só
daquele que o usuário escolher. Todo campo que você acrescenta em `getIndex({fields})` fica na memória, então acrescente
só o que você mostra. Sistemas podem definir campos de índice padrão com `CONFIG.Item.compendiumIndexFields`.

## Importe para o mundo

```js
// Importa um documento para o diretório de Itens (mantém o mesmo _id)
const item = await game.items.importFromCompendium(pack, sword.id, {}, { keepId: true });

// Importa tudo para uma pasta
await pack.importAll({ folderName: "Itens do Forja", keepId: true });

// Ou: entrega um item do compêndio direto a um ator
await actor.createEmbeddedDocuments("Item", [sword.toObject()]);
```

`importFromCompendium` registra a origem em `_stats.compendiumSource`, que você pode usar depois para
atualizar as cópias do mundo a partir do pack.

::: v14
No V14 `DocumentCollection#importDocument` mantém o id do documento por padrão, então os documentos
importados preservam as relações de UUID.
:::

## Grave em um compêndio

Os packs vêm travados. O mestre pode destravá-los, e o código pode gravar neles como em uma coleção:

```js
await pack.configure({ locked: false });
await Item.create({ name: "Lâmina de Brasa", type: "weapon" }, { pack: pack.collection });
await sword.update({ "system.price": 12 }); // documentos de um pack são atualizados no pack
```

::: tip
Em tempo de execução, só grave em compêndios *do mundo*. Os packs dentro do seu sistema ou módulo são sobrescritos
a cada atualização; edite os arquivos-fonte deles.
:::

## Aventuras

Um documento **Adventure** junta Scenes, Actors, Items, Journals, Tables, Playlists, Macros,
Cards, Combats e Folders em uma unidade importável. Crie um em um pack do tipo `"Adventure"`
(pela interface do Adventure Exporter) e os usuários o importam com um clique, mantendo os ids.

```js
const adventurePack = game.packs.get("forja-extras.adventures");
const [adventure] = await adventurePack.getDocuments();
adventure.sheet.render(true); // abre o importador
```

::: v14
Pacotes de mundo não podem mais ser instalados pelo Setup no V14. Se você distribuía um "mundo inicial",
publique uma Adventure em um módulo.

Active Effects são documentos primários no V14: declare um pack com `"type": "ActiveEffect"` para
distribuir condições e bônus que os usuários arrastam para os tokens.
:::

## Armadilhas

::: warning
- `fvtt package pack` falha (ou corrompe os dados) enquanto o Foundry está com o mundo aberto: o LevelDB fica travado.
- O `name` de um pack precisa ser único dentro do pacote e não pode mudar depois de publicado, senão todos
  os UUIDs `Compendium.forja.<name>...` quebram.
- `pack.index` fica vazio até o `getIndex()` rodar uma vez (o core o chama ao carregar o mundo, mas só
  com os campos padrão).
- Não faça um loop de `await pack.getDocument(id)` para centenas de ids: use `getDocuments({ _id__in: ids })`.
- Packs de Actor/Item em um módulo sem `system` aparecem em todos os sistemas e podem ter dados inválidos.
:::
