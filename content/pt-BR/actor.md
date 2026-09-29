# Atores

Defina os tipos personagem e NPC com modelos de dados, dê a eles uma classe de documento própria com dados derivados e rolagens, e crie, atualize e vincule tokens por código.

::: changed
- Active Effects são aplicados em **fases** (`"initial"`, `"final"` e as que você registrar): `Actor#applyActiveEffects(phase)` agora recebe a fase.
- Efeitos agora podem alterar os **Tokens** do actor (visão, luz, imagem, alpha, disposição, tamanho, forma). O Actor junta essas mudanças em `Actor#tokenActiveEffectChanges`, e o token as aplica com `TokenDocument#applyActiveEffects(phase)`.
- `template.json` está depreciado: declare os tipos com `documentTypes` no `system.json` e `CONFIG.Actor.dataModels`.
- `TokenDocument#delta` (o `ActorDelta` de um token não vinculado) **pode ser `null`**. Verifique antes de ler.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Um **Actor** é qualquer coisa que age no mundo: personagens de jogadores, NPCs, monstros, veículos, armadilhas. Todo actor tem:

- um `type` (por exemplo `character` ou `npc`), que escolhe o data model e a ficha (sheet);
- um objeto `system` com os dados do seu jogo (PV, atributos, nível...);
- **Items** embutidos (`actor.items`) e **Active Effects** (`actor.effects`);
- um `prototypeToken`, o modelo usado toda vez que o actor é colocado numa cena.

