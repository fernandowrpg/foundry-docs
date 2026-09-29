# Seu primeiro sistema

Construa o sistema mínimo `forja`: manifesto com tipos de documento, modelos de dados, uma ficha de ator e uma de item em ApplicationV2, modelos Handlebars, traduções e CSS.

::: changed
- **`template.json` está obsoleto.** Declare os tipos em `documentTypes` e defina seus dados com classes `TypeDataModel` — exatamente o que esta página faz.
- Manifesto: `compatibility.minimum` `"14"` e o campo opcional `"type": "system"`.
- Active Effects guardam suas mudanças em `effect.system.changes` (com um `type` em texto no lugar do `mode` numérico) — relevante assim que seu sistema adicionar efeitos.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que vamos construir

Um pequeno RPG de fantasia:

- Tipos de **Actor** `character` e `npc`, com pontos de vida e três atributos (força, agilidade, mente). Personagens também têm nível.
- Tipos de **Item** `weapon` e `spell`, cada um com uma fórmula de dano.
- Uma ficha de personagem em que clicar em um atributo rola `1d20 + atributo`, e clicar em um item rola o dano dele.

Tudo usa a arquitetura da V13+: data models, fichas `ApplicationV2` e ES modules.

## 1. Estrutura de pastas

```bash
Data/systems/forja/
├── system.json
├── module/
│   ├── forja.mjs              # ponto de entrada (o único arquivo em esmodules)
│   ├── data/
│   │   ├── actor.mjs          # CharacterData, NpcData
│   │   └── item.mjs           # WeaponData, SpellData
│   └── sheets/
│       ├── actor-sheet.mjs
│       └── item-sheet.mjs
├── templates/
│   ├── actor-sheet.hbs
│   └── item-sheet.hbs
├── lang/
│   ├── en.json
│   └── pt-BR.json
└── styles/
    └── forja.css
```

## 2. O manifesto

`documentTypes` diz ao Foundry quais subtipos existem. Sem ele, o diálogo "Criar Ator" não tem nada a oferecer. `htmlFields` marca campos com texto rico para que o Foundry os trate corretamente (enriquecimento, sanitização).

::: v13
```json
{
  "id": "forja",
  "title": "Forja RPG",
  "description": "Um pequeno RPG de fantasia usado como exemplo.",
  "version": "0.1.0",
  "compatibility": { "minimum": "13", "verified": "13.351" },
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
  "flags": {
    "hotReload": { "extensions": ["css", "hbs", "json"], "paths": ["styles", "templates", "lang"] }
  }
}
```

A V13 ainda lê um `template.json` se você incluir um, mas você não precisa dele: os data models o substituem. Pular esse arquivo agora poupa uma migração depois.
:::

::: v14
```json
{
  "id": "forja",
  "type": "system",
  "title": "Forja RPG",
  "description": "Um pequeno RPG de fantasia usado como exemplo.",
  "version": "0.1.0",
  "compatibility": { "minimum": "14", "verified": "14.368" },
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
  "flags": {
    "hotReload": { "extensions": ["css", "hbs", "json"], "paths": ["styles", "templates", "lang"] }
  }
}
```

::: warning
Não crie um `template.json` na V14: ele está obsoleto. Todos os dados dos tipos vêm dos data models abaixo.
:::
:::

## 3. Modelos de dados

Um **data model** é uma classe que descreve o objeto `system` de um tipo de documento: tipos de campo, valores padrão, validação. O Foundry o usa para limpar a entrada (uma string `"12"` vinda de um formulário vira o número `12`), preencher padrões na criação e dar a você um lugar para valores derivados.

`module/data/actor.mjs`:

