# Configurações e atalhos de teclado

As configurações guardam valores do seu pacote, por mundo, por navegador ou por usuário, e os atalhos de teclado permitem que os jogadores acionem seus recursos pelo teclado.

## O que é uma configuração

Uma configuração é um valor com nome dentro do namespace do seu pacote (`forja-extras.restHealing`). Você a **registra** uma vez no `init` e depois a **lê** e **grava** em qualquer lugar com `game.settings.get` / `game.settings.set`. O Foundry cuida do armazenamento, da interface de Configurar Opções, das permissões e da sincronização.

A decisão mais importante é o **escopo** (scope):

| Escopo | Guardado em | Compartilhado com | Quem pode alterar | Use para |
| --- | --- | --- | --- | --- |
| `world` | Banco de dados do mundo | Todos os usuários do mundo | GM (usuários com `SETTINGS_MODIFY`) | Regras do jogo, regras da casa |
| `client` | `localStorage` do navegador | Ninguém — só este navegador | O usuário atual | Preferências de exibição, opções de desempenho |
| `user` | Banco de dados do mundo, por usuário | Só aquele usuário, em qualquer dispositivo | Aquele usuário | Preferências pessoais que devem acompanhar o jogador |

O escopo `user` foi adicionado na V13. Antes dele, preferências por jogador precisavam ser `client` e se perdiam quando o jogador trocava de computador.

## Registre as configurações

```js
// modules/forja-extras/scripts/settings.js
export function registerSettings() {
  // Regra do mundo: aparece em Configurar Opções, só para o GM
  game.settings.register("forja-extras", "restHealing", {
    name: "FORJA_EXTRAS.Settings.RestHealing.Name",
    hint: "FORJA_EXTRAS.Settings.RestHealing.Hint",
    scope: "world",
    config: true,
    type: Boolean,
    default: true,
    onChange: (value) => console.log(`forja-extras | Cura no descanso agora é ${value}`)
  });

  // Número com um controle deslizante
  game.settings.register("forja-extras", "restDice", {
    name: "FORJA_EXTRAS.Settings.RestDice.Name",
    scope: "world",
    config: true,
    type: Number,
    range: { min: 1, max: 6, step: 1 },
    default: 2
  });

  // Lista suspensa, por usuário (acompanha o jogador em qualquer dispositivo)
  game.settings.register("forja-extras", "restAnnounce", {
    name: "FORJA_EXTRAS.Settings.RestAnnounce.Name",
    scope: "user",
    config: true,
    type: String,
    choices: {
      chat: "FORJA_EXTRAS.Settings.RestAnnounce.Chat",
      notify: "FORJA_EXTRAS.Settings.RestAnnounce.Notify",
      none: "FORJA_EXTRAS.Settings.RestAnnounce.None"
    },
    default: "chat"
  });

  // Uma instância de DataField como tipo: validada como um campo de schema
  game.settings.register("forja-extras", "maxRestsPerDay", {
    name: "FORJA_EXTRAS.Settings.MaxRests.Name",
    scope: "world",
    config: true,
    type: new foundry.data.fields.NumberField({ required: true, integer: true, min: 0, max: 10, initial: 1 }),
    default: 1,
    requiresReload: true
  });

  // Só do cliente, escondida da interface: estado interno deste navegador
  game.settings.register("forja-extras", "lastSeenVersion", {
    scope: "client",
    config: false,
    type: String,
    default: ""
  });
}
```

```js
// modules/forja-extras/scripts/main.js
import { registerSettings, registerRestMenu } from "./settings.js";
import { registerKeybindings } from "./keybindings.js";

Hooks.once("init", () => {
  registerSettings();
  registerRestMenu();    // veja "Um menu de configurações" abaixo
  registerKeybindings(); // veja "Atalhos de teclado" abaixo
});
```

### Opções de registro

