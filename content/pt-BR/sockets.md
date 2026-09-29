# Comunicação entre clientes

Envie mensagens entre clientes conectados e permita que jogadores peçam ao mestre para fazer o que eles próprios não têm permissão.

::: changed
- `User.queryMany(users, name, data, options)` (estático) consulta vários usuários de uma vez e retorna um `Map` com os resultados.
- Os handlers de query agora recebem o id do usuário que enviou a query, então o GM pode checar permissões sem confiar no payload.
- A API de socket (`game.socket.on` / `emit`) e o registro em `CONFIG.queries` não mudaram.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Todo cliente do Foundry mantém uma conexão WebSocket com o servidor. As operações de
documentos (criar, atualizar, excluir) já passam por ela, e todos os clientes são avisados
automaticamente. Você só precisa de mensagens próprias quando quer fazer algo que **não** é
uma alteração de documento, ou quando um jogador precisa de uma operação que as permissões
dele não permitem — por exemplo, causar dano a um NPC que ele não controla.

O Foundry oferece duas ferramentas:

| Ferramenta | Direção | Retorna valor? | Use para |
| --- | --- | --- | --- |
| `game.socket.emit` / `on` | Broadcast para todos os *outros* clientes | Não | Avisos, "toque esta animação", eventos sem resposta |
| User queries (`CONFIG.queries` + `user.query`) | Pedido para um usuário específico | Sim (uma Promise) | "GM, faça X e me diga o resultado" |

## Habilite o socket no manifesto

Um pacote só pode usar o próprio canal se o manifesto pedir. Sem essa flag, o servidor
descarta suas mensagens em silêncio.

```json
{
  "id": "forja",
  "title": "Forja",
  "socket": true
}
```

O nome do canal vem do id do pacote:

- sistema → `system.forja`
- módulo → `module.forja-extras`

::: warning
Alterar `socket` exige reiniciar o servidor do Foundry por completo (não basta recarregar),
porque o servidor lê os manifestos na inicialização.
:::

## Mensagens diretas: `game.socket`

```js
// systems/forja/module/socket.mjs
const CHANNEL = "system.forja";

export function registerSocket() {
  game.socket.on(CHANNEL, (message) => {
    // O servidor NÃO devolve a mensagem para quem enviou.
    switch (message.type) {
      case "ping":
        ui.notifications.info(`Ping de ${game.users.get(message.userId)?.name}`);
        break;
      case "shake":
        if (message.sceneId === canvas.scene?.id) canvas.animatePan({ duration: 250 });
        break;
    }
  });
}

export function emit(type, payload = {}) {
  game.socket.emit(CHANNEL, { type, userId: game.user.id, ...payload });
}

Hooks.once("ready", registerSocket);
```

Pontos-chave:

- Registre os listeners em `init`, `setup` ou `ready`; `game.socket` existe desde o `init`,
  mas o `ready` garante que `game.user` e os documentos já foram carregados.
- O payload precisa ser serializável em JSON. Envie ids ou UUIDs, nunca instâncias de Document.
- Quem envia não recebe a própria mensagem. Se o remetente também precisa reagir, chame o handler localmente.
- Use um campo `type` para que um único canal carregue vários tipos de mensagem.

## O padrão "o mestre executa"

Com sockets crus, todos os GMs conectados recebem a mensagem. Se houver dois GMs online,
os dois aplicariam o dano — duas vezes. Sempre eleja exatamente um cliente para agir:

```js
game.socket.on("system.forja", async (message) => {
  if (message.type !== "applyDamage") return;
  if (!game.user.isActiveGM) return; // só UM GM age
  const actor = await fromUuid(message.actorUuid);
  await actor?.applyDamage(message.amount);
});
```

`game.user.isActiveGM` é verdadeiro para exatamente um GM conectado (o "designado"). Se
nenhum GM estiver conectado, ninguém age — trate esse caso no remetente:

```js
if (!game.users.activeGM) {
  ui.notifications.warn("Nenhum GM está conectado.");
  return;
}
```

::: tip
Antes de enviar qualquer coisa, verifique se o usuário simplesmente pode fazer aquilo:
`actor.isOwner` significa que o jogador pode chamar `actor.update()` direto — sem socket.
:::

## Consultas a usuários (`User#query`)

Queries são mensagens de pedido/resposta construídas sobre o socket. Você registra um
handler com nome em `CONFIG.queries`, e qualquer cliente pode chamar
`algumUsuario.query(name, data)` e dar `await` no valor retornado pelo handler. Você **não**
precisa de `"socket": true` para queries, porque elas trafegam pelo canal do core.

`user.query(queryName, queryData, { timeout })`:

- `queryName` — uma chave registrada em `CONFIG.queries`.
- `queryData` — um objeto serializável em JSON.
- `timeout` — milissegundos até a Promise ser rejeitada.

O handler precisa estar registrado em **todos** os clientes (quem recebe é quem executa),
então registre no `init`.

::: v13
No V13 o handler recebe `(queryData, { timeout })`. Ele não sabe quem enviou a query;
se você precisa do remetente, coloque o id do usuário no payload — e lembre que um cliente
malicioso pode mentir sobre isso.

```js
CONFIG.queries["forja.ping"] = async (queryData, { timeout }) => {
  return `pong to ${queryData.userId}`;
};

const reply = await game.users.activeGM.query("forja.ping", { userId: game.user.id }, { timeout: 5000 });
```
:::

