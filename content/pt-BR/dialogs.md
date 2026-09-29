# Diálogos e notificações

Faça uma pergunta ao usuário com `DialogV2`, receba um valor de volta com `await` e dê feedback com `ui.notifications`.

::: changed
- `DialogV2` é uma `ApplicationV2`, então no V14 um diálogo pode ser **destacado (pop-out)** para uma janela separada do navegador, como qualquer outra aplicação (veja [Janelas com ApplicationV2](#applicationv2)).
- `game.i18n.localize()` aceita dados de formatação no V14, e `_loc(key, data)` é um alias global — prático para títulos de diálogo e rótulos de botões.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

`foundry.applications.api.DialogV2` é o substituto, no V13+, da antiga classe `Dialog`. É uma pequena [Janelas com ApplicationV2](#applicationv2) cujo conteúdo fica dentro de um `<form>` e cujos botões são declarados como dados. Seus helpers estáticos retornam uma **Promise**, então o fluxo habitual é:

```js
const answer = await DialogV2.something({ ... });
if ( answer === null ) return; // o usuário fechou o diálogo
```

| Helper estático | Botões | Resolve para |
|---|---|---|
| `DialogV2.confirm(config)` | Sim / Não | `true`, `false` (ou o retorno de um callback) |
| `DialogV2.prompt(config)` | Um botão "OK" | a `action` do botão, ou o retorno do callback |
| `DialogV2.input(config)` | Um botão "OK" | os dados do formulário como objeto simples, ou o retorno do callback |
| `DialogV2.wait(config)` | Os botões que você declarar | a `action` do botão clicado, ou o retorno do callback |
| `DialogV2.query(user, type, config)` | Os mesmos do `type` | a resposta do outro usuário (veja abaixo) |

Se o usuário fechar o diálogo sem escolher, a Promise resolve para `null`, ou é **rejeitada** se você passou `rejectClose: true`.

## Confirmação

```js
const { DialogV2 } = foundry.applications.api;

const ok = await DialogV2.confirm({
  window: { title: "FORJA.Dialog.RestTitle", icon: "fa-solid fa-campground" },
  content: `<p>${game.i18n.localize("FORJA.Dialog.RestBody")}</p>`,
  modal: true,          // bloqueia o resto da interface enquanto estiver aberto
  rejectClose: false    // fechar a janela resolve para null em vez de lançar erro
});

if ( ok ) {
  // Restaura os PV ao máximo
  await actor.update({ "system.hp.value": actor.system.hp.max });
}
```

Personalize os botões com `yes` e `no` (mesmo formato de qualquer botão, veja abaixo):

```js
await DialogV2.confirm({
  content: "<p>Quebrar a arma?</p>",
  yes: { label: "Quebrar", icon: "fa-solid fa-hammer" },
  no: { label: "Manter", default: true }
});
```

## Configuração de botões

| Chave | Significado |
|---|---|
| `action` | Identificador do botão; é retornado se não houver callback. |
| `label` | Texto (chaves de localização são traduzidas). |
| `icon` | Classes do Font Awesome. |
| `default` | `true` para o botão acionado pelo Enter. |
| `callback` | `(event, button, dialog) => valor`. O valor retornado (aguardado, se for async) vira o resultado da Promise. |

`button` é o elemento `<button>` clicado. Como o conteúdo do diálogo vive dentro de um `<form>`, `button.form` dá acesso a esse formulário e `button.form.elements` a todos os inputs com `name`.

## Pedir um valor

```js
const bonus = await DialogV2.prompt({
  window: { title: "FORJA.Dialog.BonusTitle" },
  content: `<input type="number" name="bonus" value="0" autofocus>`,
  ok: {
    label: "FORJA.Roll",
    icon: "fa-solid fa-dice-d20",
    // Retorna o número em vez da action do botão
    callback: (event, button, dialog) => button.form.elements.bonus.valueAsNumber
  },
  rejectClose: false
});

if ( bonus !== null ) {
  const roll = await new Roll(`1d20 + ${bonus}`).evaluate();
  await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) });
}
```

## Ler um formulário inteiro

`DialogV2.input` retorna todo campo com `name` como um objeto, já tipado (números para `type="number"`, booleanos para checkboxes):

```js
const data = await DialogV2.input({
  window: { title: "FORJA.Dialog.NewNpcTitle" },
  content: `
    <div class="form-group">
      <label>Nome</label>
      <input type="text" name="name" required>
    </div>
    <div class="form-group">
      <label>Nível</label>
      <input type="number" name="level" value="1" min="1">
    </div>
    <div class="form-group">
      <label>Elite</label>
      <input type="checkbox" name="elite">
    </div>`,
  ok: { label: "FORJA.Create" }
});
// data → { name: "Goblin", level: 3, elite: true }   (ou null se fechado)

if ( data ) {
  await Actor.implementation.create({ name: data.name, type: "character" });
}
```

Para formulários montados com `wait`, a mesma conversão está disponível com `new foundry.applications.ux.FormDataExtended(button.form).object`.

## Várias escolhas

```js
const stance = await DialogV2.wait({
  window: { title: "FORJA.Dialog.StanceTitle" },
  content: "<p>Escolha sua postura para esta rodada.</p>",
  buttons: [
    { action: "attack", label: "Atacar", icon: "fa-solid fa-khanda", default: true },
    { action: "defend", label: "Defender", icon: "fa-solid fa-shield" },
    {
      action: "flee",
      label: "Fugir",
      icon: "fa-solid fa-person-running",
      // Um callback pode executar trabalho e retornar qualquer valor
      callback: async (event, button, dialog) => {
        await actor.setFlag("forja", "fled", true);
        return "fled";
      }
    }
  ],
  rejectClose: false
});
// stance → "attack" | "defend" | "fled" | null
```

## Conteúdo personalizado a partir de um modelo

Conteúdo longo deve ficar num arquivo Handlebars. Renderize-o primeiro e passe a string HTML como `content`:

```hbs
{{!-- systems/forja/templates/dialogs/attack.hbs --}}
<div class="form-group">
  <label>{{localize "FORJA.Weapon"}}</label>
  <select name="weaponId">
    {{selectOptions weapons valueAttr="id" labelAttr="name"}}
  </select>
</div>
<div class="form-group">
  <label>{{localize "FORJA.Bonus"}}</label>
  <input type="number" name="bonus" value="0">
</div>
```

```js
const { DialogV2 } = foundry.applications.api;
const { renderTemplate } = foundry.applications.handlebars;

export async function attackDialog(actor) {
  const weapons = actor.itemTypes.weapon;
  if ( !weapons.length ) return ui.notifications.warn("FORJA.Warn.NoWeapons", { localize: true });

  const content = await renderTemplate("systems/forja/templates/dialogs/attack.hbs", { weapons });

  const result = await DialogV2.wait({
    window: { title: "FORJA.Dialog.AttackTitle" },
    classes: ["forja"],           // escopa o seu CSS
    content,
    buttons: [{
      action: "roll",
      label: "FORJA.Roll",
      default: true,
      callback: (event, button) => {
        const { weaponId, bonus } = button.form.elements;
        return { weapon: actor.items.get(weaponId.value), bonus: bonus.valueAsNumber };
      }
    }],
    // Executa depois que o diálogo renderiza: adicione listeners ou ajuste o DOM
    render: (event, dialog) => {
      dialog.element.querySelector("select[name=weaponId]")?.focus();
    },
    rejectClose: false
  });

  if ( !result ) return;
  const roll = await new Roll(`${result.weapon.system.damage} + ${result.bonus}`).evaluate();
  return roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }), flavor: result.weapon.name });
}
```

::: tip
As demais opções (`classes`, `position`, `window`, `modal`…) são [opções normais de ApplicationV2](#applicationv2), então você pode dimensionar um diálogo com `position: { width: 400 }`.
:::

## Perguntando a outro usuário

`DialogV2.query(user, type, config)` mostra um diálogo no cliente de **outro** usuário e resolve para a resposta dele. `type` é `"confirm"`, `"prompt"`, `"input"` ou `"wait"`, e `config` é o que você passaria para aquele helper.

```js
// O GM pergunta ao dono do ator se ele aceita uma oferta
const player = game.users.find(u => u.active && !u.isGM && actor.testUserPermission(u, "OWNER"));
if ( player ) {
  const accepted = await DialogV2.query(player, "confirm", {
    window: { title: "Oferta" },
    content: "<p>O mercador oferece 50 de ouro pela sua espada. Aceita?</p>"
  });
}
```

O usuário alvo precisa estar conectado. Isso é construído sobre o sistema de queries de usuário (`user.query`), descrito em [Comunicação entre clientes](#sockets).

## Diálogos de criação e exclusão de documentos

Todo documento do cliente já tem diálogos prontos, então raramente você precisa construí-los:

```js
// Escolhe nome e tipo e cria um Item no ator
const item = await Item.implementation.createDialog({}, { parent: actor }, {
  types: ["weapon", "gear"]    // restringe a lista de tipos
});

// Confirma e exclui
await item?.deleteDialog();
```

Ambos resolvem para `null` (ou `undefined`) se o usuário cancelar.

## Notificações

`ui.notifications` mostra avisos (toasts) no topo da tela.

```js
ui.notifications.info("Sua arma foi afiada.");
ui.notifications.success("FORJA.Notify.Saved", { localize: true });
ui.notifications.warn("FORJA.Notify.LowHp", { localize: true, format: { name: actor.name } });
ui.notifications.error("Algo deu errado.", { permanent: true }); // fica até ser clicada
```

- `localize: true` trata a mensagem como uma chave; `format` preenche os `{placeholders}`.
- `permanent: true` mantém a notificação até ser dispensada.
- Use-as para **feedback**, não para erros que o desenvolvedor precisa ver: combine erros com `console.error` ou lance uma exceção.

### Notificações de progresso

O V13 adicionou uma notificação de `progress` que substitui o obsoleto `SceneNavigation.displayProgressBar`:

```js
const docs = game.actors.contents;
const bar = ui.notifications.info("Migrando atores…", { progress: true });

for ( const [i, actor] of docs.entries() ) {
  await migrateActor(actor);          // sua própria função
  bar.update({ pct: (i + 1) / docs.length, message: `Migrando ${actor.name}` });
}
// Quando pct chega a 1 a barra está cheia e a notificação é removida como qualquer outra
```

## Diálogos em janela separada

::: v13
No V13, os diálogos sempre renderizam dentro da janela principal.
:::

::: v14
No V14, o usuário pode destacar um diálogo para uma janela própria do navegador. Seus callbacks continuam funcionando, mas dentro de um callback `render` use `dialog.element.ownerDocument` em vez do `document` global se precisar consultar ou criar elementos.
:::

## Armadilhas

- **Esquecer o `await`**: `DialogV2.confirm()` retorna uma Promise, que é sempre truthy — `if (DialogV2.confirm(...))` sempre passa.
- **Não tratar o `null`**: usuários fecham diálogos com Esc ou com o botão ×. Verifique `null`, ou passe `rejectClose: true` e use `try/catch`.
- **Atributos `name` duplicados** no conteúdo: `button.form.elements.x` vira uma `RadioNodeList` em vez de um elemento.
- **Entrada do usuário sem escape** no `content`: escape os nomes que você interpola (`Handlebars.escapeExpression(actor.name)`) ou renderize um template, que faz o escape por padrão.
- A antiga classe `Dialog` (AppV1) está obsoleta; não comece código novo com ela.
