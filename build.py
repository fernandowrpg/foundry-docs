#!/usr/bin/env python3
"""Bundle the guide into a single HTML file.

Usage:  python build.py
Output: docs/index.html        the site, ready for GitHub Pages ("Deploy from a branch" → /docs)
        docs/404.html          same page, so unknown URLs still open the guide
        docs/.nojekyll         tells GitHub Pages to serve the files as they are
        build/artifact.html    body-only version used for claude.ai publishing (not committed)

Only the Python standard library is needed. Locales and pages are discovered
from content/nav.json, i18n/<locale>.json and content/<locale>/<page>.md.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
nav = json.loads((ROOT / "content" / "nav.json").read_text(encoding="utf-8"))
page_ids = [p for s in nav["sections"] for p in s["pages"]]

i18n, pages, report = {}, {}, []
for loc in [l["id"] for l in nav["locales"]]:
    f = ROOT / "i18n" / f"{loc}.json"
    i18n[loc] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    pages[loc] = {}
    for pid in page_ids:
        md = ROOT / "content" / loc / f"{pid}.md"
        if md.exists():
            pages[loc][pid] = md.read_text(encoding="utf-8")
    missing = [p for p in page_ids if p not in pages[loc]]
    report.append(f"  {loc:6} {len(pages[loc]):>3}/{len(page_ids)} pages" + (f"  missing: {', '.join(missing)}" if missing else ""))

# UI keys missing per locale (compared with English)
for loc, strings in i18n.items():
    gaps = [k for k in i18n.get("en", {}) if k not in strings]
    if gaps:
        report.append(f"  {loc:6} UI strings missing: {', '.join(gaps)}")

data = json.dumps({"nav": nav, "i18n": i18n, "pages": pages}, ensure_ascii=False)
data = data.replace("</", "<\\/")  # never close the <script> early
vendor = ""
for lib in ["marked.min.js", "highlight.min.js", "handlebars.min.js"]:
    src = (ROOT / "vendor" / lib).read_text(encoding="utf-8").replace("</script", "<\\/script")
    vendor += f"<script>/* {lib} */\n{src}\n</script>\n"
template = (ROOT / "template.html").read_text(encoding="utf-8")
template = template.replace("<!--__VENDOR__", vendor + "<!--", 1)
fragment = template.replace("/*__DATA__*/null", data)

standalone = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              '<style>[hidden]{display:none!important}body{margin:0}</style>\n</head>\n<body>\n'
              + fragment + "\n</body>\n</html>\n")

docs = ROOT / "docs"
docs.mkdir(exist_ok=True)
(docs / "index.html").write_text(standalone, encoding="utf-8")
(docs / "404.html").write_text(standalone, encoding="utf-8")
(docs / ".nojekyll").write_text("", encoding="utf-8")

build = ROOT / "build"
build.mkdir(exist_ok=True)
(build / "artifact.html").write_text(fragment, encoding="utf-8")

print("Built docs/index.html (GitHub Pages) and build/artifact.html")
print("\n".join(report))
sys.exit(0)