| Opção | Significado |
| --- | --- |
| `name`, `hint` | Chaves de localização (ou texto) exibidas em Configurar Opções |
| `scope` | `"world"`, `"client"` ou `"user"` |
| `config` | `true` para exibir em Configurar Opções; `false` para configurações ocultas/internas |
| `type` | `String`, `Number`, `Boolean`, `Object`, `Array`, uma classe `DataModel` ou uma instância de `DataField` |
| `choices` | Objeto `{ valor: chaveDoRótulo }`; exibe uma lista suspensa (os rótulos são localizados) |
| `range` | `{ min, max, step }` para `Number`; exibe um controle deslizante |
| `default` | Valor retornado até alguém salvar outro |
| `onChange` | Chamado com o novo valor em todo cliente onde ele mudou |
| `requiresReload` | Pede ao usuário que recarregue depois de alterar |
| `restricted` | (menus) Só GMs podem abrir |

::: warning
`Symbol` não é permitido como tipo de configuração. Use `String` com `choices`.
:::

## Ler e gravar

```js
// Ler: síncrono
const healing = game.settings.get("forja-extras", "restHealing");

// Gravar: assíncrono, retorna o valor salvo
await game.settings.set("forja-extras", "restDice", 3);
```

Gravar uma configuração `world` exige a permissão `SETTINGS_MODIFY` (por padrão, um GM). Se a ação de um jogador precisar alterar uma configuração do mundo, envie o pedido a um GM (veja [comunicação entre clientes](#sockets)).

::: tip
Leia as configurações no hook `setup` ou depois. O registro acontece no `init`, e os valores do mundo só têm garantia de estar carregados depois disso.
:::

## Um menu de configurações com ApplicationV2

Quando um grupo de opções faz sentido junto, registre um **menu**: um botão em Configurar Opções que abre o seu próprio formulário. Guarde os valores em uma configuração oculta cujo tipo é um `DataModel`, para que sejam validados como um todo.

```js
// modules/forja-extras/scripts/rest-rules.js
const { NumberField, BooleanField } = foundry.data.fields;

export class RestRules extends foundry.abstract.DataModel {
  static LOCALIZATION_PREFIXES = ["FORJA_EXTRAS.RestRules"];

  static defineSchema() {
    return {
      healPercent: new NumberField({ required: true, integer: true, min: 0, max: 100, initial: 50 }),
      removeEffects: new BooleanField({ initial: true })
    };
  }
}
```

```js
// modules/forja-extras/scripts/rest-config.js
import { RestRules } from "./rest-rules.js";
const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

export class RestConfig extends HandlebarsApplicationMixin(ApplicationV2) {
  static DEFAULT_OPTIONS = {
    id: "forja-extras-rest-config",
    tag: "form",
    window: { title: "FORJA_EXTRAS.RestConfig.Title", icon: "fa-solid fa-bed", contentClasses: ["standard-form"] },
    position: { width: 420 },
    form: { handler: RestConfig.#onSubmit, closeOnSubmit: true }
  };

  static PARTS = {
    form: { template: "modules/forja-extras/templates/rest-config.hbs" },
    footer: { template: "templates/generic/form-footer.hbs" }
  };

  async _prepareContext(options) {
    return {
      rules: game.settings.get("forja-extras", "restRules"),
      fields: RestRules.schema.fields,
      buttons: [{ type: "submit", icon: "fa-solid fa-floppy-disk", label: "FORJA_EXTRAS.RestConfig.Save" }]
    };
  }

  /** Salva o formulário enviado na configuração */
  static async #onSubmit(event, form, formData) {
    await game.settings.set("forja-extras", "restRules", foundry.utils.expandObject(formData.object));
  }
}
```

```hbs
{{!-- modules/forja-extras/templates/rest-config.hbs --}}
<section class="forja-extras-rest-config">
  {{formGroup fields.healPercent value=rules.healPercent localize=true}}
  {{formGroup fields.removeEffects value=rules.removeEffects localize=true}}
</section>
```

```js
// modules/forja-extras/scripts/settings.js (continuação)
import { RestRules } from "./rest-rules.js";
import { RestConfig } from "./rest-config.js";

export function registerRestMenu() {
  game.settings.register("forja-extras", "restRules", {
    scope: "world",
    config: false, // editada pelo menu, não listada diretamente
    type: RestRules,
    default: {}
  });

  game.settings.registerMenu("forja-extras", "restRulesMenu", {
    name: "FORJA_EXTRAS.RestConfig.Name",
    label: "FORJA_EXTRAS.RestConfig.Label", // texto do botão
    hint: "FORJA_EXTRAS.RestConfig.Hint",
    icon: "fa-solid fa-bed",
    type: RestConfig,
    restricted: true // só GM
  });
}

// RestRules não é data model de documento, então localizamos os rótulos dos campos nós mesmos
Hooks.once("i18nInit", () => foundry.helpers.Localization.localizeDataModel(RestRules));
```

`game.settings.get("forja-extras", "restRules")` agora retorna uma instância de `RestRules`, então `rules.healPercent` é sempre um inteiro válido entre 0 e 100.

## Reagindo a mudanças

- `onChange` no registro é a opção mais simples e roda em todo cliente onde o valor mudou.
- O hook `clientSettingChanged` dispara para configurações `client`.
- Configurações `world` e `user` são documentos `Setting`, então os hooks `updateSetting` / `createSetting` também disparam para elas.

## Atalhos de teclado

Atalhos são registrados como as configurações (no `init`), aparecem em **Configurar Controles** e podem ser remapeados por cada usuário.

```js
// modules/forja-extras/scripts/keybindings.js
export function registerKeybindings() {
  game.keybindings.register("forja-extras", "quickRest", {
    name: "FORJA_EXTRAS.Keybindings.QuickRest.Name",
    hint: "FORJA_EXTRAS.Keybindings.QuickRest.Hint",
    // Atalho padrão: Shift + R. Os usuários podem alterar ou adicionar outros.
    editable: [{ key: "KeyR", modifiers: ["Shift"] }],
    onDown: (context) => {
      const tokens = canvas.tokens?.controlled ?? [];
      if (!tokens.length) return false; // não tratado: deixa outros atalhos tentarem
      for (const token of tokens) {
        const actor = token.actor;
        if (actor?.isOwner) actor.update({ "system.hp.value": actor.system.hp.max });
      }
      return true; // tratado: o evento para aqui
    },
    restricted: false, // true = só GM
    precedence: CONST.KEYBINDING_PRECEDENCE.NORMAL
  });
}
```

| Opção | Significado |
| --- | --- |
| `editable` | Atalhos padrão que o usuário pode alterar: `{ key, modifiers }`, onde `key` é um `KeyboardEvent.code` (`"KeyR"`, `"Digit1"`, `"F2"`) |
| `uneditable` | Atalhos que o usuário não pode remover |
| `onDown` / `onUp` | Handlers; retorne `true` para marcar o evento como tratado |
| `repeat` | Se `onDown` dispara repetidamente enquanto a tecla está pressionada |
| `restricted` | Só GMs podem usar |
| `precedence` | `CONST.KEYBINDING_PRECEDENCE.PRIORITY`, `NORMAL` ou `DEFERRED` — ordem em relação aos atalhos do core |

::: tip
Os modificadores são escritos como `"Shift"`, `"Control"` e `"Alt"`. `"Control"` é tratado automaticamente como ⌘ no macOS.
:::

## Armadilhas

- **Registrar fora do `init`.** Configurações e atalhos registrados depois não aparecem nos diálogos de configuração.
- **Usar `client` para regras do jogo.** Cada navegador teria seu próprio valor; regras precisam ser `world`.
- **Jogadores gravando configurações do mundo.** `game.settings.set` rejeita; encaminhe por um GM.
- **Alterar o objeto retornado.** `game.settings.get` de uma configuração `Object`/`DataModel` retorna dados que você deve tratar como somente leitura; altere com `set`.
- **Nomes sem localização.** Use chaves em `name`, `hint`, `choices` e no `label` do menu; o Foundry as localiza.
- **Esquecer o `default`.** Sem ele, `get` retorna `undefined` até o primeiro salvamento.
