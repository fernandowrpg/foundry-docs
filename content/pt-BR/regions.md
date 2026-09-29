# Regiões e áreas de efeito

As regiões da cena são áreas com forma que reagem a tokens por meio de comportamentos; no V14 elas também substituem os modelos de medição nas áreas de efeito.

::: changed
- **O MeasuredTemplate foi removido.** Áreas de efeito agora são **Template Regions**: regiões com as novas formas `line`, `cone`, `ring`, `emanation`, `token` e `grid`.
- Regiões podem ser **presas a um token** (`RegionDocument#attachment.token`) e acompanhá-lo; `RegionDocument.createTokenEmanation()` cria uma.
- `RegionLayer#placeRegion()` / `#placeRegions()` para posicionamento interativo (`attachToToken`, `onChange`, `allowEmpty`, ...).
- Novos comportamentos: **Active Effect** (aplica efeitos aos tokens dentro) e **Change Level** (troca de nível).
- `RegionDocument#teleportTokens()` e `#spawnTokens()`; as regiões têm um campo `ownership` e uma nova permissão `REGION_CREATE`.
- `RegionShape` está obsoleto em favor das subclasses de `BaseShapeData`.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Uma **Region** (`RegionDocument`, embutida em uma Scene) é um conjunto de formas mais uma faixa de elevação.
Sozinha ela não faz nada. Você adiciona **Region Behaviors** (documentos `RegionBehavior`, embutidos
na Region) que escutam **eventos**, como um token entrando, um turno de combate começando dentro
da área ou o comportamento sendo ativado.

Usos típicos: armadilhas, terreno difícil, escadas/teletransportes, zonas de escuridão, "pausar o jogo quando
alguém abrir esta porta" e (V14) áreas de magia.

## Formas e eventos

As formas básicas de região são `rectangle`, `circle`, `ellipse` e `polygon` (o V14 acrescenta as formas
de template abaixo), e qualquer forma pode ser um buraco (`hole`). As regiões têm `elevation: { bottom, top }` (`null` significa infinito).

```js
// Uma armadilha cobrindo 3x3 espaços do grid, começando no pixel (500, 500)
const size = canvas.grid.size;
const [region] = await canvas.scene.createEmbeddedDocuments("Region", [{
  name: "Fosso de estacas",
  color: "#aa3322",
  shapes: [{ type: "rectangle", x: 500, y: 500, width: 3 * size, height: 3 * size, rotation: 0, hole: false }],
  elevation: { bottom: null, top: 0 },
  visibility: CONST.REGION_VISIBILITY.GAMEMASTER
}]);
```

Os eventos que um comportamento pode escutar estão em `CONST.REGION_EVENTS`:

| Chave | Valor | Dispara quando |
| --- | --- | --- |
| `TOKEN_ENTER` / `TOKEN_EXIT` | `tokenEnter` / `tokenExit` | um token entra/sai (depois do update) |
| `TOKEN_MOVE_IN` / `TOKEN_MOVE_OUT` / `TOKEN_MOVE_WITHIN` | `tokenMoveIn` ... | um segmento de movimento cruza a região ou fica nela |
| `TOKEN_ANIMATE_IN` / `TOKEN_ANIMATE_OUT` | `tokenAnimateIn` ... | a *animação* do token cruza a borda |
| `TOKEN_TURN_START` / `TOKEN_TURN_END` | `tokenTurnStart` ... | um combatente dentro começa/termina o turno |
| `TOKEN_ROUND_START` / `TOKEN_ROUND_END` | `tokenRoundStart` ... | uma rodada de combate começa/termina com o token dentro |
| `REGION_BOUNDARY` | `regionBoundary` | a forma ou a elevação da região mudou |
| `BEHAVIOR_ACTIVATED` / `BEHAVIOR_DEACTIVATED` | `behaviorActivated` ... | o comportamento foi ativado/desativado ou criado/apagado |
| `BEHAVIOR_VIEWED` / `BEHAVIOR_UNVIEWED` | `behaviorViewed` ... | a cena começou/parou de ser visualizada |

## Comportamentos prontos

O core traz comportamentos que você configura sem código: **Adjust Darkness Level**, **Display Scrolling
Text**, **Execute Macro**, **Execute Script**, **Pause Game**, **Suppress Weather**, **Teleport
Token**, **Toggle Behavior** e **Modify Movement Cost** (V13+, dificuldade por ação de movimento).

