# Cenas e Tokens

Como as cenas descrevem um mapa, como o documento do token e o token desenhado na tela se relacionam, e como criar e mover tokens por código.

::: changed
- **Níveis de cena (Scene Levels)**: uma Scene pode empilhar vários documentos `Level` (cada um com seu próprio fundo, primeiro plano, névoa e faixa de elevação). Tokens pertencem a um nível (`TokenDocument#level`).
- **Movimento planejado**: `Token#planMovement()`, `Scene#moveTokens()` e `TokenLayer#placeTokens()` são novos.
- `TokenDocument#move()` agora resolve quando o movimento **termina**, e não quando a primeira atualização é gravada.
- Novos auxiliares de origem: `getMovementOrigin`, `getVisionOrigin`, `getLightOrigin`, `getSoundOrigin`; tokens têm `depth`.
- `Scene#activate({ viewOptions, pullUsers })`, transições de cena, `CanvasShakeEffect` e `ParticleGenerator` (VFX).
- `ignoreWalls/ignoreCost/history` de `TokenFindMovementPathOptions` foram descontinuados em favor de `constrainOptions`.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Uma **Scene** é um documento que descreve um mapa: tamanho, grade, imagem de fundo, iluminação e
todos os objetos colocados nele. Esses objetos são *documentos embutidos* da Scene: `Token`,
`Tile`, `Wall`, `AmbientLight`, `AmbientSound`, `Note`, `Drawing`, `Region` (e, na V13,
`MeasuredTemplate`).

Para cada documento embutido existem **dois** objetos que você vai encontrar:

| Objeto | Classe | Onde vive | Para que serve |
| --- | --- | --- | --- |
| `TokenDocument` | `foundry.documents.TokenDocument` | no banco de dados, em todos os clientes | dados: posição, imagem, vínculo com o ator, movimento |
| `Token` (placeable) | `foundry.canvas.placeables.Token` | no canvas, apenas na cena *visualizada* | desenho, interação com o mouse, animação |

Passe de um para o outro com `tokenDoc.object` (pode ser `null` quando a cena não está sendo
visualizada) e `token.document`. A regra prática: **leia e grave dados pelo documento; use o
placeable só para coisas visuais.** Atualizações no documento são replicadas para todos os
clientes; mudanças feitas no placeable são locais e se perdem no próximo redesenho.

```js
// Pontos de entrada úteis
game.scenes.active;          // a Scene para onde os jogadores são puxados
game.scenes.viewed;          // a Scene que este cliente está vendo (igual a canvas.scene)
canvas.tokens.controlled;    // placeables Token que o usuário selecionou
canvas.tokens.placeables;    // todos os placeables Token da cena visualizada
actor.getActiveTokens();     // placeables deste ator na cena visualizada
canvas.scene.tokens;         // EmbeddedCollection de TokenDocuments
```

## Dados da cena: grade, fundo e dimensões

Os campos importantes da Scene são `width`, `height`, `padding`, `grid` (`type`, `size`,
`distance`, `units`), `background` (`src`, ...), `initial` (visão inicial) e `tokenVision`.
A geometria derivada em pixels fica em `scene.dimensions`, calculada durante a preparação de dados.

```js
// Criar uma Scene por código
const scene = await Scene.create({
  name: "Arena da Forja",
  width: 3000,
  height: 2000,
  padding: 0.1,
  grid: { type: CONST.GRID_TYPES.SQUARE, size: 100, distance: 1.5, units: "m" },
  background: { src: "systems/forja/assets/maps/arena.webp" },
  tokenVision: true
});

const d = scene.dimensions;
console.log(d.sceneRect);      // Retângulo da área jogável (sem o padding)
console.log(d.size, d.distance, d.distancePixels); // tamanho da grade em px, unidades por quadrado, px por unidade
```

`scene.view()` mostra a cena apenas *neste* cliente. `scene.activate()` (GM) a marca como ativa e
puxa todos os jogadores para ela.

::: v14
Na V14, `Scene#activate` aceita opções: `pullUsers` e `viewOptions` (as mesmas opções de
`Scene#view`), que é também onde as novas transições de cena são configuradas. O hook `ready`
dispara só **depois** que a transição inicial de cena termina.

