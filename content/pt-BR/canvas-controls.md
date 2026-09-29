# Tela de jogo, controles de cena e HUD

Adicione botões aos controles de cena, desenhe sua própria camada na tela de jogo, estenda o HUD do token e reaja a eventos da tela de jogo.

::: changed
- `SceneControlTool` ganha as propriedades `interaction`, `control` e `creation`, que descrevem o que a ferramenta faz, e `shapeData` para definir ferramentas de desenho de Regions.
- `ui.controls.tool` e `game.activeTool` podem ser `null` quando um controle não tem ferramentas. Proteja o seu código contra isso.
- `PlaceableObject#isInteractable`: objetos travados (menos Tokens) não são mais interativos.
- `layerClass` no CONFIG dos documentos do canvas (por exemplo `CONFIG.Token.layerClass`) está obsoleto; as opções da camada agora ficam na classe `PlaceablesLayer`.
- Nova **Paleta de Objetos** (edição em lote dos objetos selecionados) e nova **aba de Objetos na barra lateral**.
- Novas APIs visuais: `foundry.canvas.vfx` (animações em linha do tempo usando anime.js), `ParticleGenerator` e `CanvasShakeEffect` (tremor de tela).
- `PlaceableObject#clear` está obsoleto em favor do protegido `_clear`.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

O **canvas** é a cena em PIXI.js onde tokens, paredes, luzes e regiões são desenhados. Ele é dividido em **camadas** (`canvas.tokens`, `canvas.walls`, `canvas.regions`…). Os **controles de cena** à esquerda da tela escolhem a camada e a ferramenta ativas. Cada objeto posicionável (um `Token`, um `Wall`) é o lado visual de um documento (`TokenDocument`, `WallDocument`).

```text
ui.controls (barra à esquerda)     canvas
 ├─ tokens  → canvas.tokens   ← objetos Token  ↔ TokenDocument
 ├─ walls   → canvas.walls    ← objetos Wall   ↔ WallDocument
 └─ forja   → canvas.forja    ← sua própria camada (opcional)
```

## Adicione uma ferramenta aos controles de cena

Desde o V13, `controls` é um **objeto indexado por nome**, e o `tools` de cada controle também é um objeto. Adicione ou altere as entradas diretamente.

```js
Hooks.on("getSceneControlButtons", controls => {
  // Um botão nos controles de Token que já existem
  controls.tokens.tools.forjaRest = {
    name: "forjaRest",
    title: "FORJA.Controls.Rest",           // traduzido automaticamente
    icon: "fa-solid fa-campground",
    order: Object.keys(controls.tokens.tools).length,
    button: true,                           // ação de clique, não um modo
    visible: game.user.isGM,
    onChange: (event, active) => game.forja.restParty()
  };

  // Um interruptor que fica ligado ou desligado
  controls.tokens.tools.forjaAuras = {
    name: "forjaAuras",
    title: "FORJA.Controls.Auras",
    icon: "fa-solid fa-circle-radiation",
    order: Object.keys(controls.tokens.tools).length,
    toggle: true,
    active: game.settings.get("forja", "showAuras"),
    onChange: (event, active) => game.settings.set("forja", "showAuras", active)
  };
});
```

::: warning
Código escrito para o V12 usava `controls.find(c => c.name === "token").tools.push(...)`. Isso falha no V13 e no V14 porque `controls` não é mais um array, e a chave é `tokens` (no plural).
:::

::: v14
As ferramentas podem descrever o comportamento delas com as novas propriedades `interaction`, `control` e `creation`, e ferramentas de desenho de Regions podem passar `shapeData`. Confira os valores aceitos no tipo `SceneControlTool` da API do V14. Sempre trate a ausência de ferramenta ativa:

```js
const tool = ui.controls.tool;        // pode ser null no V14
if ( tool?.name === "forjaAuras" ) { /* ... */ }
```
:::

## Uma camada própria na tela de jogo

Use uma camada quando precisa desenhar algo que não é um documento, como uma sobreposição de auras ou um mapa de calor no grid.

```js
// systems/forja/module/canvas/aura-layer.mjs
const { InteractionLayer } = foundry.canvas.layers;

export class ForjaAuraLayer extends InteractionLayer {
  static get layerOptions() {
    return foundry.utils.mergeObject(super.layerOptions, { name: "forjaAuras", zIndex: 180 });
  }

  /** Chamado quando o canvas desenha esta camada. */
  async _draw(options) {
    this.graphics = this.addChild(new PIXI.Graphics());
    this.refreshAuras();
  }

  /** Redesenha um círculo em volta de cada token que tem aura. */
  refreshAuras() {
    const g = this.graphics;
    if ( !g ) return;
    g.clear();
    if ( !game.settings.get("forja", "showAuras") ) return;
    for ( const token of canvas.tokens.placeables ) {
      const radius = token.actor?.system.aura?.radius;       // em unidades do grid
      if ( !radius ) continue;
      const px = radius * canvas.dimensions.distancePixels;
      const { x, y } = token.center;
      g.beginFill(0xee8a4f, 0.12).lineStyle(2, 0xee8a4f, 0.6).drawCircle(x, y, px).endFill();
    }
  }
}
```

