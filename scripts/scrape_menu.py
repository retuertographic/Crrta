#!/usr/bin/env python3
"""
Extrae la carta de La Carreta del Carretón desde su carta digital (mdtotem)
y la guarda en menu-data.json, en la raíz del repositorio.

La página es HTML servido por el servidor (no una app de JavaScript), así que
basta con requests + BeautifulSoup; no hace falta navegador.

El extractor trabaja en dos pasadas:

  1. Estructurada: busca contenedores cuyas clases o etiquetas indiquen
     "categoría" / "plato" / "precio" (que es como suelen montarse estas
     cartas digitales).
  2. De respaldo: recorre el documento en orden, tratando los encabezados
     como nombres de categoría y las líneas que terminan en un precio como
     platos.

Si ninguna pasada obtiene un resultado creíble, el script termina con error
(código 1) en vez de escribir una carta vacía: preferimos que falle el
workflow y se vea la ❌ en GitHub antes que publicar una carta equivocada.

Uso:
    python scripts/scrape_menu.py [--dump-html ruta.html]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

MENU_URL = "https://mdtotem.com/directorio/lacarretadelcarreton/index.php"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "menu-data.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; CarretonMenuBot/1.0; "
    "+https://github.com/retuertographicdesign/crrtn)"
)

# Un precio: 12, 12,50, 12.50, 12,50 €, € 12,50 …
PRICE_RE = re.compile(r"(?<![\d,.])(\d{1,3}(?:[.,]\d{1,2})?)\s*€|€\s*(\d{1,3}(?:[.,]\d{1,2})?)")
PRICE_AT_END_RE = re.compile(r"^(?P<name>.+?)[\s.·•\-–—]*(?P<price>\d{1,3}[.,]\d{2})\s*€?$")

# Mínimos para dar por buena una extracción.
MIN_ITEMS = 5
MIN_CATEGORIES = 1

# Encabezados que no son categorías de la carta.
NOT_A_CATEGORY = {
    "carta", "menu", "menú", "inicio", "contacto", "horario", "horarios",
    "reservas", "reserva", "telefono", "teléfono", "direccion", "dirección",
    "alergenos", "alérgenos", "cookies", "aviso legal", "privacidad",
    "la carreta del carreton", "la carreta del carretón",
}


def norm(text: str) -> str:
    """Colapsa espacios y quita caracteres invisibles."""
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def fold(text: str) -> str:
    """Minúsculas sin acentos, para comparar."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip()


def parse_price(raw: str) -> str | None:
    """Devuelve el precio normalizado como '12,50', o None si no hay."""
    m = PRICE_RE.search(raw)
    if not m:
        return None
    value = m.group(1) or m.group(2)
    value = value.replace(".", ",")
    if "," not in value:
        value = value + ",00"
    return value


def looks_like_category(text: str) -> bool:
    if not text or len(text) > 60:
        return False
    if fold(text) in NOT_A_CATEGORY:
        return False
    return PRICE_RE.search(text) is None


def class_hint(tag: Tag, *words: str) -> bool:
    """¿Alguna clase o id del elemento contiene alguna de estas palabras?"""
    blob = " ".join(tag.get("class") or []) + " " + (tag.get("id") or "")
    blob = fold(blob)
    return any(w in blob for w in words)


def extract_structured(soup: BeautifulSoup) -> list[dict]:
    """Pasada 1: contenedores con clases que nombran categorías y platos."""
    categories: list[dict] = []

    containers = [
        t for t in soup.find_all(True)
        if class_hint(t, "categoria", "category", "seccion", "section", "grupo", "group", "familia")
    ]
    for box in containers:
        title_el = box.find(
            lambda t: isinstance(t, Tag) and (
                t.name in ("h1", "h2", "h3", "h4", "h5", "h6")
                or class_hint(t, "titulo", "title", "nombre", "name")
            )
        )
        title = norm(title_el.get_text(" ")) if title_el else ""
        if not looks_like_category(title):
            continue

        items: list[dict] = []
        for row in box.find_all(True):
            if not class_hint(row, "plato", "producto", "item", "articulo", "dish", "product"):
                continue
            price_el = row.find(lambda t: isinstance(t, Tag) and class_hint(t, "precio", "price"))
            if price_el is None:
                continue
            price = parse_price(price_el.get_text(" "))
            if price is None:
                continue
            name_el = row.find(
                lambda t: isinstance(t, Tag) and class_hint(t, "nombre", "name", "titulo", "title")
            )
            name = norm(name_el.get_text(" ")) if name_el else ""
            if not name:
                # Sin elemento de nombre: usa el texto de la fila menos el precio.
                name = norm(row.get_text(" ").replace(price_el.get_text(" "), ""))
            if not name:
                continue
            desc_el = row.find(
                lambda t: isinstance(t, Tag) and class_hint(t, "descripcion", "description", "detalle", "ingredientes")
            )
            item = {"name": name, "price": price}
            desc = norm(desc_el.get_text(" ")) if desc_el else ""
            if desc and desc != name:
                item["description"] = desc
            items.append(item)

        if items:
            categories.append({"category": title, "items": items})

    return categories