O Foundry salva e sincroniza os dados *de origem* (source). Depois, em cada cliente, roda uma etapa de **preparação** que calcula valores derivados, como modificadores e totais, e aplica os efeitos. É ali que fica a maior parte do código de um sistema. Esta página monta o actor do `forja` passo a passo. Para os conceitos gerais, veja [Documentos](#documents) e [Modelos de dados](#data-models).

## Defina o tipo (modelo de dados)

Primeiro declare os tipos no manifesto. O Foundry só aceita tipos listados ali.

```json
{
  "id": "forja",
  "documentTypes": {
    "Actor": {
      "character": { "htmlFields": ["biography"] },
      "npc": { "htmlFields": ["biography"] }
    }
  }
}
```

Depois escreva um `TypeDataModel` por tipo. Uma classe base compartilhada concentra os campos comuns num só lugar.

```js
// systems/forja/module/data/actor.mjs
const { SchemaField, NumberField, StringField, HTMLField } = foundry.data.fields;

/** Um par {value, max}, usado para PV e mana. */
function resourceField(initial) {
  return new SchemaField({
    value: new NumberField({ required: true, integer: true, min: 0, initial }),
    max: new NumberField({ required: true, integer: true, min: 0, initial })
  });
}

function abilityField() {
  return new SchemaField({
    value: new NumberField({ required: true, integer: true, min: 1, max: 20, initial: 10 })
  });
}

export class ForjaActorBase extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      hp: resourceField(10),
      abilities: new SchemaField({
        str: abilityField(),
        agi: abilityField(),
        mnd: abilityField()
      }),
      // "bonus" é salvo e pode ser alterado por efeitos; "value" é derivado
      defense: new SchemaField({
        bonus: new NumberField({ required: true, integer: true, initial: 0 })
      }),
      biography: new HTMLField()
    };
  }

  /** Roda ANTES dos Active Effects: inicializa valores que os efeitos vão somar. */
  prepareBaseData() {
    for (const ability of Object.values(this.abilities)) ability.bonus = 0;
  }

  /** Roda DEPOIS dos Active Effects: calcula tudo que é derivado. */
  prepareDerivedData() {
    for (const ability of Object.values(this.abilities)) {
      ability.mod = Math.floor((ability.value - 10) / 2) + ability.bonus;
    }
    this.defense.value = 10 + this.abilities.agi.mod + this.defense.bonus;
    this.hp.value = Math.min(this.hp.value, this.hp.max);
  }
}

export class CharacterData extends ForjaActorBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      level: new NumberField({ required: true, integer: true, min: 1, initial: 1 }),
      mana: resourceField(5)
    };
  }
}

export class NpcData extends ForjaActorBase {
  static defineSchema() {
    return {
      ...super.defineSchema(),
      threat: new StringField({ required: true, initial: "minion", choices: ["minion", "elite", "boss"] })
    };
  }
}
```

::: tip
Deixe valores derivados como `mod` e `defense.value` **fora do schema**. Tudo que está no schema é salvo no banco. Um valor derivado salvo ali fica desatualizado e atrapalha os efeitos.
:::

## Registre

Tudo é registrado no hook `init`, antes de qualquer documento ser preparado.

```js
// systems/forja/forja.mjs
import { CharacterData, NpcData } from "./module/data/actor.mjs";
import { ForjaActor } from "./module/documents/actor.mjs";

Hooks.once("init", () => {
  CONFIG.Actor.documentClass = ForjaActor;
  CONFIG.Actor.dataModels.character = CharacterData;
  CONFIG.Actor.dataModels.npc = NpcData;

  // Atributos oferecidos como barras do token (caminhos relativos a `system`)
  CONFIG.Actor.trackableAttributes = {
    character: { bar: ["hp", "mana"], value: ["level", "defense.bonus"] },
    npc: { bar: ["hp"], value: ["defense.bonus"] }
  };
});
```

`trackableAttributes` define o que aparece nas listas "Barra 1 / Barra 2" da configuração do token. Uma entrada em `bar` precisa apontar para um objeto com `value` e `max`. Sem essa configuração, o Foundry tenta adivinhar pelo schema, e o palpite costuma incluir campos que você não quer.

### Uma classe de ator própria

O data model cuida dos dados de um único tipo. A **classe de documento** guarda a lógica comum a todos os actors e tudo que precisa do documento inteiro: seus itens, seus tokens, as mensagens no chat.

```js
// systems/forja/module/documents/actor.mjs
export class ForjaActor extends Actor {
  /** Configuração padrão do token, aplicada uma vez quando o actor é criado. */
  async _preCreate(data, options, user) {
    if ((await super._preCreate(data, options, user)) === false) return false;
    const isCharacter = this.type === "character";
    this.updateSource({
      prototypeToken: {
        actorLink: isCharacter,           // PJs compartilham uma ficha entre todos os tokens
        disposition: isCharacter
          ? CONST.TOKEN_DISPOSITIONS.FRIENDLY
          : CONST.TOKEN_DISPOSITIONS.HOSTILE,
        sight: { enabled: isCharacter },
        bar1: { attribute: "hp" },
        displayBars: CONST.TOKEN_DISPLAY_MODES.OWNER_HOVER
      }
    });
  }

  /** Dados derivados entre documentos: roda depois do prepareDerivedData do data model. */
  prepareDerivedData() {
    super.prepareDerivedData();
    // Exemplo: soma o bônus de armadura do equipamento em uso
    const armor = this.items.filter(i => i.type === "gear" && i.system.equipped);
    this.system.defense.value += armor.reduce((sum, i) => sum + (i.system.armor ?? 0), 0);
  }

  /** Nomes curtos para fórmulas: "1d20 + @str" em vez de "@abilities.str.mod". */
  getRollData() {
    const data = { ...super.getRollData() };  // copie! o super devolve o próprio this.system
    for (const [key, ability] of Object.entries(this.system.abilities)) data[key] = ability.mod;
    data.lvl = this.system.level ?? 0;
    return data;
  }
}
```

O método de rolagem depende da versão, porque a V14 trocou os roll modes por message modes:

::: v13
```js
  /** Rola um teste de atributo e publica no chat. */
  async rollAbility(key) {
    const roll = new Roll(`1d20 + @${key}`, this.getRollData());
    await roll.evaluate();
    return roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this }),
      flavor: `Teste de atributo: ${key.toUpperCase()}`
    }, { rollMode: game.settings.get("core", "rollMode") });
  }
```
:::

::: v14
```js
  /** Rola um teste de atributo e publica no chat. */
  async rollAbility(key, { messageMode } = {}) {
    const roll = new Roll(`1d20 + @${key}`, this.getRollData());
    await roll.evaluate();
    // Passe messageMode ("public" | "self" | "gm" | "blind") só se quem chamou escolheu um
    return roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this }),
      flavor: `Teste de atributo: ${key.toUpperCase()}`
    }, messageMode ? { messageMode } : {});
  }
```
:::

Na prática, o que importa é a ordem em que as etapas de `prepareData()` rodam:

::: v13
1. `system.prepareBaseData()`, depois `Actor#prepareBaseData()`
2. `prepareEmbeddedDocuments()`: os itens são preparados, depois roda `applyActiveEffects()`
3. `system.prepareDerivedData()`, depois `Actor#prepareDerivedData()`

Os efeitos alteram valores "de origem" (`system.defense.bonus`), e o passo 3 calcula os totais a partir deles. Um efeito que mira `system.defense.value` não faz nada, porque o passo 3 sobrescreve o valor.
:::

::: v14
1. `system.prepareBaseData()`, depois `Actor#prepareBaseData()`
2. `prepareEmbeddedDocuments()`: os itens são preparados, depois roda `applyActiveEffects("initial")`
3. `system.prepareDerivedData()`, depois `Actor#prepareDerivedData()`
4. As mudanças da fase `"final"` rodam **depois** dos dados derivados, então *podem* mirar valores derivados como `system.defense.value`.

Você pode registrar suas próprias fases em `CONFIG.ActiveEffect.phases` e aplicá-las onde quiser com `this.applyActiveEffects("sua-fase")`. Veja [Efeitos ativos](#active-effect).
:::

## Crie pelo código

```js
// Cria um actor com itens iniciais numa única operação no banco
const hero = await Actor.create({
  name: "Aldric",
  type: "character",
  img: "systems/forja/assets/aldric.webp",
  system: { abilities: { str: { value: 14 } }, hp: { value: 12, max: 12 } },
  items: [
    { name: "Espada Longa", type: "weapon", system: { damage: "1d8 + @str" } },
    { name: "Corda (15 m)", type: "gear" }
  ]
});

// Atualização: use caminhos com ponto dentro de `system`
await hero.update({ "system.hp.value": hero.system.hp.value - 3 });

// Vários actors de uma vez
await Actor.createDocuments([
  { name: "Goblin", type: "npc" },
  { name: "Chefe Goblin", type: "npc", system: { threat: "boss" } }
]);
```

::: warning
Nunca atribua direto, como em `actor.system.hp.value = 5`. Isso muda só a cópia preparada no *seu* cliente, e a próxima preparação sobrescreve. Sempre use `update()`.
:::

### Tokens vinculados e não vinculados

- **Vinculado** (`actorLink: true`): todos os tokens apontam para o mesmo actor do mundo. Dano no token é dano no actor. Use para PJs.
- **Não vinculado**: cada token tem um **actor sintético**, que é o actor do mundo mais um `ActorDelta` por token, guardando só as diferenças. Cinco goblins do mesmo actor mantêm cada um seus próprios PV.

```js
// token é um TokenDocument (por exemplo canvas.tokens.controlled[0].document)
const actor = token.actor;           // actor sintético para tokens não vinculados
await actor.update({ "system.hp.value": 0 }); // grava no ActorDelta do token

// Todos os tokens de um actor do mundo na cena atual
const tokens = hero.getActiveTokens(); // placeables Token
```

::: v14
```js
// V14: o delta pode ser null. Verifique antes de ler direto.
if (!token.actorLink && token.delta) {
  console.log("Campos sobrescritos:", token.delta.toObject());
}
```
:::

::: tip
Grave sempre por `token.actor` e deixe o Foundry decidir onde o dado vai parar. Código que mexe em `token.delta` diretamente é frágil.
:::

## Ficha e interface

Desde a V13 o Foundry não tem ficha de actor padrão, então você precisa registrar uma. O exemplo completo de `ActorSheetV2`, com abas, arrastar e soltar e editores, está em [Fichas](#sheets). Aqui vai o registro mínimo:

```js
Hooks.once("init", () => {
  foundry.applications.apps.DocumentSheetConfig.registerSheet(Actor, "forja", ForjaCharacterSheet, {
    types: ["character"], makeDefault: true, label: "FORJA.SheetCharacter"
  });
});
```

Um botão no template da ficha chama o método de rolagem por uma action:

```hbs
<button type="button" data-action="rollAbility" data-ability="str">FOR {{system.abilities.str.mod}}</button>
```

```js
static DEFAULT_OPTIONS = {
  actions: {
    rollAbility(event, target) { return this.document.rollAbility(target.dataset.ability); }
  }
};
```

## Receitas comuns

### Curar tudo com uma macro

```js
for (const token of canvas.tokens.controlled) {
  const { max } = token.actor.system.hp;
  await token.actor.update({ "system.hp.value": max });
}
```

### Reagir quando os PV chegam a 0

```js
Hooks.on("updateActor", (actor, changes, options, userId) => {
  if (game.user.id !== userId) return;                // roda uma vez, no cliente que fez a mudança
  const hp = foundry.utils.getProperty(changes, "system.hp.value");
  if (hp === 0) actor.toggleStatusEffect("dead", { active: true, overlay: true });
});
```

### Agrupar itens por tipo para a ficha

```js
const { weapon = [], spell = [], gear = [] } = actor.itemTypes;
```

::: v14
### Efeitos que alteram o token

Na V14 um Active Effect pode mudar propriedades do token como visão, luz, imagem, alpha, disposição, tamanho e forma. Assim uma tocha pode dar luz e um disfarce pode trocar a imagem do token. O actor junta essas mudanças por fase, e cada token dependente as aplica nos próprios `overrides`:

```js
// Veja o que os efeitos estão fazendo com os tokens (depuração)
console.log(actor.tokenActiveEffectChanges);   // { initial: [...], final: [...] }
for (const t of actor.getDependentTokens()) console.log(t.name, t.overrides);
```

A configuração do Active Effect oferece os campos do token diretamente. Para ver a `key` exata que ela grava, crie uma mudança pela interface e inspecione `effect.system.changes`. Não deixe no código uma key adivinhada.
:::

## Armadilhas

- **Tipos ausentes em `documentTypes`** fazem a criação falhar na validação. O tipo precisa estar no manifesto *e* ter um data model.
- **Devolver `this.system` em `getRollData()` e alterá-lo** corrompe os dados preparados. Faça uma cópia antes.
- **Trabalho pesado em `prepareDerivedData`**, como buscar compêndios ou usar `await`: a preparação é síncrona e roda com frequência, em todos os clientes.
- **Chamar `update()` dentro de `prepareData`** cria um loop infinito, porque cada update dispara uma nova preparação.
- **Hooks em todos os clientes**: `updateActor` dispara em todo lugar. Proteja com `userId === game.user.id` ou `game.users.activeGM?.isSelf` para o update rodar uma vez só.
- **Tokens não vinculados**: `game.actors.get(id)` devolve o actor *do mundo*, não o goblin em que você bateu. Use `token.actor`.
