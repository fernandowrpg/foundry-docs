# Tradução e localização

Coloque todo texto em arquivos de idioma, traduza os rótulos dos modelos de dados automaticamente e deixe seu pacote fácil de traduzir pela comunidade.

::: changed
- `game.i18n.localize(key, data)` agora também faz o que o `format()` fazia: passe um objeto e os `{placeholders}` são preenchidos. O `format()` continua funcionando.
- Novo atalho global `_loc(key, data)` para `game.i18n.localize`.
- `LOCALIZATION_PREFIXES` foram adicionados a mais modelos do core (`BaseDrawing`, `BaseJournalEntryPage`).
- `DataField#placeholder` é uma nova opção de campo e é traduzida automaticamente, como `label` e `hint`.
- Os títulos dos compêndios são traduzidos nos resultados de busca.
- Veja [a lista completa de mudanças](#changes-14).
:::

## Como a localização funciona

O Foundry carrega um dicionário JSON por idioma. Na inicialização ele junta os dicionários do core, do sistema e de cada módulo ativo para o idioma escolhido pelo usuário, e usa o inglês para as chaves que faltarem. Seu código nunca contém texto visível; ele contém **chaves**.

```text
lang/en.json      →  "FORJA.Sheet.Attributes": "Attributes"
lang/pt-BR.json   →  "FORJA.Sheet.Attributes": "Atributos"
código / template →  game.i18n.localize("FORJA.Sheet.Attributes")
```

## Declare os idiomas no manifesto

```json
{
  "languages": [
    { "lang": "en",    "name": "English",              "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)",   "path": "lang/pt-BR.json" }
  ]
}
```

- `lang` é o código que o usuário escolhe em **Configurar Opções → Idioma**. Use `pt-BR` para português do Brasil.
- Um módulo pode trazer traduções *para outro pacote*. Adicione `"system": "forja"` (ou `"module": "algum-modulo"`) à entrada, e o arquivo só é carregado quando esse pacote está ativo. É assim que funcionam os módulos de tradução da comunidade.

## Escreva o arquivo de idioma

As chaves podem ser planas (`"FORJA.Sheet.Attributes"`) ou objetos aninhados. Aninhado é mais fácil de manter; o Foundry achata tudo ao carregar.

```json
{
  "FORJA": {
    "Sheet": {
      "Attributes": "Atributos",
      "Inventory": "Inventário"
    },
    "Roll": {
      "Attack": "{name} ataca com {weapon}!",
      "Success": "Sucesso",
      "Failure": "Falha"
    },
    "Settings": {
      "Difficulty": { "Name": "Dificuldade padrão", "Hint": "Número-alvo usado quando nenhum é informado." }
    }
  }
}
```

::: tip
Comece toda chave com o id do seu pacote em maiúsculas (`FORJA.`, `FORJAEXTRAS.`). As chaves ficam em um dicionário global único, então um `"Attack"` solto pode colidir com o core ou com outro módulo.
:::

## Use as chaves no JavaScript

::: v13
```js
// Texto simples
game.i18n.localize("FORJA.Sheet.Attributes");            // "Atributos"

// Texto com placeholders: use format()
game.i18n.format("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });

// Confira antes de usar uma chave opcional
if ( game.i18n.has("FORJA.Tips.Rare") ) ui.notifications.info("FORJA.Tips.Rare", { localize: true });
```
:::

::: v14
```js
// Texto simples
game.i18n.localize("FORJA.Sheet.Attributes");            // "Atributos"

// localize() agora aceita dados e preenche os {placeholders}
game.i18n.localize("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });

// Atalho global, prático em código de interface longo
_loc("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });

// format() continua funcionando, então código compartilhado com o V13 não quebra
game.i18n.format("FORJA.Roll.Attack", { name: actor.name, weapon: item.name });
```
:::

`game.i18n.lang` guarda o código do idioma ativo, útil para formatar com `Intl`:

```js
const fmt = new Intl.NumberFormat(game.i18n.lang, { maximumFractionDigits: 1 });
fmt.format(1234.5); // "1,234.5" em en, "1.234,5" em pt-BR
```

## Use as chaves nos modelos Handlebars

```hbs
<h2>{{localize "FORJA.Sheet.Attributes"}}</h2>

{{!-- Placeholders são passados como argumentos nomeados --}}
<p>{{localize "FORJA.Roll.Attack" name=actor.name weapon=item.name}}</p>

{{!-- Campos do data model: os rótulos vêm do schema (veja abaixo) --}}
{{formGroup fields.hp.fields.value value=system.hp.value localize=true}}
```

## Traduza os rótulos do modelo de dados automaticamente

Em vez de escrever `label:` fixo em cada campo, declare `LOCALIZATION_PREFIXES` no modelo. O Foundry então procura `<prefixo>.FIELDS.<caminho>.label` e `.hint` para cada campo, e `formGroup` / `formInput` exibem esses textos.

```js
export class CharacterData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA.Actor.Character"];

  static defineSchema() {
    const { SchemaField, NumberField } = foundry.data.fields;
    return {
      hp: new SchemaField({
        value: new NumberField({ required: true, integer: true, min: 0, initial: 10 }),
        max:   new NumberField({ required: true, integer: true, min: 0, initial: 10 })
      })
    };
  }
}
```

```json
{
  "FORJA": {
    "Actor": {
      "Character": {
        "FIELDS": {
          "hp": {
            "label": "Pontos de vida",
            "value": { "label": "Atual", "hint": "O dano reduz este valor." },
            "max":   { "label": "Máximo" }
          }
        }
      }
    }
  }
}
```

O core traduz os modelos registrados em `CONFIG.<Document>.dataModels` durante a inicialização. Para um modelo que você mesmo monta (por exemplo, um objeto de configurações), chame o helper uma vez no `i18nInit`:

```js
Hooks.once("i18nInit", () => {
  foundry.helpers.Localization.localizeDataModel(MySettingsModel);
});
```

::: warning
Confira o namespace exato de `Localization` na documentação da API da sua versão antes de depender dele. Código mais antigo usa o global `Localization.localizeDataModel`.
:::

::: v14
Os campos também aceitam a opção `placeholder`. Ela é traduzida como `label` e `hint` (`<prefixo>.FIELDS.<caminho>.placeholder`) e aparece dentro dos inputs vazios.
:::

## Traduza os nomes dos tipos de documento

O seletor de tipo em "Criar Ator" mostra `TYPES.<Document>.<tipo>`:

```json
{
  "TYPES": {
    "Actor": { "character": "Personagem", "npc": "Personagem do mestre (NPC)" },
    "Item":  { "weapon": "Arma", "spell": "Magia", "gear": "Equipamento" }
  }
}
```

## Configurações, notificações e diálogos

A maioria das APIs do core recebe uma chave e traduz para você:

```js
game.settings.register("forja", "difficulty", {
  name: "FORJA.Settings.Difficulty.Name",   // traduzido automaticamente
  hint: "FORJA.Settings.Difficulty.Hint",
  scope: "world", config: true, type: Number, default: 10
});

ui.notifications.warn("FORJA.Warn.NoTarget", { localize: true });
```

## Momento certo: quando o dicionário está pronto?

| Hook | `game.i18n` pode ser usado? |
|---|---|
| `init` | Não. Só registre coisas; guarde **chaves**, não texto traduzido. |
| `i18nInit` | Sim. Traduza o que precisar preparar uma única vez. |
| `setup`, `ready` | Sim. |

::: warning
Chamar `localize` no `init` devolve a própria chave. Um erro comum é traduzir as opções de `CONFIG` no `init`: guarde as chaves e traduza na renderização, ou traduza no `i18nInit`.
:::

## Conteúdo de compêndios

Os documentos de um pack ficam gravados em um único idioma. Duas estratégias comuns:

1. **Um pack por idioma**, cada um declarado com sua própria chave `label` no manifesto.
2. **Módulos de tradução** (como o Babele), que trocam nomes e descrições dos documentos ao carregar. Mantenha `_id`s estáveis e nomes em inglês para facilitar.

::: v14
Os títulos dos compêndios agora são traduzidos nos resultados de busca, então dê a cada pack uma chave `label` traduzível.
:::

## Lista de verificação: um pacote pronto para tradução

- [ ] Nenhum texto visível nos arquivos `.mjs` ou `.hbs`: só chaves.
- [ ] Todas as chaves começam com o id do pacote.
- [ ] O `en.json` está completo; os outros idiomas podem ser parciais (o inglês é o fallback).
- [ ] Os placeholders têm nome (`{weapon}`), nunca concatenação de strings, porque a ordem das palavras muda entre idiomas.
- [ ] Os data models usam `LOCALIZATION_PREFIXES` em vez de rótulos fixos.
- [ ] Números e datas usam `Intl` com `game.i18n.lang`.
- [ ] O README diz aos tradutores qual arquivo copiar e como enviá-lo de volta.

## Armadilhas

- **Chave ausente aparece como a própria chave.** Se você vê `FORJA.Sheet.Attributes` na tela, a chave está escrita errado ou o arquivo de idioma não foi lido. Procure erros de JSON no console.
- **Chaves duplicadas no JSON aninhado** se sobrescrevem sem aviso. Valide os arquivos com um linter de JSON no CI.
- **pt vs pt-BR.** O idioma do usuário precisa bater exatamente com `lang`. Publique `pt-BR` se o seu público é brasileiro.
