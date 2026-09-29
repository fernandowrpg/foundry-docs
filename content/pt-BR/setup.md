# Ambiente de desenvolvimento

Instale o Foundry para desenvolvimento, vincule seu repositório à pasta de dados do usuário e ative a recarga automática e as ferramentas de depuração.

::: changed
- A V14 **não pode ser atualizada no lugar** a partir da V13: faça uma instalação nova (você pode apontá-la para uma cópia da sua pasta de dados).
- O **hot reload de CSS agora segue `@import`** — folhas de estilo divididas recarregam sem atualizar a página inteira.
- Os hooks de renderização do hot reload recebem informações sobre o arquivo alterado.
- Veja [a lista completa de mudanças](#changes-14).
:::

## Instale o Foundry para desenvolvimento

Você precisa de uma chave de licença e do download na página da sua conta em foundryvtt.com. Duas versões interessam a desenvolvedores:

- **App desktop** (Windows/macOS/Linux) — um app Electron. O mais fácil para começar.
- **Versão Node.js** — um zip que você roda com `node`. Melhor para um servidor de desenvolvimento que você reinicia muito ou roda sem interface.

::: v13
A V13 vem com **Electron 33** no app desktop. A versão Node.js exige **Node 20** (o Node 22 também é suportado).

```bash
# Versão Node.js, V13 (use Node 20 ou 22)
node --version
cd ~/foundry/v13
node main.js --dataPath=$HOME/foundrydata-v13
```
:::

::: v14
A V14 é uma **instalação nova**: o app da V13 não consegue se atualizar para a V14. Instale a V14 em uma pasta nova e use uma **pasta de dados separada** (ou uma cópia da sua da V13) — mundos migrados pela V14 não voltam para a V13.

```bash
# Versão Node.js, V14 — pasta de instalação e pasta de dados separadas
node --version
cd ~/foundry/v14
node main.js --dataPath=$HOME/foundrydata-v14
```
:::

::: tip
Mantenha uma instalação e uma pasta de dados **por versão principal**. Você vai querer testar seu pacote na V13 e na V14 lado a lado, e um mundo migrado é uma viagem só de ida.
:::

::: warning
Confira o requisito de versão do Node nas notas de lançamento do build exato que você baixar. Rodar uma versão de Node não suportada normalmente falha na inicialização com erro de sintaxe ou de módulo nativo.
:::

## A pasta de dados do usuário

O `--dataPath` (ou o caminho escolhido nas configurações do app desktop) contém:

```bash
foundrydata/
├── Config/           # options.json (porta, dataPath etc.), licença
├── Data/             # tudo que é servido aos clientes
│   ├── modules/      # uma pasta por módulo:  Data/modules/forja-extras/
│   ├── systems/      # uma pasta por sistema: Data/systems/forja/
│   └── worlds/       # uma pasta por mundo:   Data/worlds/forja-dev/
└── Logs/             # logs do servidor — olhe aqui quando um pacote não carregar
```

Os arquivos em `Data/` são servidos por URL relativa a essa pasta: `Data/systems/forja/templates/actor.hbs` vira `systems/forja/templates/actor.hbs` no seu código.

::: warning
O nome da pasta **precisa ser igual ao `id` do pacote** no manifesto. `Data/modules/forja_extras/` com `"id": "forja-extras"` não carrega.
:::

## Vincule seu repositório

Mantenha seu repositório git em outro lugar (por exemplo `~/dev/forja`) e crie um **link simbólico** (symlink) dele na pasta de dados. Você edita e faz commit em um só lugar, e pode vincular o mesmo repositório às pastas de dados da V13 e da V14.

```bash
# Linux / macOS
ln -s ~/dev/forja        ~/foundrydata-v14/Data/systems/forja
ln -s ~/dev/forja-extras ~/foundrydata-v14/Data/modules/forja-extras
```

```bash
# Windows (Prompt de Comando como administrador, ou com o Modo de Desenvolvedor ativo)
mklink /D "%LOCALAPPDATA%\FoundryVTT\Data\systems\forja" "C:\dev\forja"
mklink /D "%LOCALAPPDATA%\FoundryVTT\Data\modules\forja-extras" "C:\dev\forja-extras"
```

Reinicie o Foundry (ou volte à tela de Setup) depois de criar um link: pacotes são descobertos quando o servidor inicia ou quando a tela de Setup é atualizada.

## Crie um mundo de desenvolvimento

1. Na tela de Setup, abra **Game Worlds → Create World**.
2. Dê um id como `forja-dev` e escolha seu sistema (`forja`).
3. Inicie o mundo, entre como **Gamemaster** e ative seus módulos em **Game Settings → Manage Modules**.

::: tip
Crie um segundo mundo só com seu módulo e um sistema popular para pegar dependências acidentais. Mantenha um mundo "limpo", sem outros módulos, para relatos de bug — isso descarta conflitos.
:::

## Configuração do editor (VS Code)

O código do cliente do Foundry vem com o app como módulos JavaScript legíveis, com JSDoc. Apontar seu editor para ele dá autocompletar para `foundry.*` sem pacotes extras.

```json
{
  "compilerOptions": {
    "module": "ES2022",
    "target": "ES2022",
    "checkJs": false,
    "baseUrl": "."
  },
  "include": [
    "module/**/*.mjs",
    "scripts/**/*.mjs",
    "../../foundry/v14/resources/app/client/**/*.mjs",
    "../../foundry/v14/resources/app/common/**/*.mjs"
  ]
}
```

Salve isso como `jsconfig.json` na raiz do repositório e ajuste os caminhos para onde está sua instalação do Foundry (as pastas `client` e `common` ficam em `resources/app/` da instalação ou na raiz dela, dependendo do build).

::: tip
Existem definições TypeScript da comunidade (`@league-of-foundry-developers/foundry-vtt-types`), mas elas podem ficar atrás da versão principal mais recente. Confira no README o suporte a V13/V14 antes de depender delas.
:::

## Recarga automática

Sem hot reload, toda mudança de CSS, template ou tradução exige um F5. Declare quais arquivos o servidor deve observar no manifesto, em `flags.hotReload`:

```json
{
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "html", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```

- `extensions` — tipos de arquivo que disparam o recarregamento.
- `paths` — pastas (relativas à raiz do pacote) a observar.
- **CSS** é trocado ao vivo, **templates** são buscados de novo e aplicações abertas re-renderizam, arquivos de **lang** são mesclados de novo.
- JavaScript **não** tem hot reload — recarregue a página (F5) depois de mudar arquivos `.mjs`.

::: v14
Na V14 o hot reload também segue **`@import`** de CSS: se `styles/forja.css` importa `styles/actor.css`, editar `actor.css` também recarrega. A renderização do hot reload também recebe o contexto do arquivo alterado, para que as aplicações decidam se precisam re-renderizar.
:::

::: v13
Na V13 só os arquivos listados diretamente em `styles` são trocados ao vivo. Se você divide o CSS com `@import`, mudanças nos arquivos importados podem exigir recarregar a página.
:::

::: warning
O hot reload só funciona quando o servidor enxerga as mudanças nos arquivos. Algumas pastas vinculadas em drives de rede ou montagens do WSL não emitem eventos de alteração — edite os arquivos no mesmo sistema de arquivos em que o Foundry roda.
:::

## Ferramentas de desenvolvedor do navegador

Abra as ferramentas de desenvolvedor com **F12** (app desktop ou navegador). Você também pode conectar um navegador comum em `http://localhost:30000` — as devtools do Chrome/Firefox são mais confortáveis que as do Electron.

- **Console** — rode qualquer chamada da API: `game.actors.contents`, `canvas.tokens.controlled`, `CONFIG.Actor.dataModels`.
- **Sources** — seus arquivos aparecem em `systems/forja/…`; coloque breakpoints nos arquivos `.mjs`.
- **Network** — procure `404` em templates ou arquivos de idioma.

### Registre todos os ganchos

O Foundry pode imprimir cada chamada de hook com seus argumentos. É o jeito mais rápido de descobrir *qual* hook usar:

```js
// No console do navegador
CONFIG.debug.hooks = true;
// Agora abra uma ficha, mova um token, mande uma mensagem no chat... e observe o log.
// Para desligar:
CONFIG.debug.hooks = false;
```

::: tip
Clique com o botão direito em um elemento e escolha **Inspecionar** para achar a classe da aplicação e os atributos `data-action`; depois procure essa classe na documentação da API.
:::

### Trechos úteis para o console

```js
// O documento por trás da primeira ficha aberta
foundry.applications.instances.values().next().value?.document;

// O manifesto do seu pacote, como foi carregado
game.system.id;                    // "forja"
game.modules.get("forja-extras");  // objeto Module; .active diz se está ativo
```

## Dicas de git

- Faça commit da própria pasta do pacote (manifesto na raiz do repositório), para que o repositório possa ser vinculado diretamente.
- Adicione um `.gitignore` para saída de build e compêndios compilados, se você os gerar:

```bash
node_modules/
dist/
*.zip
# Arquivos LevelDB dos compêndios mudam a cada abertura; faça commit da fonte deles
packs/*/LOCK
packs/*/LOG*
```

- Use **tags** que batem com o `version` do manifesto (`v0.1.0`). Ferramentas de publicação e a checagem de atualizações dependem dessa string. Veja [Empacotamento e publicação](#packaging).
- Teste na V13 **e** na V14 antes de criar a tag, se o seu intervalo de `compatibility` cobre as duas.

## Próximos passos

Continue com [o manifesto](#manifest) e depois construa [seu primeiro módulo](#first-module).
