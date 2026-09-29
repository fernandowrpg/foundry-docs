# Mensagens de chat e rolagens

Publique cartões no chat, role dados com os dados do ator, crie uma classe de rolagem própria e reaja a botões em um cartão.

::: changed
- **Roll Modes viraram Message Visibility Modes (modos de visibilidade).** Eles valem para qualquer mensagem, não só rolagens, e há um novo modo "In-Character" (falar como o personagem). Modos: `"public"`, `"self"`, `"gm"`, `"blind"`.
- `ChatMessage.applyRollMode(data, mode)` → `ChatMessage.applyMode(data, mode)` (e `message.applyMode(mode)` na instância).
- `roll.toMessage(data, { rollMode })` → `roll.toMessage(data, { messageMode })`. Os nomes antigos continuam funcionando com aviso de obsolescência até o V16.
- `ChatLog.MESSAGE_PATTERNS` → `ChatLog.CHAT_COMMANDS` para comandos de chat próprios (o nome antigo sai no V16).
- A caixa de digitação do chat agora é um editor ProseMirror embutido.
- Booleanos nos dados da rolagem viram números (`true` → `1`, `false` → `0`).
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Uma **ChatMessage** é um documento do mundo com `content` em HTML, um `speaker` (quem fala), um `author` (o usuário), `rolls` opcionais, destinatários em `whisper` e `flags`. Todos os clientes guardam e renderizam a mesma mensagem, então um cartão de chat também é o jeito mais simples de mostrar o resultado de uma ação para todo mundo.

Um **Roll** não é um documento. É uma classe que interpreta uma fórmula (`"1d20 + @str"`), avalia o resultado e sabe se serializar no array `rolls` de uma mensagem.

## Publique uma mensagem

```js
await ChatMessage.create({
  speaker: ChatMessage.getSpeaker({ actor }),          // quem está falando
  content: `<p>${game.i18n.localize("FORJA.Chat.Ready")}</p>`,
  flags: { forja: { kind: "ready" } }                  // seus próprios dados
});
```

`getSpeaker()` sem argumentos usa o token controlado e depois o personagem do usuário. Passe `{ actor }` ou `{ token }` para ser explícito.

### Sussurre para os mestres

```js
await ChatMessage.create({
  content: "<p>Porta secreta encontrada.</p>",
  whisper: game.users.filter(u => u.isGM).map(u => u.id)
});
```

### Use um modelo para cartões elaborados

```js
// systems/forja/module/chat.mjs
const { renderTemplate } = foundry.applications.handlebars;

export async function postItemCard(item) {
  const content = await renderTemplate("systems/forja/templates/chat/item-card.hbs", {
    item, system: item.system, actorId: item.actor?.id
  });
  return ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor: item.actor }),
    content,
    flags: { forja: { itemUuid: item.uuid } }
  });
}
```

```hbs
{{!-- systems/forja/templates/chat/item-card.hbs --}}
<div class="forja chat-card" data-item-uuid="{{item.uuid}}">
  <header><img src="{{item.img}}" alt=""><h3>{{item.name}}</h3></header>
  <div class="card-body">{{{system.description}}}</div>
  <footer>
    <button type="button" data-action="rollDamage">{{localize "FORJA.Chat.RollDamage"}}</button>
  </footer>
</div>
```

## Role dados

```js
// Fórmula com @referências resolvidas a partir dos dados de rolagem
const roll = new Roll("1d20 + @abilities.str.mod", actor.getRollData());
await roll.evaluate();              // sempre use await: a avaliação é assíncrona

roll.total;                         // 17
roll.formula;                       // "1d20 + 3"
roll.dice[0].results;               // [{ result: 14, active: true }]
roll.isDeterministic;               // false (tem dados)
```

