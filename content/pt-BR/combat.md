# Combate e iniciativa

Configure a fórmula de iniciativa, estenda as classes de combate e de combatente, rode código no começo ou no fim de um turno e crie encontros pelo código.

::: changed
- Active Effects agora podem **expirar em eventos de combate** (`combatStart`, `roundStart`, `turnStart`, `combatEnd`, `roundEnd`, `turnEnd`) e medir a duração em `rounds` ou `turns` com o novo formato `{ value, units, expiry }`. Muitos sistemas podem apagar o próprio código de "remover o efeito no fim do turno". Veja [Efeitos ativos](#active-effect).
- `ActiveEffect.registry` acompanha os efeitos temporários e a expiração deles, então o combat tracker e os ícones do token concordam sobre o que ainda está ativo.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Um **Combat** é um documento do mundo para um encontro. Ele tem documentos **Combatant** embutidos, um por participante, cada um apontando para um token (e, por ele, para um ator). O combate guarda `round`, `turn` e se já começou (`started`); os combatentes guardam `initiative`, `defeated` e `hidden`.

O **Combat Tracker** na barra lateral é só a interface. Tudo o que ele faz (rolar iniciativa, próximo turno) é um método dos documentos, então você pode chamar os mesmos métodos pelo código.

```text
Combat (rodada 2, turno 1)
 ├─ Combatant  Aria    iniciativa 18  → Token → Actor (character)
 ├─ Combatant  Goblin  iniciativa 12  → Token → Actor (npc)   ← turno atual
 └─ Combatant  Lobo    iniciativa  7
```

## Defina a fórmula de iniciativa

A opção mais simples é o manifesto do sistema:

```json
{ "initiative": "1d20 + @abilities.agi.mod" }
```

Definir pelo código dá mais controle, como casas decimais para desempate:

```js
Hooks.once("init", () => {
  CONFIG.Combat.initiative = {
    formula: "1d20 + @abilities.agi.mod",
    decimals: 2          // usado para desempatar, aparece como 15.03
  };
});
```

As referências `@...` são resolvidas a partir de `actor.getRollData()`.

## Uma fórmula própria por combatente

Quando a fórmula depende do ator (por exemplo, NPCs rolam `1d10`), sobrescreva a classe Combatant.

```js
// systems/forja/module/documents/combatant.mjs
export class ForjaCombatant extends Combatant {
  /** Devolve a fórmula de iniciativa deste combatente. */
  _getInitiativeFormula() {
    if ( this.actor?.type === "npc" ) return "1d10 + @level";
    return super._getInitiativeFormula();   // CONFIG.Combat.initiative.formula
  }
}
```

```js
Hooks.once("init", () => {
  CONFIG.Combatant.documentClass = ForjaCombatant;
});
```

## Uma classe de combate própria

Sobrescreva `Combat` para mudar a ordem dos turnos ou aplicar regras quando turnos e rodadas mudam.

```js
// systems/forja/module/documents/combat.mjs
export class ForjaCombat extends Combat {
  /** Maior iniciativa primeiro; empates favorecem personagens sobre NPCs. */
  _sortCombatants(a, b) {
    const diff = (b.initiative ?? -Infinity) - (a.initiative ?? -Infinity);
    if ( diff ) return diff;
    return (a.actor?.type === "character" ? -1 : 1);
  }

  /** Roda uma vez, no cliente do mestre ativo, quando o turno de um combatente começa. */
  async _onStartTurn(combatant, context) {
    await super._onStartTurn(combatant, context);
    const actor = combatant.actor;
    if ( !actor ) return;
    // Recupera 1 de vigor no começo de cada turno
    const stamina = actor.system.stamina;
    if ( stamina && stamina.value < stamina.max ) {
      await actor.update({ "system.stamina.value": stamina.value + 1 });
    }
  }

  /** Roda no cliente do mestre ativo quando uma rodada termina. */
  async _onEndRound(context) {
    await super._onEndRound(context);
    ChatMessage.create({ content: `<p>${game.i18n.localize("FORJA.Combat.RoundEnd")}</p>` });
  }
}
```

```js
Hooks.once("init", () => {
  CONFIG.Combat.documentClass = ForjaCombat;
});
```

::: tip
`_onStartTurn`, `_onEndTurn`, `_onStartRound` e `_onEndRound` rodam **em um cliente só** (o do mestre ativo), que é exatamente o que você quer para atualizar o banco de dados. Hooks como `combatTurn` rodam em **todos** os clientes, então use-os para interface, não para updates.
:::

## Ganchos de combate

| Hook | Argumentos | Roda em | Use para |
|---|---|---|---|
| `combatStart` | `(combat, updateData)` | cliente que iniciou | anunciar a luta |
| `combatRound` | `(combat, updateData, options)` | cliente que avançou | avisos de rodada |
| `combatTurn` | `(combat, updateData, options)` | cliente que avançou | retorno visual |
| `combatTurnChange` | `(combat, prior, current)` | todos os clientes | reagir ao novo turno ativo |
| `preUpdateCombat` / `updateCombat` | hooks de documento | veja [Ganchos de eventos](#hooks) | controle de baixo nível |
| `deleteCombat` | `(combat, options, userId)` | todos os clientes | limpeza |

```js
Hooks.on("combatTurnChange", (combat, prior, current) => {
  const combatant = combat.combatant;           // quem está no turno agora
  if ( combatant?.isOwner ) ui.notifications.info(game.i18n.format("FORJA.Combat.YourTurn", { name: combatant.name }));
});
```

## Crie um encontro pelo código

```js
// Coloca os tokens selecionados em um combate novo e ativo na cena atual
const tokens = canvas.tokens.controlled.map(t => t.document);
const combat = await Combat.implementation.create({ scene: canvas.scene.id, active: true });
await TokenDocument.implementation.createCombatants(tokens, { combat });

await combat.rollAll();          // rola para todos que ainda não têm iniciativa
await combat.startCombat();      // rodada 1, turno 0
```

Outros métodos úteis:

```js
await combat.rollNPC();                          // só os combatentes que não são de jogadores
await combat.rollInitiative([combatantId], { formula: "1d20 + 5" });
await combat.nextTurn();
await combat.previousTurn();
await combat.nextRound();
await combat.endCombat();                        // pede confirmação e depois apaga

// A partir de um ator: adiciona os tokens dele ao combate e rola
await actor.rollInitiative({ createCombatants: true, rerollInitiative: false });
```

## Dados do combatente (opcional)

Sistemas podem dar um data model próprio aos combatentes, por exemplo para contar as ações que restam na rodada.

```json
{ "documentTypes": { "Combatant": { "base": {} } } }
```

```js
class ForjaCombatantData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    const { NumberField } = foundry.data.fields;
    return { actionsLeft: new NumberField({ required: true, integer: true, min: 0, initial: 2 }) };
  }
}

Hooks.once("init", () => {
  CONFIG.Combatant.dataModels.base = ForjaCombatantData;
});
```

## Marcadores de turno

O V13 trouxe os **marcadores de turno de combate**: uma textura animada embaixo do token que está no turno. Os usuários configuram isso nas opções do Combat Tracker. Um sistema pode fornecer uma imagem padrão por `CONFIG.Combat` (confira `CONFIG.Combat.fallbackTurnMarker` na documentação da API da sua versão).

## Efeitos que duram "até o fim do seu próximo turno"

::: v13
O V13 não tem eventos de expiração prontos. Guarde a duração em rodadas/turnos e remova os efeitos você mesmo, normalmente no `_onStartTurn`:

```js
async _onStartTurn(combatant, context) {
  await super._onStartTurn(combatant, context);
  const expired = combatant.actor?.effects.filter(e => e.duration.remaining !== null && e.duration.remaining <= 0) ?? [];
  if ( expired.length ) await combatant.actor.deleteEmbeddedDocuments("ActiveEffect", expired.map(e => e.id));
}
```
:::

::: v14
Declare isso no efeito e deixe o core cuidar:

```js
await actor.createEmbeddedDocuments("ActiveEffect", [{
  name: "Aparar",
  img: "icons/skills/melee/weapons-crossed-swords-yellow.webp",
  duration: { value: 1, units: "turns", expiry: "turnEnd" },   // termina no fim do próximo turno
  system: { changes: [{ key: "system.defense", type: "add", value: "2" }] }
}]);
```

Os eventos de expiração vêm de `CONST.ACTIVE_EFFECT_EXPIRY_EVENTS`. Sistemas e módulos podem definir outros eventos, mas aí precisam tratá-los.
:::

## Personalize o registro de combate

O tracker é uma ApplicationV2 no V13 e no V14. Para acrescentar um elemento pequeno em cada linha, use o hook de renderização com o `HTMLElement` que ele passa:

```js
Hooks.on("renderCombatTracker", (app, html, context) => {
  for ( const li of html.querySelectorAll("[data-combatant-id]") ) {
    const combatant = app.viewed?.combatants.get(li.dataset.combatantId);
    const left = combatant?.system?.actionsLeft;
    if ( left === undefined ) continue;
    li.querySelector(".token-name")?.insertAdjacentHTML("beforeend", `<span class="forja-actions">${left}⚔</span>`);
  }
});
```

Para mudanças maiores, crie uma subclasse do tracker e defina `CONFIG.ui.combat` com a sua classe no `init`.

## Armadilhas

- **Atualizar documentos no `combatTurn`**: todos os clientes rodam o hook, então você ganha um update por usuário conectado. Use `_onStartTurn` ou confira `game.user.isActiveGM`.
- **Combatentes sem token**: combatentes podem existir sem token (ou com um token apagado). Sempre use `combatant.actor?.`.
- **Desempate**: sem `decimals`, os empates ficam na ordem de inserção, que os jogadores enxergam como aleatória.