def extract_flow(soup: BeautifulSoup) -> list[dict]:
    """Pasada 2: recorrido lineal — encabezados y líneas con precio al final."""
    categories: list[dict] = []
    current: dict | None = None

    for el in soup.find_all(True):
        if el.name in ("script", "style", "nav", "header", "footer"):
            continue

        text = norm(el.get_text(" "))
        if not text:
            continue

        # ¿Es un encabezado de categoría?
        is_heading = el.name in ("h1", "h2", "h3", "h4", "h5", "h6") or class_hint(
            el, "categoria", "category", "seccion", "grupo"
        )
        if is_heading and looks_like_category(text):
            if current and current["items"]:
                categories.append(current)
            current = {"category": text, "items": []}
            continue

        # ¿Es una línea "plato ..... precio"? Solo hojas del árbol, para no
        # contar el mismo texto una vez por cada contenedor que lo envuelve.
        if any(isinstance(child, Tag) for child in el.children):
            continue
        m = PRICE_AT_END_RE.match(text)
        if not m:
            continue
        name = norm(m.group("name"))
        price = parse_price(m.group("price") + " €")
        if not name or price is None or len(name) < 2:
            continue
        if current is None:
            current = {"category": "Carta", "items": []}
        current["items"].append({"name": name, "price": price})

    if current and current["items"]:
        categories.append(current)
    return categories


def dedupe(categories: list[dict]) -> list[dict]:
    """Quita categorías vacías y platos repetidos dentro de cada categoría."""
    clean: list[dict] = []
    for cat in categories:
        seen: set[tuple[str, str]] = set()
        items = []
        for item in cat["items"]:
            key = (fold(item["name"]), item["price"])
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
        if items:
            clean.append({"category": cat["category"], "items": items})
    return clean


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dump-html",
        metavar="RUTA",
        help="Guarda el HTML descargado en esta ruta (útil para depurar selectores).",
    )
    args = parser.parse_args()

    try:
        res = requests.get(MENU_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
        res.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERROR: no se pudo descargar la carta: {exc}", file=sys.stderr)
        return 1

    res.encoding = res.apparent_encoding or res.encoding
    html = res.text

    if args.dump_html:
        Path(args.dump_html).write_text(html, encoding="utf-8")
        print(f"HTML guardado en {args.dump_html} ({len(html)} caracteres)")

    soup = BeautifulSoup(html, "html.parser")

    categories = dedupe(extract_structured(soup))
    strategy = "estructurada"
    total = sum(len(c["items"]) for c in categories)

    if len(categories) < MIN_CATEGORIES or total < MIN_ITEMS:
        categories = dedupe(extract_flow(soup))
        strategy = "recorrido lineal"
        total = sum(len(c["items"]) for c in categories)

    if len(categories) < MIN_CATEGORIES or total < MIN_ITEMS:
        print(
            "ERROR: la extracción no dio un resultado creíble "
            f"({len(categories)} categorías, {total} platos; mínimo "
            f"{MIN_CATEGORIES} y {MIN_ITEMS}).\n"
            "Probablemente la carta digital ha cambiado de estructura. "
            "Lanza el script con --dump-html para inspeccionar el HTML y "
            "ajustar los selectores.",
            file=sys.stderr,
        )
        return 1

    payload = {
        "source": MENU_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "categories": categories,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"OK ({strategy}): {len(categories)} categorías y {total} platos "
        f"escritos en {OUTPUT_PATH.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
