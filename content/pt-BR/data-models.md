# Modelos de dados

Um `TypeDataModel` define o formato, os valores padrão, a validação e os valores derivados dos dados `system` de cada tipo de ator e item do seu sistema.

::: changed
- O `template.json` está **depreciado**: declare os tipos em `documentTypes` no manifesto e defina-os com `TypeDataModel` (ou deixe-os sem schema).
- `SchemaField#extendFields()` e `SchemaField#removeFields()` permitem que pacotes adicionem ou removam campos de um schema existente.
- `DataModel#getFieldForProperty(key)` retorna o `DataField` por trás de um caminho de propriedade.
- Nova opção de `DataField`, `placeholder`, localizada automaticamente.
- Novo callback `TypeDataModel#onEmbed(element)` e novos métodos do ciclo de atualização `_updateDiff` / `_updateCommit`.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Todo `Actor` e `Item` tem um `type` (no `forja`: `character`, `npc`, `weapon`) e um objeto `system` com os dados daquele tipo. Um **TypeDataModel** é uma classe que descreve o `system` de um tipo:

- **Schema** — quais campos existem, seus tipos, padrões e limites. O Foundry valida toda criação e atualização contra ele, então dados inválidos nunca chegam ao banco.
- **Preparação** — métodos que calculam valores que não ficam salvos no banco (modificadores, totais).
- **Migração** — um ponto para converter dados antigos salvos para o formato atual.
- **Comportamento** — quaisquer getters ou métodos que você queira em `actor.system`.

Como o model é uma classe de verdade, `actor.system.attributes.strength.mod` pode ser um valor calculado e `actor.system.isHeavy` pode ser um getter.

## Declare os tipos no manifesto

Os tipos são declarados no `system.json` em `documentTypes`. O servidor não consegue executar seus models em JavaScript, então é aqui também que você informa quais campos contêm HTML (para serem sanitizados) e quais contêm caminhos de arquivo (com as categorias permitidas).

```json
{
  "id": "forja",
  "documentTypes": {
    "Actor": {
      "character": {
        "htmlFields": ["biography"],
        "filePathFields": { "crest": ["IMAGE"] }
      },
      "npc": {
        "htmlFields": ["biography"]
      }
    },
    "Item": {
      "weapon": {
        "htmlFields": ["description"],
        "filePathFields": { "sound": ["AUDIO"] }
      }
    }
  }
}
```

::: v13
A V13 ainda aceita um arquivo `template.json` que lista os tipos e seus dados padrão. Ele continua funcionando, mas você deve declarar os tipos com `documentTypes` e definir os dados com `TypeDataModel`, que é o que a V14 exige. Dá para usar os dois durante uma transição; o data model tem prioridade para um tipo que tenha um.
:::

::: v14
O `template.json` está **depreciado** na V14 e gera um aviso. Remova-o, declare todo tipo em `documentTypes` e dê a cada tipo um `TypeDataModel` (um tipo sem model simplesmente tem um objeto `system` sem validação).
:::

## Defina o esquema

`defineSchema()` retorna um objeto de instâncias de `DataField`. Todas as classes de campo ficam em `foundry.data.fields`. Uma classe base compartilhada evita repetir campos entre `character` e `npc`.

```js
// systems/forja/data/actor-base.mjs
const { SchemaField, NumberField, HTMLField } = foundry.data.fields;

export class ActorBaseData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA.Actor.Base"];

  static defineSchema() {
    return {
      hp: new SchemaField({
        value: new NumberField({ required: true, integer: true, min: 0, initial: 10 }),
        max: new NumberField({ required: true, integer: true, min: 0, initial: 10 })
      }),
      biography: new HTMLField({ required: true, blank: true })
    };
  }
}
```

