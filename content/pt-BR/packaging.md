# Empacotamento e distribuição

Versione, construa, lance e publique seu sistema ou módulo, e suporte V13 e V14 com um único código.

::: changed
- O manifesto aceita um campo explícito opcional `"type": "system"` ou `"type": "module"`.
- O V14 não pode ser atualizado no lugar a partir do V13, então teste numa instalação limpa do V14.
- Pacotes de mundo não podem mais ser instalados pelo Setup — distribua conteúdo como documentos Adventure num compêndio.
- Veja [a lista completa de mudanças](#changes-14).
:::

## Como a instalação funciona

Quando um usuário cola uma URL de manifesto (ou escolhe seu pacote na lista), o Foundry:

1. Baixa o JSON do manifesto a partir de `manifest`.
2. Confere `compatibility` com a versão do core em execução e `relationships` com os pacotes instalados.
3. Baixa o zip de `download` e extrai em `Data/systems/<id>/` ou `Data/modules/<id>/`.
4. Depois, "Check for updates" busca o `manifest` de novo e compara a `version` — se for mais nova, baixa o novo `download`.

Então as duas URLs têm funções diferentes:

- `manifest` deve sempre apontar para o manifesto **mais recente** (para que as atualizações sejam encontradas).
- `download` deve apontar para o zip **desta versão exata** (para que manifesto e arquivos batam).

## Versionamento

Use [versionamento semântico](https://semver.org/): `MAJOR.MINOR.PATCH`. O Foundry compara
versões com `foundry.utils.isNewerVersion`, que entende números separados por ponto. Incremente:

- **PATCH** para correções,
- **MINOR** para funcionalidades que não quebram dados,
- **MAJOR** quando você abandona uma versão do core ou precisa de uma [migração de mundo](#migrations).

## Campos do manifesto para distribuição

```json
{
  "id": "forja",
  "title": "Forja",
  "version": "2.1.0",
  "compatibility": {
    "minimum": "13",
    "verified": "14.368"
  },
  "url": "https://github.com/forja-rpg/forja",
  "manifest": "https://github.com/forja-rpg/forja/releases/latest/download/system.json",
  "download": "https://github.com/forja-rpg/forja/releases/download/v2.1.0/forja.zip",
  "bugs": "https://github.com/forja-rpg/forja/issues",
  "changelog": "https://github.com/forja-rpg/forja/blob/main/CHANGELOG.md",
  "relationships": {
    "requires": [],
    "recommends": [
      {
        "id": "forja-extras",
        "type": "module",
        "reason": "Compêndios e automação extras"
      }
    ]
  }
}
```

::: v13
O V13 não define o campo `type`: é o nome do arquivo (`system.json` / `module.json`) que diz
ao Foundry o tipo do pacote. Enquanto seu `minimum` ainda for 13, o mais seguro é omiti-lo.
:::

::: v14
`"type": "system" | "module"` é opcional e deixa explícito o tipo do pacote (útil para
ferramentas que leem o manifesto sem saber o nome do arquivo). Adicione quando seu `minimum` for 14:

```json
{
  "id": "forja",
  "type": "system",
  "compatibility": { "minimum": "14", "verified": "14.368" }
}
```
:::

### Faixas de compatibilidade

| Chave | Significado | Efeito |
| --- | --- | --- |
| `minimum` | Versão mais antiga do core que roda o pacote | Cores mais antigos recusam instalar/ativar |
| `verified` | Versão mais nova que você realmente testou | Cores mais novos mostram um aviso de "não verificado" |
| `maximum` | Versão mais nova permitida | Cores mais novos recusam ativar |

Use números de geração (`"13"`, `"14"`) para faixas amplas e builds completos (`"14.368"`)
para `verified`. Só defina `maximum` se você *sabe* que a próxima geração quebra seu pacote.

### Relações entre pacotes

`relationships.requires` bloqueia a ativação até a dependência estar instalada e ativa;
`recommends` apenas sugere; `conflicts` avisa. Cada entrada pode ter a própria faixa de
`compatibility`, por exemplo o `forja-extras` exigindo `forja` `>= 2.0.0`:

```json
{
  "relationships": {
    "systems": [
      { "id": "forja", "type": "system", "compatibility": { "minimum": "2.0.0" } }
    ]
  }
}
```

## Estrutura do zip

O zip precisa conter os arquivos do pacote na **raiz** (não dentro de uma pasta `forja/`):

```bash
forja.zip
├── system.json
├── forja.mjs
├── module/
├── templates/
├── styles/
├── lang/
│   ├── en.json
│   └── pt-BR.json
└── packs/          # compêndios LevelDB compilados
    └── monsters/
```

Deixe de fora `src/`, `node_modules/`, `.git/` e os fontes YAML/JSON dos seus packs.

## Construindo compêndios com a linha de comando `fvtt`

Mantenha o conteúdo dos compêndios como JSON/YAML no git (`src/packs/<name>/`) e compile para
LevelDB na hora do lançamento com a [`@foundryvtt/foundryvtt-cli`](https://github.com/foundryvtt/foundryvtt-cli):

```bash
npm install --save-dev @foundryvtt/foundryvtt-cli
```

```js
// tools/build-packs.mjs
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { readdir } from "node:fs/promises";

const packs = await readdir("src/packs", { withFileTypes: true });
for (const dir of packs.filter((d) => d.isDirectory())) {
  console.log(`Compiling ${dir.name}`);
  await compilePack(`src/packs/${dir.name}`, `packs/${dir.name}`, { yaml: true, log: true });
}
```

O caminho inverso (`extractPack`) transforma um pack LevelDB editado de volta em YAML, para
você versionar as alterações feitas dentro do Foundry.

::: warning
Feche o Foundry (ou pelo menos o mundo) antes de compilar para uma pasta `packs/` que ele está
usando — o LevelDB mantém um lock nos packs abertos.
:::

## Fluxo de publicação com GitHub Actions

Envie uma tag como `v2.1.0` e o workflow compila os packs, grava a versão e a URL de download
no manifesto, compacta tudo e publica uma release no GitHub com **ambos** `system.json` e
`forja.zip` como assets. Como a release é a "latest", `releases/latest/download/system.json`
passa a servir o novo manifesto.

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    env:
      FOUNDRY_RELEASE_TOKEN: ${{ secrets.FOUNDRY_RELEASE_TOKEN }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22

      - run: npm ci

      - name: Build compendiums
        run: node tools/build-packs.mjs

      - name: Write version and URLs into the manifest
        run: |
          VERSION="${GITHUB_REF_NAME#v}"
          REPO="https://github.com/${GITHUB_REPOSITORY}"
          jq --arg v "$VERSION" \
             --arg m "$REPO/releases/latest/download/system.json" \
             --arg d "$REPO/releases/download/${GITHUB_REF_NAME}/forja.zip" \
             '.version=$v | .manifest=$m | .download=$d' system.json > tmp.json
          mv tmp.json system.json

      - name: Zip package
        run: zip -r forja.zip system.json forja.mjs module templates styles lang packs assets

      - name: Publish GitHub release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            system.json
            forja.zip
          generate_release_notes: true

      - name: Notify the Foundry package listing
        if: ${{ env.FOUNDRY_RELEASE_TOKEN != '' }}
        run: |
          VERSION="${GITHUB_REF_NAME#v}"
          curl -sSf -X POST https://foundryvtt.com/_api/packages/release_version/ \
            -H "Content-Type: application/json" \
            -H "Authorization: $FOUNDRY_RELEASE_TOKEN" \
            -d "{
              \"id\": \"forja\",
              \"release\": {
                \"version\": \"$VERSION\",
                \"manifest\": \"https://github.com/${GITHUB_REPOSITORY}/releases/download/${GITHUB_REF_NAME}/system.json\",
                \"notes\": \"https://github.com/${GITHUB_REPOSITORY}/releases/tag/${GITHUB_REF_NAME}\",
                \"compatibility\": { \"minimum\": \"13\", \"verified\": \"14.368\" }
              }
            }"
```

Para um módulo, troque `system.json` por `module.json` e `forja` por `forja-extras`.

::: tip
A Package Release API exige a URL do manifesto da release **específica** (não `latest`),
como no último passo. Adicione `"dry-run": true` ao corpo para testar seu token primeiro. Enviar
duas releases em menos de 60 segundos retorna `429 Too Many Requests`.
:::

## Publicando no foundryvtt.com

1. Entre no foundryvtt.com e crie a listagem do pacote pelo package admin da sua conta
   ("Submit a package"). O id do pacote precisa ser igual ao `id` do manifesto.
2. Preencha título, descrição e a **URL do manifesto** de uma release.
3. Depois da aprovação, cada nova versão é registrada manualmente na página de admin ou
   automaticamente com o token da Package Release API mostrado lá (guarde-o como o secret
   `FOUNDRY_RELEASE_TOKEN` do repositório).

Veja os guias oficiais em https://foundryvtt.com/article/package-release-api/ e a
Knowledge Base sobre submissão de pacotes.

## Suportando V13 e V14 num único código

Muitos pacotes mantêm `minimum: "13"` por um tempo. Detecte recursos em tempo de execução em
vez de manter dois branches:

```js
// systems/forja/module/compat.mjs
export const compat = {
  /** Número da geração do core: 13 ou 14. */
  get generation() {
    return game.release.generation;
  },

  get isV14() {
    return game.release.generation >= 14;
  },

  /** Verdadeiro quando o build em execução é mais novo que `build` (ex.: "14.360"). */
  isAfter(build) {
    return foundry.utils.isNewerVersion(game.version, build);
  },

  /** Igualdade profunda que funciona nas duas versões. */
  equals(a, b) {
    return (foundry.utils.equals ?? foundry.utils.objectsEqual)(a, b);
  },

  /** localize com dados no V14, format no V13. */
  localize(key, data) {
    if (!data) return game.i18n.localize(key);
    return this.isV14 ? game.i18n.localize(key, data) : game.i18n.format(key, data);
  },

  /** Opções de rolagem para o chat. `mode` usa os nomes do V14: public, gm, blind, self. */
  toMessageOptions(mode) {
    if (this.isV14) return { messageMode: mode };
    const ROLL_MODES = { public: "publicroll", gm: "gmroll", blind: "blindroll", self: "selfroll" };
    return { rollMode: ROLL_MODES[mode] ?? mode };
  },

  /** O array cru de changes, onde quer que esta versão o guarde. */
  effectChanges(effect) {
    return effect.system?.changes ?? effect.changes ?? [];
  }
};
```

```js
import { compat } from "./compat.mjs";

const roll = await new Roll("1d20 + @might", actor.getRollData()).evaluate();
await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) }, compat.toMessageOptions("gm"));
```

Por que duas verificações: `game.release.generation` é um número simples (13 ou 14) e é o
jeito mais fácil de ramificar pela versão principal. `foundry.utils.isNewerVersion(game.version, "14.360")`
compara builds completos, o que você precisa quando uma correção chegou numa versão pontual específica.

::: warning
Prefira **detecção de recurso** (`"changes" in effect.system`) a checagens de versão sempre
que possível — ela sobrevive a versões pontuais futuras que façam backport ou renomeiem coisas.
:::

## Matriz de testes

Antes de criar a tag de uma release, rode o mesmo teste rápido em cada core suportado:

| Verificação | V13 (13.351) | V14 (14.368) |
| --- | --- | --- |
| Criar mundo novo, sem erros no console | ✔ | ✔ |
| Abrir cada tipo de ficha (sheet) | ✔ | ✔ |
| Rolar para o chat em cada modo de mensagem/rolagem | ✔ | ✔ |
| Aplicar e expirar um active effect | ✔ | ✔ |
| Migração de mundo a partir da release anterior | ✔ | ✔ |
| Importar do compêndio | ✔ | ✔ |
| Módulo `forja-extras` ativado | ✔ | ✔ |

Mantenha uma instalação do Foundry por geração (caminhos de dados separados) para alternar
rápido; lembre que o V14 precisa ser uma instalação separada.

## Armadilhas

::: warning
- `manifest` apontando para uma versão específica — os usuários nunca veem atualizações.
- `download` apontando para `latest` — um manifesto antigo baixa arquivos novos e as versões não batem.
- Compactar a pasta pai — o pacote acaba em `Data/systems/forja/forja/` e não é encontrado.
- Esquecer de incrementar `version` — "Check for updates" compara versões, não datas.
- Distribuir `node_modules` ou os fontes dos packs — downloads enormes, sem benefício.
:::