`actor.getRollData()` devolve uma cópia de `actor.system` (mais o que sua classe Actor acrescentar), então `@abilities.str.mod` funciona quando o seu data model tem esse caminho. Veja [Atores](#actor).

### Mande a rolagem para o chat

::: v13
```js
await roll.toMessage({
  speaker: ChatMessage.getSpeaker({ actor }),
  flavor: game.i18n.format("FORJA.Roll.Attack", { name: actor.name, weapon: item.name })
}, {
  rollMode: game.settings.get("core", "rollMode")   // publicroll | gmroll | blindroll | selfroll
});
```

`CONST.DICE_ROLL_MODES` guarda os valores: `PUBLIC` = `"publicroll"`, `PRIVATE` = `"gmroll"`, `BLIND` = `"blindroll"`, `SELF` = `"selfroll"`.

Quando você monta os dados da mensagem na mão, aplique o modo explicitamente. Desde o V13, `ChatMessage#_preCreate` só aplica o modo quando `options.rollMode` é informado:

```js
const data = { speaker: ChatMessage.getSpeaker({ actor }), rolls: [roll] };
ChatMessage.applyRollMode(data, game.settings.get("core", "rollMode"));
await ChatMessage.create(data);
```
:::

::: v14
```js
await roll.toMessage({
  speaker: ChatMessage.getSpeaker({ actor }),
  flavor: game.i18n.localize("FORJA.Roll.Attack", { name: actor.name, weapon: item.name })
}, {
  messageMode: "gm"          // "public" | "self" | "gm" | "blind"; omita para usar o modo atual do usuário
});
```

Os modos de visibilidade agora valem para qualquer mensagem, então você esconde um cartão simples do mesmo jeito:

```js
const data = { speaker: ChatMessage.getSpeaker({ actor }), content: "<p>Armadilha desarmada.</p>" };
ChatMessage.applyMode(data, "blind");   // estático: altera whisper/blind nos dados
await ChatMessage.create(data);

// Em uma mensagem que já existe
message.applyMode("public");
```
:::

## Uma classe de rolagem própria

Crie uma subclasse de `Roll` quando o seu sistema tem lógica de dados própria (contagem de sucessos, dados explosivos, template de chat próprio).

```js
// systems/forja/module/dice/forja-roll.mjs
export class ForjaRoll extends Roll {
  static CHAT_TEMPLATE = "systems/forja/templates/chat/roll.hbs";

  /** Sucesso quando o total alcança o número-alvo guardado nas opções. */
  get isSuccess() {
    if ( !this._evaluated ) return undefined;
    return this.total >= (this.options.target ?? 10);
  }

  /** Acrescenta nossos dados ao contexto do template de chat. */
  async _prepareChatRenderContext(options = {}) {
    const context = await super._prepareChatRenderContext(options);
    context.isSuccess = this.isSuccess;
    context.target = this.options.target;
    return context;
  }
}
```

```js
// forja.mjs
import { ForjaRoll } from "./module/dice/forja-roll.mjs";

Hooks.once("init", () => {
  CONFIG.Dice.rolls.push(ForjaRoll);   // necessário para as mensagens recriarem a classe a partir do JSON
});

// Uso
const roll = await new ForjaRoll("2d6 + @skill", { skill: 2 }, { target: 9 }).evaluate();
await roll.toMessage({ speaker: ChatMessage.getSpeaker({ actor }) });
```

::: warning
Se você esquecer o `CONFIG.Dice.rolls.push(...)`, a rolagem ainda é publicada, mas depois de recarregar a página a mensagem recria um `Roll` comum e seus getters próprios devolvem `undefined`.
:::

::: v14
Valores booleanos nos dados da rolagem agora viram números. `@hasShield` com `true` vira `1`, então fórmulas como `1d20 + @hasShield * 2` funcionam sem você converter o valor.
:::

## Reaja a botões em um cartão de chat

Os cartões são renderizados de novo em cada cliente e a cada recarga, então conecte os listeners no hook de renderização, não no momento em que cria a mensagem.

```js
// V13 e V14: html é um HTMLElement
Hooks.on("renderChatMessageHTML", (message, html, context) => {
  const card = html.querySelector(".forja.chat-card");
  if ( !card ) return;
  card.querySelector("[data-action='rollDamage']")?.addEventListener("click", async event => {
    event.preventDefault();
    const item = await fromUuid(card.dataset.itemUuid);
    if ( !item?.isOwner ) return ui.notifications.warn("FORJA.Warn.NotOwner", { localize: true });
    const roll = await new Roll(item.system.damage, item.getRollData()).evaluate();
    await roll.toMessage({ speaker: message.speaker, flavor: item.name });
  });
});
```

::: tip
Guarde os dados de que precisa no próprio cartão (`data-item-uuid`) ou em `message.flags`. Não dependa de variáveis do momento em que o cartão foi criado: elas somem depois de recarregar.
:::

## Comandos de chat próprios

::: v13
O hook `chatMessage` roda antes de uma mensagem digitada ser enviada. Devolva `false` para impedir o tratamento padrão.

```js
Hooks.on("chatMessage", (chatLog, text, chatData) => {
  const match = text.match(/^\/forja\s+(\d+)/i);
  if ( !match ) return;                // não é nosso: deixe o Foundry tratar
  const target = Number(match[1]);
  new ForjaRoll("2d6", {}, { target }).toMessage({ speaker: ChatMessage.getSpeaker() });
  return false;                        // já tratamos
});
```
:::

::: v14
O hook `chatMessage` continua funcionando para casos simples. A lista de comandos do core mudou de `ChatLog.MESSAGE_PATTERNS` para `ChatLog.CHAT_COMMANDS`, que é a estrutura a estender quando você quer que o seu comando se comporte como um comando do core. Confira o formato das entradas na página `ChatLog` da API do V14 antes de acrescentar a ela.

```js
Hooks.on("chatMessage", (chatLog, text, chatData) => {
  const match = text.match(/^\/forja\s+(\d+)/i);
  if ( !match ) return;
  const target = Number(match[1]);
  new ForjaRoll("2d6", {}, { target }).toMessage({ speaker: ChatMessage.getSpeaker() });
  return false;
});
```
:::

## Receitas comuns

### Rolar um item a partir da ficha

```js
// Dentro de ForjaItem (CONFIG.Item.documentClass)
async roll() {
  const roll = await new Roll(this.system.attackFormula, this.getRollData()).evaluate();
  return roll.toMessage({
    speaker: ChatMessage.getSpeaker({ actor: this.actor }),
    flavor: this.name,
    flags: { forja: { itemUuid: this.uuid } }
  });
}
```

### Ler de volta a rolagem de uma mensagem

```js
const message = game.messages.contents.at(-1);
const [roll] = message.rolls;           // já recriada como ForjaRoll se estiver registrada
console.log(roll.total, roll.isSuccess);
```

### Mostrar dados 3D ou esperar animações

Módulos como o Dice So Nice se conectam ao `toMessage`. Sempre use `await` quando o próximo passo depender de os dados já terem aparecido.

## Armadilhas

- **Esquecer `await roll.evaluate()`**: `roll.total` fica `undefined` até a rolagem ser avaliada.
- **HTML inseguro**: `content` é guardado como HTML. Nunca insira texto do usuário sem escapar (`Handlebars.escapeExpression(text)` ou um template com `{{...}}`, que escapa por padrão).
- **Listeners em `createChatMessage`**: rodam uma vez, em um cliente só. Use `renderChatMessageHTML`.
- **jQuery**: V13 e V14 passam `HTMLElement`. `html.find(...)` não existe mais.
