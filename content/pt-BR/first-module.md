# Seu primeiro módulo

Construa o `forja-extras` passo a passo: manifesto, script de entrada, uma configuração, traduções, um comando de chat e um botão no cabeçalho das fichas.

::: changed
- `game.i18n.localize()` agora aceita dados para placeholders (ele absorveu o `format()`), e existe um atalho global **`_loc(key, data)`**.
- Controles de cabeçalho e entradas de menu de contexto compartilham um só formato (`label`, `icon`, `onClick`, `visible`).
- A entrada do chat agora é um editor ProseMirror embutido, então o hook `chatMessage` pode receber HTML — remova as tags antes de interpretar comandos.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que vamos construir

Um módulo que:

1. Registra no log quando carrega (hooks `init` e `ready`).
2. Registra uma **configuração de mundo** com um texto de boas-vindas.
3. Envia as boas-vindas ao chat para o Mestre quando o mundo fica pronto.
4. Trata um comando de chat `/forja hello`.
5. Adiciona um botão **"Rolagem rápida"** ao menu do cabeçalho de toda ficha de ator.

Ele funciona em qualquer sistema, mas declaramos o `forja` como alvo para combinar com o resto do guia.

## 1. Estrutura de pastas

```bash
Data/modules/forja-extras/
├── module.json
├── scripts/
│   └── main.mjs
├── lang/
│   ├── en.json
│   └── pt-BR.json
└── styles/
    └── forja-extras.css
```

Se o seu repositório fica em outro lugar, crie um symlink como explicado em [Ambiente](#setup).

## 2. O manifesto

::: v13
```json
{
  "id": "forja-extras",
  "title": "Forja Extras",
  "description": "Ferramentas de conveniência para o sistema Forja.",
  "version": "0.1.0",
  "compatibility": { "minimum": "13", "verified": "13.351" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "flags": {
    "hotReload": { "extensions": ["css", "json"], "paths": ["styles", "lang"] }
  }
}
```
:::

::: v14
```json
{
  "id": "forja-extras",
  "type": "module",
  "title": "Forja Extras",
  "description": "Ferramentas de conveniência para o sistema Forja.",
  "version": "0.1.0",
  "compatibility": { "minimum": "14", "verified": "14.368" },
  "esmodules": ["scripts/main.mjs"],
  "styles": ["styles/forja-extras.css"],
  "languages": [
    { "lang": "en", "name": "English", "path": "lang/en.json" },
    { "lang": "pt-BR", "name": "Português (Brasil)", "path": "lang/pt-BR.json" }
  ],
  "flags": {
    "hotReload": { "extensions": ["css", "json"], "paths": ["styles", "lang"] }
  }
}
```
:::

Deixamos `relationships.systems` de fora por enquanto, para você poder testar em qualquer mundo. Cada campo é explicado em [o manifesto](#manifest).

## 3. Traduções

Coloque todo texto visível ao usuário em arquivos de idioma. As chaves ficam agrupadas sob um prefixo exclusivo do seu pacote (`FORJA_EXTRAS`) para nunca colidirem com o core ou com outros pacotes.

```json
{
  "FORJA_EXTRAS": {
    "Settings": {
      "Greeting": { "Name": "Greeting message", "Hint": "Posted to chat for the GM when the world loads." }
    },
    "DefaultGreeting": "The forge is hot, {name}!",
    "QuickRoll": "Quick roll",
    "QuickRollFlavor": "{actor} makes a quick roll",
    "UnknownCommand": "Unknown command: {cmd}"
  }
}
```

Salve isso como `lang/en.json`. O arquivo em português tem as **mesmas chaves**:

```json
{
  "FORJA_EXTRAS": {
    "Settings": {
      "Greeting": { "Name": "Mensagem de boas-vindas", "Hint": "Enviada ao chat para o Mestre quando o mundo carrega." }
    },
    "DefaultGreeting": "A forja está quente, {name}!",
    "QuickRoll": "Rolagem rápida",
    "QuickRollFlavor": "{actor} faz uma rolagem rápida",
    "UnknownCommand": "Comando desconhecido: {cmd}"
  }
}
```

::: tip
Objetos JSON aninhados viram chaves com pontos: `FORJA_EXTRAS.Settings.Greeting.Name`. Veja [Tradução](#localization).
:::

## 4. O script de entrada

Crie `scripts/main.mjs`. Guardamos o id do módulo em uma constante para nunca digitá-lo errado.

::: v13
```js
const MODULE_ID = "forja-extras";

// Auxiliar: localiza com ou sem dados para placeholders
const t = (key, data) =>
  data ? game.i18n.format(`FORJA_EXTRAS.${key}`, data) : game.i18n.localize(`FORJA_EXTRAS.${key}`);

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | init`);

  // Configurações precisam ser registradas no init, antes que algo as leia
  game.settings.register(MODULE_ID, "greeting", {
    name: "FORJA_EXTRAS.Settings.Greeting.Name",
    hint: "FORJA_EXTRAS.Settings.Greeting.Hint",
    scope: "world",      // salva no mundo, igual para todos; só Mestres podem mudar
    config: true,        // mostra em Configure Settings
    type: String,
    default: ""
  });
});