```js
// systems/forja/data/character.mjs
import { ActorBaseData } from "./actor-base.mjs";

const {
  SchemaField, NumberField, StringField, BooleanField, ArrayField, SetField,
  TypedObjectField, EmbeddedDataField, DocumentUUIDField, FilePathField, ColorField
} = foundry.data.fields;

/** Um pequeno model reutilizável embutido no personagem */
class WalletData extends foundry.abstract.DataModel {
  static defineSchema() {
    return {
      gold: new NumberField({ required: true, integer: true, min: 0, initial: 0 }),
      silver: new NumberField({ required: true, integer: true, min: 0, initial: 0 })
    };
  }
  get totalInSilver() {
    return this.gold * 10 + this.silver;
  }
}

const attribute = () => new SchemaField({
  value: new NumberField({ required: true, integer: true, min: 1, max: 20, initial: 10 })
});

export class CharacterData extends ActorBaseData {
  static LOCALIZATION_PREFIXES = [...super.LOCALIZATION_PREFIXES, "FORJA.Actor.Character"];

  static defineSchema() {
    return {
      ...super.defineSchema(),
      level: new NumberField({ required: true, integer: true, min: 1, max: 10, initial: 1 }),
      attributes: new SchemaField({
        strength: attribute(),
        agility: attribute(),
        mind: attribute()
      }),
      origin: new StringField({
        required: true,
        blank: false,
        initial: "human",
        choices: { human: "FORJA.Origin.Human", dwarf: "FORJA.Origin.Dwarf", elf: "FORJA.Origin.Elf" }
      }),
      inspired: new BooleanField({ initial: false }),
      languages: new SetField(new StringField({ blank: false })),
      skills: new TypedObjectField(new SchemaField({
        rank: new NumberField({ required: true, integer: true, min: 0, max: 5, initial: 0 }),
        trained: new BooleanField()
      })),
      notes: new ArrayField(new SchemaField({
        title: new StringField({ required: true, blank: false }),
        text: new StringField()
      })),
      wallet: new EmbeddedDataField(WalletData),
      patron: new DocumentUUIDField({ type: "Actor" }),
      crest: new FilePathField({ categories: ["IMAGE"] }),
      color: new ColorField({ initial: "#b5651d" })
    };
  }

  prepareDerivedData() {
    // Modificador derivado de cada atributo, não é salvo no banco
    for (const attr of Object.values(this.attributes)) {
      attr.mod = Math.floor((attr.value - 10) / 2);
    }
    // A defesa é sempre derivada, por isso não faz parte do schema
    this.defense = 10 + this.attributes.agility.mod;
  }

  getRollData() {
    // Achata o que as fórmulas precisam: @str, @agi, @mind, @level, @defense
    return {
      level: this.level,
      hp: this.hp,
      attributes: this.attributes,
      defense: this.defense,
      str: this.attributes.strength.mod,
      agi: this.attributes.agility.mod,
      mind: this.attributes.mind.mod
    };
  }
}
```

```js
// systems/forja/data/npc.mjs
import { ActorBaseData } from "./actor-base.mjs";
const { NumberField, ObjectField } = foundry.data.fields;

export class NpcData extends ActorBaseData {
  static LOCALIZATION_PREFIXES = [...super.LOCALIZATION_PREFIXES, "FORJA.Actor.Npc"];

  static defineSchema() {
    return {
      ...super.defineSchema(),
      threat: new NumberField({ required: true, integer: true, min: 0, initial: 1 }),
      // Dados livres, sem validação: use com moderação
      extra: new ObjectField()
    };
  }
}
```

```js
// systems/forja/data/weapon.mjs
const { StringField, NumberField, BooleanField, HTMLField, SetField, FilePathField } = foundry.data.fields;

export class WeaponData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA.Item.Weapon"];

  static defineSchema() {
    return {
      description: new HTMLField({ required: true, blank: true }),
      damage: new StringField({ required: true, blank: false, initial: "1d6" }),
      weight: new NumberField({ required: true, min: 0, initial: 1 }),
      equipped: new BooleanField({ initial: false }),
      properties: new SetField(new StringField({
        choices: { light: "FORJA.Weapon.Light", heavy: "FORJA.Weapon.Heavy", thrown: "FORJA.Weapon.Thrown" }
      })),
      sound: new FilePathField({ categories: ["AUDIO"] })
    };
  }

  get isHeavy() {
    return this.properties.has("heavy");
  }
}
```