```js
const { SchemaField, NumberField, HTMLField } = foundry.data.fields;

// Pequeno auxiliar: um atributo = { value }
const attribute = () => new SchemaField({
  value: new NumberField({ required: true, integer: true, min: 0, initial: 1 })
});

// Campos compartilhados por todo ator do Forja
class ForjaActorData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      hp: new SchemaField({
        value: new NumberField({ required: true, integer: true, min: 0, initial: 10 }),
        max: new NumberField({ required: true, integer: true, min: 0, initial: 10 })
      }),
      attributes: new SchemaField({
        strength: attribute(),
        agility: attribute(),
        mind: attribute()
      }),
      biography: new HTMLField()
    };
  }

  // Dados derivados: calculados sempre que o documento é preparado, nunca salvos
  prepareDerivedData() {
    this.hp.value = Math.min(this.hp.value, this.hp.max);
  }
}

export class CharacterData extends ForjaActorData {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      level: new NumberField({ required: true, integer: true, min: 1, initial: 1 })
    };
  }
}

export class NpcData extends ForjaActorData {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      threat: new NumberField({ required: true, integer: true, min: 0, initial: 1 })
    };
  }
}
```

`module/data/item.mjs`:

```js
const { StringField, NumberField, HTMLField } = foundry.data.fields;

export class WeaponData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      damage: new StringField({ required: true, initial: "1d6" }),
      // Qual atributo é somado às rolagens de ataque
      attribute: new StringField({ required: true, initial: "strength", choices: ["strength", "agility", "mind"] }),
      description: new HTMLField()
    };
  }
}

export class SpellData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      damage: new StringField({ required: true, initial: "" }),
      cost: new NumberField({ required: true, integer: true, min: 0, initial: 1 }),
      description: new HTMLField()
    };
  }
}
```

