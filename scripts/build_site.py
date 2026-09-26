#!/usr/bin/env python3
"""
Genera la web en varios idiomas, cada uno en su propia URL.

    python scripts/build_site.py

Lee las plantillas de src/, las traducciones de src/i18n.json, los
metadatos de src/meta.json y los datos de menu-data.json y
novedades-data.json, y escribe en la raíz del repositorio:

    /              español   (index.html, novedades.html, novedades/…)
    /en/           inglés
    sitemap.xml, robots.txt

Por qué un generador y no traducir en el navegador: con el idioma en el
propio JavaScript, Google solo ve la versión española — el resto del
contenido no existe hasta que alguien pulsa un botón. Con una URL por
idioma y sus etiquetas hreflang, cada versión se indexa por separado.

Por el mismo motivo la carta se escribe entera en el HTML en vez de
pedirse con fetch: los platos son justo lo que la gente busca.

Para añadir un idioma: añádelo a LANGUAGES, traduce src/i18n.json y
src/meta.json, y vuelve a ejecutar.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"

SITE_URL = "https://retuertographic.github.io/Crrta"

# código -> (carpeta de salida, etiqueta hreflang, locale para las fechas)
LANGUAGES = {
    "es": ("", "es-ES", "es-ES"),
    "en": ("en", "en", "en-GB"),
}
DEFAULT_LANG = "es"

PAGES = ["index.html", "novedades.html", "novedades/abrimos-nuestra-web.html"]

MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}

FLAGS = {"es": "🇪🇸", "en": "🇬🇧", "de": "🇩🇪"}


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def fmt_date(iso: str, lang: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    month = MONTHS.get(lang, MONTHS["en"])[m - 1]
    return f"{d} de {month} de {y}" if lang == "es" else f"{d} {month} {y}"


def t(i18n: dict, lang: str, key: str, fallback: str = "") -> str:
    return i18n.get(lang, {}).get(key) or i18n[DEFAULT_LANG].get(key) or fallback


def field(obj: dict, key: str, lang: str) -> str:
    """Devuelve obj[key_lang] y, si no existe esa traducción, obj[key]."""
    if lang != DEFAULT_LANG:
        value = obj.get(f"{key}_{lang}")
        if value:
            return value
    return obj.get(key) or ""


def prefix_for(page: str, lang: str) -> str:
    """Camino relativo desde la página hasta la raíz del sitio.

    Cuenta lo que baja la propia página (novedades/…) y también la carpeta
    del idioma (/en/), porque assets/ e img/ viven en la raíz y no se
    duplican por idioma."""
    depth = page.count("/") + (1 if LANGUAGES[lang][0] else 0)
    return "../" * depth


def page_url(page: str, lang: str) -> str:
    folder = LANGUAGES[lang][0]
    path = "" if page == "index.html" else page
    parts = [p for p in (folder, path) if p]
    url = f"{SITE_URL}/" + "/".join(parts)
    # La portada de cada idioma es un directorio: mejor con barra final,
    # así no depende de la redirección del servidor.
    return url + "/" if page == "index.html" and folder else url


# --------------------------------------------------------------- la carta

def render_carta(menu: dict, i18n: dict, lang: str) -> tuple[str, str, str]:
    categories = [c for c in menu.get("categories", []) if c.get("items")]
    if not categories:
        empty = t(i18n, lang, "carta_empty")
        return "", f'<div class="menu-panel active"><p class="menu-empty">{empty}</p></div>', ""

    tabs = ['<div class="menu-tabs" role="tablist">']
    panels = []
    allergen_names = i18n.get(lang, {}).get("allergens", {}) or {}
    maybe_label = t(i18n, lang, "allergens_maybe_label")

    for index, cat in enumerate(categories):
        slug = f"cat{index}"
        active = " active" if index == 0 else ""
        label = esc(field(cat, "category", lang))
        tabs.append(
            f'<button class="menu-tab{active}" data-category="{slug}" role="tab" '
            f'aria-selected="{"true" if index == 0 else "false"}">{label}</button>'
        )

        rows = [f'<div class="menu-panel{active}" data-category="{slug}" role="tabpanel">']
        for item in cat["items"]:
            if "group" in item:
                rows.append(f'<div class="menu-group">{esc(field(item, "group", lang))}</div>')
                continue

            rows.append('<div class="menu-item"><div class="mi-main">')
            rows.append(f'<div class="mi-name">{esc(field(item, "name", lang))}</div>')
            description = field(item, "description", lang)
            if description:
                rows.append(f'<div class="mi-desc">{esc(description)}</div>')

            certain = item.get("allergens") or []
            maybe = item.get("allergens_maybe") or []
            if certain or maybe:
                chips = [f'<div class="mi-allergens" aria-label="{esc(t(i18n, lang, "allergens_label"))}">']
                for code in certain:
                    chips.append(f'<span class="al">{esc(allergen_names.get(code, code))}</span>')
                for code in maybe:
                    name = esc(allergen_names.get(code, code))
                    chips.append(f'<span class="al maybe" title="{esc(maybe_label)}">{name} ?</span>')
                chips.append("</div>")
                rows.append("".join(chips))
            rows.append("</div>")

            prices = item.get("prices") or ([{"value": item["price"]}] if item.get("price") else [])
            rows.append('<div class="mi-prices">')
            for price in prices:
                label_text = field(price, "label", lang)
                label_html = f'<span class="pl">{esc(label_text)}</span>' if label_text else ""
                value = esc(str(price.get("value", "")).replace(".", ","))
                rows.append(f'<span class="mi-price">{label_html}{value} €</span>')
            rows.append("</div></div>")

        rows.append("</div>")
        panels.append("".join(rows))

    tabs.append("</div>")

    notes = [t(i18n, lang, "note_igic") if "igic" in n.lower() else n
             for n in (menu.get("notes") or [])]
    notes.append(t(i18n, lang, "note_allergens"))
    notes_html = f'<div class="menu-notes">{esc(" ".join(n for n in notes if n))}</div>'

    return "\n".join(tabs), "\n".join(panels), notes_html


# ------------------------------------------------------------- novedades

def render_novedades(posts: list[dict], i18n: dict, lang: str, prefix: str) -> str:
    if not posts:
        return f'<div class="nov-grid"><div class="nov-empty">{esc(t(i18n, lang, "novedades_empty"))}</div></div>'
    cards = ['<div class="nov-grid">']
    for post in sorted(posts, key=lambda p: p["date"], reverse=True):
        title = esc(field(post, "title", lang) or post.get("title_es", ""))
        excerpt = esc(field(post, "excerpt", lang) or post.get("excerpt_es", ""))
        cards.append(
            f'<article class="nov-card">'
            f'<div class="thumb"><img src="{prefix}{esc(post["image"])}" alt="{title}" loading="lazy"></div>'
            f'<div class="body"><div class="nov-date">{esc(fmt_date(post["date"], lang))}</div>'
            f'<h3>{title}</h3><p>{excerpt}</p>'
            f'<a class="read-more" href="{prefix}novedades/{esc(post["slug"])}.html">'
            f'{esc(t(i18n, lang, "read_more"))}</a></div></article>'
        )
    cards.append("</div>")
    return "\n".join(cards)


# ------------------------------------------------------------ <head> y UI

def render_head(page: str, lang: str, meta: dict, prefix: str) -> str:
    info = meta.get(page, {}).get(lang) or meta.get(page, {}).get(DEFAULT_LANG, {})
    title = info.get("title", "La Carreta del Carretón")
    description = info.get("description", "")
    og_type = info.get("og_type", "website")
    image = info.get("image", "img/logo-square.jpg")

    lines = [
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
        f'<link rel="canonical" href="{esc(page_url(page, lang))}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:type" content="{esc(og_type)}">',
        f'<meta property="og:url" content="{esc(page_url(page, lang))}">',
        f'<meta property="og:image" content="{SITE_URL}/{esc(image)}">',
        f'<meta property="og:locale" content="{esc(LANGUAGES[lang][1].replace("-", "_"))}">',
    ]
    # hreflang: cada versión se anuncia a sí misma y a las demás.
    for code in LANGUAGES:
        lines.append(
            f'<link rel="alternate" hreflang="{esc(LANGUAGES[code][1])}" '
            f'href="{esc(page_url(page, code))}">'
        )
    lines.append(
        f'<link rel="alternate" hreflang="x-default" href="{esc(page_url(page, DEFAULT_LANG))}">'
    )
    return "\n".join(lines)


def render_lang_switch(page: str, lang: str, i18n: dict) -> str:
    """Enlaces de verdad entre idiomas: los buscadores los siguen y
    funcionan sin JavaScript."""
    items = []
    here = prefix_for(page, lang)
    for code in LANGUAGES:
        if code == lang:
            continue
        # Relativo a propósito: así los enlaces siguen funcionando en local
        # y si el sitio cambia de dominio. Los absolutos se reservan para
        # canonical, hreflang y og:url, donde hacen falta.
        folder = LANGUAGES[code][0]
        url = here + (f"{folder}/" if folder else "") + page
        name = esc(t(i18n, code, "lang_name", code.upper()))
        items.append(
            f'<a class="lang-link" href="{esc(url)}" hreflang="{esc(LANGUAGES[code][1])}" '
            f'lang="{esc(code)}"><span class="flag">{FLAGS.get(code, "")}</span>'
            f'<span>{esc(code.upper())}</span><span class="sr-only"> — {name}</span></a>'
        )
    return f'<div class="lang-switch">{"".join(items)}</div>'


def apply_translations(markup: str, i18n: dict, lang: str) -> str:
    """Sustituye el contenido de cada elemento con data-i18n por su texto."""
    pattern = re.compile(
        r'(<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*\bdata-i18n="(?P<key>[^"]+)"[^>]*)>)(?P<body>.*?)(</(?P=tag)>)',
        re.S,
    )
    missing: set[str] = set()

    def replace(m: re.Match) -> str:
        key = m.group("key")
        value = i18n.get(lang, {}).get(key)
        if value is None:
            missing.add(key)
            value = i18n[DEFAULT_LANG].get(key, m.group("body"))
        return f'{m.group(1)}{value}{m.group(6)}'

    result = pattern.sub(replace, markup)
    for key in sorted(missing):
        print(f"  aviso [{lang}]: falta la traducción de «{key}»", file=sys.stderr)
    return result


# ------------------------------------------------------------------ build

def build() -> int:
    i18n = json.loads((SRC / "i18n.json").read_text(encoding="utf-8"))
    meta = json.loads((SRC / "meta.json").read_text(encoding="utf-8"))
    menu = json.loads((REPO / "menu-data.json").read_text(encoding="utf-8"))
    posts = json.loads((REPO / "novedades-data.json").read_text(encoding="utf-8")).get("posts", [])

    for code in LANGUAGES:
        if code not in i18n:
            print(f"ERROR: falta el idioma «{code}» en src/i18n.json", file=sys.stderr)
            return 1

    # Fragmento opcional para analíticas o mapas de calor. Si el archivo no
    # existe, no se inyecta nada: la web no carga terceros por defecto.
    analytics_file = SRC / "partials" / "analytics.html"
    analytics = analytics_file.read_text(encoding="utf-8").strip() if analytics_file.exists() else ""

    header_tpl = (SRC / "partials" / "header.html").read_text(encoding="utf-8")
    footer_tpl = (SRC / "partials" / "footer.html").read_text(encoding="utf-8")

    written: list[str] = []
    for lang, (folder, _, _) in LANGUAGES.items():
        out_root = REPO / folder if folder else REPO
        carta_tabs, carta_panels, carta_notes = render_carta(menu, i18n, lang)

        for page in PAGES:
            template = (SRC / "pages" / page).read_text(encoding="utf-8")
            prefix = prefix_for(page, lang)

            header = header_tpl.replace("<!--{{LANG_SWITCH}}-->", render_lang_switch(page, lang, i18n))
            body = (template
                    .replace("<!--{{HEADER}}-->", header)
                    .replace("<!--{{FOOTER}}-->", footer_tpl)
                    .replace("<!--{{HEAD}}-->", render_head(page, lang, meta, prefix))
                    .replace("<!--{{ANALYTICS}}-->", analytics)
                    .replace("<!--{{CARTA_TABS}}-->", carta_tabs)
                    .replace("<!--{{CARTA_PANELS}}-->", carta_panels)
                    .replace("<!--{{CARTA_NOTES}}-->", carta_notes)
                    .replace("<!--{{NOVEDADES}}-->", render_novedades(posts, i18n, lang, prefix)))

            if "{{POST_DATE}}" in body:
                slug = Path(page).stem
                post = next((p for p in posts if p["slug"] == slug), None)
                body = body.replace("{{POST_DATE}}", esc(fmt_date(post["date"], lang)) if post else "")

            body = apply_translations(body, i18n, lang)
            body = body.replace("{{LANG}}", lang).replace("{{PREFIX}}", prefix)

            target = out_root / page
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            written.append(str(target.relative_to(REPO)))

    write_sitemap()
    write_robots()
    print(f"OK: {len(written)} páginas en {len(LANGUAGES)} idiomas"
          + ("" if analytics else " · sin analíticas (no hay src/partials/analytics.html)"))
    for path in written:
        print(f"  · {path}")
    print("  · sitemap.xml\n  · robots.txt")
    return 0


def write_sitemap() -> None:
    today = date.today().isoformat()
    urls = []
    for page in PAGES:
        for lang in LANGUAGES:
            alternates = "".join(
                f'\n    <xhtml:link rel="alternate" hreflang="{LANGUAGES[c][1]}" '
                f'href="{page_url(page, c)}"/>' for c in LANGUAGES
            )
            urls.append(
                f"  <url>\n    <loc>{page_url(page, lang)}</loc>"
                f"\n    <lastmod>{today}</lastmod>{alternates}\n  </url>"
            )
    (REPO / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(urls) + "\n</urlset>\n",
        encoding="utf-8",
    )


def write_robots() -> None:
    (REPO / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )


if __name__ == "__main__":
    sys.exit(build())
