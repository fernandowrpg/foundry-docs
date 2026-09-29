# Itens

Defina os tipos arma, magia e equipamento, coloque-os dentro de atores, role-os no chat, aceite-os ao arrastar e soltar e faça com que concedam efeitos ativos.

::: changed
- Os efeitos de itens guardam suas mudanças em `effect.system.changes`, com um `type` em texto no lugar do `mode` numérico. Veja [Efeitos ativos](#active-effect).
- `CONFIG.ActiveEffect.legacyTransferral` foi **removido**. Efeitos transferidos sempre ficam no item e se aplicam via `actor.allApplicableEffects()`.
- `template.json` está depreciado: use `documentTypes` + `CONFIG.Item.dataModels`.
- Novo callback `TypeDataModel#onEmbed(element)`. Ele trata de **embeds HTML** (`@Embed` em diários), *não* de adicionar um item a um actor. Veja abaixo.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Um **Item** é algo que um actor tem ou sabe: uma espada, uma magia, uma corda, uma habilidade de classe. Itens vivem em dois lugares:

- como **itens do mundo**, na barra lateral de Itens e em compêndios (modelos que o mestre distribui);
- como **itens embutidos** dentro de um actor (`actor.items`), que são cópias independentes pertencentes àquele actor.

Arrastar um item do mundo para a ficha de um personagem *copia* o item. Editar a cópia nunca muda o original. Por isso os itens embutidos são o lugar certo para estado de cada personagem, como quantidade, equipado ou cargas.

## Defina o tipo (modelo de dados)

```json
{
  "documentTypes": {
    "Item": {
      "weapon": { "htmlFields": ["description"] },
      "spell": { "htmlFields": ["description"] },
      "gear": { "htmlFields": ["description"] }
    }
  }
}
```

```js
// systems/forja/module/data/item.mjs
const { SchemaField, NumberField, StringField, BooleanField, HTMLField } = foundry.data.fields;

class ForjaItemBase extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      description: new HTMLField(),
      weight: new NumberField({ required: true, min: 0, initial: 0 })
    };
  }
}

export class WeaponData extends ForjaItemBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      damage: new StringField({ required: true, initial: "1d6" }),   // fórmula de rolagem
      ability: new StringField({ required: true, initial: "str", choices: ["str", "agi", "mnd"] }),
      equipped: new BooleanField({ initial: false })
    };
  }

  /** Fórmula de ataque montada a partir do atributo escolhido. */
  get attackFormula() {
    return `1d20 + @${this.ability}`;
  }
}

export class SpellData extends ForjaItemBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      cost: new NumberField({ required: true, integer: true, min: 0, initial: 1 }), // mana
      formula: new StringField({ required: true, blank: true, initial: "" }),
      range: new StringField({ required: true, initial: "touch", choices: ["self", "touch", "near", "far"] })
    };
  }
}

export class GearData extends ForjaItemBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      quantity: new NumberField({ required: true, integer: true, min: 0, initial: 1 }),
      armor: new NumberField({ required: true, integer: true, min: 0, initial: 0 }),
      equipped: new BooleanField({ initial: false })
    };
  }

  prepareDerivedData() {
    this.totalWeight = this.weight * this.quantity;
  }
}
```

## Registre

```js
// systems/forja/forja.mjs
import { WeaponData, SpellData, GearData } from "./module/data/item.mjs";
import { ForjaItem } from "./module/documents/item.mjs";

Hooks.once("init", () => {
  CONFIG.Item.documentClass = ForjaItem;
  Object.assign(CONFIG.Item.dataModels, { weapon: WeaponData, spell: SpellData, gear: GearData });
});
```

### Uma classe de item própria

```js
// systems/forja/module/documents/item.mjs
export class ForjaItem extends Item {
  /** Fórmulas do item podem usar valores do actor (@str) e do item (@item.cost). */
  getRollData() {
    const data = { ...(this.actor?.getRollData() ?? {}) };
    data.item = { ...this.system };
    return data;
  }

  /** Publica um cartão do item no chat, com rolagem se ele tiver fórmula. */
  async roll() {
    const formula = this.type === "weapon" ? this.system.damage : this.system.formula;
    const rolls = [];
    if (formula) {
      const roll = new Roll(formula, this.getRollData());
      await roll.evaluate();
      rolls.push(roll);
    }

    const content = await foundry.applications.handlebars.renderTemplate(
      "systems/forja/templates/chat/item-card.hbs",
      { item: this, rolls }
    );

    const chatData = {
      speaker: ChatMessage.getSpeaker({ actor: this.actor }),
      content,
      rolls,
      flags: { forja: { itemUuid: this.uuid } }   // permite que os botões do cartão achem o item depois
    };
    return ChatMessage.create(chatData);
  }
}
```

```hbs
{{!-- systems/forja/templates/chat/item-card.hbs --}}
<div class="forja item-card">
  <header><img src="{{item.img}}" width="32" height="32"> <h3>{{item.name}}</h3></header>
  <div class="description">{{{item.system.description}}}</div>
  {{#if (eq item.type "weapon")}}
    <button type="button" data-action="attack">Atacar</button>
  {{/if}}
</div>
```

O tratamento de botões e a visibilidade das mensagens (roll modes / message modes) estão em [Chat e rolagens](#chat-roll).

## Crie pelo código

```js
const actor = game.actors.getName("Aldric");

// Adiciona itens embutidos (sempre um array)
const [sword] = await actor.createEmbeddedDocuments("Item", [
  { name: "Espada Longa", type: "weapon", system: { damage: "1d8 + @str", equipped: true } },
  { name: "Tocha", type: "gear", system: { quantity: 3 } }
]);

// O mesmo pela classe, informando o parent
await Item.create({ name: "Raio de Fogo", type: "spell", system: { cost: 2, formula: "2d6" } }, { parent: actor });

// Leitura
actor.items.getName("Tocha");
actor.items.filter(i => i.type === "weapon" && i.system.equipped);

// Atualizar e apagar
await sword.update({ "system.equipped": false });
await actor.updateEmbeddedDocuments("Item", [{ _id: sword.id, name: "Espada Longa Lascada" }]);
await actor.deleteEmbeddedDocuments("Item", [sword.id]);

// Um item do mundo (barra lateral), sem parent
await Item.create({ name: "Poção de Cura", type: "gear" });
```

::: tip
Agrupe suas mudanças. Uma chamada `createEmbeddedDocuments` com 10 itens é uma ida ao banco e uma re-renderização. Dez chamadas `Item.create` são dez de cada.
:::

## Ficha e interface

Registre uma ficha de item (o passo a passo completo de `ItemSheetV2` está em [Fichas](#sheets)):

```js
foundry.applications.apps.DocumentSheetConfig.registerSheet(Item, "forja", ForjaItemSheet, {
  types: ["weapon", "spell", "gear"], makeDefault: true, label: "FORJA.SheetItem"
});
```

### Soltando itens na ficha do ator

A `ActorSheetV2` já trata os drops. Quando o que foi solto é um Item, `_onDropItem(event, item)` recebe o Item já resolvido, venha ele da barra lateral ou de um compêndio. Se o item já pertence a este actor, ele é reordenado; caso contrário, é criado como cópia embutida. Sobrescreva o método para acrescentar regras, como empilhar equipamentos:

```js
// systems/forja/module/sheets/character-sheet.mjs
export class ForjaCharacterSheet extends foundry.applications.api.HandlebarsApplicationMixin(
  foundry.applications.sheets.ActorSheetV2
) {
  /** @override */
  async _onDropItem(event, item) {
    if (!this.actor.isOwner) return null;
    // Mesmo actor: deixe o core reordenar
    if (item.parent === this.actor) return super._onDropItem(event, item);

    // Empilha equipamentos de mesmo nome em vez de duplicar
    if (item.type === "gear") {
      const existing = this.actor.items.find(i => i.type === "gear" && i.name === item.name);
      if (existing) {
        return existing.update({ "system.quantity": existing.system.quantity + item.system.quantity });
      }
    }

    // Magias exigem nível suficiente (regra de exemplo)
    if (item.type === "spell" && this.actor.system.level < 2) {
      ui.notifications.warn("É preciso nível 2 para aprender magias.");
      return null;
    }

    return super._onDropItem(event, item);
  }
}
```

Para criar o item você mesmo, por exemplo para alterá-lo antes, remova os metadados do compêndio com `fromCompendium`. Ele devolve dados puros, sem `_id`, pasta, ordenação ou permissões:

```js
const data = game.items.fromCompendium(item);    // funciona para itens do mundo e de compêndio
data.system.quantity = 1;
return this.actor.createEmbeddedDocuments("Item", [data]);
```

## Efeitos concedidos por itens (transferência)

Um Active Effect num item com `transfer: true` se aplica ao **actor dono**, como um anel de força ou uma armadura que aumenta a defesa. O efeito continua no item: apague o item e o efeito vai junto.

::: v13
```js
await ring.createEmbeddedDocuments("ActiveEffect", [{
  name: "Anel de Força",
  img: "icons/equipment/finger/ring-band-gold.webp",
  transfer: true,
  changes: [
    { key: "system.abilities.str.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "1" }
  ]
}]);
```

Defina `CONFIG.ActiveEffect.legacyTransferral = false` no `init` (o padrão para sistemas novos). Assim os efeitos transferidos ficam no item e são aplicados via `actor.allApplicableEffects()`, em vez de serem *copiados* para o actor.
:::

::: v14
```js
await ring.createEmbeddedDocuments("ActiveEffect", [{
  name: "Anel de Força",
  img: "icons/equipment/finger/ring-band-gold.webp",
  transfer: true,
  system: {
    changes: [
      { key: "system.abilities.str.bonus", type: "add", value: "1", phase: "initial" }
    ]
  }
}]);
```

Efeitos transferidos sempre ficam no item e se aplicam via `actor.allApplicableEffects()` (`legacyTransferral` não existe mais).
:::

Só os efeitos de itens **equipados** deveriam valer. Suprima os outros na sua classe de ActiveEffect:

```js
export class ForjaActiveEffect extends ActiveEffect {
  get isSuppressed() {
    const item = this.parent;
    if ((item instanceof Item) && ("equipped" in item.system) && !item.system.equipped) return true;
    return super.isSuppressed;
  }
}
// no init: CONFIG.ActiveEffect.documentClass = ForjaActiveEffect;
```

::: v14
### Sobre `TypeDataModel#onEmbed`

A V14 adicionou `onEmbed(element)` ao `TypeDataModel`. O core o chama quando o **HTML embutido** deste documento, gerado por `toEmbed()` para um enricher `@Embed[...]`, é adicionado ao DOM. Use-o para ligar eventos no cartão do seu item dentro de uma página de diário:

```js
export class SpellData extends ForjaItemBase {
  // ...
  onEmbed(element) {
    element.querySelector("[data-action=cast]")?.addEventListener("click", () => this.parent.roll());
  }
}
```

Para reagir quando um item é **adicionado a um actor**, use `_preCreate` / `_onCreate` no data model e confira `this.parent.parent` (o actor).
:::

## Receitas comuns

### Reagir quando um item é adicionado a um ator

```js
export class SpellData extends ForjaItemBase {
  async _preCreate(data, options, user) {
    if ((await super._preCreate(data, options, user)) === false) return false;
    const actor = this.parent.parent;           // this.parent é o Item
    if (actor?.type === "npc") this.updateSource({ cost: 0 });   // NPCs lançam de graça
  }
}
```

### Gastar mana ao lançar

```js
async function castSpell(spell) {
  const actor = spell.actor;
  const mana = actor.system.mana.value;
  if (mana < spell.system.cost) return ui.notifications.warn("Mana insuficiente.");
  await actor.update({ "system.mana.value": mana - spell.system.cost });
  return spell.roll();
}
```

### Usar um consumível

```js
const torch = actor.items.getName("Tocha");
if (torch.system.quantity <= 1) await torch.delete();
else await torch.update({ "system.quantity": torch.system.quantity - 1 });
```

## Armadilhas

- **`item.actor` é `null` em itens do mundo.** Proteja todo lugar que lê dados do actor (`this.actor?.`).
- **Atualizar o item do mundo não atualiza as cópias.** Itens embutidos são independentes. Use uma [migração](#migrations) ou solte-os de novo.
- **`createEmbeddedDocuments` exige um array** e devolve um array, mesmo para um único item.
- **Empilhar pelo nome** quebra com nomes traduzidos. Em sistemas reais, guarde um identificador estável, como `system.identifier` ou uma flag.
- **Efeitos transferidos de itens não equipados** continuam valendo, a menos que você implemente `isSuppressed`.
- **Na V13, `legacyTransferral: true`** (a opção mantida para mundos antigos) copia os efeitos para o actor. A cópia então sobrevive ao item. Garanta que esteja `false`.