Hooks.once("ready", async () => {
  console.log(`${MODULE_ID} | ready`);
  if (!game.user.isGM) return;

  const custom = game.settings.get(MODULE_ID, "greeting");
  const text = custom || t("DefaultGreeting", { name: game.user.name });

  await ChatMessage.create({
    content: `<p>${text}</p>`,
    whisper: [game.user.id]   // só o Mestre vê
  });
});
```
:::

::: v14
```js
const MODULE_ID = "forja-extras";

// Auxiliar: na V14 localize() aceita dados de placeholder (format() não é mais necessário)
const t = (key, data) => game.i18n.localize(`FORJA_EXTRAS.${key}`, data);
// Atalho global equivalente: _loc("FORJA_EXTRAS.DefaultGreeting", { name })

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | init`);

  // Configurações precisam ser registradas no init, antes que algo as leia
  game.settings.register(MODULE_ID, "greeting", {
    name: "FORJA_EXTRAS.Settings.Greeting.Name",
    hint: "FORJA_EXTRAS.Settings.Greeting.Hint",
    scope: "world",      // salva no mundo, igual para todos; só Mestres podem mudar
    config: true,        // mostra em Configure Settings
    type: String,
    default: ""
  });
});

Hooks.once("ready", async () => {
  console.log(`${MODULE_ID} | ready`);
  if (!game.user.isGM) return;

  const custom = game.settings.get(MODULE_ID, "greeting");
  const text = custom || t("DefaultGreeting", { name: game.user.name });

  await ChatMessage.create({
    content: `<p>${text}</p>`,
    whisper: [game.user.id]   // só o Mestre vê
  });
});
```
:::

### Por que `init` e `ready`?

- **`init`** roda antes de os dados do mundo serem preparados. Registrar configurações, mudanças em `CONFIG`, fichas e data models é aqui.
- **`ready`** roda quando tudo já carregou. Ler documentos, criar mensagens de chat e falar com outros usuários é aqui.
- `Hooks.once` se desregistra depois da primeira chamada; use `Hooks.on` para eventos que se repetem.

Recarregue o mundo (F5), ative **Forja Extras** em *Manage Modules*, e você deve ver as boas-vindas no chat. Mude o texto em **Configure Settings → Forja Extras**.

## 5. Um comando de chat

O hook `chatMessage` dispara quando um usuário envia texto pela caixa do chat. Retornar `false` impede o Foundry de criar uma mensagem normal.

```js
Hooks.on("chatMessage", (chatLog, message, chatData) => {
  // Remove HTML (a entrada do chat da V14 é um editor de texto rico) e espaços extras
  const text = message.replace(/<[^>]*>/g, "").trim();
  if (!text.startsWith("/forja")) return; // não é nosso: deixa o Foundry tratar

  const [, cmd = ""] = text.split(/\s+/);
  if (cmd === "hello") {
    ChatMessage.create({
      speaker: chatData.speaker,
      content: `<p>${t("DefaultGreeting", { name: game.user.name })}</p>`
    });
  } else {
    ui.notifications.warn(t("UnknownCommand", { cmd: cmd || "(vazio)" }));
  }
  return false; // já tratamos: não publica o texto cru "/forja ..."
});
```

