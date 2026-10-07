#!/usr/bin/env python3
"""
Genera la web en varios idiomas, cada uno en su propia URL.

    python scripts/build_site.py

Lee las plantillas de src/pages/, los elementos comunes de
src/partials/, las traducciones de src/i18n.json, los metadatos de
src/meta.json y los datos de menu-data.json y novedades-data.json, y
escribe en la raíz del repositorio:

    /              español   (index.html, novedades.html, novedades/…)
    /en/           inglés
    sitemap.xml, robots.txt

Por qué un generador y no traducir en el navegador: con el idioma en el
propio JavaScript, Google solo ve la versión española — el resto del
contenido no existe hasta que alguien pulsa un botón. Con una URL por
idioma y sus etiquetas hreflang, cada versión se indexa por separado.

Por el mismo motivo la carta se escribe entera en el HTML en vez de
pedirse con fetch: los platos son justo lo que la gente busca.

Nada común se escribe dos veces: cabecera, pie, <head>, formularios
y banner de cookies viven en src/partials/ y las páginas solo ponen el
marcador. Cada archivo de esa carpeta es un marcador con su nombre en
mayúsculas (consent-banner.html -> <!--{{CONSENT_BANNER}}-->), así que
para añadir un elemento común basta con dejar el archivo ahí.

El canonical va dentro de head.html, que es común: de este modo ninguna
página puede publicarse sin él.

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

PAGES = [
    "index.html",
    "legal.html",
    "catering.html",
    "novedades.html",
    "novedades/abrimos-nuestra-web.html",
    "404.html",
]

MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}

FLAGS = {"es": "🇪🇸", "en": "🇬🇧", "de": "🇩🇪"}

# Buzones con versión por idioma. Los demás correos (info@,
# protecciondedatos@) son iguales en todos y van escritos en la plantilla.
MAILBOXES = {
    "bookings": {"es": "reservas@lacarretadelcarreton.com",
                 "en": "bookings@lacarretadelcarreton.com"},
    "care": {"es": "atencionalcliente@lacarretadelcarreton.com",
             "en": "customercare@lacarretadelcarreton.com"},
}


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def fmt_date(iso: str, lang: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    month = MONTHS.get(lang, MONTHS["en"])[m - 1]
    return f"{d} de {month} de {y}" if lang == "es" else f"{d} {month} {y}"


def t(i18n: dict, lang: str, key: str, fallback: str = "") -> str:
    return i18n.get(lang, {}).get(key) or i18n[DEFAULT_LANG].get(key) or fallback


def field(obj: dict, key: str, lang: str) -> str:
    """Devuelve el valor de key en este idioma.

    Hay dos convenciones en los datos: la carta trae «name» y «name_en», y
    las novedades «title_es» y «title_en». Se prueban las dos, por ese orden,
    y se cae al idioma por defecto si falta la traducción."""
    if lang != DEFAULT_LANG:
        value = obj.get(f"{key}_{lang}")
        if value:
            return value
    return obj.get(key) or obj.get(f"{key}_{DEFAULT_LANG}") or ""


def prefix_for(page: str, lang: str) -> str:
    """Camino relativo desde la página hasta la raíz del sitio.

    Cuenta lo que baja la propia página (novedades/…) y también la carpeta
    del idioma (/en/), porque assets/ e img/ viven en la raíz y no se
    duplican por idioma."""
    depth = page.count("/") + (1 if LANGUAGES[lang][0] else 0)
    return "../" * depth


def lang_prefix_for(page: str) -> str:
    """Camino desde la página hasta la raíz de SU idioma.

    Es lo que usan los enlaces entre páginas ({{HOME}}), porque tienen que
    quedarse dentro del idioma: desde /en/ se enlaza a /en/legal.html, no a
    /legal.html. Para assets/ e img/, que no se duplican por idioma, está
    {{PREFIX}}, que sube hasta la raíz del sitio."""
    return "../" * page.count("/")


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

    for index, cat in enumerate(categories):
        slug = f"cat{index}"
        active = " active" if index == 0 else ""
        label = esc(field(cat, "category", lang))
        tabs.append(
            f'<button class="menu-tab{active}" data-category="{slug}" role="tab" '
            f'id="tab-{slug}" aria-controls="panel-{slug}" '
            f'tabindex="{"0" if index == 0 else "-1"}" '
            f'aria-selected="{"true" if index == 0 else "false"}">{label}</button>'
        )

        rows = [f'<div class="menu-panel{active}" data-category="{slug}" role="tabpanel" '
                f'id="panel-{slug}" aria-labelledby="tab-{slug}" tabindex="0">']
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
            # El gluten que se puede quitar bajo petición sigue siendo gluten:
            # se marca igual que los demás y se añade aparte lo que se puede
            # pedir. Mezclarlo en una sola etiqueta se lee como «no lleva».
            sin_gluten = bool(item.get("gluten_on_request"))
            if certain:
                chips = [f'<div class="mi-allergens" role="group" aria-label="{esc(t(i18n, lang, "allergens_label"))}">']
                for code in certain:
                    chips.append(f'<span class="al">{esc(allergen_names.get(code, code))}</span>')
                if sin_gluten:
                    chips.append(
                        f'<span class="al on-request" title="{esc(t(i18n, lang, "allergens_gluten_note"))}">'
                        f'{esc(t(i18n, lang, "allergens_gluten_chip"))}</span>'
                    )
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

def render_novedades(posts: list[dict], i18n: dict, lang: str,
                     prefix: str, home: str) -> str:
    if not posts:
        return f'<div class="nov-grid"><div class="nov-empty">{esc(t(i18n, lang, "novedades_empty"))}</div></div>'
    cards = ['<div class="nov-grid">']
    for post in sorted(posts, key=lambda p: p["date"], reverse=True):
        title = esc(field(post, "title", lang))
        excerpt = esc(field(post, "excerpt", lang))
        cards.append(
            f'<article class="nov-card">'
            f'<div class="thumb"><img src="{prefix}{esc(post["image"])}" alt="{title}" loading="lazy"></div>'
            f'<div class="body"><div class="nov-date">{esc(fmt_date(post["date"], lang))}</div>'
            f'<h3>{title}</h3><p>{excerpt}</p>'
            f'<a class="read-more" href="{home}novedades/{esc(post["slug"])}.html">'
            f'{esc(t(i18n, lang, "read_more"))}</a></div></article>'
        )
    cards.append("</div>")
    return "\n".join(cards)


# ------------------------------------------------------------- partials

PARTIALS = SRC / "partials"


def load_partials() -> dict[str, str]:
    """Carga src/partials/ en un diccionario de marcadores.

    Cada archivo se convierte en un marcador con su nombre en mayúsculas y
    los guiones como subrayados: consent-banner.html -> <!--{{CONSENT_BANNER}}-->
    Para añadir un elemento común basta con dejar el archivo aquí y poner
    su marcador en la página; no hay que tocar este script."""
    partials = {}
    for path in sorted(PARTIALS.glob("*.html")):
        name = path.stem.replace("-", "_").upper()
        partials[name] = path.read_text(encoding="utf-8").strip("\n")
    return partials


def marker(name: str) -> str:
    return f"<!--{{{{{name}}}}}-->"


MARKER_RE = re.compile(r"<!--\{\{(?P<name>[A-Z0-9_]+)\}\}-->")
LINE_MARKER_RE = re.compile(
    r"^(?P<indent>[ \t]*)<!--\{\{(?P<name>[A-Z0-9_]+)\}\}-->[ \t]*\n", re.M)
NOTE_RE = re.compile(r"[ \t]*<!--#.*?-->[ \t]*\n?", re.S)


def expand_partials(markup: str, partials: dict[str, str]) -> str:
    """Sustituye los marcadores por su partial, incluidos los anidados.

    Repite hasta que no cambie nada, porque un partial puede contener el
    marcador de otro (head.html trae dentro <!--{{SEO}}-->, y el bloque de
    contacto trae el del formulario). Si el marcador está solo en su línea,
    el contenido hereda su sangría y, cuando está vacío, se va también la
    línea: así el HTML publicado sigue siendo legible."""
    def by_line(m: re.Match) -> str:
        name = m.group("name")
        if name not in partials:
            return m.group(0)
        content = partials[name]
        if not content.strip():
            return ""
        indent = m.group("indent")
        body = "\n".join(indent + ln if ln.strip() else ln
                         for ln in content.split("\n"))
        return body + "\n"

    def inline(m: re.Match) -> str:
        return partials.get(m.group("name"), m.group(0))

    for _ in range(10):
        before = markup
        markup = LINE_MARKER_RE.sub(by_line, markup)
        markup = MARKER_RE.sub(inline, markup)
        if markup == before:
            return markup
    raise RuntimeError("marcadores de partials en bucle: revisa src/partials/")


def strip_source_notes(markup: str) -> str:
    """Quita los comentarios que empiezan por <!--# .

    Son notas para quien edita src/; no tienen por qué descargarlas todas
    las visitas. Los comentarios normales (<!-- ... -->) sí se publican."""
    return NOTE_RE.sub("", markup)


def leftover_markers(markup: str) -> list[str]:
    """Marcadores que se han quedado sin resolver.

    Un marcador mal escrito no da error: desaparece en un comentario HTML y
    la página sale sin ese trozo. Mejor avisar."""
    return sorted(set(re.findall(r"<!--\{\{([A-Z0-9_]+)\}\}-->", markup)))


# ------------------------------------------------------------ <head> y UI

def render_seo(page: str, lang: str, meta: dict) -> str:
    """title, description, canonical, og: y hreflang de esta página.

    El canonical apunta siempre a la propia URL (autorreferente) y
    las etiquetas hreflang declaran las dos versiones, para que Google
    no trate español e inglés como contenido duplicado."""
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


def render_breadcrumbs(page: str, lang: str, i18n: dict, posts: list[dict]) -> str:
    """Migas de pan en JSON-LD, para que Google enseñe la ruta en el resultado
    en vez de la URL cruda.

    La portada no lleva: es el primer escalón de todas las demás. La 404
    tampoco, que no está en ninguna ruta."""
    if page in ("index.html", "404.html"):
        return ""

    inicio = t(i18n, lang, "nav_home", "Inicio")
    ruta = [(inicio, page_url("index.html", lang))]
    if page == "catering.html":
        ruta.append((t(i18n, lang, "nav_catering"), page_url(page, lang)))
    elif page == "novedades.html":
        ruta.append((t(i18n, lang, "nav_novedades"), page_url(page, lang)))
    elif page == "legal.html":
        ruta.append((t(i18n, lang, "legal_title"), page_url(page, lang)))
    elif page.startswith("novedades/"):
        ruta.append((t(i18n, lang, "nav_novedades"), page_url("novedades.html", lang)))
        post = next((x for x in posts if x["slug"] == Path(page).stem), None)
        if post:
            ruta.append((field(post, "title", lang), page_url(page, lang)))
    else:
        return ""

    items = [
        {"@type": "ListItem", "position": i, "name": nombre, "item": url}
        for i, (nombre, url) in enumerate(ruta, start=1)
    ]
    datos = {"@context": "https://schema.org", "@type": "BreadcrumbList",
             "itemListElement": items}
    return ('<script type="application/ld+json">\n'
            + json.dumps(datos, ensure_ascii=False, indent=2)
            + "\n</script>")


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


def render_form(tpl: str, forms: dict, slot: str, lang: str,
                i18n: dict, kind: str) -> str:
    """Rellena src/partials/form.html con el GUID del formulario.

    Si ese formulario no tiene GUID para este idioma no se publica nada:
    mejor que un iframe vacío."""
    guid = (forms.get(slot, {}) or {}).get(lang, "").strip()
    if not guid:
        return ""
    title = esc(t(i18n, lang, "cat_quote_title" if slot == "catering" else "contact_form_title"))
    return (tpl
            .replace("{{FORM_KIND}}", esc(kind))
            .replace("{{FORM_URL}}", esc(forms["base_url"] + guid))
            .replace("{{FORM_TITLE}}", title))


def render_contacto(tpl_block: str, tpl_form: str, forms: dict,
                    lang: str, i18n: dict) -> str:
    """El formulario de contacto con su titular, o nada si no hay GUID."""
    inner = render_form(tpl_form, forms, "contacto", lang, i18n, "contacto")
    if not inner:
        return ""
    return tpl_block.replace(marker("FORM"), inner)


def render_analytics(ga4: str, hotjar: str, cfg: dict, prefix: str) -> str:
    """Config y cargador del consentimiento. Los scripts de Google y Hotjar
    NO se escriben aquí: los inyecta consent.js cuando alguien acepta."""
    if not (ga4 or hotjar):
        return ""
    config = {
        "ga4Id": ga4,
        "hotjarId": hotjar,
        "trackContactClicks": bool(cfg.get("track_contact_clicks", True)),
    }
    return (
        f"<script>window.SITE_ANALYTICS={json.dumps(config, ensure_ascii=False)};</script>\n"
        f'<script src="{prefix}assets/consent.js" defer></script>'
    )


def resolve_mailboxes(markup: str, lang: str) -> str:
    """Pone en cada enlace marcado con data-mailbox la dirección del idioma.

    Antes lo hacía JavaScript en la página; al pasar a generar el sitio se
    quedó sin resolver y las páginas en inglés enseñaban el buzón español.
    Ahora se resuelve aquí, que además lo deja en el HTML publicado."""
    pattern = re.compile(
        r'<a(?P<before>[^>]*?)\sdata-mailbox="(?P<key>[^"]+)"(?P<after>[^>]*)>(?P<body>.*?)</a>',
        re.S,
    )

    def replace(m: re.Match) -> str:
        addresses = MAILBOXES.get(m.group("key"))
        if not addresses:
            return m.group(0)
        address = addresses.get(lang) or addresses[DEFAULT_LANG]
        attrs = re.sub(
            r'href="mailto:[^"]*"', f'href="mailto:{address}"',
            m.group("before") + m.group("after"),
        )
        body = m.group("body")
        if "data-mailbox-text" in body:
            body = re.sub(
                r'(data-mailbox-text[^>]*>)[^<]*', rf'\g<1>{address}', body
            )
        else:
            body = address
        return f"<a{attrs}>{body}</a>"

    return pattern.sub(replace, markup)


def strip_conditionals(markup: str, analytics: bool) -> str:
    """Quita los bloques marcados con data-if/data-unless que no apliquen.

    Está para que la política de cookies diga siempre la verdad: si no hay
    analítica configurada no se publica el párrafo que dice que la hay, y
    al revés."""
    drop = "data-unless" if analytics else "data-if"
    pattern = re.compile(
        rf'[ \t]*<(?P<tag>[a-zA-Z0-9]+)[^>]*\b{drop}="analytics"[^>]*>.*?</(?P=tag)>\n?',
        re.S,
    )
    result = pattern.sub("", markup)
    keep = "data-if" if analytics else "data-unless"
    return result.replace(f'{keep}="analytics" ', "")


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

    # Los placeholders van en un atributo, no en el contenido del elemento.
    def replace_ph(m: re.Match) -> str:
        key = m.group("key")
        value = i18n.get(lang, {}).get(key)
        if value is None:
            missing.add(key)
            value = i18n[DEFAULT_LANG].get(key, "")
        return f'placeholder="{html.escape(value, quote=True)}"'

    result = re.sub(
        r'data-i18n-ph="(?P<key>[^"]+)"\s+placeholder="[^"]*"', replace_ph, result
    )

    # Atributos traducibles: data-i18n-attr="aria-label=cookie_title", y
    # varios separados por ';'. Hace falta porque aria-label y title no son
    # el contenido del elemento y data-i18n no los alcanza.
    def replace_attrs(m: re.Match) -> str:
        tag = m.group(0)
        for pair in m.group("spec").split(";"):
            attr, _, key = pair.partition("=")
            attr, key = attr.strip(), key.strip()
            if not (attr and key):
                continue
            value = i18n.get(lang, {}).get(key)
            if value is None:
                missing.add(key)
                value = i18n[DEFAULT_LANG].get(key, "")
            value = html.escape(value, quote=True)
            if re.search(rf'\s{re.escape(attr)}="', tag):
                tag = re.sub(rf'(\s{re.escape(attr)}=")[^"]*"',
                             lambda hit: hit.group(1) + value + '"', tag, count=1)
            else:
                tag = tag[:-1].rstrip() + f' {attr}="{value}">'
        return tag

    result = re.sub(
        r'<[a-zA-Z0-9]+[^>]*\bdata-i18n-attr="(?P<spec>[^"]+)"[^>]*>',
        replace_attrs, result,
    )

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

    forms = json.loads((SRC / "forms.json").read_text(encoding="utf-8"))
    analytics_cfg = json.loads((SRC / "analytics.json").read_text(encoding="utf-8"))
    ga4 = (analytics_cfg.get("ga4_id") or "").strip()
    hotjar = (analytics_cfg.get("hotjar_id") or "").strip()
    measuring = bool(ga4 or hotjar)

    # Elementos comunes: cada archivo de src/partials/ es un marcador.
    partials = load_partials()
    # Estos no se insertan tal cual, hay que rellenarlos antes.
    tpl_form = partials.pop("FORM")
    tpl_contacto = partials.pop("FORM_CONTACTO")
    tpl_banner = partials.pop("CONSENT_BANNER")
    tpl_prefs = partials.pop("CONSENT_PREFS")

    written: list[str] = []
    for lang, (folder, _, _) in LANGUAGES.items():
        out_root = REPO / folder if folder else REPO
        carta_tabs, carta_panels, carta_notes = render_carta(menu, i18n, lang)

        # Lo que es igual en todas las páginas de este idioma.
        common = dict(partials)
        common["CARTA_TABS"] = carta_tabs
        common["CARTA_PANELS"] = carta_panels
        common["CARTA_NOTES"] = carta_notes
        common["FORM_CATERING"] = render_form(
            tpl_form, forms, "catering", lang, i18n, "catering")
        common["FORM_CONTACTO"] = render_contacto(
            tpl_contacto, tpl_form, forms, lang, i18n)
        # Sin IDs de medición no hay nada que consentir: ni banner ni botón.
        common["CONSENT_BANNER"] = tpl_banner if measuring else ""
        common["CONSENT_PREFS"] = tpl_prefs if measuring else ""

        for page in PAGES:
            template = (SRC / "pages" / page).read_text(encoding="utf-8")
            prefix = prefix_for(page, lang)     # hasta la raíz del sitio
            home = lang_prefix_for(page)        # hasta la raíz del idioma

            # Y lo que cambia en cada página.
            slots = dict(common)
            slots["SEO"] = render_seo(page, lang, meta)
            slots["BREADCRUMBS"] = render_breadcrumbs(page, lang, i18n, posts)
            slots["ANALYTICS"] = render_analytics(ga4, hotjar, analytics_cfg, prefix)
            slots["LANG_SWITCH"] = render_lang_switch(page, lang, i18n)
            slots["NOVEDADES"] = render_novedades(posts, i18n, lang, prefix, home)

            body = strip_source_notes(expand_partials(template, slots))
            for name in leftover_markers(body):
                print(f"  aviso [{lang}] {page}: marcador <!--{{{{{name}}}}}--> "
                      f"sin resolver (¿falta src/partials/?)", file=sys.stderr)

            if "{{POST_DATE}}" in body:
                slug = Path(page).stem
                post = next((p for p in posts if p["slug"] == slug), None)
                body = body.replace("{{POST_DATE}}", esc(fmt_date(post["date"], lang)) if post else "")

            body = resolve_mailboxes(body, lang)
            body = strip_conditionals(body, measuring)
            body = apply_translations(body, i18n, lang)
            body = (body.replace("{{LANG}}", lang)
                    .replace("{{PREFIX}}", prefix)
                    .replace("{{HOME}}", home))

            target = out_root / page
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            written.append(str(target.relative_to(REPO)))

    write_sitemap()
    write_robots()
    tools = ", ".join(n for n, on in (("GA4", ga4), ("Hotjar", hotjar)) if on) or "ninguna"
    print(f"OK: {len(written)} páginas en {len(LANGUAGES)} idiomas · medición: {tools}")
    if not measuring:
        print("  (sin IDs en src/analytics.json: no se inyecta nada ni aparece el banner)")
    for path in written:
        print(f"  · {path}")
    print("  · sitemap.xml\n  · robots.txt")
    return 0


def write_sitemap() -> None:
    today = date.today().isoformat()
    urls = []
    for page in PAGES:
        if page == "404.html":
            continue
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
        "User-agent: *\n"
        "Allow: /\n"
        # El código con el que se genera la web no es la web. _config.yml ya
        # evita publicarlo; esto es la segunda barrera.
        "Disallow: /src/\n"
        "Disallow: /scripts/\n"
        "Disallow: /carta/\n"
        f"\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )


if __name__ == "__main__":
    sys.exit(build())
