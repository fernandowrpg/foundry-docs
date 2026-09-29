# Efeitos ativos

Bônus, condições e efeitos de itens que alteram os dados do ator durante a preparação. É a entidade que mais mudou entre o V13 e o V14.

::: changed
- **As mudanças trocaram de lugar:** `effect.changes` → `effect.system.changes`. O `mode` numérico virou um `type` em texto (`"add"`, `"subtract"`, `"multiply"`, `"override"`, `"upgrade"`, `"downgrade"`, `"custom"`). O core migra os dados do mundo. O código e os arquivos-fonte dos compêndios você precisa atualizar.
- **Fases:** toda mudança tem uma `phase` (`"initial"` ou `"final"`, mais as fases que você registrar). `Actor#applyActiveEffects(phase)`.
- **Duração:** `{ seconds, rounds, turns, startRound... }` → `{ value, units, expiry, expired }`. **Eventos de expiração** prontos (`combatStart`, `roundStart`, `turnStart`, `combatEnd`, `roundEnd`, `turnEnd`) são acompanhados por `ActiveEffect.registry`.
- **Documentos primários:** efeitos podem ficar na barra lateral e em compêndios, e podem ser soltos em um Token para valer no ator dele.
- **Mudanças no token:** efeitos podem alterar visão, luz, imagem, alpha, disposição, tamanho e forma do token.
- `CONFIG.statusEffects` é um **objeto** indexado por id (arrays ainda funcionam). `CONFIG.ActiveEffect.legacyTransferral` foi **removido**.
- Novo **comportamento de Region** "Active Effect" aplica efeitos aos tokens que entram em uma região.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Um **Active Effect** é um conjunto nomeado de *mudanças* ("+1 em força", "defesa vira 18") com duração e status opcionais. Os efeitos ficam embutidos em um **Actor** (e valem para ele) ou em um **Item** (com `transfer: true` eles valem para o dono do item, veja [Itens](#item)).

A ideia central: efeitos **nunca gravam no banco de dados**. Durante a preparação dos dados, o Foundry pega os dados-fonte do ator, aplica cada mudança ativa em memória e guarda o que mudou em `actor.overrides`. Desative ou apague o efeito e o valor volta na hora. Em que momento da preparação os efeitos rodam está descrito em [Atores](#actor).

## Defina o tipo (modelo de dados)

O formato de uma *mudança* é onde as versões diferem.

::: v13
```js
// Uma mudança no V13, guardada em effect.changes (array)
{
  key: "system.abilities.str.bonus",       // caminho do dado no ator
  mode: CONST.ACTIVE_EFFECT_MODES.ADD,      // número, veja a tabela
  value: "2",                               // sempre texto
  priority: null                            // null → mode * 10
}
```

| `CONST.ACTIVE_EFFECT_MODES` | Valor | Efeito |
|---|---|---|
| `CUSTOM` | 0 | Seu código decide, pelo hook `applyActiveEffect` |
| `MULTIPLY` | 1 | `atual * valor` |
| `ADD` | 2 | `atual + valor` (use `-2` para subtrair; em arrays, acrescenta) |
| `DOWNGRADE` | 3 | `min(atual, valor)` |
| `UPGRADE` | 4 | `max(atual, valor)` |
| `OVERRIDE` | 5 | substitui por `valor` |

Duração (tudo opcional): `{ startTime, seconds, combat, rounds, turns, startRound, startTurn }`.
:::

::: v14
```js
// Uma mudança no V14, guardada em effect.system.changes (array)
{
  key: "system.abilities.str.bonus",       // caminho do dado no alvo
  type: "add",                              // texto, veja a tabela
  value: 2,                                 // desserializado: JSON se for válido, senão texto
  phase: "initial",                         // "initial" | "final" | uma fase registrada
  priority: null                            // null → prioridade padrão do tipo
}
```

| `type` | Prioridade padrão (`CONST.ACTIVE_EFFECT_CHANGE_TYPES`) | Efeito |
|---|---|---|
| `custom` | 0 | Seu código decide, pelo hook `applyActiveEffect` |
| `multiply` | 10 | `atual * valor` |
| `add` | 20 | `atual + valor` |
| `subtract` | 20 | `atual - valor` |
| `downgrade` | 30 | `min(atual, valor)` |
| `upgrade` | 40 | `max(atual, valor)` |
| `override` | 50 | substitui por `valor` |

Fases (`CONST.ACTIVE_EFFECT_CHANGE_PHASES`): cada fase é um grupo de prioridade próprio. Toda mudança `initial` roda antes de qualquer mudança `final`, sejam quais forem as prioridades. As mudanças `final` rodam depois dos dados derivados, então podem mirar valores derivados.

Duração: `{ value, units, expiry, expired }`. `units` é um de `CONST.ACTIVE_EFFECT_DURATION_UNITS` (`years`, `months`, `days`, `hours`, `minutes`, `seconds`, `rounds`, `turns`). `expiry` é o id de um evento ou `null`. O efeito expira quando **as duas coisas** acontecem: a duração acabou **e** o evento de expiração ocorreu. Com `value: null` e `expiry: null` o efeito dura para sempre.
:::

### Um tipo de efeito próprio

Efeitos têm os campos `type` e `system`, como atores e itens. Declare um tipo no manifesto para guardar dados extras, como o número de acúmulos:

```json
{ "documentTypes": { "ActiveEffect": { "buff": {} } } }
```

::: v13
```js
// systems/forja/module/data/effect.mjs
const { NumberField, BooleanField } = foundry.data.fields;

export class BuffData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      stacks: new NumberField({ required: true, integer: true, min: 1, initial: 1 }),
      dispellable: new BooleanField({ initial: true })
    };
  }
}
```
:::

::: v14
No V14 o data model do efeito **é dono das mudanças**. Estenda `foundry.data.ActiveEffectTypeDataModel` e mantenha o schema dele. Você pode redefinir `changes`, mas precisa manter `type`, `phase` e `priority`.

```js
// systems/forja/module/data/effect.mjs
const { NumberField, BooleanField } = foundry.data.fields;

export class BuffData extends foundry.data.ActiveEffectTypeDataModel {
  static defineSchema() {
    return {
      ...super.defineSchema(),               // mantém `changes`
      stacks: new NumberField({ required: true, integer: true, min: 1, initial: 1 }),
      dispellable: new BooleanField({ initial: true })
    };
  }
}
```
:::

## Registre

```js
// systems/forja/forja.mjs
import { BuffData } from "./module/data/effect.mjs";
import { ForjaActiveEffect } from "./module/documents/effect.mjs";

Hooks.once("init", () => {
  CONFIG.ActiveEffect.documentClass = ForjaActiveEffect;   // veja "Itens" para isSuppressed
  CONFIG.ActiveEffect.dataModels.buff = BuffData;
});
```

::: v13
```js
Hooks.once("init", () => {
  // Sistemas novos: mantenha os efeitos transferidos no próprio item
  CONFIG.ActiveEffect.legacyTransferral = false;

  // Status effects: um ARRAY de { id, name, img, ...dados do efeito }
  CONFIG.statusEffects = [
    ...CONFIG.statusEffects.filter(s => ["dead", "prone", "blind"].includes(s.id)),
    {
      id: "stunned",
      name: "FORJA.Status.Stunned",
      img: "systems/forja/icons/stunned.svg",
      changes: [{ key: "system.defense.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "-2" }]
    }
  ];
});
```
:::

::: v14
```js
Hooks.once("init", () => {
  // Status effects: um OBJETO indexado por id (arrays ainda são aceitos)
  const keep = ["dead", "prone", "blind"];
  for (const id of Object.keys(CONFIG.statusEffects)) if (!keep.includes(id)) delete CONFIG.statusEffects[id];
  CONFIG.statusEffects.stunned = {
    id: "stunned",
    name: "FORJA.Status.Stunned",
    img: "systems/forja/icons/stunned.svg",
    system: { changes: [{ key: "system.defense.bonus", type: "subtract", value: 2, phase: "initial" }] }
  };

  // Opcional: uma fase própria e um evento de expiração próprio
  CONFIG.ActiveEffect.phases["forja-armor"] = { label: "FORJA.Phase.Armor", hint: "FORJA.Phase.ArmorHint" };
  CONFIG.ActiveEffect.expiryEvents["forja.rest"] = "FORJA.Expiry.Rest";
});
```
:::

## Crie pelo código

Uma bênção de 3 rodadas em um ator, mais uma condição permanente baseada em status:

::: v13
```js
const actor = game.actors.getName("Aldric");

await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Bênção",
  img: "icons/magic/holy/prayer-hands-glowing-yellow.webp",
  type: "buff",
  system: { stacks: 1 },
  origin: someSpell.uuid,                   // de onde veio (opcional)
  duration: { rounds: 3 },                  // rodada/turno inicial são preenchidos durante o combate
  statuses: ["blessed"],
  changes: [
    { key: "system.abilities.str.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "1" },
    { key: "system.defense.bonus", mode: CONST.ACTIVE_EFFECT_MODES.UPGRADE, value: "2" }
  ]
}]);

// Liga/desliga um status configurado (cria ou apaga o efeito)
await actor.toggleStatusEffect("stunned");
await actor.toggleStatusEffect("dead", { active: true, overlay: true });
actor.statuses.has("stunned");            // Set com os ids de status ativos
```

::: warning
O V13 **não remove efeitos expirados** sozinho. `duration.remaining` faz a contagem regressiva, mas apagar fica por conta do seu sistema ou de um módulo. Veja "Expirar efeitos" abaixo.
:::
:::

::: v14
```js
const actor = game.actors.getName("Aldric");

await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Bênção",
  img: "icons/magic/holy/prayer-hands-glowing-yellow.webp",
  type: "buff",
  origin: someSpell.uuid,                   // DocumentUUIDField
  duration: { value: 3, units: "rounds", expiry: "turnEnd" },
  statuses: ["blessed"],
  system: {
    stacks: 1,
    changes: [
      { key: "system.abilities.str.bonus", type: "add", value: 1, phase: "initial" },
      // "final" roda depois do prepareDerivedData, então pode mirar o total derivado
      { key: "system.defense.value", type: "upgrade", value: 14, phase: "final" }
    ]
  }
}]);

// "Até o fim do combate", não importa quantas rodadas
await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Fúria", duration: { value: null, units: "rounds", expiry: "combatEnd" },
  system: { changes: [{ key: "system.abilities.str.bonus", type: "add", value: 2, phase: "initial" }] }
}]);

// Status effects
await actor.toggleStatusEffect("stunned");
const data = await ActiveEffect.fromStatusEffect("stunned");  // um ActiveEffect que você pode ajustar
actor.statuses.has("stunned");

// Um efeito primário (da barra lateral): sem pai. O mestre pode arrastá-lo para um token.
await ActiveEffect.create({ name: "Envenenado", img: "icons/svg/poison.svg" });
```

Quando um efeito expira, `ActiveEffect.registry` age conforme `CONFIG.ActiveEffect.expiryAction` (`"update"`, `"delete"` ou `null`).
:::

### Lógica de mudança própria

Com `CUSTOM` / `"custom"`, o core não faz nada e dispara o hook `applyActiveEffect` (mesma assinatura nas duas versões). Coloque o que deve ser gravado no acumulador `changes`. Este exemplo soma uma fórmula avaliada com os dados de rolagem do ator:

::: v13
```js
Hooks.on("applyActiveEffect", (actor, change, current, delta, changes) => {
  if (!change.key.startsWith("system.") || !String(change.value).startsWith("formula:")) return;
  const formula = Roll.replaceFormulaData(change.value.slice(8), actor.getRollData());
  changes[change.key] = Number(current) + Roll.safeEval(formula);
});
// Mudança: { key: "system.hp.max", mode: CONST.ACTIVE_EFFECT_MODES.CUSTOM, value: "formula:@lvl * 2" }
```
:::

::: v14
```js
Hooks.on("applyActiveEffect", (actor, change, current, delta, changes) => {
  if (!change.key.startsWith("system.") || !String(change.value).startsWith("formula:")) return;
  const formula = Roll.replaceFormulaData(change.value.slice(8), actor.getRollData());
  changes[change.key] = Number(current) + Roll.safeEval(formula);
});
// Mudança: { key: "system.hp.max", type: "custom", value: "formula:@lvl * 2", phase: "initial" }
```

::: tip
O V14 já resolve expressões com `@` em valores de texto por meio de `ActiveEffect#getReplacementData`. Antes de escrever código próprio, tente uma mudança `add` simples com o valor `"@lvl"`. Tipos de mudança próprios também podem ser registrados em `CONFIG.ActiveEffect.changeTypes`. Veja na [API](https://foundryvtt.com/api/v14/) o formato de `ActiveEffectChangeTypeConfig`.
:::
:::

::: v14
### Migrando dados no formato do V13 para o V14

O core migra os documentos do mundo e dos compêndios quando eles carregam. O **seu** código e os seus arquivos JSON, como os arrays `changes` nos arquivos-fonte dos packs, geradores e macros, ainda precisam do formato novo. Use este helper:

```js
const MODE_TO_TYPE = { 0: "custom", 1: "multiply", 2: "add", 3: "downgrade", 4: "upgrade", 5: "override" };
const DURATION_UNITS = ["seconds", "turns", "rounds"];   // campos do V13, verificados nesta ordem

/** Converte dados-fonte de ActiveEffect do V13 para o formato do V14. Devolve um objeto novo. */
export function effectToV14(data) {
  const out = foundry.utils.deepClone(data);
  const changes = out.changes ?? [];
  delete out.changes;
  out.system ??= {};
  out.system.changes = changes.map(c => ({
    key: c.key,
    type: MODE_TO_TYPE[c.mode] ?? "add",
    value: c.value,
    phase: "initial",                          // comportamento do V13 = antes dos dados derivados
    priority: c.priority ?? null
  }));

  const d = out.duration ?? {};
  const unit = DURATION_UNITS.find(u => Number.isFinite(d[u]) && d[u] > 0);
  out.duration = unit ? { value: d[unit], units: unit, expiry: null } : { value: null, units: "seconds", expiry: null };
  return out;
}

// Suportando as duas versões em um único módulo:
const effectData = game.release.generation >= 14 ? effectToV14(v13Data) : v13Data;
```
:::

## Ficha e interface

O core traz a ficha `ActiveEffectConfig` (`effect.sheet.render(true)`). A sua ficha de ator normalmente lista os efeitos com botões de ligar/desligar e apagar:

```hbs
<ul class="effects">
  {{#each effects as |effect|}}
  <li data-effect-id="{{effect.id}}" data-parent-uuid="{{effect.parent.uuid}}" class="{{#if effect.disabled}}disabled{{/if}}">
    <img src="{{effect.img}}" width="24" height="24"> {{effect.name}}
    <a data-action="toggleEffect"><i class="fa-solid fa-power-off"></i></a>
    <a data-action="editEffect"><i class="fa-solid fa-pen"></i></a>
  </li>
  {{/each}}
</ul>
```

```js
// Na sua subclasse de ActorSheetV2
static DEFAULT_OPTIONS = {
  actions: {
    async toggleEffect(event, target) {
      const effect = await ForjaCharacterSheet.#getEffect(target);
      return effect?.update({ disabled: !effect.disabled });
    },
    async editEffect(event, target) {
      (await ForjaCharacterSheet.#getEffect(target))?.sheet.render(true);
    }
  }
};

static async #getEffect(target) {
  const { effectId, parentUuid } = target.closest("[data-effect-id]").dataset;
  const parent = await fromUuid(parentUuid);            // o ator, ou um item no caso de efeitos transferidos
  return parent?.effects.get(effectId);
}

async _prepareContext(options) {
  const context = await super._prepareContext(options);
  context.effects = [...this.actor.allApplicableEffects()];   // inclui os efeitos dos itens
  return context;
}
```

## Receitas comuns

### Expirar efeitos

::: v13
Remova os efeitos cuja duração acabou sempre que o combate avançar. Só o mestre roda isto:

```js
Hooks.on("updateCombat", async (combat, changes) => {
  if (!game.user.isActiveGM || !("turn" in changes || "round" in changes)) return;
  for (const combatant of combat.combatants) {
    const actor = combatant.actor;
    const expired = actor?.temporaryEffects.filter(e => e.duration.remaining <= 0) ?? [];
    for (const effect of expired) await effect.delete();
  }
});
```
:::

::: v14
O core faz isso por você. Para o seu evento próprio `forja.rest`, você mesmo dispara a expiração:

```js
async function shortRest(actor) {
  const ids = actor.effects.filter(e => e.duration.expiry === "forja.rest").map(e => e.id);
  await actor.deleteEmbeddedDocuments("ActiveEffect", ids);
}
```
:::

### Ler o valor final e quem o alterou

```js
actor.system.abilities.str.bonus;                       // depois dos efeitos
actor.overrides;                                        // { "system.abilities.str.bonus": 1, ... }
[...actor.allApplicableEffects()].filter(e => e.active); // efeitos que estão valendo agora
```

::: v14
### Efeitos vindos de regiões e de arrastar

Adicione um comportamento **Active Effect** a uma Region da cena para aplicar os efeitos escolhidos aos tokens que entram nela, como uma nuvem de veneno ou uma área abençoada. O mestre também pode arrastar um efeito da barra lateral ou de um compêndio para um Token. As duas coisas funcionam sem código. Para pós-processar, use os hooks `preCreateActiveEffect` / `createActiveEffect`.
:::

## Armadilhas

- **Mirar valores derivados.** Os efeitos no V13, e a fase `initial` no V14, rodam *antes* do `prepareDerivedData`. Mire um campo gravado, como `bonus`, ou use a fase `final` no V14.
- **Erros de digitação na chave falham em silêncio.** Uma `key` errada simplesmente não faz nada. Confira `actor.overrides`.
- **No V13 os valores são texto.** `"2"` é convertido conforme o tipo do campo alvo. Para arrays e objetos, o valor precisa ser JSON válido.
- **Efeitos transferidos** valem a partir do item. Não procure por eles em `actor.effects`. Use `allApplicableEffects()`.
- **Misturar formatos:** código do V14 que grava `changes` no nível de cima, ou `mode`, cria efeitos sem mudanças. Use o `effectToV14()` acima.
- **Expirar em todos os clientes.** No V13, apague os efeitos expirados só no mestre ativo, senão cada cliente conectado vai tentar apagar.