Adicione isso abaixo do hook `ready` em `main.mjs`. Digite `/forja hello` no chat para testar.

::: warning
O core é dono de comandos como `/roll`, `/whisper` e `/ooc`. Escolha um prefixo exclusivo do seu pacote e nunca retorne `false` para texto que você não tratou — isso engoliria a mensagem do usuário.
:::

## 6. Um botão no cabeçalho das fichas

Janelas ApplicationV2 têm um menu no cabeçalho (o botão "⋮"). Antes de montá-lo, o Foundry chama um hook chamado `getHeaderControls` + **nome da classe** para cada classe na cadeia de herança da aplicação. Escutar `getHeaderControlsActorSheetV2`, portanto, alcança toda ficha de ator construída sobre `ActorSheetV2`, seja qual for o sistema.

```js
Hooks.on("getHeaderControlsActorSheetV2", (app, controls) => {
  const actor = app.document;
  controls.push({
    icon: "fa-solid fa-dice-d20",
    label: "FORJA_EXTRAS.QuickRoll",       // localizado automaticamente
    action: "forjaExtrasQuickRoll",        // nome único, com prefixo para evitar colisões
    visible: () => actor.isOwner,          // só para usuários donos do ator
    onClick: async () => {
      const roll = await new Roll("1d20").evaluate();
      await roll.toMessage({
        speaker: ChatMessage.getSpeaker({ actor }),
        flavor: t("QuickRollFlavor", { actor: actor.name })
      });
    }
  });
});
```

Abra qualquer ficha de ator, clique no menu do cabeçalho e escolha **Rolagem rápida**.

::: tip
Descubra quais nomes de hook uma aplicação dispara definindo `CONFIG.debug.hooks = true` e abrindo-a: você verá `getHeaderControlsForjaActorSheet`, `getHeaderControlsActorSheetV2`, `getHeaderControlsDocumentSheetV2`, `getHeaderControlsApplicationV2`… Escolha o mais específico que cubra o que você precisa.
:::

::: v13
Na V13 uma entrada de controle de cabeçalho é `{ icon, label, action, onClick?, visible?, ownership? }`. O `onClick` recebe o `PointerEvent` do clique.
:::

::: v14
Na V14 controles de cabeçalho e entradas de menu de contexto foram unificados, então uma entrada segue o formato do menu de contexto (`label`, `icon`, `onClick`, `visible`, `group`, `classes`) mais `action` e `ownership`. O código acima funciona sem mudanças.
:::

## 7. Um pouco de CSS

`styles/forja-extras.css` é carregado em todas as páginas. Limite suas regras com uma classe para nunca mudar o visual do core por acidente:

```css
/* Só afeta mensagens de chat que marcamos com esta classe */
.chat-message .forja-extras-greeting {
  font-style: italic;
  color: var(--color-text-secondary);
}
```

Para usá-lo, mude o conteúdo das boas-vindas para `<p class="forja-extras-greeting">${text}</p>`. Com `flags.hotReload` definido, edições de CSS aplicam sem recarregar.

## O que conferir quando não funciona

- O módulo está **ativado** em *Manage Modules* (e você recarregou).
- O console (F12) mostra `forja-extras | init`. Se não, confira o caminho em `esmodules` e procure um erro de sintaxe em vermelho.
- As chaves aparecem cruas (`FORJA_EXTRAS.QuickRoll`) → o caminho do arquivo de idioma está errado ou o JSON é inválido.
- `game.settings.get` lança "not a registered game setting" → rodou antes do `init`, ou o id/chave está escrito errado.

## Próximos passos

- Transforme isso em um pacote de verdade para o seu jogo: [Seu primeiro sistema](#first-system).
- Aprofunde: [Ganchos de eventos](#hooks), [Configurações](#settings), [Tradução](#localization), [Chat e rolagens](#chat-roll).
- Publique: [Empacotamento e publicação](#packaging).