::: v14
No V14 o handler também recebe o id do usuário que enviou a query (no segundo argumento,
junto com `timeout`). Confira o nome exato da propriedade na
[documentação da API V14](https://foundryvtt.com/api/v14/classes/foundry.documents.User.html)
para o seu build; este guia lê o valor de forma defensiva e cai para o payload.

`User.queryMany(users, queryName, queryData, { timeout })` é estático. Ele retorna um
`Map<User, PromiseSettledResult>`, então um usuário lento ou desconectado não quebra os demais:

```js
const players = game.users.filter((u) => u.active && !u.isGM);
const results = await User.queryMany(players, "forja.ping", {}, { timeout: 5000 });
for (const [user, result] of results) {
  if (result.status === "fulfilled") console.log(user.name, result.value);
  else console.warn(user.name, "não respondeu", result.reason);
}
```
:::

## Exemplo completo: o jogador pede ao mestre para aplicar dano

O personagem do jogador ataca um goblin que o jogador não controla. O cliente do jogador
não pode atualizar o goblin, então pede ao GM.

### Método de dano compartilhado

```js
// systems/forja/module/documents/actor.mjs
export class ForjaActor extends Actor {
  /** Aplica dano e retorna o novo valor de PV. */
  async applyDamage(amount) {
    const hp = this.system.hp;
    const value = Math.clamp(hp.value - amount, 0, hp.max);
    await this.update({ "system.hp.value": value });
    return value;
  }
}
```

### Estilo 1: mensagem direta pelo socket (sem resposta)

```js
// systems/forja/module/socket.mjs
const CHANNEL = "system.forja";

Hooks.once("ready", () => {
  game.socket.on(CHANNEL, async (message) => {
    if (message.type !== "applyDamage") return;
    if (!game.user.isActiveGM) return;
    const target = await fromUuid(message.actorUuid);
    if (!target) return;
    const value = await target.applyDamage(message.amount);
    // Avisa todo mundo (inclusive quem pediu) com uma mensagem no chat.
    ChatMessage.create({ content: `${target.name} sofre ${message.amount} de dano (PV ${value}).` });
  });
});

export async function requestDamage(actor, amount) {
  if (actor.isOwner) return actor.applyDamage(amount); // não precisa pedir
  if (!game.users.activeGM) return ui.notifications.warn("Nenhum GM está conectado.");
  game.socket.emit(CHANNEL, { type: "applyDamage", actorUuid: actor.uuid, amount });
}
```

A desvantagem: o jogador nunca sabe se deu certo, e o GM não consegue responder com um valor.

### Estilo 2: consulta ao usuário (pedido e resposta)

```js
// systems/forja/module/queries.mjs
Hooks.once("init", () => {
  CONFIG.queries["forja.applyDamage"] = async (queryData, queryOptions = {}) => {
    // A query é enviada ao GM ativo, então isto roda no cliente do GM.
    const senderId = queryOptions.userId ?? queryOptions.user ?? queryData.userId;
    const sender = game.users.get(senderId);
    const target = await fromUuid(queryData.actorUuid);
    if (!target) throw new Error("Target not found");

    // Valida: o valor deve ser um inteiro positivo, e o remetente um usuário real.
    const amount = Number(queryData.amount);
    if (!sender || !Number.isInteger(amount) || amount < 0) throw new Error("Invalid request");

    const value = await target.applyDamage(amount);
    return { hp: value };
  };
});

export async function requestDamage(actor, amount) {
  if (actor.isOwner) return { hp: await actor.applyDamage(amount) };
  const gm = game.users.activeGM;
  if (!gm) {
    ui.notifications.warn("Nenhum GM está conectado.");
    return null;
  }
  try {
    return await gm.query(
      "forja.applyDamage",
      { actorUuid: actor.uuid, amount, userId: game.user.id },
      { timeout: 10_000 }
    );
  } catch (err) {
    ui.notifications.error(`O GM não conseguiu aplicar o dano: ${err.message}`);
    return null;
  }
}
```

Uso a partir de uma action da ficha (sheet) ou de uma macro:

```js
const target = game.user.targets.first()?.actor;
if (target) {
  const result = await requestDamage(target, 5);
  if (result) ui.notifications.info(`${target.name} agora tem ${result.hp} PV.`);
}
```

## Receitas comuns

- **Executar algo em todos os clientes, inclusive no remetente**: chame o handler localmente e depois faça `emit`.
- **Canal de módulo**: no `forja-extras` use `"module.forja-extras"` e `"socket": true` no `module.json`.
- **Nomes de query com namespace**: prefixe com o id do pacote (`forja.applyDamage`) para evitar colisões.
- **Queries embutidas**: o core registra entradas próprias em `CONFIG.queries` (por exemplo `dialog`); nunca as sobrescreva.

## Armadilhas

::: warning
- Esquecer `"socket": true` — o `emit` funciona, mas ninguém recebe nada.
- Agir em todos os clientes de GM — sempre proteja com `game.user.isActiveGM`.
- Enviar objetos Document — eles não são serializáveis; envie o `uuid`.
- Confiar no payload — o handler do GM roda com direitos de GM; valide cada campo.
- Registrar o handler da query só no cliente do GM — o GM pode mudar; registre em todos os clientes no `init`.
- Não tratar timeouts — `user.query` rejeita se o alvo desconectar ou se o handler lançar erro.
:::
