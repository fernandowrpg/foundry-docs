# Guia do Construtor Foundry / Foundry Builder's Guide

Documentação bilíngue (português do Brasil e inglês) para criar **módulos e sistemas** no
Foundry Virtual Tabletop **V13** e **V14**. O site tem um menu superior para trocar a versão, trocar o
idioma e comparar as duas versões lado a lado, além de páginas "O que mudou" para cada versão.

*Bilingual (Brazilian Portuguese and English) documentation for building Foundry VTT modules and
systems on V13 and V14, with a version switcher, a language switcher, a side-by-side compare mode
and "What changed" pages. English instructions are at the end.*

## Estrutura

```
content/nav.json             menu: seções, páginas, versões e idiomas
content/<idioma>/<pagina>.md  uma página por idioma (en, pt-BR)
i18n/<idioma>.json           textos da interface (menus, botões, rótulos)
template.html                layout, CSS e o renderizador em JavaScript
vendor/                      marked e highlight.js (embutidos no build, funcionam offline)
build.py                     gera o site em docs/
docs/index.html              o site pronto (é esta pasta que o GitHub Pages publica)
ci/check-docs.yml            workflow opcional: copie para .github/workflows/ para o GitHub conferir o build
AUTHORING.md                 regras para escrever páginas (blocos de versão, avisos, estilo)
FACTS.md                     fatos de API conferidos nas notas de versão oficiais
```

## Gerar o site

Só precisa do Python 3, sem dependências:

```bash
python build.py
```

O comando mostra quantas páginas cada idioma tem e quais estão faltando. Depois de editar
qualquer página, rode o build e faça commit da pasta `docs/` junto.

## Publicar no GitHub Pages

1. Envie o projeto para um repositório no GitHub, com a pasta `docs/` na raiz do repositório.
2. No repositório, abra **Settings → Pages**.
3. Em **Source**, escolha **Deploy from a branch**.
4. Em **Branch**, escolha `main` e a pasta **`/docs`**, e clique em **Save**.
5. Em um ou dois minutos o site fica em `https://<seu-usuario>.github.io/<nome-do-repositorio>/`.

A cada `git push` com a pasta `docs/` atualizada, o GitHub Pages publica a nova versão sozinho.
Opcional: copie `ci/check-docs.yml` para `.github/workflows/check-docs.yml`. Esse workflow avisa (com um erro no GitHub) se você esqueceu de
rodar `python build.py` antes do commit.

## Adicionar um idioma (por exemplo, espanhol)

1. Copie `i18n/en.json` para `i18n/es.json` e traduza os valores (não as chaves).
2. Crie a pasta `content/es/` e traduza as páginas que quiser. As páginas que faltarem aparecem
   em inglês, com um aviso de "ainda não traduzida".
3. Acrescente o idioma em `content/nav.json`:
   ```json
   { "id": "es", "label": "Español", "short": "ES" }
   ```
4. Rode `python build.py`.

Mantenha a mesma estrutura do inglês em cada página (mesmos títulos `##`, mesmos blocos `:::` e o mesmo
código; só o texto e os comentários do código mudam). O próprio `build.py` lista as chaves de
interface que faltam em cada idioma.

## Adicionar uma versão do Foundry (por exemplo, V15)

1. Acrescente a versão em `content/nav.json` (`versions`) com `build`, `released` e `changelog`.
2. Crie a página `changes-15` nos dois idiomas e coloque-a na seção `changes`.
3. Nas páginas, use `::: v15` para o conteúdo novo, `::: v14+` para o que vale do V14 em diante, e
   `::: changed-15` para os quadros "Mudou no V15".

## Blocos especiais nas páginas

| Bloco | Mostrado quando |
|---|---|
| `::: v13` / `::: v14` | só na versão escolhida (lado a lado no modo Comparar) |
| `::: v14+` | na versão 14 e nas seguintes |
| `::: changed` | quadro "Mudou no V14", só quando o V14 está escolhido |
| `::: tip` / `::: warning` / `::: deprecated` | sempre |

Veja os detalhes em `AUTHORING.md`.

---

## English

- **Build:** `python build.py` (Python 3, no dependencies). Output: `docs/index.html`, a single self-contained file.
- **GitHub Pages:** Settings → Pages → Deploy from a branch → `main` + `/docs` → Save. Commit `docs/` after every build.
- **Add a language:** copy `i18n/en.json` to `i18n/<code>.json`, add `content/<code>/` pages (missing pages fall back to English with a notice), register the locale in `content/nav.json`, rebuild.
- **Add a Foundry version:** add it to `versions` in `content/nav.json`, write `changes-<n>` in each language, and use `::: v<n>`, `::: v<n>+` and `::: changed-<n>` blocks.
- **Writing rules:** see `AUTHORING.md`. Verified API facts are in `FACTS.md`.

Sources: the official Foundry VTT release notes (https://foundryvtt.com/releases/) and API documentation
(https://foundryvtt.com/api/v13/, https://foundryvtt.com/api/v14/), checked on 2026-09-29.