Mais tipos de campo e métodos de ciclo de vida em [Modelos de dados](#data-models).

## 4. A ficha de ator

Fichas são classes ApplicationV2. `HandlebarsApplicationMixin` adiciona a renderização de templates via `static PARTS`; `ActorSheetV2` adiciona o salvamento do documento, arrastar e soltar e ações específicas de ator. Botões no template chamam métodos por meio de `data-action="nome"` → `DEFAULT_OPTIONS.actions.nome`.

`module/sheets/actor-sheet.mjs`:

```js
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2 } = foundry.applications.sheets;
const { TextEditor } = foundry.applications.ux;

export class ForjaActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "actor"],
    position: { width: 560, height: 640 },
    window: { resizable: true },
    form: { submitOnChange: true },   // salva cada campo assim que ele muda
    actions: {
      rollAttribute: ForjaActorSheet.#onRollAttribute,
      rollItem: ForjaActorSheet.#onRollItem,
      createItem: ForjaActorSheet.#onCreateItem,
      editItem: ForjaActorSheet.#onEditItem,
      deleteItem: ForjaActorSheet.#onDeleteItem
    }
  };

  static PARTS = {
    sheet: { template: "systems/forja/templates/actor-sheet.hbs" }
  };

  /** Dados disponíveis dentro do template. */
  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const actor = this.document;
    context.actor = actor;
    context.system = actor.system;
    context.isCharacter = actor.type === "character";
    context.attributes = Object.entries(CONFIG.FORJA.attributes).map(([key, label]) => ({
      key, label, value: actor.system.attributes[key].value
    }));
    context.weapons = actor.items.filter(i => i.type === "weapon");
    context.spells = actor.items.filter(i => i.type === "spell");
    context.enrichedBiography = await TextEditor.implementation.enrichHTML(actor.system.biography, {
      secrets: actor.isOwner, relativeTo: actor
    });
    return context;
  }

  /** Encontra o Item embutido de um elemento clicado. */
  #getItem(target) {
    const id = target.closest("[data-item-id]")?.dataset.itemId;
    return this.document.items.get(id);
  }

  // Ações: "this" é a instância da ficha
  static async #onRollAttribute(event, target) {
    const key = target.dataset.attribute;
    const roll = await new Roll("1d20 + @attr", { attr: this.document.system.attributes[key].value }).evaluate();
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this.document }),
      flavor: game.i18n.localize(CONFIG.FORJA.attributes[key])
    });
  }

  static async #onRollItem(event, target) {
    const item = this.#getItem(target);
    if (!item?.system.damage) return ui.notifications.warn(game.i18n.localize("FORJA.NoDamage"));
    const roll = await new Roll(item.system.damage).evaluate();
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this.document }),
      flavor: `${game.i18n.localize("FORJA.Damage")}: ${item.name}`
    });
  }

  static async #onCreateItem(event, target) {
    const type = target.dataset.type;
    await this.document.createEmbeddedDocuments("Item", [{
      name: game.i18n.localize(`TYPES.Item.${type}`), type
    }]);
  }

  static #onEditItem(event, target) {
    this.#getItem(target)?.sheet.render({ force: true });
  }

  static async #onDeleteItem(event, target) {
    await this.#getItem(target)?.delete();
  }
}
```

::: tip
`super._prepareContext()` já fornece `document`, `source`, `fields`, `editable` e `user`. Adicionamos atalhos (`actor`, `system`) para os templates ficarem curtos.
:::

### O modelo da ficha do ator

`templates/actor-sheet.hbs` — o template de uma parte precisa ter **um único elemento raiz**:

```hbs
<section class="forja-actor">
  <header class="sheet-header">
    <img class="profile" src="{{actor.img}}" alt="{{actor.name}}" data-action="editImage" data-edit="img">
    <div class="identity">
      <input name="name" type="text" value="{{actor.name}}" placeholder="{{localize 'FORJA.Name'}}">
      <label>{{localize "FORJA.HP"}}
        <input name="system.hp.value" type="number" value="{{system.hp.value}}">
        / <input name="system.hp.max" type="number" value="{{system.hp.max}}">
      </label>
      {{#if isCharacter}}
      <label>{{localize "FORJA.Level"}} <input name="system.level" type="number" value="{{system.level}}"></label>
      {{else}}
      <label>{{localize "FORJA.Threat"}} <input name="system.threat" type="number" value="{{system.threat}}"></label>
      {{/if}}
    </div>
  </header>

  <section class="attributes">
    {{#each attributes as |attr|}}
    <div class="attribute">
      <button type="button" data-action="rollAttribute" data-attribute="{{attr.key}}">{{localize attr.label}}</button>
      <input name="system.attributes.{{attr.key}}.value" type="number" value="{{attr.value}}">
    </div>
    {{/each}}
  </section>

  <section class="items">
    <h3>{{localize "TYPES.Item.weapon"}}
      <button type="button" data-action="createItem" data-type="weapon"><i class="fa-solid fa-plus"></i></button>
    </h3>
    <ul>
      {{#each weapons as |item|}}
      <li class="item" data-item-id="{{item.id}}">
        <img src="{{item.img}}" alt="">
        <a data-action="rollItem">{{item.name}}</a>
        <span class="formula">{{item.system.damage}}</span>
        <a data-action="editItem"><i class="fa-solid fa-pen"></i></a>
        <a data-action="deleteItem"><i class="fa-solid fa-trash"></i></a>
      </li>
      {{/each}}
    </ul>

    <h3>{{localize "TYPES.Item.spell"}}
      <button type="button" data-action="createItem" data-type="spell"><i class="fa-solid fa-plus"></i></button>
    </h3>
    <ul>
      {{#each spells as |item|}}
      <li class="item" data-item-id="{{item.id}}">
        <img src="{{item.img}}" alt="">
        <a data-action="rollItem">{{item.name}}</a>
        <span class="formula">{{item.system.cost}} {{localize "FORJA.Mana"}}</span>
        <a data-action="editItem"><i class="fa-solid fa-pen"></i></a>
        <a data-action="deleteItem"><i class="fa-solid fa-trash"></i></a>
      </li>
      {{/each}}
    </ul>
  </section>

  <h3>{{localize "FORJA.Biography"}}</h3>
  <prose-mirror name="system.biography" value="{{system.biography}}" toggled>{{{enrichedBiography}}}</prose-mirror>
</section>
```

Os inputs são salvos automaticamente porque o `name` deles corresponde a um caminho do documento (`system.hp.value`) e o formulário tem `submitOnChange`.

## 5. A ficha de item

`module/sheets/item-sheet.mjs`:

```js
const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ItemSheetV2 } = foundry.applications.sheets;
const { TextEditor } = foundry.applications.ux;

export class ForjaItemSheet extends HandlebarsApplicationMixin(ItemSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["forja", "item"],
    position: { width: 420, height: 480 },
    window: { resizable: true },
    form: { submitOnChange: true }
  };

  static PARTS = {
    sheet: { template: "systems/forja/templates/item-sheet.hbs" }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const item = this.document;
    context.item = item;
    context.system = item.system;
    context.isWeapon = item.type === "weapon";
    context.attributeChoices = CONFIG.FORJA.attributes;
    context.enrichedDescription = await TextEditor.implementation.enrichHTML(item.system.description, {
      secrets: item.isOwner, relativeTo: item
    });
    return context;
  }
}
```

`templates/item-sheet.hbs`:

```hbs
<section class="forja-item">
  <header class="sheet-header">
    <img class="profile" src="{{item.img}}" alt="{{item.name}}" data-action="editImage" data-edit="img">
    <input name="name" type="text" value="{{item.name}}">
  </header>

  <div class="form-group">
    <label>{{localize "FORJA.Damage"}}</label>
    <input name="system.damage" type="text" value="{{system.damage}}" placeholder="1d6">
  </div>

  {{#if isWeapon}}
  <div class="form-group">
    <label>{{localize "FORJA.Attribute.label"}}</label>
    <select name="system.attribute">
      {{selectOptions attributeChoices selected=system.attribute localize=true}}
    </select>
  </div>
  {{else}}
  <div class="form-group">
    <label>{{localize "FORJA.Cost"}}</label>
    <input name="system.cost" type="number" value="{{system.cost}}">
  </div>
  {{/if}}

  <prose-mirror name="system.description" value="{{system.description}}" toggled>{{{enrichedDescription}}}</prose-mirror>
</section>
```

## 6. O ponto de entrada: registre tudo

`module/forja.mjs` é o único arquivo listado em `esmodules`. Ele importa as classes e as registra durante o `init`.

```js
import { CharacterData, NpcData } from "./data/actor.mjs";
import { WeaponData, SpellData } from "./data/item.mjs";
import { ForjaActorSheet } from "./sheets/actor-sheet.mjs";
import { ForjaItemSheet } from "./sheets/item-sheet.mjs";

Hooks.once("init", () => {
  console.log("forja | init");

  // Constantes do sistema usadas por fichas e rolagens
  CONFIG.FORJA = {
    attributes: {
      strength: "FORJA.Attribute.strength",
      agility: "FORJA.Attribute.agility",
      mind: "FORJA.Attribute.mind"
    }
  };

  // Liga cada subtipo de documentTypes ao seu data model
  Object.assign(CONFIG.Actor.dataModels, { character: CharacterData, npc: NpcData });
  Object.assign(CONFIG.Item.dataModels, { weapon: WeaponData, spell: SpellData });

  // Registra as fichas (a V13+ não tem fichas padrão do core para ator/item)
  const { DocumentSheetConfig } = foundry.applications.apps;
  DocumentSheetConfig.registerSheet(Actor, "forja", ForjaActorSheet, {
    types: ["character", "npc"], makeDefault: true, label: "FORJA.Sheet.Actor"
  });
  DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
    types: ["weapon", "spell"], makeDefault: true, label: "FORJA.Sheet.Item"
  });
});
```

::: warning
As chaves em `CONFIG.Actor.dataModels` precisam bater exatamente com as chaves em `documentTypes`. Um tipo sem data model tem um objeto `system` vazio — sem erros, só campos faltando.
:::

## 7. Traduções

`TYPES.<Document>.<tipo>` é a convenção do core para nomes de tipo em diálogos e fichas.

`lang/en.json`:

```json
{
  "TYPES": {
    "Actor": { "character": "Character", "npc": "NPC" },
    "Item": { "weapon": "Weapon", "spell": "Spell" }
  },
  "FORJA": {
    "Name": "Name",
    "HP": "Hit points",
    "Level": "Level",
    "Threat": "Threat",
    "Damage": "Damage",
    "Cost": "Mana cost",
    "Mana": "MP",
    "Biography": "Biography",
    "NoDamage": "This item has no damage formula.",
    "Attribute": { "label": "Attribute", "strength": "Strength", "agility": "Agility", "mind": "Mind" },
    "Sheet": { "Actor": "Forja actor sheet", "Item": "Forja item sheet" }
  }
}
```

`lang/pt-BR.json`:

```json
{
  "TYPES": {
    "Actor": { "character": "Personagem", "npc": "PdM" },
    "Item": { "weapon": "Arma", "spell": "Magia" }
  },
  "FORJA": {
    "Name": "Nome",
    "HP": "Pontos de vida",
    "Level": "Nível",
    "Threat": "Ameaça",
    "Damage": "Dano",
    "Cost": "Custo de mana",
    "Mana": "PM",
    "Biography": "Biografia",
    "NoDamage": "Este item não tem fórmula de dano.",
    "Attribute": { "label": "Atributo", "strength": "Força", "agility": "Agilidade", "mind": "Mente" },
    "Sheet": { "Actor": "Ficha de ator Forja", "Item": "Ficha de item Forja" }
  }
}
```

## 8. Estilos

`styles/forja.css` — limite tudo à classe `forja` que você definiu em `DEFAULT_OPTIONS.classes`:

```css
.forja.sheet .sheet-header { display: flex; gap: 0.5rem; align-items: center; }
.forja.sheet .sheet-header .profile { width: 80px; height: 80px; object-fit: cover; cursor: pointer; }
.forja.sheet .identity { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.forja.sheet .identity input[type="number"] { width: 4rem; }
.forja.sheet .attributes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin: 0.5rem 0; }
.forja.sheet .attribute { display: flex; flex-direction: column; align-items: center; }
.forja.sheet .items ul { list-style: none; padding: 0; margin: 0; }
.forja.sheet .item { display: flex; align-items: center; gap: 0.5rem; }
.forja.sheet .item img { width: 24px; height: 24px; }
.forja.sheet .item .formula { margin-left: auto; opacity: 0.8; }
.forja.sheet prose-mirror { min-height: 8rem; }
```

## 9. Teste

1. Reinicie o Foundry (pacote novo), crie um mundo com **Forja RPG** e inicie-o.
2. Na aba Actors, crie um **Personagem**. Sua ficha abre.
3. Mude PV e atributos, clique em **Força** para rolar, adicione uma arma e clique no nome dela para rolar o dano.
4. Arraste o ator para uma cena: a barra do token mostra os PV (`primaryTokenAttribute`).

::: v14
Quando você adicionar Active Effects, lembre-se de que na V14 as mudanças deles ficam em `effect.system.changes`, cada uma com `{ key, value, type, phase, priority }`, em que `type` é uma string como `"add"` ou `"override"`. Veja [Efeitos ativos](#active-effect).
:::

::: v13
Quando você adicionar Active Effects, as mudanças deles ficam em `effect.changes`, cada uma com `{ key, value, mode, priority }`, em que `mode` é um número de `CONST.ACTIVE_EFFECT_MODES`. Veja [Efeitos ativos](#active-effect).
:::

## Armadilhas

- **A ficha não abre / "no sheet registered"** — confira se `registerSheet` rodou no `init` e se a lista `types` bate com `documentTypes`.
- **Campos não salvam** — o `name` do input precisa ser o caminho completo (`system.hp.value`, não `hp.value`), e o valor precisa passar na validação (por exemplo `min: 0`).
- **Números salvos como texto** — só acontece sem data model; o `NumberField` converte as strings do formulário para você.
- **Mudanças no template não aparecem** — ative `flags.hotReload` para `hbs` ou recarregue; JavaScript sempre precisa de F5.
- **Usuários sem permissão ainda conseguem digitar** — adicione `{{#unless editable}}disabled{{/unless}}` aos inputs, ou veja [Fichas](#sheets) para uma abordagem mais limpa.

## Próximos passos

- Aumente os dados: [Modelos de dados](#data-models), [Atores](#actor), [Itens](#item).
- Fichas melhores com abas e arrastar e soltar: [Janelas com ApplicationV2](#applicationv2), [Fichas](#sheets).
- Rolagens e cartões de chat: [Chat e rolagens](#chat-roll). Efeitos: [Efeitos ativos](#active-effect). Combate: [Combate](#combat).
- Mantenha mundos antigos funcionando quando o schema mudar: [Migrações](#migrations).
