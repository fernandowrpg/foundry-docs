# Estilos, modelos e temas

Carregue seu CSS, limite o alcance dele para não vazar, dê suporte aos temas claro e escuro, e organize modelos, modelos parciais e funções auxiliares do Handlebars.

::: changed
- `<code>` agora tem estilo **inline** por padrão. Adicione a classe `block` (`<code class="block">`) para um bloco de código.
- O hot reload de CSS segue os `@import`, então você pode dividir os estilos em vários arquivos e continuar com recarga ao vivo.
- As aplicações podem ser **destacadas** em uma janela separada do navegador. Mantenha todo o estilo nos seus arquivos CSS em vez de injetar tags `<style>` pelo JavaScript, para que os estilos também existam nessa janela.
- O Font Awesome foi atualizado para a 7.2.
- Veja [a lista completa de mudanças](#changes-14).
:::

## Carregue suas folhas de estilo

Liste-as no manifesto. Os caminhos são relativos à pasta do pacote.

```json
{
  "styles": ["styles/forja.css"]
}
```

Com mais de dois ou três arquivos, mantenha um arquivo de entrada e importe o resto:

```css
/* styles/forja.css */
@import url("./variables.css");
@import url("./sheets.css");
@import url("./chat.css");
```

::: tip
Ative o hot reload de CSS e templates durante o desenvolvimento (veja [Ambiente de desenvolvimento](#setup)). As mudanças de estilo aparecem sem recarregar o mundo.
:::

## Limite o alcance de cada regra

O Foundry, o sistema e todos os módulos dividem a mesma página. Seletores soltos como `h2 {}` ou `.header {}` mudam outros pacotes. Coloque o id do pacote nas suas aplicações e use-o como prefixo em toda regra.

```js
// Na sua ApplicationV2 / ficha
static DEFAULT_OPTIONS = { classes: ["forja", "sheet", "actor"] };
```

```css
/* Certo: só afeta as fichas do Forja */
.forja.sheet .attributes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }

/* Errado: muda todas as aplicações do mundo */
.window-content h2 { color: red; }
```

## Camadas de cascata do CSS (V13+)

Desde o V13 o core coloca os próprios estilos em **camadas de cascata** (`@layer`). Duas regras decorrem de como as camadas funcionam:

1. Estilos **fora** de qualquer camada vencem os estilos de dentro de uma camada, seja qual for a especificidade do seletor. O CSS comum do seu pacote sobrescreve o core sem `!important` nem seletores enormes.
2. Se você quer que outros módulos consigam sobrescrever os *seus* estilos com facilidade, coloque o seu CSS em uma camada própria.

```css
/* Tudo neste arquivo pode ser sobrescrito por CSS sem camada de outros módulos */
@layer forja {
  .forja.sheet .resource { border: 1px solid var(--forja-line); border-radius: 6px; }
}
```

Abra as ferramentas de desenvolvedor do navegador e veja a visão **Layers** do painel de estilos para conhecer os nomes das camadas do core na sua versão.

## Temas claro e escuro

O V13 trouxe o Theme V2: a interface segue a preferência clara ou escura do sistema operacional, e o usuário pode trocar. O core adiciona `.theme-dark` ou `.theme-light` à página e às aplicações. Defina suas cores como propriedades personalizadas e troque-as por tema, em vez de escrever cada regra duas vezes.

```css
.forja {
  --forja-ink: #1f2530;
  --forja-paper: #f6f1e7;
  --forja-line: #c9bfae;
  --forja-accent: #9c3d17;
}
.theme-dark .forja,
.forja.theme-dark {
  --forja-ink: #e7e3dc;
  --forja-paper: #1d2129;
  --forja-line: #3a404c;
  --forja-accent: #f08a57;
}

.forja.sheet .window-content { background: var(--forja-paper); color: var(--forja-ink); }
.forja .roll-button { background: var(--forja-accent); color: var(--forja-paper); }
```

::: tip
O core define muitas propriedades personalizadas próprias (cores de texto, bordas, fontes). Inspecione o `body` nas ferramentas de desenvolvedor e reaproveite-as quando fizer sentido, para que suas fichas combinem com o resto da interface nos dois temas.
:::

Você pode forçar um tema em uma aplicação com a classe:

```js
static DEFAULT_OPTIONS = { classes: ["forja", "sheet", "theme-light"] };  // sempre claro, como pergaminho
```

## Modelos e modelos parciais

Os templates Handlebars (`.hbs`) são baixados e compilados uma vez. Pré-carregue os partials no `init`, para usá-los pelo nome em outros templates.

```js
Hooks.once("init", async () => {
  await foundry.applications.handlebars.loadTemplates([
    "systems/forja/templates/parts/resource-bar.hbs",
    "systems/forja/templates/parts/item-row.hbs"
  ]);
});
```

```hbs
{{!-- Use um partial pelo caminho, passando dados --}}
{{> "systems/forja/templates/parts/resource-bar.hbs" label="FORJA.HP" value=system.hp.value max=system.hp.max}}

{{!-- systems/forja/templates/parts/resource-bar.hbs --}}
<div class="forja resource-bar">
  <span class="label">{{localize label}}</span>
  <meter min="0" max="{{max}}" value="{{value}}"></meter>
  <span class="value">{{value}} / {{max}}</span>
</div>
```

Os templates listados nas `PARTS` de uma aplicação são carregados automaticamente; você só precisa de `loadTemplates` para os partials e para templates que renderiza você mesmo com `renderTemplate`.

## Funções auxiliares do Handlebars

O core traz helpers úteis: `localize`, `formGroup`, `formInput`, `selectOptions`, `editor`, `numberFormat`, `eq`, `ne`, `gt`, `and`, `or`, `not`, `ifThen`, `concat`. Registre os seus no `init`:

```js
Hooks.once("init", () => {
  // {{forjaSigned 3}} → "+3"
  Handlebars.registerHelper("forjaSigned", n => (Number(n) >= 0 ? `+${n}` : `${n}`));

  // {{#forjaTimes 3}}<i class="pip"></i>{{/forjaTimes}}
  Handlebars.registerHelper("forjaTimes", function(n, options) {
    let out = "";
    for ( let i = 0; i < n; i++ ) out += options.fn({ index: i });
    return out;
  });
});
```

::: warning
Use o id do pacote como prefixo no nome dos helpers. Helpers são globais, e um módulo que registra `signed` pode substituir o seu sem aviso.
:::

## Ícones

O Foundry inclui o Font Awesome. Use as classes `fa-solid` / `fa-regular`:

```hbs
<button type="button" data-action="rollAttack"><i class="fa-solid fa-dice-d20"></i> {{localize "FORJA.Attack"}}</button>
```

::: v14
O Font Awesome foi atualizado para a 7.2. A maioria dos nomes de ícone não mudou, mas confira os ícones que você usa e que tenham sido renomeados entre versões principais do Font Awesome.
:::

## Trechos de código na sua interface

::: v13
Use `<code>` para identificadores curtos e `<pre><code>` para código de várias linhas, para o resultado ficar igual em todo lugar.
:::

::: v14
`<code>` é inline por padrão. Para um bloco, adicione a classe:

```html
<p>Use <code>@UUID[...]</code> para linkar documentos.</p>
<code class="block">Hooks.once("ready", () => console.log("forja pronto"));</code>
```
:::

## Janelas destacadas

::: v14
Diálogos e outras janelas ApplicationV2 podem ser destacados em uma janela própria do navegador. Essa janela é um `document` separado:

- Mantenha todo o CSS nas folhas de estilo do manifesto. Estilos que você adiciona em tempo de execução com `document.head.append(style)` só existem na janela principal.
- Use `this.element` (e os elementos dentro dele) em vez de `document.querySelector` global no código da sua aplicação.
- Tooltips e menus de contexto funcionam na janela destacada porque o core os ativa em cada janela.
:::

## Armadilhas

- **`!important` para todo lado**: com camadas de cascata você raramente precisa dele. Remova e confira se a regra está fora de qualquer camada.
- **Tamanhos fixos em pixels**: as fichas são redimensionáveis e os usuários mudam a escala da interface. Prefira `rem`, `%`, grid e flex.
- **Cores que só funcionam em um tema**: teste cada ficha nos temas claro e escuro antes de publicar.
