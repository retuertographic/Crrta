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
import unicodedata
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"

# Dominio propio. GitHub Pages lo sirve por el archivo CNAME de la raíz, y
# redirige retuertographic.github.io/Crrta aquí, así que los enlaces
# antiguos siguen funcionando.
SITE_URL = "https://lacarretadelcarreton.com"
SITE_NAME = "La Carreta del Carretón"

# Las imágenes de vista previa al compartir. Son JPEG de 1200x630 y las
# genera scripts/build_share.py; aquí solo se enlazan. Las fotos del sitio
# son WebP, que WhatsApp no sabe enseñar en la vista previa de un enlace,
# y las redes dibujan la tarjeta en 1,91:1, así que no vale con enlazar la
# foto original.
SHARE_DIR = "img/share"
SHARE_DEFECTO = f"{SHARE_DIR}/default.jpg"
SHARE_ANCHO, SHARE_ALTO = 1200, 630

# código -> (carpeta de salida, etiqueta hreflang, locale para las fechas)
LANGUAGES = {
    "es": ("", "es-ES", "es-ES"),
    "en": ("en", "en", "en-GB"),
}
DEFAULT_LANG = "es"

PAGES = [
    "index.html",
    "legal.html",
    "aviso-legal.html",
    "privacidad.html",
    "cookies.html",
    "catering.html",
    "novedades.html",
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

            foto = item.get("photo")
            clase = "menu-item con-foto" if foto else "menu-item"
            rows.append(f'<div class="{clase}">')
            if foto:
                # Decorativa: el nombre del plato está justo al lado, así que
                # repetirlo en el alt solo estorba a quien usa lector.
                # {{PREFIX}} lo resuelve el bucle de páginas al final, igual
                # que en las plantillas: render_carta no sabe a qué
                # profundidad se va a publicar.
                # El 84x84 no es el tamaño del archivo sino el del hueco que
                # ocupa: el CSS fija las dos medidas y recorta con
                # object-fit, así que es lo que hay que reservar.
                rows.append(f'<div class="mi-foto"><img src="{{{{PREFIX}}}}{esc(foto)}" alt="" '
                            f'loading="lazy" width="84" height="84"></div>')
            rows.append('<div class="mi-main">')
            nombre = esc(field(item, "name", lang))
            distintivo = item.get("badge")
            if distintivo in ("estrella", "casa"):
                clave = "badge_estrella" if distintivo == "estrella" else "badge_casa"
                nombre += (f'<span class="mi-badge mi-badge--{distintivo}">'
                           f'{esc(t(i18n, lang, clave))}</span>')
            rows.append(f'<div class="mi-name">{nombre}</div>')
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
        # El alt describe la foto, no repite el titular: el titular ya va
        # justo debajo y un lector de pantalla lo diría dos veces.
        alt = esc(field(post, "alt", lang))
        ancho, alto = post.get("image_w"), post.get("image_h")
        medidas = f' width="{int(ancho)}" height="{int(alto)}"' if ancho and alto else ""
        cards.append(
            f'<article class="nov-card">'
            f'<div class="thumb"><img src="{prefix}{esc(post["image"])}" alt="{alt}"'
            f'{medidas} loading="lazy"></div>'
            f'<div class="body"><div class="nov-date">{esc(fmt_date(post["date"], lang))}</div>'
            f'<h3>{title}</h3><p>{excerpt}</p>'
            f'<a class="read-more" href="{home}novedades/{esc(post["slug"])}.html">'
            f'{esc(t(i18n, lang, "read_more"))}</a></div></article>'
        )
    cards.append("</div>")
    return "\n".join(cards)


def post_page(post: dict) -> str:
    """La ruta publicada de una entrada."""
    return f"novedades/{post['slug']}.html"


def render_post_cover(post: dict, lang: str, prefix: str) -> str:
    """La foto de cabecera, si la entrada tiene.

    Las medidas van en el HTML para que el navegador reserve el hueco antes
    de descargarla: sin ellas el texto salta cuando llega la imagen."""
    imagen = post.get("image")
    if not imagen:
        return ""
    alt = esc(field(post, "alt", lang))
    ancho, alto = post.get("image_w"), post.get("image_h")
    medidas = f' width="{int(ancho)}" height="{int(alto)}"' if ancho and alto else ""
    return (f'<img class="post-cover" src="{prefix}{esc(imagen)}" alt="{alt}"'
            f'{medidas}>')


def render_post_body(post: dict, lang: str) -> str:
    """El cuerpo de la entrada, bloque a bloque, igual que los legales."""
    html_out = []
    for b in post.get("cuerpo", []):
        tipo = b["t"]
        if tipo in ("h2", "h3"):
            html_out.append(f"<{tipo}>{esc(b[lang])}</{tipo}>")
        elif tipo == "p":
            html_out.append(f"<p>{texto_inline(b[lang])}</p>")
        elif tipo == "destacado":
            html_out.append(f'<p class="post-destacado">{texto_inline(b[lang])}</p>')
        elif tipo == "ul":
            items = "".join(f"<li>{texto_inline(x)}</li>" for x in b[lang])
            html_out.append(f"<ul>{items}</ul>")
        else:
            print(f"  aviso: bloque «{tipo}» desconocido en la entrada "
                  f"«{post.get('slug')}»", file=sys.stderr)
    return "\n    ".join(html_out)


def limpia_novedades(out_root: Path, post_pages: list[str]) -> list[str]:
    """Borra las entradas publicadas que ya no toca publicar.

    Hace falta porque el generador solo escribe, nunca borra: una entrada
    que se programa para más adelante, que se renombra o que se quita del
    archivo de datos dejaría su HTML antiguo colgado en el servidor, fuera
    del listado y del sitemap pero accesible por su URL."""
    carpeta = out_root / "novedades"
    if not carpeta.is_dir():
        return []
    validos = {Path(x).name for x in post_pages}
    retiradas = []
    for f in sorted(carpeta.glob("*.html")):
        if f.name not in validos:
            f.unlink()
            retiradas.append(str(f.relative_to(REPO)))
    return retiradas


def meta_de_posts(posts: list[dict]) -> dict:
    """El SEO de cada entrada sale de sus propios datos.

    Si la entrada no trae «seo», se usan su título y su entradilla: una
    novedad sin description es peor que una description repetida."""
    out = {}
    for post in posts:
        seo = post.get("seo") or {}
        por_idioma = {}
        for lang in LANGUAGES:
            info = dict(seo.get(lang) or {})
            info.setdefault("title", f"{field(post, 'title', lang)} · La Carreta del Carretón")
            info.setdefault("description", field(post, "excerpt", lang))
            info["og_type"] = "article"
            info["published"] = post["date"]
            if post.get("image"):
                info.setdefault("image", post["image"])
                info.setdefault("image_alt", field(post, "alt", lang))
            por_idioma[lang] = info
        out[post_page(post)] = por_idioma
    return out


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

# Etiqueta de cada hueco del titular cuando está sin rellenar. Sale
# publicado tal cual, a propósito: un aviso legal al que le falta el NIF
# tiene que notarse, no esconderse.
PENDIENTE = {
    "nombre": {"es": "nombre del titular", "en": "owner's name"},
    "nif": {"es": "NIF", "en": "tax ID"},
    "registro": {"es": "Registro Mercantil", "en": "Commercial Register"},
}

ENLACE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def slug(text: str) -> str:
    base = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


def legal_tokens(text: str, titular: dict, lang: str) -> str:
    """Mete los datos del titular. Lo que falte se publica como [PENDIENTE: ...]."""
    def uno(m):
        clave = m.group(1)
        valor = (titular.get(clave) or "").strip()
        if valor:
            return valor
        etiqueta = PENDIENTE.get(clave, {}).get(lang) or clave
        return f"[{'PENDIENTE' if lang == 'es' else 'TO BE COMPLETED'}: {etiqueta}]"
    return re.sub(r"\[\[(\w+)\]\]", uno, text)


def texto_inline(text: str) -> str:
    """Escapa el texto y convierte [texto](enlace).

    Un enlace que empieza por ~ es interno y se resuelve al idioma de la
    página; si el texto empieza por «mailto:», el enlace es un correo. Lo
    usan los textos legales y las entradas de novedades, que son los dos
    sitios donde el texto lo escribe una persona en un archivo de datos."""
    def enlace(m):
        etiqueta, url = m.group(1), m.group(2)
        if etiqueta.startswith("mailto:"):
            etiqueta, url = etiqueta[7:], "mailto:" + url
        elif url.startswith("~"):
            url = "{{HOME}}" + url[1:]
        fuera = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
        return f'<a href="{url}"{fuera}>{etiqueta}</a>'

    return ENLACE.sub(enlace, esc(text))


def legal_inline(text: str, titular: dict, lang: str) -> str:
    """Igual, con los datos del titular ya sustituidos."""
    return texto_inline(legal_tokens(text, titular, lang))


def render_legal(bloques: list, titular: dict, lang: str, consentimiento: bool) -> str:
    """Un documento legal de src/legal.json, en el idioma de la página."""
    vistos: set[str] = set()
    html_out: list[str] = []
    for b in bloques:
        if b.get("solo_si") and not (titular.get(b["solo_si"]) or "").strip():
            continue
        if b.get("solo_si_consentimiento") and not consentimiento:
            continue
        if b.get("solo_idioma") and b["solo_idioma"] != lang:
            continue
        tipo = b["t"]
        if tipo in ("h2", "h3"):
            texto = legal_tokens(b[lang], titular, lang)
            ident, n = slug(texto), 2
            while ident in vistos:
                ident, n = f"{ident}-{n}", n + 1
            vistos.add(ident)
            html_out.append(f"<{tipo} id=\"{esc(ident)}\">{esc(texto)}</{tipo}>")
        elif tipo == "p":
            clase = f' class="{esc(b["clase"])}"' if b.get("clase") else ""
            html_out.append(f"<p{clase}>{legal_inline(b[lang], titular, lang)}</p>")
        elif tipo == "ul":
            items = "".join(f"<li>{legal_inline(x, titular, lang)}</li>" for x in b[lang])
            html_out.append(f"<ul>{items}</ul>")
        elif tipo == "tabla":
            cab = "".join(f'<th scope="col">{esc(c)}</th>' for c in b["cabecera"][lang])
            filas = "".join(
                "<tr>" + "".join(f"<td>{legal_inline(c, titular, lang)}</td>" for c in fila) + "</tr>"
                for fila in b["filas"][lang])
            # tabindex y role: la caja se desplaza a lo ancho en móvil y una
            # zona con scroll tiene que poder recorrerse con el teclado.
            etiqueta = esc((b.get("etiqueta") or {}).get(lang, ""))
            html_out.append(
                f'<div class="legal-tabla" role="region" aria-label="{etiqueta}" tabindex="0">'
                f"<table><thead><tr>{cab}</tr></thead><tbody>{filas}</tbody></table></div>")
    return "\n    ".join(html_out)


# Los tres documentos legales, en el orden en que se enseñan.
LEGAL_PAGES = [("aviso-legal.html", "footer_legal"),
               ("privacidad.html", "footer_privacy"),
               ("cookies.html", "footer_cookies")]


def render_legal_fecha(iso: str, i18n: dict, lang: str) -> str:
    return (f'<p class="legal-updated">{esc(t(i18n, lang, "legal_updated"))} '
            f'{esc(fmt_date(iso, lang))}.</p>')


def render_legal_otros(page: str, i18n: dict, lang: str) -> str:
    """Los otros dos documentos, al pie de cada uno. Dos clics como mucho
    desde cualquier página, que es lo que pide la guía."""
    otros = [(destino, clave) for destino, clave in LEGAL_PAGES if destino != page]
    if not otros:
        return ""
    enlaces = "".join(
        f'<a href="{{{{HOME}}}}{destino}">{esc(t(i18n, lang, clave))}</a>'
        for destino, clave in otros)
    return ('<nav class="legal-otros" aria-labelledby="otros-legales">'
            f'<h2 id="otros-legales">{esc(t(i18n, lang, "legal_otros"))}</h2>'
            f"{enlaces}</nav>")


DIAS = {
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}


def fecha_larga(iso: str, lang: str) -> str:
    """«Viernes 6 de noviembre» / «Friday 6 November». Sin el año: son
    fechas de las próximas semanas y el año sobra para leerlas."""
    d = date.fromisoformat(iso)
    dia = DIAS.get(lang, DIAS["en"])[d.weekday()]
    mes = MONTHS.get(lang, MONTHS["en"])[d.month - 1]
    texto = f"{dia} {d.day} de {mes}" if lang == "es" else f"{dia} {d.day} {mes}"
    return texto[0].upper() + texto[1:]


def render_salsa_fechas(eventos: dict, i18n: dict, lang: str) -> str:
    """El hueco de las fechas de Guachin Salsa.

    Las que ya han pasado no se publican: una fecha vieja en una web es
    peor que no poner ninguna. Si no queda ninguna por delante, vuelve el
    aviso de que no hay fecha confirmada."""
    hoy = date.today()
    futuras = [e["fecha"] for e in (eventos.get("guachin_salsa") or [])
               if date.fromisoformat(e["fecha"]) >= hoy]
    if not futuras:
        return (f'<strong>{esc(t(i18n, lang, "salsa_next_title"))}</strong>\n'
                f'          <p>{esc(t(i18n, lang, "salsa_next_none"))}</p>')
    clave = "salsa_next_title" if len(futuras) == 1 else "salsa_next_titles"
    fechas = "".join(f"<li>{esc(fecha_larga(f, lang))}</li>" for f in sorted(futuras))
    return (f'<strong>{esc(t(i18n, lang, clave))}</strong>\n'
            f'          <ul class="salsa-fechas">{fechas}</ul>\n'
            f'          <p>{esc(t(i18n, lang, "salsa_next_book"))}</p>')


def render_menus(datos: dict, i18n: dict, lang: str) -> str:
    """Los menús cerrados para grupos, una tarjeta por menú.

    El aviso del IGIC va dentro de cada tarjeta y no una vez arriba: el que
    llega a un menú desde el móvil o desde un enlace se encuentra el precio
    sin el aviso al lado, y la carta de la web sí lleva el IGIC incluido.
    Repetirlo cuatro veces es el precio de que no se lea separado de su
    precio."""
    aviso_igic = datos["nota"][lang]
    tarjetas = []
    for m in datos.get("menus", []):
        etiqueta = (m.get("etiqueta") or {}).get(lang, "")
        bloques = []
        for b in m["bloques"]:
            nota = (b.get("nota") or {}).get(lang, "")
            cabecera = esc(b["titulo"][lang]) + (f' <span class="menu-nota">{esc(nota)}</span>' if nota else "")
            lineas = []
            for pl in b["platos"]:
                det = (pl.get("detalle") or {}).get(lang, "")
                lineas.append(f'<li>{esc(pl["plato"])}'
                              + (f' <span class="menu-det">{esc(det)}</span>' if det else "")
                              + "</li>")
            cierre = (b.get("cierre") or {}).get(lang, "")
            bloques.append(
                f'<div class="menu-bloque"><h4>{cabecera}</h4><ul>{"".join(lineas)}</ul>'
                + (f'<p class="menu-cierre">{esc(cierre)}</p>' if cierre else "")
                + "</div>")
        tarjetas.append(
            f'<article class="menu-card{" menu-card--destacado" if m.get("destacado") else ""}">'
            f'<header class="menu-head">'
            f'<h3>{esc(m["titulo"][lang])}'
            + (f' <span class="menu-etiqueta">{esc(etiqueta)}</span>' if etiqueta else "")
            + f'</h3><p class="menu-precio">{esc(m["precio"])} €'
            f'<span>{esc(t(i18n, lang, "menus_por_persona"))}</span></p>'
            f'<p class="menu-igic">{esc(aviso_igic)}</p>'
            f'<p class="menu-resumen">{esc(m["resumen"][lang])}</p></header>'
            f'<div class="menu-bloques">{"".join(bloques)}</div></article>')
    return "\n      ".join(tarjetas)


def render_cmp(cmp: dict) -> str:
    """El gestor de consentimiento de cookies, si lo hay.

    Va en el <head> y antes que nada: un aviso de cookies tiene que poder
    decidir antes de que cargue nada que ponga cookies. Se respeta el orden
    que da el proveedor —primero su script de arranque, luego la variable
    de configuración, luego el resto— porque de ese orden depende que el
    segundo encuentre la configuración puesta.

    El preconnect no lo pide el proveedor: lo añadimos para que el
    navegador abra la conexión con su servidor mientras todavía está
    leyendo el <head>, que es tiempo que se le quita al primer script, que
    es síncrono y bloquea el dibujado."""
    scripts = (cmp or {}).get("scripts") or []
    if not scripts:
        return ""

    lineas = []
    origenes = []
    for s in scripts:
        o = re.match(r"https?://[^/]+", s.get("src", ""))
        if o and o.group(0) not in origenes:
            origenes.append(o.group(0))
    for o in origenes:
        lineas.append(f'<link rel="preconnect" href="{esc(o)}" crossorigin>')

    config = (cmp or {}).get("config") or {}
    primera, resto = scripts[0], scripts[1:]

    def etiqueta(s: dict) -> str:
        extra = "".join(
            f" {esc(k)}" if v is True else f' {esc(k)}="{esc(v)}"'
            for k, v in s.items() if k != "src" and v is not False)
        return f'<script src="{esc(s["src"])}"{extra}></script>'

    lineas.append(etiqueta(primera))
    if config.get("variable"):
        # json.dumps y no una plantilla: así un valor con comillas no puede
        # romper el script ni colar nada dentro de la página.
        valor = json.dumps(config.get("valor") or {}, ensure_ascii=False)
        valor = valor.replace("</", "<\\/")      # ni cerrar el <script> antes de tiempo
        lineas.append(f'<script>window.{config["variable"]} = {valor};</script>')
    lineas += [etiqueta(s) for s in resto]
    return "\n".join(lineas)


def share_image(image: str | None, page: str) -> str:
    """La imagen de vista previa de esta página, relativa a la raíz.

    Si la página declara foto propia se usa su versión de img/share/; si no
    la declara, o todavía no se ha generado, se usa la del logotipo. El
    aviso está para enterarse al generar y no al compartir el enlace."""
    if image:
        destino = f"{SHARE_DIR}/{Path(image).stem}.jpg"
        if (REPO / destino).exists():
            return destino
        print(f"  aviso {page}: falta {destino}; se comparte con el logotipo. "
              f"Ejecuta scripts/build_share.py", file=sys.stderr)
    return SHARE_DEFECTO


def render_seo(page: str, lang: str, meta: dict, i18n: dict) -> str:
    """title, description, canonical, og:, twitter: y hreflang de esta página.

    El canonical apunta siempre a la propia URL (autorreferente) y
    las etiquetas hreflang declaran las dos versiones, para que Google
    no trate español e inglés como contenido duplicado.

    Las og: y twitter: son las que leen WhatsApp, Facebook, X y Telegram
    al pegar un enlace. Van con el tamaño declarado porque sin él algunas
    enseñan una miniatura pequeña en vez de la tarjeta grande."""
    info = meta.get(page, {}).get(lang) or meta.get(page, {}).get(DEFAULT_LANG, {})
    title = info.get("title", SITE_NAME)
    description = info.get("description", "")
    og_type = info.get("og_type", "website")
    image = share_image(info.get("image"), page)
    if image == SHARE_DEFECTO:
        image_alt = t(i18n, lang, "og_logo_alt", SITE_NAME)
    else:
        image_alt = info.get("image_alt") or title

    lines = [
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
        f'<link rel="canonical" href="{esc(page_url(page, lang))}">',
        f'<meta property="og:site_name" content="{esc(SITE_NAME)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:type" content="{esc(og_type)}">',
        f'<meta property="og:url" content="{esc(page_url(page, lang))}">',
        f'<meta property="og:image" content="{SITE_URL}/{esc(image)}">',
        f'<meta property="og:image:type" content="image/jpeg">',
        f'<meta property="og:image:width" content="{SHARE_ANCHO}">',
        f'<meta property="og:image:height" content="{SHARE_ALTO}">',
        f'<meta property="og:image:alt" content="{esc(image_alt)}">',
        # El tercer campo, no el segundo: el segundo es el hreflang, que para
        # el inglés es «en» a secas, y og:locale pide idioma_PAÍS.
        f'<meta property="og:locale" content="{esc(LANGUAGES[lang][2].replace("-", "_"))}">',
    ]
    for code in LANGUAGES:
        if code != lang:
            lines.append('<meta property="og:locale:alternate" content="'
                         f'{esc(LANGUAGES[code][2].replace("-", "_"))}">')
    if og_type == "article" and info.get("published"):
        lines.append('<meta property="article:published_time" '
                     f'content="{esc(info["published"])}">')
    # X y Telegram leen las suyas; sin twitter:card sale el enlace pelado.
    lines += [
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
        f'<meta name="twitter:image" content="{SITE_URL}/{esc(image)}">',
        f'<meta name="twitter:image:alt" content="{esc(image_alt)}">',
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


# --------------------------------------------------- datos estructurados

RESTAURANTE_ID = f"{SITE_URL}/#restaurante"


def editor() -> dict:
    """Quién firma y quién publica, para las páginas que no son la portada.

    Va con @id al nodo Restaurant de la portada, pero repitiendo nombre y
    logotipo: así cada página se entiende sola y Google no depende de haber
    leído antes la portada."""
    return {
        "@type": "Organization",
        "@id": RESTAURANTE_ID,
        "name": SITE_NAME,
        "url": f"{SITE_URL}/",
        "logo": {"@type": "ImageObject",
                 "url": url_absoluta("img/logo-square.jpg"),
                 "width": 1990, "height": 2000},
    }


def jsonld(datos: dict) -> str:
    return ('<script type="application/ld+json">\n'
            + json.dumps(datos, ensure_ascii=False, indent=2)
            + "\n</script>")


def url_absoluta(rel: str) -> str:
    return f"{SITE_URL}/{rel.lstrip('/')}"


def render_schema_post(post: dict, lang: str) -> str:
    """La ficha de una novedad para Google.

    author y publisher apuntan por @id a la ficha del restaurante que está
    en la portada, en vez de repetirla: así Google ve un solo negocio.

    No lleva dateModified a propósito: no se guarda cuándo se tocó cada
    entrada, y poner la fecha de publicación ahí sería decir que nunca se
    ha cambiado, que no siempre es verdad."""
    page = post_page(post)
    url = page_url(page, lang)
    datos = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "@id": f"{url}#articulo",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": field(post, "title", lang),
        "description": field(post, "excerpt", lang),
        "datePublished": post["date"],
        "inLanguage": LANGUAGES[lang][2],
        "isPartOf": {"@type": "Blog", "@id": f'{page_url("novedades.html", lang)}#blog'},
        "author": editor(),
        "publisher": editor(),
    }
    imagen = share_image(post.get("image"), page)
    datos["image"] = [url_absoluta(imagen)]
    return jsonld(datos)


def render_schema_blog(posts: list[dict], i18n: dict, lang: str) -> str:
    """El índice de novedades, con sus entradas."""
    url = page_url("novedades.html", lang)
    entradas = []
    for post in sorted(posts, key=lambda x: x["date"], reverse=True):
        p_url = page_url(post_page(post), lang)
        entradas.append({
            "@type": "BlogPosting",
            "@id": f"{p_url}#articulo",
            "url": p_url,
            "headline": field(post, "title", lang),
            "datePublished": post["date"],
            "image": url_absoluta(share_image(post.get("image"), post_page(post))),
        })
    return jsonld({
        "@context": "https://schema.org",
        "@type": "Blog",
        "@id": f"{url}#blog",
        "url": url,
        "name": f'{t(i18n, lang, "nav_novedades")} · {SITE_NAME}',
        "inLanguage": LANGUAGES[lang][2],
        "publisher": editor(),
        "blogPost": entradas,
    })


def render_schema_eventos(eventos: dict, i18n: dict, lang: str) -> str:
    """Las fechas de Guachin Salsa que quedan por delante, como eventos.

    Sin hora: los carteles no la dicen y schema.org admite startDate con
    fecha sola. Sin offers ni performer por lo mismo; Google los marca como
    recomendados, no obligatorios, y es mejor no decir nada que inventarlo."""
    hoy = date.today()
    futuras = sorted(e["fecha"] for e in (eventos.get("guachin_salsa") or [])
                     if date.fromisoformat(e["fecha"]) >= hoy)
    if not futuras:
        return ""
    salida = []
    for fecha in futuras:
        salida.append(jsonld({
            "@context": "https://schema.org",
            "@type": "Event",
            "@id": f"{SITE_URL}/#guachin-{fecha}",
            "name": f"Guachin Salsa · {SITE_NAME}",
            "description": t(i18n, lang, "salsa_p2"),
            "startDate": fecha,
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "url": f'{page_url("index.html", lang)}#guachin',
            "image": [url_absoluta(share_image("img/guachin-baile.webp", "index.html"))],
            "location": {"@id": RESTAURANTE_ID},
            "organizer": {"@id": RESTAURANTE_ID},
            "inLanguage": LANGUAGES[lang][2],
        }))
    return "\n".join(salida)


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
    todas = json.loads((REPO / "novedades-data.json").read_text(encoding="utf-8")).get("posts", [])
    # «date» es la fecha de publicación: una entrada con fecha futura no se
    # publica todavía (ni tarjeta, ni página, ni sitemap). Se puede dejar
    # escrita hoy y que salga sola el día que toque, porque el sitio se
    # vuelve a generar cada mañana (.github/workflows/rehacer-cada-dia.yml).
    hoy = date.today()
    posts = [x for x in todas if date.fromisoformat(x["date"]) <= hoy]
    programadas = [x for x in todas if date.fromisoformat(x["date"]) > hoy]
    for x in sorted(programadas, key=lambda x: x["date"]):
        print(f"  · programada para el {x['date']}: {field(x, 'title', DEFAULT_LANG)}")
    # Cada entrada se publica como página propia a partir de una sola
    # plantilla: añadir una novedad es añadir un objeto al archivo de datos.
    post_pages = [post_page(x) for x in posts]
    meta.update(meta_de_posts(posts))

    for code in LANGUAGES:
        if code not in i18n:
            print(f"ERROR: falta el idioma «{code}» en src/i18n.json", file=sys.stderr)
            return 1

    forms = json.loads((SRC / "forms.json").read_text(encoding="utf-8"))
    legal = json.loads((SRC / "legal.json").read_text(encoding="utf-8"))
    menus = json.loads((SRC / "menus.json").read_text(encoding="utf-8"))
    eventos = json.loads((SRC / "eventos.json").read_text(encoding="utf-8"))
    titular = legal["titular"]
    analytics_cfg = json.loads((SRC / "analytics.json").read_text(encoding="utf-8"))
    ga4 = (analytics_cfg.get("ga4_id") or "").strip()
    hotjar = (analytics_cfg.get("hotjar_id") or "").strip()
    measuring = bool(ga4 or hotjar)
    # El aviso de cookies lo pone un gestor externo: en cuanto haya scripts
    # en src/analytics.json («cmp»), se inyectan y se retira el banner
    # propio, para no tener dos avisos peleándose.
    cmp = analytics_cfg.get("cmp") or {}
    cmp_on = bool(cmp.get("scripts"))
    consentimiento = bool(measuring or cmp_on)

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
        # Con gestor externo, el banner propio sobra.
        propio = measuring and not cmp_on
        common["CONSENT_BANNER"] = tpl_banner if propio else ""
        common["CONSENT_PREFS"] = tpl_prefs if propio else ""
        common["CMP"] = render_cmp(cmp)
        common["MENUS"] = render_menus(menus, i18n, lang)
        common["MENUS_PIE"] = esc(menus["pie"][lang])
        common["SALSA_FECHAS"] = render_salsa_fechas(eventos, i18n, lang)
        common["SCHEMA_EVENTOS"] = render_schema_eventos(eventos, i18n, lang)
        common["SCHEMA_BLOG"] = render_schema_blog(posts, i18n, lang)
        for clave, doc in (("DOC_AVISO", "aviso-legal"),
                           ("DOC_PRIVACIDAD", "privacidad"),
                           ("DOC_COOKIES", "cookies")):
            common[clave] = render_legal(
                legal["documentos"][doc], titular, lang, consentimiento)

        for page in PAGES + post_pages:
            origen = (SRC / "pages" / "novedades" / "_entrada.html"
                      if page in post_pages else SRC / "pages" / page)
            template = origen.read_text(encoding="utf-8")
            prefix = prefix_for(page, lang)     # hasta la raíz del sitio
            home = lang_prefix_for(page)        # hasta la raíz del idioma

            # Y lo que cambia en cada página.
            slots = dict(common)
            slots["SEO"] = render_seo(page, lang, meta, i18n)
            slots["BREADCRUMBS"] = render_breadcrumbs(page, lang, i18n, posts)
            slots["ANALYTICS"] = render_analytics(ga4, hotjar, analytics_cfg, prefix)
            slots["LANG_SWITCH"] = render_lang_switch(page, lang, i18n)
            slots["NOVEDADES"] = render_novedades(posts, i18n, lang, prefix, home)
            slots["LEGAL_ACTUALIZADO"] = render_legal_fecha(legal["actualizado"], i18n, lang)
            slots["LEGAL_OTROS"] = render_legal_otros(page, i18n, lang)
            if page in post_pages:
                post = posts[post_pages.index(page)]
                slots["POST_TITLE"] = esc(field(post, "title", lang))
                slots["POST_DATE"] = esc(fmt_date(post["date"], lang))
                slots["POST_COVER"] = render_post_cover(post, lang, prefix)
                slots["POST_BODY"] = render_post_body(post, lang)
                slots["SCHEMA_POST"] = render_schema_post(post, lang)

            body = strip_source_notes(expand_partials(template, slots))
            for name in leftover_markers(body):
                print(f"  aviso [{lang}] {page}: marcador <!--{{{{{name}}}}}--> "
                      f"sin resolver (¿falta src/partials/?)", file=sys.stderr)

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

        for retirada in limpia_novedades(out_root, post_pages):
            print(f"  retirada: {retirada}")

    write_sitemap(PAGES + post_pages)
    write_robots()
    tools = ", ".join(n for n, on in (("GA4", ga4), ("Hotjar", hotjar)) if on) or "ninguna"
    print(f"OK: {len(written)} páginas en {len(LANGUAGES)} idiomas · medición: {tools}")
    faltan = [k for k in PENDIENTE if not (titular.get(k) or "").strip()]
    if faltan:
        print("  AVISO: los textos legales salen con huecos sin rellenar en "
              "src/legal.json → " + ", ".join(faltan), file=sys.stderr)
        print("         El artículo 10 de la LSSICE exige publicar al menos "
              "nombre del titular y NIF.", file=sys.stderr)
    futuras = [e["fecha"] for e in (eventos.get("guachin_salsa") or [])
               if date.fromisoformat(e["fecha"]) >= date.today()]
    if len(futuras) == 0:
        print("  AVISO: no queda ninguna fecha de Guachin Salsa por delante en "
              "src/eventos.json; el hueco dice que no hay fecha confirmada.", file=sys.stderr)
    elif len(futuras) < 2:
        print(f"  · Guachin Salsa: solo queda {len(futuras)} fecha por delante ({futuras[0]})")
    else:
        print(f"  · Guachin Salsa: {len(futuras)} fechas por delante, la próxima el {min(futuras)}")
    if cmp_on:
        print(f"  · aviso de cookies: {cmp.get('nombre') or 'gestor externo'} "
              f"({len(cmp['scripts'])} scripts)")
    elif measuring:
        print("  · aviso de cookies: banner propio")
    if not measuring:
        print("  (sin IDs en src/analytics.json: no se inyecta nada ni aparece el banner)")
    for path in written:
        print(f"  · {path}")
    print("  · sitemap.xml\n  · robots.txt")
    return 0


def write_sitemap(paginas: list[str]) -> None:
    today = date.today().isoformat()
    urls = []
    for page in paginas:
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