## Referência de campos

| Campo | Armazena | Observações |
| --- | --- | --- |
| `StringField` | string | `blank`, `trim`, `choices` |
| `NumberField` | número | `min`, `max`, `step`, `integer`, `positive`, `choices` |
| `BooleanField` | booleano | padrão `false` |
| `HTMLField` | string HTML | editado com o editor de texto rico; liste-o em `htmlFields` |
| `SchemaField` | objeto aninhado com chaves fixas | recebe um objeto de campos |
| `ArrayField` | array | recebe o campo do elemento: `new ArrayField(new StringField())` |
| `SetField` | `Set` em memória, array no banco | valores únicos |
| `ObjectField` | qualquer objeto simples | conteúdo sem validação |
| `TypedObjectField` | objeto com **chaves arbitrárias**, cada valor validado | ótimo para "perícias por id" |
| `EmbeddedDataField` | uma instância de outro `DataModel` | sub-models reutilizáveis com métodos |
| `DocumentUUIDField` | string UUID | `type` restringe o tipo de documento |
| `FilePathField` | caminho de arquivo | `categories`: `IMAGE`, `AUDIO`, `VIDEO`, `TEXT`… |
| `ColorField` | string `#rrggbb` | exibido como seletor de cor nos formulários |

### Opções comuns

| Opção | Significado |
| --- | --- |
| `required` | A chave precisa existir (o Foundry preenche com `initial` se faltar) |
| `nullable` | `null` é um valor aceito |
| `initial` | Valor padrão (ou uma função que o retorna) |
| `min` / `max` / `integer` | Restrições numéricas (`NumberField`) |
| `blank` | Se `""` é válido (`StringField`) |
| `choices` | Valores permitidos: um array, um objeto `{ valor: chaveDoRótulo }` ou uma função |
| `label` / `hint` | Texto para formulários; normalmente fornecido por `LOCALIZATION_PREFIXES` |

::: v14
**`placeholder`** é uma nova opção exibida como texto de placeholder do input nos formulários gerados. Ela é localizada automaticamente, então você pode passar uma chave:

```js
// Texto de placeholder para um campo vazio no formulário
name: new foundry.data.fields.StringField({ placeholder: "FORJA.Placeholder.Nickname" })
```
:::

## Registre os modelos

```js
// systems/forja/forja.mjs
import { CharacterData } from "./data/character.mjs";
import { NpcData } from "./data/npc.mjs";
import { WeaponData } from "./data/weapon.mjs";

Hooks.once("init", () => {
  CONFIG.Actor.dataModels.character = CharacterData;
  CONFIG.Actor.dataModels.npc = NpcData;
  CONFIG.Item.dataModels.weapon = WeaponData;
});
```

O core localiza automaticamente os models registrados em `CONFIG.<Documento>.dataModels`. Para outros models (como `WalletData` usado sozinho), chame `foundry.helpers.Localization.localizeDataModel(Model)` no hook `i18nInit`.

## Rótulos automáticos com `LOCALIZATION_PREFIXES`

Em vez de escrever `label` e `hint` em cada campo, dê à classe um ou mais prefixos. O Foundry procura `<prefixo>.FIELDS.<caminho do campo>.label` e `.hint`:

```json
{
  "FORJA": {
    "Actor": {
      "Base": {
        "FIELDS": {
          "hp": {
            "label": "Pontos de Vida",
            "value": { "label": "Atual" },
            "max": { "label": "Máximo" }
          },
          "biography": { "label": "Biografia" }
        }
      },
      "Character": {
        "FIELDS": {
          "level": { "label": "Nível", "hint": "De 1 a 10." },
          "attributes": {
            "strength": { "value": { "label": "Força" } }
          }
        }
      }
    }
  }
}
```