::: v14
O V14 acrescenta **Change Level** (escadas, escadas de mão e elevadores entre [Níveis de cena](#scene-token--niveis-de-cena))
e **Active Effect**, que aplica Active Effects aos tokens enquanto eles estão dentro da região.
:::

## Defina um tipo de comportamento próprio (modelo de dados)

Um tipo de comportamento é uma subclasse `TypeDataModel` de `foundry.data.regionBehaviors.RegionBehaviorType`.
Há duas formas de tratar eventos:

- `static events = { [nomeDoEvento]: handler }`: eventos que o tipo trata **sempre**.
- Um campo `events` no schema (criado com `this._createEventsField()`): eventos que o **usuário**
  escolhe na ficha de configuração; eles são enviados para `_handleRegionEvent(event)`.

```js
// modules/forja-extras/scripts/trap-behavior.mjs
const { fields } = foundry.data;

export class TrapBehaviorType extends foundry.data.regionBehaviors.RegionBehaviorType {
  static LOCALIZATION_PREFIXES = ["FORJA_EXTRAS.Trap"];

  static defineSchema() {
    return {
      // Deixa o mestre escolher quais eventos disparam a armadilha; padrão: entrar
      events: this._createEventsField({
        events: [
          CONST.REGION_EVENTS.TOKEN_ENTER,
          CONST.REGION_EVENTS.TOKEN_TURN_START
        ],
        initial: [CONST.REGION_EVENTS.TOKEN_ENTER]
      }),
      damage: new fields.StringField({ required: true, blank: false, initial: "2d6" }),
      once: new fields.BooleanField({ initial: true })
    };
  }

  /** @override */
  async _handleRegionEvent(event) {
    // Comportamentos rodam em TODOS os clientes. Deixe só o mestre ativo agir: o mestre pode
    // atualizar o ator E o comportamento, que o jogador que se moveu talvez não possua
    if (!game.users.activeGM?.isSelf) return;
    const token = event.data.token;
    const actor = token?.actor;
    if (!actor) return;

    const roll = await new Roll(this.damage).evaluate();
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ token }),
      flavor: game.i18n.format("FORJA_EXTRAS.Trap.Triggered", { name: token.name })
    });
    const hp = actor.system.hp;
    await actor.update({ "system.hp.value": Math.max(hp.value - roll.total, 0) });

    // Desativa o comportamento depois do primeiro disparo
    if (this.once) await this.parent.update({ disabled: true });
  }
}
```

`this.parent` é o documento `RegionBehavior` e `this.region` é o `RegionDocument`.
`event` tem `name`, `data`, `region` e `user`; nos eventos de token, `event.data.token` é o
`TokenDocument` (eventos de movimento também trazem `event.data.movement`).

## Registre

Declare o subtipo no manifesto e conecte o data model no `init`. Subtipos de módulo recebem
o id do módulo como namespace, então a chave do tipo é `forja-extras.trap`.

```json
{
  "id": "forja-extras",
  "documentTypes": {
    "RegionBehavior": {
      "trap": {}
    }
  }
}
```

```js
// modules/forja-extras/scripts/main.mjs
import { TrapBehaviorType } from "./trap-behavior.mjs";

Hooks.once("init", () => {
  CONFIG.RegionBehavior.dataModels["forja-extras.trap"] = TrapBehaviorType;
  CONFIG.RegionBehavior.typeIcons["forja-extras.trap"] = "fa-solid fa-burst";
});
```

```json
{
  "TYPES": { "RegionBehavior": { "forja-extras.trap": "Armadilha" } },
  "FORJA_EXTRAS": {
    "Trap": {
      "FIELDS": {
        "damage": { "label": "Dano", "hint": "Fórmula de rolagem aplicada ao token." },
        "once": { "label": "Uso único" }
      },
      "Triggered": "{name} ativa uma armadilha!"
    }
  }
}
```

A ficha de configuração do comportamento é gerada automaticamente a partir do schema.

## Crie pelo código

```js
await region.createEmbeddedDocuments("RegionBehavior", [{
  name: "Estacas",
  type: "forja-extras.trap",
  system: { damage: "3d6", once: false }
}]);
```

## Áreas de efeito

::: v13
### `MeasuredTemplate` (V13)

No V13 as áreas de magia são documentos `MeasuredTemplate` embutidos na Scene. `t` é um de
`CONST.MEASURED_TEMPLATE_TYPES`: `"circle"`, `"cone"`, `"rect"`, `"ray"`. `distance` fica nas
unidades da cena, `direction` e `angle` em graus. O ângulo padrão do cone e a largura do raio ficam em
`CONFIG.MeasuredTemplate.defaults`.

```js
/** Cria um cone de 6 m à frente do token de quem conjura */
async function castCone(token) {
  const [template] = await canvas.scene.createEmbeddedDocuments("MeasuredTemplate", [{
    t: CONST.MEASURED_TEMPLATE_TYPES.CONE,
    x: token.center.x,
    y: token.center.y,
    distance: 6,
    angle: 60,
    direction: token.document.rotation + 90,
    fillColor: game.user.color.css,
    flags: { forja: { spell: "fire-breath" } }
  }]);
  return template;
}

// Quais tokens estão dentro? Testa o centro dos tokens contra a forma do template
function tokensInTemplate(templateDoc) {
  const t = templateDoc.object;
  return canvas.tokens.placeables.filter(tok =>
    t.shape.contains(tok.center.x - templateDoc.x, tok.center.y - templateDoc.y));
}
```
:::

::: v14
### Regiões de área de efeito (V14)

O documento `MeasuredTemplate` não existe mais. Uma área de efeito é uma Region que usa as
formas de template (`circle`, `cone`, `line`, `ring`, `emanation`, `token`, `grid`). Por ser uma
região, ela pode ter comportamentos: o comportamento **Active Effect** aplica uma condição a tudo
que está dentro, e `region.tokens` diz quem está na área.

O jeito mais fácil e robusto é o posicionamento interativo: o usuário posiciona a forma e o core
cuida do encaixe no grid, da rotação e da pré-visualização.

```js
/** Deixa o usuário posicionar um cone de fogo; a região é criada ao confirmar */
async function castCone(token) {
  const region = await canvas.regions.placeRegion({
    name: "Sopro de fogo",
    color: game.user.color.css,
    shapes: [{ type: "cone" }],
    flags: { forja: { spell: "fire-breath" } }
  }, {
    attachToToken: false,
    onChange: (data) => { /* pré-visualização ao vivo: reaja às mudanças da forma */ }
  });
  if (!region) return null;           // cancelado
  return [...region.tokens];          // TokenDocuments dentro da área
}
```

::: warning
Os nomes dos campos de cada forma (raio, ângulo, largura, ...) são definidos pela subclasse de
`BaseShapeData` dela (por exemplo `foundry.data.ConeShapeData`). Confira a API do V14 antes de escrever
os dados da forma na mão; na dúvida, deixe o `placeRegion` preencher.
:::

Uma **emanação** que acompanha um token (auras) é criada com `RegionDocument.createTokenEmanation()`
ou definindo `attachment.token` com o id do token; a região passa a se mover com o token.

`RegionDocument#teleportTokens(tokens, options)` move tokens para dentro de uma região (opções
`placement: "center" | "relative" | "random"`, `avoidOccupied`, `snap`, `level`), e
`RegionDocument#spawnTokens(tokenData, options)` cria tokens lá (`create: false` devolve
documentos efêmeros, não salvos).

Os jogadores precisam da nova permissão `REGION_CREATE` para criar regiões, e o `ownership` da
região controla quem pode editá-la.
:::

::: v14
## Migrando uma área de efeito para uma região

1. Troque `createEmbeddedDocuments("MeasuredTemplate", ...)` por `canvas.regions.placeRegion()`
   (interativo) ou `createEmbeddedDocuments("Region", ...)` (dados fixos).
2. Mova `t`/`distance`/`direction`/`angle` para uma única entrada em `shapes`, usando os tipos de forma do V14.
3. Troque o seu cálculo de "quem está no template" por `region.tokens` ou
   `tokenDoc.testInsideRegion(region)`.
4. Troque os hooks em `createMeasuredTemplate` por `createRegion` (confira a sua flag, por exemplo
   `region.getFlag("forja", "spell")`).
5. Troque efeitos contínuos feitos à mão por um comportamento **Active Effect**.
6. Remova toda referência a `CONFIG.MeasuredTemplate`, `canvas.templates` e à classe
   `MeasuredTemplate`. Antes de publicar, teste em uma cópia do mundo a migração de mundos antigos
   que ainda têm templates.
:::

## Receitas comuns

```js
// Um token está dentro de uma região agora?
const inside = tokenDoc.testInsideRegion(region);

// Todas as regiões que contêm um token
console.log([...tokenDoc.regions].map(r => r.name));

// Teletransporta um token para uma região de destino
await destination.teleportToken(tokenDoc);
```

## Armadilhas

::: warning
- Os eventos de região são enviados a **todos** os clientes. Proteja com `game.users.activeGM?.isSelf`
  (o mestre faz o trabalho) ou `event.user.isSelf` (quem causou o evento faz), senão a sua armadilha
  dispara uma vez por jogador conectado.
- Um jogador não pode atualizar documentos que não possui: se um comportamento precisa atualizar a região, o ator ou
  a cena quando um jogador se move, mande a mudança para o mestre por uma [consulta ou socket](#sockets).
- `TOKEN_ENTER` dispara depois que o update do token é salvo. Se você precisa reagir *durante* o
  movimento (por exemplo, para parar o token na borda com `tokenDoc.stopMovement()`), use a
  família `TOKEN_MOVE_IN`.
- Esquecer o `documentTypes` no manifesto faz `type: "forja-extras.trap"` ser rejeitado como inválido.
:::
