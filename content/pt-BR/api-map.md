# Guia rápido da API

Uma referência rápida de "quero… → use isto" para as APIs do Foundry que você usa todo dia, no V13 e no V14.

::: changed
- `foundry.utils.objectsEqual` → `foundry.utils.equals`; `game.i18n.localize` agora aceita dados (mais o alias `_loc`).
- `ActiveEffect#changes` → `effect.system.changes`; `CONFIG.statusEffects` é um objeto.
- `MeasuredTemplate` removido (use Regions); `rollMode` → `messageMode`; `MESSAGE_PATTERNS` → `CHAT_COMMANDS`.
- `User.queryMany` adicionado. Veja [a lista completa de mudanças](#changes-14).
:::

## Espaços de nomes: globais antigos → caminhos do V13+

O V13 moveu a maioria das classes para namespaces `foundry.*`. Os globais antigos ainda
funcionam (com aviso de depreciação) até o V15, então código novo deve sempre usar o caminho
com namespace. Classes de documento (`Actor`, `Item`, `ChatMessage`, `Roll`…) continuam
sendo globais válidos.

| Global antigo | Caminho com namespace (V13 e V14) |
| --- | --- |
| `Application` | `foundry.appv1.api.Application` (legado — prefira ApplicationV2) |
| `FormApplication` | `foundry.appv1.api.FormApplication` (legado) |
| `Dialog` | `foundry.appv1.api.Dialog` (legado — prefira `DialogV2`) |
| `ActorSheet` / `ItemSheet` | `foundry.appv1.sheets.ActorSheet` / `ItemSheet` (legado) |
| — | `foundry.applications.api.ApplicationV2` |
| — | `foundry.applications.api.HandlebarsApplicationMixin` |
| — | `foundry.applications.api.DialogV2` |
| — | `foundry.applications.api.DocumentSheetV2` |
| — | `foundry.applications.sheets.ActorSheetV2` / `ItemSheetV2` |
| `DocumentSheetConfig` | `foundry.applications.apps.DocumentSheetConfig` |
| `FilePicker` | `foundry.applications.apps.FilePicker` |
| `TextEditor` | `foundry.applications.ux.TextEditor.implementation` |
| `DragDrop` | `foundry.applications.ux.DragDrop` |
| `ContextMenu` | `foundry.applications.ux.ContextMenu` |
| `loadTemplates` / `renderTemplate` | `foundry.applications.handlebars.loadTemplates` / `renderTemplate` |
| `Actors` / `Items` | `foundry.documents.collections.Actors` / `Items` |
| `CompendiumCollection` | `foundry.documents.collections.CompendiumCollection` |
| `ChatLog` | `foundry.applications.sidebar.tabs.ChatLog` |
| `Token` | `foundry.canvas.placeables.Token` |
| `TokenLayer` | `foundry.canvas.layers.TokenLayer` |
| `ClientSettings` | `foundry.helpers.ClientSettings` |

::: tip
Não sabe onde algo mora? No console do navegador, digite `foundry.` e deixe o autocomplete
guiar você, ou pesquise na [API V13](https://foundryvtt.com/api/v13/) /
[API V14](https://foundryvtt.com/api/v14/). O aviso de depreciação no console também mostra o caminho novo.
:::

## Chaves de CONFIG que você vai usar

| Quero… | Chave | Exemplo |
| --- | --- | --- |
| Usar minha própria classe de Actor | `CONFIG.Actor.documentClass` | `CONFIG.Actor.documentClass = ForjaActor` |
| Definir os dados dos tipos de actor | `CONFIG.Actor.dataModels` | `CONFIG.Actor.dataModels.character = CharacterData` |
| Escolher atributos das barras do token | `CONFIG.Actor.trackableAttributes` | `{ character: { bar: ["hp"], value: ["might"] } }` |
| Usar minha própria classe de Item | `CONFIG.Item.documentClass` | `CONFIG.Item.documentClass = ForjaItem` |
| Definir os dados dos tipos de item | `CONFIG.Item.dataModels` | `CONFIG.Item.dataModels.weapon = WeaponData` |
| Definir a fórmula de iniciativa | `CONFIG.Combat.initiative` | `{ formula: "1d20 + @might", decimals: 2 }` |
| Registrar uma classe de Roll própria | `CONFIG.Dice.rolls` | `CONFIG.Dice.rolls.push(ForjaRoll)` |
| Substituir as condições de status | `CONFIG.statusEffects` | veja abaixo |
| Adicionar enrichers de texto inline | `CONFIG.TextEditor.enrichers` | `push({ pattern, enricher })` |
| Tratar user queries | `CONFIG.queries` | `CONFIG.queries["forja.applyDamage"] = fn` |
| Adicionar ações de movimento de token | `CONFIG.Token.movement.actions` | `CONFIG.Token.movement.actions.fly = {...}` |
| Adicionar um tipo de Region behavior | `CONFIG.RegionBehavior.dataModels` | `CONFIG.RegionBehavior.dataModels["forja.trap"] = TrapBehavior` |

```js
// systems/forja/forja.mjs
Hooks.once("init", () => {
  CONFIG.Actor.documentClass = ForjaActor;
  CONFIG.Actor.dataModels = { character: CharacterData, npc: NpcData };
  CONFIG.Actor.trackableAttributes = {
    character: { bar: ["hp"], value: ["might"] },
    npc: { bar: ["hp"], value: [] }
  };
  CONFIG.Item.documentClass = ForjaItem;
  CONFIG.Item.dataModels = { weapon: WeaponData, spell: SpellData };
  CONFIG.Combat.initiative = { formula: "1d20 + @might", decimals: 2 };

  // [[/dano 2d6]] → um link de dano clicável
  CONFIG.TextEditor.enrichers.push({
    pattern: /\[\[\/dano (?<formula>[^\]]+)\]\]/gi,
    enricher: async (match) => {
      const a = document.createElement("a");
      a.classList.add("forja-damage");
      a.dataset.formula = match.groups.formula;
      a.textContent = match.groups.formula;
      return a;
    }
  });
});
```

### Efeitos de status

::: v13
`CONFIG.statusEffects` é um **array** de `{ id, name, img }`.

```js
CONFIG.statusEffects = [
  { id: "dead", name: "FORJA.StatusDead", img: "icons/svg/skull.svg" },
  { id: "stunned", name: "FORJA.StatusStunned", img: "icons/svg/daze.svg" }
];
```
:::

::: v14
`CONFIG.statusEffects` é um **objeto** indexado por id (arrays ainda são aceitos por compatibilidade).

```js
CONFIG.statusEffects = {
  dead: { id: "dead", name: "FORJA.StatusDead", img: "icons/svg/skull.svg" },
  stunned: { id: "stunned", name: "FORJA.StatusStunned", img: "icons/svg/daze.svg" }
};
```
:::

## Objetos `game.*`

| Objeto | O que é | Uso típico |
| --- | --- | --- |
| `game.actors` | Coleção de Actors do mundo | `game.actors.getName("Goblin")` |
| `game.items` | Coleção de Items do mundo | `game.items.filter((i) => i.type === "weapon")` |
| `game.packs` | Todos os compêndios | `game.packs.get("forja.monsters")` |
| `game.settings` | Registro de configurações | `game.settings.get("forja", "systemMigrationVersion")` |
| `game.i18n` | Localização | `game.i18n.localize("FORJA.Attack")` |
| `game.user` | O usuário atual | `game.user.isGM`, `game.user.isActiveGM`, `game.user.targets` |
| `game.users` | Todos os usuários | `game.users.activeGM`, `game.users.filter((u) => u.active)` |
| `game.socket` | Cliente Socket.io | `game.socket.emit("system.forja", data)` — veja [comunicação entre clientes](#sockets) |
| `game.system` | O pacote de sistema ativo | `game.system.id`, `game.system.version` |
| `game.modules` | Todos os módulos instalados | `game.modules.get("forja-extras")?.active` |
| `game.release` | Informações da versão do core | `game.release.generation` (13 ou 14), `game.version` |

## Funções auxiliares de `foundry.utils`

| Helper | O que faz |
| --- | --- |
| `mergeObject(original, other, options)` | Merge profundo; retorna `original` (alterado) a menos que `{ inplace: false }` |
| `deepClone(obj)` | Cópia profunda que trata bem Dates, Sets e instâncias de classe |
| `duplicate(obj)` | Cópia via JSON (perde funções/Dates) — prefira `deepClone` |
| `getProperty(obj, "a.b.c")` | Lê um caminho com pontos |
| `setProperty(obj, "a.b.c", v)` | Grava um caminho com pontos; retorna `true` se mudou |
| `expandObject({ "a.b": 1 })` | `{ a: { b: 1 } }` — dados de formulário para objeto aninhado |
| `flattenObject({ a: { b: 1 } })` | `{ "a.b": 1 }` — objeto aninhado para chaves de update |
| `randomID(length = 16)` | Id aleatório no estilo de documento |
| `isNewerVersion(v1, v0)` | `true` se `v1` for mais nova que `v0` |
| `debounce(fn, ms)` | Adia chamadas até passar `ms` sem novas chamadas |
| `isEmpty(value)` | `true` para `undefined`, `{}`, `[]` e Sets/Maps vazios |

::: v13
- Igualdade profunda: `foundry.utils.objectsEqual(a, b)`.
- `debounce` retorna uma função simples.
:::

::: v14
- Igualdade profunda: `foundry.utils.equals(a, b)` (substitui `objectsEqual`).
- `debounce(fn, ms).cancel()` cancela uma chamada pendente.
- Novos: `foundry.utils.isPlainObject`, `diffObject(a, b, { bidirectional: true })`, `buildRelativeUuid`.
:::

```js
const { mergeObject, getProperty, expandObject, isNewerVersion } = foundry.utils;

const defaults = { hp: { value: 10, max: 10 }, might: 1 };
const data = mergeObject(defaults, { hp: { value: 4 } }, { inplace: false });
getProperty(data, "hp.value"); // 4
expandObject({ "system.hp.value": 3 }); // { system: { hp: { value: 3 } } }
isNewerVersion("2.1.0", "2.0.9"); // true
```

## V13 → V14: renomeados e substituídos

| Quero… | V13 | V14 |
| --- | --- | --- |
| Ler as changes de um efeito | `effect.changes` | `effect.system.changes` |
| Operação da change | `mode: CONST.ACTIVE_EFFECT_MODES.ADD` (número) | `type: "add"` (string) |
| Duração do efeito | `{ rounds, turns, seconds, … }` | `{ value, units, expiry, expired }` |
| Templates de área | `MeasuredTemplate` | Scene Regions (formas cone, linha, anel, emanação) |
| Classes de forma de Region | `RegionShape` | `BaseShapeData` |
| Árvore de polígonos de Region | `foundry.data.regionShapes.RegionPolygonTree` | `foundry.data.PolygonTree` |
| Privacidade da rolagem | `roll.toMessage(data, { rollMode })` | `roll.toMessage(data, { messageMode })` |
| Aplicar um modo aos dados do chat | `ChatMessage.applyRollMode(data, mode)` | `ChatMessage.applyMode(data, mode)` |
| Comandos de chat | `ChatLog.MESSAGE_PATTERNS` | `ChatLog.CHAT_COMMANDS` |
| Lista de status effects | array | objeto indexado por id |
| Excluir uma chave num update | `"-=key": null` | `foundry.data.operators.ForcedDeletion` |
| Substituir uma chave num update | `"==key": value` | `foundry.data.operators.ForcedReplacement` |
| Igualdade profunda | `foundry.utils.objectsEqual` | `foundry.utils.equals` |
| Localizar com dados | `game.i18n.format(key, data)` | `game.i18n.localize(key, data)` / `_loc(key, data)` |
| Consultar vários usuários | laço com `user.query(...)` | `User.queryMany(users, name, data)` |
| Limpar um placeable | sobrescrever `clear()` | sobrescrever `_clear()` |
| Camada de canvas própria | `layerClass` no CONFIG do documento | depreciado — veja a documentação da API |
| Opções de pathfinding | `ignoreWalls`, `ignoreCost`, `history` | `constrainOptions` |
| Opções de animação de movimento | `getAnimationOptions(token)` recebe um `Token` | `TokenMovementActionConfig#getAnimationOptions(tokenDocument)` |
| Plugins do ProseMirror | `foundry.prosemirror.defaultPlugins` | `ProseMirrorEditor.buildDefaultPlugins()` |
| Definição do schema de dados | `template.json` (ainda funciona) | `documentTypes` + data models (`template.json` depreciado) |

::: warning
`ChatMessage.applyRollMode` é o nome no V13 do helper estático de roll mode; confirme na
[API V13](https://foundryvtt.com/api/v13/) antes de depender dele. Para o checklist completo
de migração, veja [Migrando seu pacote do V13 para o V14](#migrations).
:::

## Armadilhas

::: warning
- Defaults com `mergeObject`: ele **altera** o primeiro argumento, a menos que `inplace: false`.
- `setProperty` num Document não salva nada — use `doc.update({ "a.b": v })`.
- `game.packs.get` precisa do id completo da coleção (`"forja.monsters"`), não só do nome do pack.
- `game.user.isGM` é verdadeiro para todo GM; use `isActiveGM` quando só um cliente deve agir.
:::