Esses rótulos são usados por `{{formGroup}}` e `{{formInput}}` nas fichas, e por `field.label` no seu próprio código. Veja [localização](#localization).

## Preparação de dados

- `prepareBaseData()` roda **antes** de os Active Effects serem aplicados — prepare valores que os efeitos podem modificar.
- `prepareDerivedData()` roda **depois** que itens e efeitos embutidos são preparados — calcule totais e modificadores.

Os dois rodam em todo cliente, toda vez que o documento muda. Apenas atribua valores a `this`; nunca chame `update()` aqui. A ordem completa, junto com os métodos do documento, está na página de [documentos](#documents).

## Dados de rolagem

O Foundry não chama `system.getRollData()` sozinho. Conecte-o a partir da sua classe de ator para que fórmulas como `1d20 + @str` funcionem:

```js
// systems/forja/documents/actor.mjs
export class ForjaActor extends Actor {
  getRollData() {
    // Usa os dados de rolagem do data model quando ele fornece um
    return this.system.getRollData?.() ?? super.getRollData();
  }
}
```

## Migrando dados antigos

`static migrateData(source)` recebe os dados **brutos** salvos toda vez que um documento é carregado ou atualizado, antes da validação. Converta formatos antigos e sempre chame `super`.

```js
// systems/forja/data/character.mjs (dentro de CharacterData)
static migrateData(source) {
  // Versões antigas guardavam os pontos de vida como um único número chamado "health"
  if (typeof source.health === "number") {
    source.hp ??= {};
    source.hp.value ??= source.health;
    delete source.health;
  }
  return super.migrateData(source);
}
```

`migrateData` só altera a cópia em memória. Para reescrever o banco de forma permanente, rode uma migração do mundo (veja [migrações](#migrations)).

## Estendendo um esquema a partir de um módulo

::: v13
Não existe API pública na V13 para adicionar campos ao data model de outro pacote. Módulos devem guardar seus dados em [marcadores (`flags`)](#documents).
:::

::: v14
`SchemaField#extendFields(fields)` e `SchemaField#removeFields(names)` modificam a definição de um schema. Um módulo pode usá-los no `init` (os scripts do sistema carregam primeiro, então o model já está registrado):

```js
// modules/forja-extras/scripts/main.js
Hooks.once("init", () => {
  const CharacterData = CONFIG.Actor.dataModels.character;
  // Adiciona system.reputation a todo personagem do forja
  CharacterData.schema.extendFields({
    reputation: new foundry.data.fields.NumberField({ required: true, integer: true, initial: 0 })
  });
});
```

`getFieldForProperty` encontra o campo por trás de um caminho, o que é útil para ler rótulos ou choices de forma genérica:

```js
const field = actor.system.getFieldForProperty("attributes.strength.value");
console.log(field.label, field.max); // "Força", 20
```

`onEmbed(element)` é chamado quando o HTML embutido do documento (`@Embed[...]`) foi adicionado ao DOM — use-o para anexar listeners ao conteúdo embutido.
:::

## Armadilhas

- **Esquecer `...super.defineSchema()`** em uma subclasse descarta todos os campos da base.
- **Salvar valores derivados.** Um `mod` calculado em `prepareDerivedData` não pode ser também um campo do schema, ou será sobrescrito a cada atualização.
- **Usar `ObjectField` para tudo** joga fora a validação. Prefira `SchemaField` ou `TypedObjectField`.
- **Esquecer `htmlFields`** significa que o conteúdo HTML pode não ser tratado corretamente pelo servidor.
- **Os valores de `choices` são rótulos.** Para `{ human: "FORJA.Origin.Human" }` o valor salvo é `"human"`, e a chave do rótulo é localizada para exibição.
- **Registrar tarde demais.** Os models precisam ser definidos no `init`, antes de os documentos serem construídos.
