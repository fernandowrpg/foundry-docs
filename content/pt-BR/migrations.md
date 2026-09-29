# Migrações de dados

Mantenha mundos antigos funcionando quando o formato dos seus dados muda, e leve seu pacote do V13 para o V14.

::: changed
- `ActiveEffect#changes` foi movido para `effect.system.changes`; o `mode` numérico virou um `type` em string.
- A `duration` do efeito agora é `{ value, units, expiry, expired }`.
- `template.json` está depreciado; use `documentTypes` no manifesto mais data models.
- `MeasuredTemplate` deixou de existir (absorvido pelas Regions); as chaves de update `-=` / `==` estão depreciadas.
- As depreciações do V12 foram removidas. Veja [a lista completa de mudanças](#changes-14).
:::

## Duas camadas de migração

O Foundry oferece duas ferramentas complementares, e um sistema maduro usa as duas:

| Camada | Onde | Quando roda | Persiste? |
| --- | --- | --- | --- |
| `static migrateData(source)` | Seu `TypeDataModel` | Toda vez que um documento é construído (carga, importação, compêndio) | Não — só em memória até o documento ser salvo |
| Script de migração do mundo | Hook `ready`, só no GM | Uma vez a cada nova versão do sistema | Sim — grava no banco de dados |

O `migrateData` é a rede de segurança: ele deixa dados antigos legíveis **em todo lugar**,
inclusive em compêndios e JSON importado. O script do mundo é a faxina: ele grava o novo
formato no disco, para que o `migrateData` acabe sem nada a fazer e para que consultas a dados
crus (como `pack.getIndex({ fields })`) vejam o formato novo.

## Por documento: `migrateData`

Suponha que a versão 1.x guardava os pontos de vida como um número `system.hp`, e a 2.0 usa `{ value, max }`.

```js
// systems/forja/module/data/character.mjs
const { HTMLField, NumberField, SchemaField } = foundry.data.fields;

export class CharacterData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      hp: new SchemaField({
        value: new NumberField({ integer: true, min: 0, initial: 10 }),
        max: new NumberField({ integer: true, min: 0, initial: 10 })
      }),
      might: new NumberField({ integer: true, min: 0, initial: 1 }),
      notes: new HTMLField()
    };
  }

  static migrateData(source) {
    // 1.x: hp era um número simples
    if (typeof source.hp === "number") {
      source.hp = { value: source.hp, max: source.hp };
    }
    // 1.x: "vigor" foi renomeado para "might"
    if ("vigor" in source && !("might" in source)) {
      source.might = source.vigor;
      delete source.vigor;
    }
    return super.migrateData(source);
  }
}
```

Regras para o `migrateData`:

- Ele recebe dados de **origem** (objeto simples), possivelmente parciais (updates também passam por ele). Verifique se a chave existe antes de mexer nela.
- Altere e retorne `source`; sempre chame `super.migrateData(source)`.
- Mantenha-o idempotente: rodar duas vezes não pode causar problema.
- Nunca leia outros documentos ou o estado de `game` aqui — ele pode rodar antes de o mundo estar pronto.

## Mantenha código antigo funcionando: `shimData`

Se outros módulos leem `actor.system.vigor`, renomear o campo quebra esses módulos. O
`shimData` permite adicionar um acessor depreciado aos dados preparados:

```js
static shimData(data, options) {
  data = super.shimData(data, options);
  if (!Object.hasOwn(data, "vigor")) {
    Object.defineProperty(data, "vigor", {
      get() {
        foundry.utils.logCompatibilityWarning(
          "system.vigor is deprecated, use system.might",
          { since: "Forja 2.0", until: "Forja 3.0" }
        );
        return this.might;
      },
      configurable: true,
      enumerable: false
    });
  }
  return data;
}
```

Anuncie uma versão de remoção e apague o shim quando chegar lá.

## Script de migração do mundo

```js
// systems/forja/module/migration.mjs
export const MIGRATION_VERSION = "2.0.0";

export function registerMigrationSetting() {
  game.settings.register("forja", "systemMigrationVersion", {
    scope: "world",
    config: false,
    type: String,
    default: ""
  });
}

export async function migrateWorldIfNeeded() {
  if (!game.user.isActiveGM) return;
  const current = game.settings.get("forja", "systemMigrationVersion");
  // Um mundo novo em folha não tem nada para migrar.
  if (!current && !game.actors.size && !game.items.size) {
    return game.settings.set("forja", "systemMigrationVersion", game.system.version);
  }
  if (current && !foundry.utils.isNewerVersion(MIGRATION_VERSION, current)) return;
  await migrateWorld();
  await game.settings.set("forja", "systemMigrationVersion", game.system.version);
}

/**
 * Retorna um objeto de update para os dados de origem de um Actor, ou null.
 * `source` vem de toObject(), então o migrateData JÁ rodou sobre ele:
 * mudanças tratadas lá só precisam ser gravadas de volta (veja `persist`).
 */
function migrateActorData(source, persist = false) {
  const update = {};
  // Persiste as correções em memória do migrateData (hp número → { value, max }).
  if (persist) update["system.hp"] = source.system.hp;
  // O que o migrateData não consegue: mover uma flag antiga para o schema.
  const notes = source.flags?.forja?.legacyNotes;
  if (notes !== undefined) {
    update["system.notes"] = notes;
    update["flags.forja.-=legacyNotes"] = null;
  }
  const items = (source.items ?? []).map((i) => {
    const u = migrateItemData(i);
    return u ? { _id: i._id, ...u } : null;
  }).filter(Boolean);
  if (items.length) update.items = items;
  return foundry.utils.isEmpty(update) ? null : update;
}

function migrateItemData(source) {
  const update = {};
  if (source.flags?.forja?.weight !== undefined) {
    update["system.weight"] = source.flags.forja.weight;
    update["flags.forja.-=weight"] = null;
  }
  return foundry.utils.isEmpty(update) ? null : update;
}

async function updateInBatches(cls, updates, options = {}, size = 100) {
  // diff: false envia os valores mesmo se forem iguais aos dados em memória (já migrados).
  for (let i = 0; i < updates.length; i += size) {
    await cls.updateDocuments(updates.slice(i, i + size), { diff: false, ...options });
  }
}

export async function migrateWorld() {
  const steps = 4;
  const bar = ui.notifications.info("Forja: migrando os dados do mundo…", { progress: true, permanent: true });
  const report = (step, message) => bar.update({ pct: step / steps, message });

  // 1. Actors do mundo (e seus items embutidos)
  const actorUpdates = game.actors.map((a) => {
    const u = migrateActorData(a.toObject(), true);
    return u ? { _id: a.id, ...u } : null;
  }).filter(Boolean);
  await updateInBatches(Actor, actorUpdates);
  report(1, "Actors migrados");

  // 2. Items do mundo
  const itemUpdates = game.items.map((i) => {
    const u = migrateItemData(i.toObject());
    return u ? { _id: i.id, ...u } : null;
  }).filter(Boolean);
  await updateInBatches(Item, itemUpdates);
  report(2, "Items migrados");

  // 3. Actors de tokens não vinculados nas cenas (os dados ficam no ActorDelta do token)
  for (const scene of game.scenes) {
    for (const token of scene.tokens) {
      if (token.actorLink || !token.actor) continue;
      const u = migrateActorData(token.actor.toObject());
      if (u) await token.actor.update(u, { diff: false });
    }
  }
  report(3, "Cenas migradas");

  // 4. Compêndios do mundo ou deste sistema
  for (const pack of game.packs) {
    if (!["Actor", "Item"].includes(pack.documentName)) continue;
    if (pack.metadata.packageType === "module") continue; // módulos migram os próprios packs
    const wasLocked = pack.locked;
    await pack.configure({ locked: false });
    const docs = await pack.getDocuments();
    const fn = pack.documentName === "Actor" ? (src) => migrateActorData(src, true) : migrateItemData;
    const updates = docs.map((d) => {
      const u = fn(d.toObject());
      return u ? { _id: d.id, ...u } : null;
    }).filter(Boolean);
    await updateInBatches(pack.documentClass, updates, { pack: pack.collection });
    await pack.configure({ locked: wasLocked });
  }
  report(4, "Compêndios migrados");
  bar.update({ pct: 1, message: "Forja: migração concluída" });
  setTimeout(() => ui.notifications.remove(bar), 3000);
}
```

```js
// systems/forja/forja.mjs
import { registerMigrationSetting, migrateWorldIfNeeded } from "./module/migration.mjs";

Hooks.once("init", registerMigrationSetting);
Hooks.once("ready", migrateWorldIfNeeded);
```

Por que essas escolhas:

- **`isActiveGM`** — só um cliente pode gravar; senão dois GMs disputam entre si.
- **`toObject()`** — retorna dados de origem que *já* passaram pelo `migrateData`, então não dá para detectar o formato antigo ali. Em vez disso, grave os valores migrados de volta com `diff: false` (senão o Foundry vê "nada mudou" e não envia nada), e use o script para o que o `migrateData` não consegue fazer, como mover flags para o schema.
- **Actors de tokens** — em tokens não vinculados só o delta é guardado; pulamos a gravação forçada de `hp` ali para não copiar os valores do actor base para cada delta.
- **Lotes** — um único `updateDocuments` com milhares de entradas pode estourar o tempo do socket.
- **Só packs do sistema** — módulos devem migrar os próprios compêndios.

::: warning
Peça aos GMs que **façam backup do mundo** antes de atualizar. Migrações não podem ser desfeitas.
:::

::: tip
A notificação com `progress: true` (V13+) substitui o depreciado
`SceneNavigation.displayProgressBar`. Chame `update({ pct, message })` no objeto retornado.
:::

## Migrando seu pacote do V13 para o V14

### Lista de verificação

- [ ] `compatibility` no manifesto: `{ "minimum": "13", "verified": "14" }` se você suporta os dois, ou `"minimum": "14"` se abandonar o V13. Opcionalmente adicione `"type": "system"` / `"module"`.
- [ ] Troque o `template.json` por `documentTypes` no `system.json` e `CONFIG.<Doc>.dataModels`.
- [ ] Active Effects: `changes` → `system.changes`, `mode` (número) → `type` (string). Veja o código abaixo.
- [ ] Duração de efeitos: leia `{ value, units, expiry, expired }`; as unidades vêm de `CONST.ACTIVE_EFFECT_DURATION_UNITS`.
- [ ] Remova qualquer uso de `CONFIG.ActiveEffect.legacyTransferral`.
- [ ] `MeasuredTemplate` → Scene Regions (formas cone, linha, anel, emanação; `RegionLayer#placeRegion`).
- [ ] `Roll#toMessage(data, { rollMode })` → `{ messageMode }`; use `ChatMessage.applyMode(chatData, mode)`.
- [ ] `ChatLog.MESSAGE_PATTERNS` → `ChatLog.CHAT_COMMANDS`.
- [ ] `CONFIG.statusEffects` é um objeto indexado por id (arrays ainda são aceitos).
- [ ] `"-=key": null` / `"==key": value` → `foundry.data.operators.ForcedDeletion` / `ForcedReplacement`.
- [ ] Remova código que dependia das depreciações do V12 — elas não existem mais no V14.
- [ ] `RegionShape` → `BaseShapeData`; `foundry.data.regionShapes.RegionPolygonTree` → `foundry.data.PolygonTree`.
- [ ] Sobrescreva `PlaceableObject#_clear` em vez de `clear`.
- [ ] Pare de definir `layerClass` no CONFIG de documentos de canvas.
- [ ] Opções `ignoreWalls` / `ignoreCost` / `history` de `Token#findMovementPath` → `constrainOptions`.
- [ ] `foundry.utils.objectsEqual` → `foundry.utils.equals`.
- [ ] `game.i18n.format(key, data)` → `game.i18n.localize(key, data)` (ou `_loc(key, data)`).
- [ ] Teste numa **instalação limpa do V14** — o V14 não atualiza no lugar a partir do V13.

### Mudanças nos efeitos ativos: V13 e V14

::: v13
```js
// Dados de origem de um efeito no V13
const effectData = {
  name: "Bless",
  changes: [
    { key: "system.attack.bonus", mode: CONST.ACTIVE_EFFECT_MODES.ADD, value: "2", priority: 20 }
  ],
  duration: { rounds: 10 }
};
```
:::

::: v14
```js
// Dados de origem de um efeito no V14
const effectData = {
  name: "Bless",
  system: {
    changes: [
      { key: "system.attack.bonus", type: "add", value: 2, phase: "initial", priority: 20 }
    ]
  },
  duration: { value: 10, units: "rounds", expiry: "turnEnd" }
};
```
:::

O core migra os dados de efeito que ele mesmo guarda, mas o seu **código** e qualquer dado de
efeito que você monta em tempo de execução (ou guarda em `flags`, macros, importações JSON)
precisam ser atualizados. Um helper que lê os dois formatos permite que um único código rode
nas duas versões:

```js
// systems/forja/module/compat/effects.mjs
const MODE_TO_TYPE = { 0: "custom", 1: "multiply", 2: "add", 3: "downgrade", 4: "upgrade", 5: "override" };

/** Retorna as changes no formato do V14, qualquer que seja a versão em execução. */
export function getEffectChanges(effect) {
  const raw = effect.system?.changes ?? effect.changes ?? [];
  return raw.map((c) => ({
    key: c.key,
    value: c.value,
    type: c.type ?? MODE_TO_TYPE[c.mode] ?? "custom",
    priority: c.priority ?? null
  }));
}

/** Converte dados de origem antigos de efeito (ex.: de flags ou JSON) para o formato do V14. */
export function migrateEffectSource(source) {
  if (!Array.isArray(source.changes)) return source;
  source.system ??= {};
  source.system.changes = source.changes.map((c) => ({
    key: c.key,
    value: c.value,
    type: MODE_TO_TYPE[c.mode] ?? "custom",
    phase: "initial",
    priority: c.priority ?? undefined
  }));
  delete source.changes;
  return source;
}
```

::: warning
O mapeamento acima segue os números de `CONST.ACTIVE_EFFECT_MODES` do V13
(CUSTOM 0, MULTIPLY 1, ADD 2, DOWNGRADE 3, UPGRADE 4, OVERRIDE 5). O V14 também tem `subtract`,
que não tem equivalente no V13. Confira com `CONST.ACTIVE_EFFECT_CHANGE_TYPES` na
[API V14](https://foundryvtt.com/api/v14/).
:::

### Operadores de exclusão

::: v13
```js
await actor.update({ "system.-=obsoleteField": null });
```
:::

::: v14
```js
const { ForcedDeletion } = foundry.data.operators;
await actor.update({ "system.obsoleteField": ForcedDeletion.create() });
```
A sintaxe `-=` ainda funciona, com aviso de depreciação. Confira o uso exato do operador no seu
build na [API V14](https://foundryvtt.com/api/v14/modules/foundry.data.operators.html).
:::

## Armadilhas

::: warning
- Rodar a migração do mundo em todos os clientes — proteja com `game.user.isActiveGM`.
- Gravar `systemMigrationVersion` **antes** de a migração terminar — uma falha no meio deixa o mundo marcado como migrado.
- `migrateData` não idempotente (por exemplo, multiplicar um valor) — ele roda a cada carga.
- Esquecer tokens não vinculados e compêndios — eles guardam cópias próprias dos dados do actor.
- Ler `game` ou outros documentos no `migrateData` — ele roda durante a construção, muitas vezes antes do `ready`.
:::
