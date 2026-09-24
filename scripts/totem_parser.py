#!/usr/bin/env python3
"""
Lector de la carta digital de mdtotem para La Carreta del Carretón.

Cada categoría de la carta es una página con esta forma:

    <div class="encabezadoTexto">Aperitivos</div>
    ...
    <div id="eventos">
      <div class="numeroPlato">1</div>
      <p><strong><span style="font-size:20px">Tostones</span></strong></p>
      <p><span style="font-size:18px">Plátano verde frito</span></p>
      <div class="preciosTexto">1 ración: 4,20€</div>
      <div class="preciosTexto">IGIC INCLUIDO</div>
      <table>… <img src=".../alergenos/gluten.png"> …</table>
      <hr class="rojo">
      <div class="numeroPlato">2</div>
      …
    </div>

Es decir: el título de la categoría vive en `.encabezadoTexto`, y dentro de
`#eventos` cada `.numeroPlato` abre un plato nuevo. Del bloque de cada plato
sacamos nombre, descripción, uno o varios precios (1/2 ración y 1 ración) y
los alérgenos, que vienen como nombres de archivo de imagen.

Este módulo solo parsea. Quien descarga las páginas o las lee de disco es
build_menu.py.
"""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup, Tag

# "1 ración: 4,20€", "1/2 ración: 8,60 €", "Ración 12,30€"
PRICE_LINE_RE = re.compile(
    r"^(?P<label>.*?)[\s:.\-–—]*(?P<value>\d{1,3}(?:[.,]\d{1,2})?)\s*€?\s*$"
)
ALLERGEN_RE = re.compile(r"/alergenos/([a-z0-9_-]+)\.png", re.I)

# Notas que no son precio (impuestos, avisos).
NOTE_WORDS = ("igic", "igíc", "iva", "impuesto")

# Traducción de los nombres de categoría al inglés.
CATEGORY_EN = {
    "fuera de carta": "Off-menu specials",
    "aperitivos": "Starters",
    "ensaladas": "Salads",
    "vegetariano": "Vegetarian",
    "sopas": "Soups",
    "pollo": "Chicken",
    "res": "Beef",
    "carne de cochino": "Pork",
    "pescado y marisco": "Fish & seafood",
    "postres": "Desserts",
    "bebidas": "Drinks",
    "vinos": "Wines",
}

# Etiquetas de ración al inglés.
PORTION_EN = {
    "1/2 racion": "Half portion",
    "media racion": "Half portion",
    "1 racion": "Full portion",
    "racion": "Full portion",
    "unidad": "Each",
}


def norm(text: str) -> str:
    """Colapsa espacios (incluido &nbsp;) y recorta."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def tidy(text: str) -> str:
    """Arregla la puntuación suelta con la que vienen algunos textos
    ('lechuga , frutas ( Uva ) .' -> 'lechuga, frutas (Uva).')."""
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"([,.;:])(?=[^\s\d])", r"\1 ", text)
    return norm(text)


def fold(text: str) -> str:
    """Minúsculas sin acentos, para comparar."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip()


def is_price_box(tag: Tag) -> bool:
    return "preciosTexto" in (tag.get("class") or [])


def parse_price_line(text: str) -> tuple[str, str] | None:
    """'1/2 ración: 4,80€' -> ('1/2 ración', '4,80'). None si no es un precio."""
    m = PRICE_LINE_RE.match(text)
    if not m:
        return None
    label = norm(m.group("label")).strip(" :.-–—")
    value = m.group("value").replace(".", ",")
    if "," not in value:
        value += ",00"
    return label, value


def parse_item_block(block: list[Tag], number: str | None) -> dict | None:
    """Convierte los elementos de un plato en un diccionario."""
    name = ""
    description_parts: list[str] = []
    prices: list[dict] = []
    allergens: list[str] = []
    notes: list[str] = []

    for el in block:
        # Alérgenos: están como <img src=".../alergenos/gluten.png">.
        for img in el.find_all("img") if isinstance(el, Tag) else []:
            m = ALLERGEN_RE.search(img.get("src") or "")
            if m and m.group(1).lower() not in allergens:
                allergens.append(m.group(1).lower())

        if not isinstance(el, Tag):
            continue

        text = norm(el.get_text(" "))
        if not text:
            continue

        if is_price_box(el):
            if any(w in fold(text) for w in NOTE_WORDS):
                if text not in notes:
                    notes.append(text)
                continue
            parsed = parse_price_line(text)
            if parsed:
                label, value = parsed
                prices.append({"label": label, "value": value} if label else {"value": value})
            continue

        if el.name in ("p", "h1", "h2", "h3", "h4"):
            # Dentro de algunos <p> vienen anidados los divs de precio; si al
            # quitarlos no queda texto, no es ni nombre ni descripción.
            own = norm(
                " ".join(
                    t for t in el.find_all(string=True)
                    if not (t.parent and is_price_box(t.parent))
                )
            )
            if not own:
                continue
            if not name:
                name = tidy(own)
            else:
                description_parts.append(own)

    if not name:
        return None

    item: dict = {"name": name}
    if number and number.isdigit():
        item["number"] = int(number)
    description = tidy(" ".join(description_parts))
    if description and fold(description) != fold(name):
        item["description"] = description
    if prices:
        item["prices"] = prices
    if allergens:
        item["allergens"] = sorted(set(allergens))
    if notes:
        item["_notes"] = notes
    return item


def parse_page(html: str) -> dict | None:
    """Devuelve {'category': …, 'items': [...], 'notes': [...]} o None."""
    soup = BeautifulSoup(html, "html.parser")

    head = soup.find(class_="encabezadoTexto")
    category = norm(head.get_text(" ")) if head else ""

    eventos = soup.find(id="eventos")
    if eventos is None:
        return None

    items: list[dict] = []
    notes: list[str] = []
    current_block: list[Tag] = []
    current_number: str | None = None
    started = False

    def flush() -> None:
        nonlocal current_block, current_number
        if started:
            item = parse_item_block(current_block, current_number)
            if item:
                for n in item.pop("_notes", []):
                    if n not in notes:
                        notes.append(n)
                items.append(item)
        current_block = []

    for child in eventos.children:
        if not isinstance(child, Tag):
            continue
        if "numeroPlato" in (child.get("class") or []):
            flush()
            started = True
            current_number = norm(child.get_text(" "))
            continue
        if started:
            current_block.append(child)
    flush()

    if not category and not items:
        return None
    return {"category": category or "Carta", "items": items, "notes": notes}


def to_category(page: dict) -> dict:
    """Da forma final a una categoría para menu-data.json."""
    cat: dict = {"category": page["category"]}
    en = CATEGORY_EN.get(fold(page["category"]))
    if en:
        cat["category_en"] = en
    cat["items"] = page["items"]
    return cat


def portion_en(label: str) -> str | None:
    return PORTION_EN.get(fold(label))
