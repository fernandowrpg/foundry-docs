# Diários e páginas

Diários guardam páginas de texto, imagens, PDFs e vídeo; você pode acrescentar seus próprios tipos de página, enriquecedores de texto e edição de texto rico nas fichas.

::: changed
- **O TinyMCE saiu**: o ProseMirror é o único editor de texto rico (`foundry.prosemirror.defaultPlugins` → `foundry.applications.ux.ProseMirrorEditor.buildDefaultPlugins()`).
- O ProseMirror ganha blocos **details** recolhíveis, **tabelas**, tamanho/cor de fonte e legendas.
- `CONFIG[documentName].embedHandlers` permite personalizar como um tipo de documento é renderizado pelo `@Embed`.
- `JournalEntrySheet#viewedPageDocuments` expõe as páginas que estão sendo mostradas.
- `BaseJournalEntryPage` ganha `LOCALIZATION_PREFIXES`, então os rótulos dos campos das páginas são traduzidos automaticamente.
- Veja [a lista completa de mudanças](#changes-14).
:::

## O que é

Um **JournalEntry** é um documento primário (barra lateral, compêndios) que contém documentos
**JournalEntryPage** embutidos. Cada página tem um `type`; o core traz:

| Tipo | Dados principais | Observações |
| --- | --- | --- |
| `text` | `text.content`, `text.format` (`CONST.JOURNAL_ENTRY_PAGE_FORMATS.HTML` ou `MARKDOWN`) | o padrão |
| `image` | `src`, `image.caption` | |
| `pdf` | `src` | exibido no visualizador de PDF embutido |
| `video` | `src`, `video.{controls, loop, autoplay, volume, timestamp, width, height}` | aceita URLs do YouTube |

Todas as páginas têm `name`, `title.{show, level}` (título mostrado no diário e no sumário dele),
`sort`, `ownership` e `flags`. A permissão da página é verificada separadamente da do
diário, então o mestre pode esconder dos jogadores uma única página "secreta".

## Crie pelo código

```js
const entry = await JournalEntry.create({
  name: "Forja: Lore",
  pages: [
    {
      name: "O Reino de Ferro",
      type: "text",
      title: { show: true, level: 1 },
      text: {
        format: CONST.JOURNAL_ENTRY_PAGE_FORMATS.HTML,
        content: "<p>Forjado no fogo. Veja @UUID[Actor.abc123def456gh78]{o Rei Ferreiro}.</p>"
      }
    },
    {
      name: "Mapa do Reino",
      type: "image",
      src: "systems/forja/assets/maps/kingdom.webp",
      image: { caption: "O mundo conhecido" }
    }
  ]
});

// Abre o diário em uma página específica
const page = entry.pages.getName("Mapa do Reino");
entry.sheet.render({ force: true, pageId: page.id });
```

Acrescente uma página a um diário existente com
`entry.createEmbeddedDocuments("JournalEntryPage", [data])`.

## Links e enriquecimento

O texto rico no Foundry é guardado como HTML puro e **enriquecido** na hora de renderizar. O enriquecimento transforma
padrões de texto em HTML interativo:

- `@UUID[Actor.abc123]{Rótulo}`: um link de conteúdo (arraste, clique para abrir). Funciona com UUIDs
  de compêndio: `@UUID[Compendium.forja.items.Item.xyz]`.
- `@UUID[.pageId]`: link relativo para uma página irmã do mesmo diário.
- `@Embed[JournalEntry.abc.JournalEntryPage.def]`: embute o conteúdo da página no texto.
- `[[/r 1d20+3]]` e `[[1d6]]`: links de rolagem e rolagens inline.
- `<section class="secret">`: visível só para os donos (quando `secrets: true`).

Nas suas fichas, **sempre** enriqueça antes de mostrar texto rico:

```js
// Dentro do _prepareContext de uma ficha ApplicationV2
const TextEditor = foundry.applications.ux.TextEditor.implementation;
context.enrichedBiography = await TextEditor.enrichHTML(this.document.system.biography, {
  secrets: this.document.isOwner,  // mostra as seções secretas só para os donos
  rollData: this.document.getRollData(),
  relativeTo: this.document         // resolve links @UUID relativos
});
```

```hbs
{{!-- Campo de texto rico editável --}}
<prose-mirror name="system.biography" value="{{system.biography}}"
              data-document-uuid="{{document.uuid}}" toggled>
  {{{enrichedBiography}}}
</prose-mirror>
```

## Enriquecedores próprios

`CONFIG.TextEditor.enrichers` é um array de objetos `{ pattern, enricher }`. `pattern` precisa ser uma
`RegExp` global; `enricher(match, options)` é assíncrono e devolve um `HTMLElement` (ou `null` para
deixar o texto como está).

```js
// modules/forja-extras/scripts/enrichers.mjs
// Sintaxe: @Check[strength|dc=12]
Hooks.once("init", () => {
  CONFIG.TextEditor.enrichers.push({
    pattern: /@Check\[(\w+)(?:\|dc=(\d+))?\]/gi,
    enricher: async (match, options) => {
      const [, ability, dc] = match;
      const a = document.createElement("a");
      a.classList.add("forja-check");
      a.dataset.ability = ability;
      if (dc) a.dataset.dc = dc;
      const label = game.i18n.localize(`FORJA.Ability.${ability}`);
      a.innerHTML = `<i class="fa-solid fa-dice-d20"></i> ${label}${dc ? ` (CD ${dc})` : ""}`;
      return a;
    }
  });

  // Um único listener delegado trata todos os links enriquecidos, onde quer que sejam renderizados
  document.body.addEventListener("click", event => {
    const link = event.target.closest("a.forja-check");
    if (!link) return;
    event.preventDefault();
    const actor = canvas.tokens.controlled[0]?.actor ?? game.user.character;
    if (!actor) return ui.notifications.warn("FORJA.NoActor", { localize: true });
    actor.system.rollCheck?.(link.dataset.ability, { dc: Number(link.dataset.dc) || null });
  });
});
```

::: tip
Nas versões recentes, a configuração do enriquecedor também aceita chaves extras (como `id`, `replaceParent` e um callback de renderização).
Confira `TextEditorEnricherConfig` na API da versão que você mira.
:::

## Defina um tipo de página próprio (modelo de dados)

Um módulo pode acrescentar um tipo de página, por exemplo uma "nota de NPC" com campos estruturados. Declare-o no
manifesto (tipos de módulo recebem namespace, como `forja-extras.npcnote`):

```json
{
  "id": "forja-extras",
  "documentTypes": {
    "JournalEntryPage": {
      "npcnote": { "htmlFields": ["notes"] }
    }
  }
}
```

`htmlFields` diz ao core quais campos contêm HTML (para busca e enriquecimento de links).

```js
// modules/forja-extras/scripts/npc-note.mjs
const { fields } = foundry.data;

export class NpcNoteData extends foundry.abstract.TypeDataModel {
  static LOCALIZATION_PREFIXES = ["FORJA_EXTRAS.NpcNote"];

  static defineSchema() {
    return {
      actor: new fields.DocumentUUIDField({ type: "Actor" }),
      role: new fields.StringField({ required: true, initial: "" }),
      attitude: new fields.StringField({
        required: true, initial: "neutral",
        choices: { friendly: "FORJA_EXTRAS.NpcNote.Friendly", neutral: "FORJA_EXTRAS.NpcNote.Neutral", hostile: "FORJA_EXTRAS.NpcNote.Hostile" }
      }),
      notes: new fields.HTMLField()
    };
  }
}
```

## Ficha

As fichas de página têm dois modos: **visualização** (dentro do diário) e **edição** (em janela própria). A
classe base Handlebars das fichas de página é
`foundry.applications.sheets.journal.JournalEntryPageHandlebarsSheet`, com `VIEW_PARTS`
e `EDIT_PARTS` separados.

```js
// modules/forja-extras/scripts/npc-note-sheet.mjs
const Base = foundry.applications.sheets.journal.JournalEntryPageHandlebarsSheet;

export class NpcNoteSheet extends Base {
  static DEFAULT_OPTIONS = { classes: ["forja-extras", "npc-note"] };

  static EDIT_PARTS = {
    header: Base.EDIT_PARTS.header,
    content: { template: "modules/forja-extras/templates/npc-note-edit.hbs" },
    footer: Base.EDIT_PARTS.footer
  };

  static VIEW_PARTS = {
    content: { template: "modules/forja-extras/templates/npc-note-view.hbs" }
  };

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    const system = this.document.system;
    context.system = system;
    context.fields = system.schema.fields;
    context.linkedActor = system.actor ? await fromUuid(system.actor) : null;
    context.enrichedNotes = await foundry.applications.ux.TextEditor.implementation.enrichHTML(
      system.notes, { secrets: this.document.isOwner, relativeTo: this.document });
    return context;
  }
}
```

```hbs
{{!-- modules/forja-extras/templates/npc-note-edit.hbs --}}
<section class="npc-note-edit">
  {{formGroup fields.actor value=system.actor}}
  {{formGroup fields.role value=system.role localize=true}}
  {{formGroup fields.attitude value=system.attitude localize=true}}
  <prose-mirror name="system.notes" value="{{system.notes}}" toggled>{{{enrichedNotes}}}</prose-mirror>
</section>
```

```hbs
{{!-- modules/forja-extras/templates/npc-note-view.hbs --}}
<article class="npc-note-view attitude-{{system.attitude}}">
  {{#if linkedActor}}<img src="{{linkedActor.img}}" alt="{{linkedActor.name}}">{{/if}}
  <p><strong>{{system.role}}</strong></p>
  <div class="notes">{{{enrichedNotes}}}</div>
</article>
```

## Registre

```js
// modules/forja-extras/scripts/main.mjs
import { NpcNoteData } from "./npc-note.mjs";
import { NpcNoteSheet } from "./npc-note-sheet.mjs";

Hooks.once("init", () => {
  CONFIG.JournalEntryPage.dataModels["forja-extras.npcnote"] = NpcNoteData;
  foundry.applications.apps.DocumentSheetConfig.registerSheet(JournalEntryPage, "forja-extras", NpcNoteSheet, {
    types: ["forja-extras.npcnote"],
    makeDefault: true,
    label: "FORJA_EXTRAS.NpcNote.Sheet"
  });
});
```

Acrescente `"TYPES": { "JournalEntryPage": { "forja-extras.npcnote": "Nota de NPC" } }` ao seu arquivo
de idioma para o tipo aparecer com um nome bonito no diálogo "criar página".

::: v14
## ProseMirror no V14

Sem o TinyMCE, todo campo de texto rico usa ProseMirror. Novidades do V14:

- **Details** (seções recolhíveis) e **tabelas** no menu do editor; tamanho e cor de fonte e
  legendas em imagens.
- Templates de conteúdo inline e em bloco no editor.
- Se você estendeu o editor com plugins, monte os padrões com
  `foundry.applications.ux.ProseMirrorEditor.buildDefaultPlugins()` em vez de ler
  `foundry.prosemirror.defaultPlugins`.
- `CONFIG[documentName].embedHandlers` personaliza como um documento é embutido pelo `@Embed`. A
  assinatura exata do handler está na [API do V14](https://foundryvtt.com/api/v14/).
- `JournalEntrySheet#viewedPageDocuments` devolve as páginas mostradas no momento, útil para
  módulos que acrescentam controles à página visível.
:::

## Armadilhas

::: warning
- Mostrar `system.notes` com `{{{ }}}` **sem** enriquecer exibe o texto `@UUID[...]` cru e,
  pior, revela as seções secretas para os jogadores.
- As regex dos enriquecedores precisam da flag `g`; sem ela o core dá erro ou só encontra uma ocorrência.
- Os enriquecedores rodam em todos os clientes e a cada renderização: mantenha-os rápidos e não crie documentos
  dentro deles.
- A permissão da página é separada da do diário: um jogador pode ver o diário mas não uma página.
- Um tipo de página próprio sem ficha registrada fica sem nada utilizável: sempre registre uma.
:::