```js
// Ativar sem puxar usuários que estão vendo outras cenas
await scene.activate({ pullUsers: false });
```

Uma Scene agora pode conter vários **Levels** (documentos `Level` embutidos em `scene.levels`).
Cada nível tem `name`, uma faixa de `elevation`, suas próprias configurações de `background`,
`foreground` e `fog`, e `visibility`. Propriedades da cena como `background` são mapeadas para o
nível filho, então cenas simples de um nível continuam funcionando. Veja
[Níveis](#scene-token--niveis-de-cena) abaixo.
:::

## Tokens protótipo

Todo Actor tem um `prototypeToken` (um data model `PrototypeToken`, não um documento). Ele é o
modelo usado quando o ator é colocado em uma cena. Sistemas normalmente definem padrões sensatos em
`Actor#_preCreate`:

```js
// systems/forja/module/documents/actor.mjs
export class ForjaActor extends Actor {
  async _preCreate(data, options, user) {
    if ((await super._preCreate(data, options, user)) === false) return false;
    // Personagens de jogadores: token vinculado, amistoso, com visão
    if (this.type === "character") {
      this.updateSource({
        prototypeToken: {
          actorLink: true,
          disposition: CONST.TOKEN_DISPOSITIONS.FRIENDLY,
          sight: { enabled: true }
        }
      });
    }
  }
}
```

`actorLink: true` significa que o token e o ator do mundo compartilham os mesmos dados
(personagens de jogadores). `actorLink: false` faz de cada token uma cópia independente, cujas
diferenças ficam em um `ActorDelta` (monstros: dez goblins, dez barras de PV).

## Criar um token por código

Nunca monte os dados do token à mão a partir do ator: `actor.getTokenDocument()` mescla o
protótipo, resolve imagens curinga (wildcard) e vincula o ator para você.

```js
/**
 * Coloca o token de um ator em um espaço da grade da cena visualizada.
 * @param {Actor} actor
 * @param {{x:number, y:number}} point   Um ponto em pixels do canvas
 */
async function placeActor(actor, point) {
  const scene = canvas.scene;
  // Alinhar à grade para o token cair em um espaço
  const snapped = scene.grid.getSnappedPoint(point, { mode: CONST.GRID_SNAPPING_MODES.TOP_LEFT_CORNER });
  const tokenDoc = await actor.getTokenDocument({ x: snapped.x, y: snapped.y, hidden: false });
  // Qualquer uma destas duas linhas funciona
  const [created] = await scene.createEmbeddedDocuments("Token", [tokenDoc.toObject()]);
  // const created = await TokenDocument.implementation.create(tokenDoc, { parent: scene });
  return created;
}
```

::: v14
A V14 também oferece um fluxo de posicionamento interativo, o mesmo usado ao arrastar atores: o
usuário vê uma prévia, pode girá-la com a roda do mouse e confirma com um clique.

```js
const tokenDoc = await actor.getTokenDocument();
// Resolve com os TokenDocuments criados (vazio/null se o usuário cancelar)
const placed = await canvas.tokens.placeTokens([tokenDoc.toObject()], { allowRotation: true });
```
:::

## Movimento

::: v13
A V13 introduziu uma API de movimento completa. Mover um token não é mais "atualizar `x` e `y`":
um movimento é uma lista de **waypoints**, cada um com uma **ação de movimento** (andar, voar,
nadar, ...), medida com a grade e os custos de terreno, guardada em `movementHistory` e anunciada
por hooks.
:::

::: v14
A V14 mantém a API de movimento da V13 e acrescenta **movimento planejado** e movimentos de vários
tokens (abaixo).
:::

### Mover com pontos de passagem

```js
const tokenDoc = canvas.tokens.controlled[0]?.document;
if (tokenDoc) {
  // Andar dois espaços para a direita e depois voar um espaço para cima
  const size = canvas.grid.size;
  await tokenDoc.move([
    { x: tokenDoc.x + 2 * size, y: tokenDoc.y, action: "walk" },
    { x: tokenDoc.x + 2 * size, y: tokenDoc.y - size, action: "fly", elevation: 5 }
  ], { showRuler: true });
}
```

As opções incluem `method` (`"api"`, `"dragging"`, `"keyboard"`, ...), `autoRotate`, `showRuler`
e `constrainOptions` (para restrições de paredes/custo). `move()` retorna uma `Promise<boolean>`:
`false` se um hook ou a checagem de permissão o cancelou.

::: v14
Na V14 a promise resolve quando o movimento **terminou** (incluindo a animação e eventuais pausas),
então você pode dar `await` com segurança antes do próximo passo. Na V13 ela resolve assim que o
movimento é enviado.
:::

### Medir um caminho e ler o histórico

```js
// Distância e custo de um caminho hipotético (nenhum movimento acontece)
const result = tokenDoc.measureMovementPath([
  { x: tokenDoc.x, y: tokenDoc.y, elevation: tokenDoc.elevation },
  { x: tokenDoc.x + 500, y: tokenDoc.y, elevation: tokenDoc.elevation }
]);
console.log(result.distance, result.cost, result.spaces);

// O que o token já fez (por exemplo, neste turno de combate)
console.log(tokenDoc.movementHistory);
```

### Ganchos: validar ou reagir ao movimento

```js
// Cancelar um movimento que custa mais que o deslocamento do ator (uma regra da Forja)
Hooks.on("preMoveToken", (tokenDoc, movement, operation) => {
  const speed = tokenDoc.actor?.system.speed ?? 6;
  if (movement.passed.cost + movement.pending.cost > speed) {
    ui.notifications.warn(game.i18n.localize("FORJA.Movement.TooFar"));
    return false;
  }
});

Hooks.on("moveToken", (tokenDoc, movement, operation, user) => {
  console.log(`${tokenDoc.name} moveu ${movement.passed.distance} ${canvas.scene.grid.units}`);
});
```

### Ações de movimento personalizadas

As ações de movimento ficam em `CONFIG.Token.movement.actions`. Adicione as suas no `init`:

```js
Hooks.once("init", () => {
  CONFIG.Token.movement.actions.glide = {
    // Partir de "walk" para que toda chave esperada pelo core tenha valor
    ...CONFIG.Token.movement.actions.walk,
    label: "FORJA.Movement.Glide",
    icon: "fa-solid fa-feather",
    order: 25,
    // Só atores com o traço "glide" podem selecioná-la
    canSelect: (token) => !!token.actor?.system.traits?.glide
  };
});
```

::: tip
Outras chaves da configuração de ação (funções de custo, terreno, animação) estão documentadas na
API em `TokenMovementActionConfig`. Confira a versão que você está mirando antes de depender delas.
:::

### Classe de token e régua personalizadas

Para mudanças visuais (um anel de vida, um rótulo de régua próprio), crie uma subclasse do
placeable e registre-a:

```js
class ForjaToken extends foundry.canvas.placeables.Token {
  /** Tinge de vermelho uma barra de recurso vazia */
  _drawBar(number, bar, data) {
    super._drawBar(number, bar, data);
    bar.tint = data.value <= 0 ? 0xff3333 : 0xffffff;
  }
}

class ForjaTokenRuler extends foundry.canvas.placeables.tokens.TokenRuler {
  /** Nosso próprio template de rótulo, copiado do core e estendido */
  static WAYPOINT_LABEL_TEMPLATE = "systems/forja/templates/hud/waypoint-label.hbs";

  /** Acrescenta o custo do movimento ao rótulo do waypoint */
  _getWaypointLabelContext(waypoint, state) {
    const context = super._getWaypointLabelContext(waypoint, state);
    // O contexto alimenta o template do rótulo; inspecione-o no console para ver as chaves
    if (context) context.forjaCost = waypoint.measurement?.cost;
    return context;
  }
}

Hooks.once("init", () => {
  CONFIG.Token.objectClass = ForjaToken;
  CONFIG.Token.rulerClass = ForjaTokenRuler;
});
```

::: v14
### Movimento planejado e movimento de vários tokens

A V14 permite que o usuário *planeje* um movimento (a régua fica na tela até ser confirmada) e que o
código mova muitos tokens em uma única operação:

```js
// Deixar o usuário planejar um caminho para o token controlado (resolve null se cancelar)
const token = canvas.tokens.controlled[0];
const plan = await token?.planMovement();
if (plan) console.log(plan.origin, plan.destination, plan.waypoints);

// Mover vários tokens juntos; as chaves são ids de tokens
const size = canvas.grid.size;
const instructions = {};
for (const t of canvas.tokens.controlled) {
  instructions[t.id] = { waypoints: [{ x: t.document.x + size, y: t.document.y }] };
}
const results = await canvas.scene.moveTokens(instructions);
```

O hook `planToken` dispara quando um usuário planeja um movimento. O formato exato de
`TokenMovementInstruction` está documentado na [API da V14](https://foundryvtt.com/api/v14/).

Colisão e visão agora usam os *pontos de origem* do token: `getMovementOrigin()`,
`getVisionOrigin()`, `getLightOrigin()`, `getSoundOrigin()`. Sobrescreva-os em uma subclasse de
`TokenDocument` se o seu sistema usa uma geometria de token fora do padrão.
:::

::: v14
## Níveis de cena

Um nível é uma fatia da cena entre duas elevações (térreo, sacada, porão). Cada `TokenDocument`
tem um campo `level` com o id do nível em que está; visão, iluminação e névoa são calculadas por
nível, e paredes/superfícies entre níveis bloqueiam a visão.

```js
// Listar os níveis da cena visualizada
for (const level of canvas.scene.levels) {
  console.log(level.index, level.name, level.elevation, level.isView);
}

// Tokens em um determinado nível
const cellar = canvas.scene.levels.getName("Porão");
const tokensInCellar = canvas.scene.tokens.filter(t => t.level === cellar?.id);
```

`Scene#getSurfaces()` retorna as superfícies (pisos/tetos) da cena filtradas por tipo (`"move"`,
`"sight"`, `"light"`, `"sound"`, `"darkness"`) e por nível; `Scene#testSurfaceCollision()` testa se
uma linha entre dois pontos elevados cruza alguma. Use o comportamento de região **Change Level**
(veja [Regiões](#regions)) para escadas.

## Efeitos visuais: tremor de tela e partículas

```js
// Tremer o canvas por 1,5 segundo (por exemplo, uma magia de terremoto)
const shake = new foundry.canvas.animation.CanvasShakeEffect({
  duration: 1500,
  maxDisplacement: 15,
  smoothness: 0.5
});
await shake.play();
```

`CanvasShakeEffect` é local ao cliente que o executa: transmita-o com um [socket](#sockets) se
todos os jogadores devem senti-lo. `ParticleGenerator` (em `foundry.canvas.vfx`) emite efeitos de
partículas; veja as opções na API da V14.
:::

## Receitas comuns

```js
// Mover a câmera até o token de um ator e selecioná-lo
const token = actor.getActiveTokens()[0];
if (token) {
  await canvas.animatePan({ x: token.center.x, y: token.center.y, scale: 1.5 });
  token.control({ releaseOthers: true });
}

// Renomear todos os tokens de uma cena ligados a um ator
const updates = canvas.scene.tokens
  .filter(t => t.actorId === actor.id)
  .map(t => ({ _id: t.id, name: actor.name }));
await canvas.scene.updateEmbeddedDocuments("Token", updates);
```

## Armadilhas

::: warning
- `tokenDoc.object` é `null` quando a cena dele não é a visualizada. Sempre verifique.
- `token.actor` de um token não vinculado é um ator *sintético*. Atualizá-lo grava no `ActorDelta`
  do token, não no ator do mundo.
- Atualizar `x`/`y` diretamente ainda funciona, mas ignora waypoints e a ação de movimento; prefira
  `TokenDocument#move` para que réguas, hooks e histórico continuem corretos.
- Hooks como `moveToken` rodam em todos os clientes. Só um cliente (por exemplo
  `game.users.activeGM?.isSelf`) deve criar documentos em resposta.
- Classes de placeable personalizadas devem chamar `super` em toda sobrescrita: o pipeline de
  renderização do core depende disso.
:::