```js
Hooks.once("init", () => {
  CONFIG.Canvas.layers.forjaAuras = { layerClass: ForjaAuraLayer, group: "interface" };
});

// Mantém atualizado
Hooks.on("refreshToken", () => canvas.forjaAuras?.refreshAuras());
Hooks.on("canvasReady", () => canvas.forjaAuras?.refreshAuras());
```

::: v14
As cenas podem ter vários **Levels** (níveis). Se a sua sobreposição só faz sentido no nível visualizado, ignore os tokens que não estão nele. Veja [Cenas e tokens](#scene-token) para helpers que conhecem níveis, como `Scene#getSurfaces`.
:::

## Estenda o HUD do token

O HUD do token é o anel de botões em volta de um token selecionado. O hook de renderização entrega a aplicação do HUD e o `HTMLElement` dela.

```js
Hooks.on("renderTokenHUD", (hud, html, context) => {
  const token = hud.object;                         // o Token posicionável
  if ( !token.actor?.isOwner ) return;
  const button = document.createElement("button");
  button.type = "button";
  button.classList.add("control-icon");
  button.dataset.tooltip = game.i18n.localize("FORJA.HUD.SecondWind");
  button.innerHTML = '<i class="fa-solid fa-heart-pulse"></i>';
  button.addEventListener("click", () => token.actor.secondWind());
  html.querySelector(".col.right")?.append(button);
});
```

## Ganchos da tela de jogo que você vai usar

| Hook | Argumentos | Quando |
|---|---|---|
| `canvasInit` | `(canvas)` | uma cena começa a carregar |
| `canvasReady` | `(canvas)` | a cena está desenhada e interativa |
| `drawToken` / `refreshToken` | `(token, flags)` | um token é desenhado ou redesenhado |
| `controlToken` | `(token, controlled)` | um token é selecionado ou solto |
| `hoverToken` | `(token, hovered)` | o mouse entra ou sai de um token |
| `targetToken` | `(user, token, targeted)` | um usuário marca um token como alvo |
| `updateToken` | hook de documento | os dados do token mudaram (posição, elevação…) |

```js
Hooks.on("controlToken", (token, controlled) => {
  if ( controlled ) console.log("forja | selecionado", token.name, token.document.uuid);
});
```

## Personalize a medição de movimento

O V13 trouxe a medição ao arrastar com waypoints. Você pode mudar o visual da régua criando uma subclasse da régua do token e registrando-a:

```js
const { TokenRuler } = foundry.canvas.placeables.tokens;

class ForjaTokenRuler extends TokenRuler {
  /** Colore cada segmento conforme a ação de movimento (andar, voar…). */
  _getSegmentStyle(waypoint) {
    const style = super._getSegmentStyle(waypoint);
    if ( waypoint.action === "fly" ) style.color = 0x80a6e6;
    return style;
  }
}

Hooks.once("init", () => {
  CONFIG.Token.rulerClass = ForjaTokenRuler;
});
```

::: v14
`TokenRuler#_getWaypointStyle` permite escolher o símbolo dos waypoints (variações de círculo, quadrado, losango, triângulo e hexágono). Os waypoints intermediários agora aparecem no caminho desenhado.
:::

Para as regras de movimento em si (custo, ações, movimento planejado), veja [Cenas e tokens](#scene-token) e [Regiões](#regions).

## Efeitos visuais

::: v13
O V13 não tem uma API geral de efeitos visuais. Use `CanvasAnimation` (`foundry.canvas.animation.CanvasAnimation`) para animar propriedades, ou um container PIXI na sua própria camada.

```js
const { CanvasAnimation } = foundry.canvas.animation;
await CanvasAnimation.animate([{ parent: token.mesh, attribute: "alpha", to: 0.2 }], { duration: 300 });
await CanvasAnimation.animate([{ parent: token.mesh, attribute: "alpha", to: 1 }], { duration: 300 });
```
:::

::: v14
O V14 traz três ferramentas para retorno visual:

- **`foundry.canvas.vfx`**: animações no canvas guiadas por linha do tempo. A biblioteca anime.js que ela usa fica disponível como `globalThis.animejs`.
- **`ParticleGenerator`**: partículas leves (faíscas, poeira, brasas) com rotação aleatória e callback `onUpdate`.
- **`CanvasShakeEffect`** (`foundry.canvas.animation`): tremor de tela para momentos de impacto. Ele sacode a cena, mas não a interface nem as partículas.

Essas APIs são novas. Leia as páginas delas na [API do V14](https://foundryvtt.com/api/v14/) para ver as opções do construtor antes de construir em cima delas, e deixe os efeitos opcionais com uma configuração de cliente: alguns jogadores sentem enjoo com movimento na tela.
:::

## Armadilhas

- **Desenhar no `init`**: o canvas ainda não existe. Desenhe no `canvasReady` ou no `_draw` da sua camada.
- **Esquecer a limpeza**: objetos PIXI que você adiciona fora de uma camada sobrevivem à troca de cena. Destrua-os no `canvasTearDown`, ou mantenha-os dentro de uma camada para o core limpar.
- **Usar documentos só para visual**: criar um `Drawing` para cada aura grava no banco de dados a cada mudança. Desenhe em uma camada.
