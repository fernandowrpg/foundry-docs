# Tipos de ficha

Dê a cada tipo de documento do seu sistema a ficha certa: uma ficha por tipo, uma ficha que se adapta ao tipo, fichas alternativas que o usuário pode escolher e uma classe base compartilhada para não repetir código.

::: changed
- A API de registro de fichas (`DocumentSheetConfig.registerSheet`) é a **mesma** no V13 e no V14. O código desta página funciona nas duas versões, a não ser onde um bloco diz o contrário.
- As fichas podem ser **destacadas** em uma janela própria do navegador, e o cabeçalho do `DocumentSheet` ganha um botão de **ownership** (permissões).
- Active Effects são documentos primários, então os **tipos** de efeito também podem ter fichas próprias (veja "Fichas para outros documentos").
- Uma classe de documento pode declarar nos metadados se o tipo `base` pode ser criado, o que esconde o `base` do diálogo "Criar".
- Veja [a lista completa de mudanças](#changes-14).
:::

## Tipos e fichas são coisas diferentes

Um **tipo** é dado: `character`, `npc`, `weapon`, `spell`. Você o declara no manifesto e dá a ele um data model ([Modelos de dados](#data-models)). Uma **ficha** é a janela que mostra e edita um documento. O Foundry liga os dois por um registro:

```text
system.json                 CONFIG.Actor.dataModels        CONFIG.Actor.sheetClasses
documentTypes.Actor   →     character → CharacterData  →   character → { "forja.ForjaCharacterSheet": {...default: true},
  character                 npc       → NpcData                          "forja.ForjaCompactSheet":   {...} }
  npc                                                      npc       → { "forja.ForjaNpcSheet":       {...default: true} }
```

Cada ficha registrada recebe um id `<escopo>.<NomeDaClasse>` (por exemplo `forja.ForjaNpcSheet`). O escopo é o primeiro argumento de `registerSheet`; use o id do seu pacote.

::: warning
Desde o V13 o core **não** registra ficha padrão de ator nem de item. Todo tipo que você declara precisa de pelo menos uma ficha registrada, senão o clique duplo nesse documento não faz nada. Registrar sem `types` aplica a ficha a **todos** os tipos daquele documento.
:::

## Como o Foundry escolhe a ficha

Quando um documento é aberto, o Foundry procura a ficha nesta ordem:

1. **A ficha escolhida para este documento**, guardada em `flags.core.sheetClass` (definida no diálogo "Configurar Ficha" no cabeçalho da ficha, ou pelo código).
2. **O padrão que o mestre escolheu para o tipo**, no mesmo diálogo (salvo na configuração de mundo `core.sheetClasses`).
3. **A ficha registrada com `makeDefault: true`** para aquele tipo.
4. A primeira ficha registrada para aquele tipo.

É por isso que os usuários trocam de ficha sem mexer no seu código, e é por isso que renomear a classe de uma ficha quebra a escolha que eles salvaram: o id guardado na flag deixa de existir, e o Foundry volta para o padrão.

## Lista de verificação para acrescentar um tipo novo

1. Declare-o no manifesto em `documentTypes`.
2. Escreva o data model dele e registre em `CONFIG.<Document>.dataModels`.
3. Coloque o nome dele nos arquivos de idioma em `TYPES.<Document>.<tipo>`.
4. Registre uma ficha para ele (um dos padrões abaixo).
5. Crie os templates dele.

```json
{
  "documentTypes": {
    "Actor": { "character": {}, "npc": {}, "vehicle": {} },
    "Item":  { "weapon": {}, "gear": {}, "spell": { "htmlFields": ["description"] } }
  }
}
```

```json
{
  "TYPES": {
    "Actor": { "character": "Personagem", "npc": "NPC", "vehicle": "Veículo" },
    "Item":  { "weapon": "Arma", "gear": "Equipamento", "spell": "Magia" }
  },
  "FORJA": {
    "Sheet": {
      "Character": "Ficha de personagem do Forja",
      "Npc": "Ficha de NPC do Forja",
      "Vehicle": "Ficha de veículo do Forja",
      "Compact": "Ficha compacta do Forja",
      "Item": "Ficha de item do Forja",
      "Spell": "Ficha de magia do Forja"
    }
  }
}
```

## Padrão 1: uma classe base compartilhada

A maioria das fichas compartilha as mesmas opções, ações e contexto (o documento, os dados `system`, os campos, o HTML enriquecido). Coloque isso em uma classe base e deixe em cada ficha só as diferenças.

```js
// systems/forja/module/sheets/base-actor-sheet.mjs
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2 } = foundry.applications.sheets;
const TextEditor = foundry.applications.ux.TextEditor.implementation;

export class ForjaBaseActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "actor-sheet"],
    position: { width: 620, height: 720 },
    window: { resizable: true },
    form: { submitOnChange: true },
    actions: {
      roll: ForjaBaseActorSheet.#onRoll,
      editItem: ForjaBaseActorSheet.#onEditItem,
      deleteItem: ForjaBaseActorSheet.#onDeleteItem
    }
  };

  /** Parts que toda ficha de ator tem. As subclasses espalham estas nas suas próprias PARTS. */
  static BASE_PARTS = {
    header: { template: "systems/forja/templates/actor/header.hbs" },
    tabs: { template: "templates/generic/tab-navigation.hbs" }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const actor = this.actor;
    return Object.assign(context, {
      actor,
      system: actor.system,
      systemSource: context.source.system,
      systemFields: actor.system.schema.fields,
      itemGroups: actor.itemTypes,
      enrichedBiography: await TextEditor.enrichHTML(actor.system.biography ?? "", {
        secrets: actor.isOwner, rollData: actor.getRollData(), relativeTo: actor
      })
    });
  }

  async _preparePartContext(partId, context, options) {
    context = await super._preparePartContext(partId, context, options);
    if ( context.tabs && (partId in context.tabs) ) context.tab = context.tabs[partId];
    return context;
  }

  _getItem(target) {
    return this.actor.items.get(target.closest("[data-item-id]")?.dataset.itemId);
  }

  static async #onRoll(event, target) {
    const roll = new Roll(`1d20 + @abilities.${target.dataset.ability}.value`, this.actor.getRollData());
    await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor: this.actor }) });
  }

  static #onEditItem(event, target) { this._getItem(target)?.sheet.render({ force: true }); }

  static async #onDeleteItem(event, target) { await this._getItem(target)?.deleteDialog(); }
}
```

O que as subclasses herdam e o que não herdam:

| Propriedade estática | Como é herdada |
|---|---|
| `DEFAULT_OPTIONS` | **Mesclada** com a do pai. A subclasse só lista o que muda (classes extras, uma ação nova, outra largura). |
| `PARTS` | **Substituída**. Uma subclasse que define `PARTS` precisa listar todas as parts que quer, então espalhe as parts do pai explicitamente. |
| `TABS` | **Substituída**, como `PARTS`. |
| Métodos de instância (`_prepareContext`…) | Herança normal do JavaScript: chame `super` primeiro. |

::: tip
Handlers estáticos privados (`static #onRoll`) só podem ser referenciados dentro da classe que os declara. Registre-os no `DEFAULT_OPTIONS.actions` dessa classe; as subclasses recebem os handlers pela mesclagem.
:::

## Padrão 2: uma ficha por tipo

Use quando os tipos são muito diferentes, como uma ficha de personagem completa e um bloco de estatísticas de NPC em uma página. Cada tipo ganha sua própria classe e seus templates.

```js
// systems/forja/module/sheets/character-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

export class ForjaCharacterSheet extends ForjaBaseActorSheet {
  static DEFAULT_OPTIONS = { classes: ["character"] };   // mesclado: forja actor-sheet character

  static PARTS = {
    ...ForjaBaseActorSheet.BASE_PARTS,
    abilities: { template: "systems/forja/templates/actor/abilities.hbs" },
    inventory: { template: "systems/forja/templates/actor/inventory.hbs", scrollable: [""] },
    biography: { template: "systems/forja/templates/actor/biography.hbs" }
  };

  static TABS = {
    primary: {
      tabs: [{ id: "abilities" }, { id: "inventory" }, { id: "biography" }],
      initial: "abilities",
      labelPrefix: "FORJA.Tab"
    }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    context.tabs = this._prepareTabs("primary");
    return context;
  }
}
```

```js
// systems/forja/module/sheets/npc-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

export class ForjaNpcSheet extends ForjaBaseActorSheet {
  static DEFAULT_OPTIONS = {
    classes: ["npc"],
    position: { width: 460, height: 560 }                // janela menor
  };

  /** Um único bloco de estatísticas com rolagem: sem abas. */
  static PARTS = {
    header: ForjaBaseActorSheet.BASE_PARTS.header,
    statblock: { template: "systems/forja/templates/actor/npc-statblock.hbs", scrollable: [""] }
  };
}
```

```js
// systems/forja/forja.mjs
import { ForjaCharacterSheet } from "./module/sheets/character-sheet.mjs";
import { ForjaNpcSheet } from "./module/sheets/npc-sheet.mjs";

Hooks.once("init", () => {
  const { DocumentSheetConfig } = foundry.applications.apps;

  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaCharacterSheet, {
    types: ["character"], makeDefault: true, label: "FORJA.Sheet.Character"
  });
  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaNpcSheet, {
    types: ["npc"], makeDefault: true, label: "FORJA.Sheet.Npc"
  });
});
```

## Padrão 3: uma ficha que se adapta ao tipo

Use quando os tipos compartilham quase todo o layout e diferem em poucas seções, como `character` e `vehicle`, que têm inventário, mas só o personagem tem atributos. Declare todas as parts uma vez e escolha quais renderizar para o documento atual.

```js
// systems/forja/module/sheets/adaptive-actor-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

/** Quais parts e abas cada tipo mostra. */
const LAYOUT = {
  character: ["abilities", "inventory", "biography"],
  vehicle:   ["crew", "inventory"]
};

export class ForjaAdaptiveSheet extends ForjaBaseActorSheet {
  static PARTS = {
    ...ForjaBaseActorSheet.BASE_PARTS,
    abilities: { template: "systems/forja/templates/actor/abilities.hbs" },
    crew:      { template: "systems/forja/templates/actor/crew.hbs" },
    inventory: { template: "systems/forja/templates/actor/inventory.hbs", scrollable: [""] },
    biography: { template: "systems/forja/templates/actor/biography.hbs" }
  };

  static TABS = {
    primary: {
      tabs: [{ id: "abilities" }, { id: "crew" }, { id: "inventory" }, { id: "biography" }],
      initial: "inventory",
      labelPrefix: "FORJA.Tab"
    }
  };

  /** Renderiza só as parts que pertencem ao tipo deste documento. */
  _configureRenderOptions(options) {
    super._configureRenderOptions(options);
    const wanted = LAYOUT[this.document.type] ?? [];
    options.parts = ["header", "tabs", ...wanted].filter(p => !options.parts || options.parts.includes(p));
  }

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    // Mantém só as abas deste tipo
    const wanted = LAYOUT[this.document.type] ?? [];
    const tabs = this._prepareTabs("primary");
    context.tabs = Object.fromEntries(Object.entries(tabs).filter(([id]) => wanted.includes(id)));
    return context;
  }
}
```

```js
DocumentSheetConfig.registerSheet(Actor, "forja", ForjaAdaptiveSheet, {
  types: ["character", "vehicle"], makeDefault: true, label: "FORJA.Sheet.Character"
});
```

::: warning
Se a aba inicial (`initial`) não está na lista de um tipo, a ficha abre sem aba ativa. Escolha como `initial` uma aba que todos os tipos têm, como acima (`inventory`), ou defina `this.tabGroups.primary` no `_prepareContext` antes de chamar `_prepareTabs`.
:::

O template de uma part compartilhada ainda pode variar conforme o tipo:

```hbs
{{!-- systems/forja/templates/actor/inventory.hbs --}}
<section class="tab inventory {{tab.cssClass}}" data-tab="inventory" data-group="primary">
  {{#if (eq actor.type "vehicle")}}
    <p class="capacity">{{localize "FORJA.Vehicle.Cargo"}}: {{system.cargo.value}} / {{system.cargo.max}}</p>
  {{/if}}
  {{#each itemGroups.gear as |item|}}
    <div class="item-row" data-item-id="{{item.id}}">{{item.name}}
      <a data-action="editItem"><i class="fa-solid fa-pen"></i></a>
    </div>
  {{/each}}
</section>
```

### Qual padrão usar?

| Situação | Padrão |
|---|---|
| Os tipos compartilham a maioria dos campos e do layout | Uma ficha adaptável (Padrão 3) |
| Os tipos são completamente diferentes | Uma ficha por tipo (Padrão 2) |
| Várias fichas repetem opções e ações | Classe base compartilhada (Padrão 1), sempre |
| Os usuários querem outro visual para o mesmo tipo | Fichas alternativas (próxima seção) |

## Fichas alternativas para o mesmo tipo

Registre uma segunda ficha para o mesmo tipo **sem** `makeDefault`. Ela aparece no diálogo "Configurar Ficha", onde o usuário pode escolhê-la para um ator, e o mestre pode torná-la o padrão do tipo.

```js
// systems/forja/module/sheets/compact-sheet.mjs
import { ForjaBaseActorSheet } from "./base-actor-sheet.mjs";

export class ForjaCompactSheet extends ForjaBaseActorSheet {
  static DEFAULT_OPTIONS = { classes: ["compact"], position: { width: 360, height: 480 } };
  static PARTS = {
    header: ForjaBaseActorSheet.BASE_PARTS.header,
    summary: { template: "systems/forja/templates/actor/compact.hbs" }
  };
}
```

```js
DocumentSheetConfig.registerSheet(Actor, "forja", ForjaCompactSheet, {
  types: ["character", "npc"],
  label: "FORJA.Sheet.Compact"          // não é a padrão: o usuário escolhe se quiser
});
```

`registerSheet` também aceita `canBeDefault: false` (o usuário pode escolhê-la por documento, mas ela nunca vira o padrão do tipo) e `canConfigure: false` (esconde a opção de configurar a ficha). Confira `DocumentSheetConfig.registerSheet` na API para ver a lista completa de opções da sua versão.

### Escolha uma ficha pelo código

```js
// A partir de agora, abre este ator com a ficha compacta
await actor.setFlag("core", "sheetClass", "forja.ForjaCompactSheet");

// Volta para o padrão do tipo
await actor.unsetFlag("core", "sheetClass");

// Quais fichas existem para um tipo?
console.log(Object.keys(CONFIG.Actor.sheetClasses.character));
// ["forja.ForjaCharacterSheet", "forja.ForjaCompactSheet"]
```

O core fecha a ficha aberta e usa a nova classe na próxima vez que o documento for aberto.

### Uma visão limitada para os outros jogadores

Jogadores com permissão só **Limitada** em um ator devem ver uma descrição curta, não a ficha completa. Você não precisa registrar outra ficha para isso: troque as parts na mesma ficha.

```js
_configureRenderOptions(options) {
  super._configureRenderOptions(options);
  if ( this.document.limited ) options.parts = ["header", "limited"];   // nome, imagem, biografia pública
}
```

Acrescente uma entrada `limited` em `PARTS` com o template dela, e garanta que o `_prepareContext` não exponha dados secretos (enriqueça a biografia com `secrets: false` para quem tem visão limitada).

## Fichas de item por tipo

Itens seguem as mesmas regras. Uma configuração comum é uma ficha de item genérica mais uma especial para magias:

```js
// systems/forja/module/sheets/spell-sheet.mjs
import { ForjaItemSheet } from "./item-sheet.mjs";

export class ForjaSpellSheet extends ForjaItemSheet {
  static DEFAULT_OPTIONS = { classes: ["spell"] };
  static PARTS = {
    header: ForjaItemSheet.PARTS.header,
    casting: { template: "systems/forja/templates/item/spell-casting.hbs" },
    details: ForjaItemSheet.PARTS.details
  };
}
```

```js
DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
  types: ["weapon", "gear"], makeDefault: true, label: "FORJA.Sheet.Item"
});
DocumentSheetConfig.registerSheet(Item, "forja", ForjaSpellSheet, {
  types: ["spell"], makeDefault: true, label: "FORJA.Sheet.Spell"
});
```

## Fichas para outros documentos

O mesmo registro funciona para qualquer tipo de documento que tenha ficha. Estenda a classe base correspondente:

| Documento | Classe base a estender |
|---|---|
| Actor | `foundry.applications.sheets.ActorSheetV2` |
| Item | `foundry.applications.sheets.ItemSheetV2` |
| ActiveEffect | `foundry.applications.sheets.ActiveEffectConfig` |
| JournalEntryPage | `foundry.applications.sheets.journal.JournalEntryPageHandlebarsSheet` (veja [Diários](#journal)) |
| Qualquer outro documento | `foundry.applications.api.DocumentSheetV2` |

Comportamentos de região não precisam de ficha: a janela de configuração deles é gerada a partir do data model ([Regiões](#regions)).

```js
// Uma ficha para o tipo de Active Effect "buff"
class ForjaBuffConfig extends foundry.applications.sheets.ActiveEffectConfig {
  static DEFAULT_OPTIONS = { classes: ["forja", "buff-config"] };
}

DocumentSheetConfig.registerSheet(ActiveEffect, "forja", ForjaBuffConfig, {
  types: ["buff"], makeDefault: true, label: "FORJA.Sheet.Buff"
});
```

::: v14
Active Effects são documentos primários no V14: aparecem na barra lateral e nos compêndios e abrem com a ficha registrada para o tipo deles, como atores e itens. O data model `system` do efeito é dono das `changes`, então uma ficha de efeito própria deve manter a part "Changes" do core. Veja [Efeitos ativos](#active-effect).
:::

## Esconda o tipo `base`

::: v13
Quando um documento tem tipos, o diálogo "Criar" lista todos os tipos registrados. Documentos criados sem tipo recebem `base`, que só faz sentido se você o declarou e registrou. Declare só os tipos que você realmente suporta e registre uma ficha para cada um.
:::

::: v14
Cada classe de documento agora pode dizer nos metadados se o tipo `base` pode ser criado e oferecido nos diálogos de criação. Se o seu sistema não tem ator `base`, esconda-o para os usuários não criarem um por engano. Confira a chave exata na entrada `metadata` da classe do documento na [API do V14](https://foundryvtt.com/api/v14/) antes de depender dela.
:::

## Armadilhas

- **Um tipo sem ficha**: abrir o documento não faz nada. Registre uma ficha para cada tipo declarado.
- **Esquecer `types`**: a ficha fica registrada para todos os tipos, inclusive os que módulos acrescentarem depois.
- **Duas fichas com `makeDefault: true` para o mesmo tipo**: vence a última registrada. Mantenha um padrão por tipo.
- **Renomear a classe de uma ficha**: o id `forja.NomeDaClasse` muda e os usuários perdem a escolha salva. Mantenha os nomes das classes estáveis depois de publicar.
- **Esperar que `PARTS` seja mesclado**: só o `DEFAULT_OPTIONS` é mesclado. Espalhe as parts do pai explicitamente.
- **Registrar no `ready`**: as fichas precisam ser registradas no `init`, antes de qualquer documento abrir.
