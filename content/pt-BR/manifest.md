# O manifesto do pacote

Cada campo do `module.json` e do `system.json`, o que ele faz, e exemplos completos para V13 e V14.

::: changed
- `compatibility.minimum` deve ser `"14"` em pacotes que usam API exclusiva da V14.
- O novo campo opcional de nível superior **`"type": "system" | "module"`** deixa o tipo do pacote explícito.
- **`template.json` está obsoleto**: declare subtipos em `documentTypes` e defina seus dados com classes `TypeDataModel` em `CONFIG.<Document>.dataModels`.
- Veja [a lista completa de mudanças](#changes-14).
:::

## Para que serve o manifesto

O manifesto é um arquivo JSON na raiz do pacote. O Foundry o lê para **descobrir** o pacote na tela de Setup, **verificar a compatibilidade** com a versão do core em execução, **resolver dependências** e saber quais **arquivos carregar** no cliente. É também o que o instalador baixa para procurar atualizações.

- Um módulo usa `module.json` → `Data/modules/<id>/module.json`
- Um sistema usa `system.json` → `Data/systems/<id>/system.json`

::: warning
JSON não tem comentários nem vírgulas sobrando no final. Um único erro de sintaxe esconde o pacote da tela de Setup — confira `Logs/` ou passe o arquivo por um validador de JSON.
:::

## Campos compartilhados

### Identidade

| Campo | Obrigatório | Observações |
|---|---|---|
| `id` | sim | Minúsculas, hífens, sem espaços. Precisa ser igual ao nome da pasta. Nunca mude depois de publicar — mundos e flags fazem referência a ele. |
| `title` | sim | Nome legível mostrado na interface. |
| `description` | sim | Mostrado no Setup e na lista de módulos; aceita HTML. |
| `version` | sim | Qualquer string, mas use versionamento semântico (`"1.2.0"`). Atualizações são detectadas comparando esse valor. |
| `authors` | não | Array de `{ name, email?, url?, discord? }`. |

### Compatibilidade

```json
"compatibility": {
  "minimum": "13",
  "verified": "13.351",
  "maximum": "13"
}
```

- `minimum` — a versão mais antiga do core em que o pacote roda. Abaixo dela, o pacote não pode ser ativado.
- `verified` — a versão mais nova que você realmente testou. Versões mais novas mostram um aviso, mas ainda rodam.
- `maximum` — teto rígido. Deixe de fora, a menos que você *saiba* que uma versão principal mais nova quebra o pacote.

::: tip
Use o número principal (`"13"`) para dizer "qualquer build 13.x" e um build completo (`"13.351"`) em `verified`.
:::

### Código, estilos e traduções

| Campo | Observações |
|---|---|
| `esmodules` | Array de **ES modules** JavaScript a carregar (com suporte a `import`/`export`). Use este. |
| `scripts` | Array de scripts clássicos (sem `import`). Só para código legado. |
| `styles` | Array de arquivos CSS adicionados a todas as páginas do jogo. |
| `languages` | Array de `{ lang, name, path }`, por exemplo `{ "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }`. |

::: tip
Carregue **um** arquivo de entrada em `esmodules` e faça `import` do resto a partir dele. A ordem de carregamento entre várias entradas é mais difícil de acompanhar.
:::

### Compêndios

```json
"packs": [
  {
    "name": "weapons",
    "label": "Forja: Armas",
    "path": "packs/weapons",
    "type": "Item",
    "system": "forja",
    "ownership": { "PLAYER": "OBSERVER", "ASSISTANT": "OWNER" }
  }
],
"packFolders": [
  { "name": "Forja", "sorting": "m", "color": "#6b3b1f", "packs": ["weapons"], "folders": [] }
]
```

`type` é o tipo de documento que o compêndio guarda (`Actor`, `Item`, `JournalEntry`, `Scene`, `Adventure`…). `system` restringe o compêndio de um módulo a mundos daquele sistema. `packFolders` agrupa compêndios na barra lateral de Compêndios. Mais em [Compêndios](#compendium).

### Relacionamentos

```json
"relationships": {
  "systems":    [{ "id": "forja", "type": "system", "compatibility": { "minimum": "0.1.0" } }],
  "requires":   [{ "id": "lib-wrapper", "type": "module" }],
  "recommends": [{ "id": "dice-so-nice", "type": "module", "reason": "Dados 3D para as rolagens do Forja" }],
  "conflicts":  [{ "id": "old-forja-helper", "type": "module", "reason": "Substituído por este módulo" }]
}
```

- `systems` — (módulos) os sistemas que este módulo suporta. Com uma entrada aqui, o módulo só pode ser ativado em mundos desses sistemas.
- `requires` — precisa estar instalado e ativo; o Foundry oferece instalar/ativar.
- `recommends` — sugerido, não obrigatório.
- `conflicts` — avisa o usuário quando ambos estão ativos.

Cada entrada pode ter `manifest` (URL para instalá-lo) e `compatibility` para intervalos de versão.

### Rede e distribuição

| Campo | Observações |
|---|---|
| `socket` | `true` dá ao pacote um canal de socket `module.<id>` / `system.<id>`. Veja [Comunicação entre clientes](#sockets). |
| `url` | Página do projeto ou repositório. |
| `manifest` | URL estável do manifesto **mais recente**. O Foundry a busca para verificar atualizações. |
| `download` | URL do zip **desta versão**. |
| `license`, `readme`, `bugs`, `changelog` | Caminhos ou URLs mostrados nos detalhes do pacote. |
| `media` | Array de `{ type, url, thumbnail?, caption? }` para capturas de tela, vídeos, capas. |
| `flags` | Objeto livre para seus próprios dados e ferramentas de desenvolvimento, por exemplo `flags.hotReload` (veja [Ambiente](#setup--recarga-automatica)). |

## Campos exclusivos de sistema

| Campo | Observações |
|---|---|
| `documentTypes` | Subtipos por documento: `{ "Actor": { "character": {}, "npc": {} } }`. Cada tipo pode listar `htmlFields` (campos com texto rico, para enriquecimento/segurança) e `filePathFields`. |
| `grid` | Grid padrão para novas cenas: `{ "type": 1, "distance": 1.5, "units": "m" }` (`type` 1 = quadrado). |
| `primaryTokenAttribute` | Caminho dentro de `system` mostrado na primeira barra do token, por exemplo `"hp"`. |
| `secondaryTokenAttribute` | Segunda barra, por exemplo `"mana"`. |
| `initiative` | Fórmula de iniciativa padrão, por exemplo `"1d20 + @attributes.agility.value"`. |
| `background` | Caminho da imagem mostrada atrás do sistema na tela de Setup. |

::: tip
`primaryTokenAttribute` aponta para um objeto com `value` e `max` (como `system.hp`), para que a barra conheça o intervalo.
:::

## Exemplos completos

### `module.json`

::: v13
```json
{
  "id": "forja-extras",
  "title": "Forja Extras",
  "description": "Ferramentas de conveniência para o sistema Forja.",
  "version": "0.1.0",
  "authors": [{ "name": "Seu Nome", "url": "https://github.com/you" }],
  "compatibility": { "minimum": "13", "verified": "13.351", "maximum": "13" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "relationships": {
    "systems": [{ "id": "forja", "type": "system" }]
  },
  "socket": true,
  "url": "https://github.com/you/forja-extras",
  "manifest": "https://github.com/you/forja-extras/releases/latest/download/module.json",
  "download": "https://github.com/you/forja-extras/releases/download/v0.1.0/forja-extras.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```
:::

::: v14
```json
{
  "id": "forja-extras",
  "type": "module",
  "title": "Forja Extras",
  "description": "Ferramentas de conveniência para o sistema Forja.",
  "version": "0.1.0",
  "authors": [{ "name": "Seu Nome", "url": "https://github.com/you" }],
  "compatibility": { "minimum": "14", "verified": "14.368", "maximum": "14" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "relationships": {
    "systems": [{ "id": "forja", "type": "system" }]
  },
  "socket": true,
  "url": "https://github.com/you/forja-extras",
  "manifest": "https://github.com/you/forja-extras/releases/latest/download/module.json",
  "download": "https://github.com/you/forja-extras/releases/download/v0.1.0/forja-extras.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```
:::

### `system.json`

::: v13
```json
{
  "id": "forja",
  "title": "Forja RPG",
  "description": "Um pequeno RPG de fantasia usado como exemplo.",
  "version": "0.1.0",
  "authors": [{ "name": "Seu Nome" }],
  "compatibility": { "minimum": "13", "verified": "13.351", "maximum": "13" },
  "esmodules": ["module/forja.mjs"],
  "styles": ["styles/forja.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    },
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] }
    }
  },
  "grid": { "type": 1, "distance": 1.5, "units": "m" },
  "primaryTokenAttribute": "hp",
  "initiative": "1d20 + @attributes.agility.value",
  "background": "systems/forja/assets/background.webp",
  "socket": true,
  "url": "https://github.com/you/forja",
  "manifest": "https://github.com/you/forja/releases/latest/download/system.json",
  "download": "https://github.com/you/forja/releases/download/v0.1.0/forja.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```

A V13 ainda aceita um arquivo `template.json` ao lado do `system.json` para descrever dados padrão por tipo. Funciona, mas sistemas novos devem definir os dados com `TypeDataModel` — é o que a V14 espera.
:::

::: v14
```json
{
  "id": "forja",
  "type": "system",
  "title": "Forja RPG",
  "description": "Um pequeno RPG de fantasia usado como exemplo.",
  "version": "0.1.0",
  "authors": [{ "name": "Seu Nome" }],
  "compatibility": { "minimum": "14", "verified": "14.368", "maximum": "14" },
  "esmodules": ["module/forja.mjs"],
  "styles": ["styles/forja.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    },
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] }
    }
  },
  "grid": { "type": 1, "distance": 1.5, "units": "m" },
  "primaryTokenAttribute": "hp",
  "initiative": "1d20 + @attributes.agility.value",
  "background": "systems/forja/assets/background.webp",
  "socket": true,
  "url": "https://github.com/you/forja",
  "manifest": "https://github.com/you/forja/releases/latest/download/system.json",
  "download": "https://github.com/you/forja/releases/download/v0.1.0/forja.zip",
  "flags": {
    "hotReload": {
      "extensions": ["css", "hbs", "json"],
      "paths": ["styles", "templates", "lang"]
    }
  }
}
```

::: warning
`template.json` está **obsoleto** na V14. Declare todo subtipo em `documentTypes` e registre um `TypeDataModel` para ele em `CONFIG.Actor.dataModels` / `CONFIG.Item.dataModels` (veja [Primeiro sistema](#first-system) e [Modelos de dados](#data-models)).
:::
:::

## Suportando V13 e V14 ao mesmo tempo

Um manifesto pode cobrir as duas versões principais: `"minimum": "13", "verified": "14.368"`, sem `maximum`. Aí você precisa usar só API que existe na V13 *ou* proteger o código da V14:

```js
// Ramifica pela geração do core em execução
if (game.release.generation >= 14) {
  // API exclusiva da V14 aqui
} else {
  // Alternativa para a V13
}
```

::: warning
O campo `"type"` é novo na V14. Ele é opcional, então deixe-o de fora de um manifesto que também precisa carregar na V13.
:::

## Armadilhas

- **`id` ≠ nome da pasta** → o pacote não aparece.
- **Maiúsculas/minúsculas erradas no caminho** (`Scripts/main.mjs` vs `scripts/main.mjs`) funcionam no Windows e quebram em servidores Linux.
- **`manifest` apontando para uma versão específica** → os usuários nunca veem atualizações. Ele precisa sempre servir o manifesto mais novo.
- **Esquecer `documentTypes`** → seus tipos não aparecem no diálogo "Criar Ator".
- **Mudar `version` sem atualizar `download`** → os usuários instalam o zip antigo.
