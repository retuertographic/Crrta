#!/usr/bin/env python3
"""
Genera menu-data.json a partir de la hoja de cálculo de la carta.

La fuente de verdad es la hoja "Carta La Carreta del Carretón — con
alérgenos" de Google Sheets. En el repositorio vive una copia exportada a
CSV en carta/carta-hoja.csv, para que la carta publicada se pueda
reconstruir sin depender de tener acceso a la hoja.

    python scripts/build_menu.py                      # usa carta/carta-hoja.csv
    python scripts/build_menu.py otra-exportacion.csv

Para actualizar la carta: edita la hoja, expórtala
(Archivo → Descargar → CSV), sustituye carta/carta-hoja.csv y ejecuta el
script. Las columnas deben mantener el orden de la cabecera.

Sobre los alérgenos: la hoja marca "X" cuando el plato lo lleva según su
receta habitual y "?" cuando podría llevarlo. Las dos son estimaciones,
no una analítica, así que el "?" se publica aparte, como "puede contener",
y la web añade el aviso de consultar en sala. No se mezclan.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CSV = REPO / "carta" / "carta-hoja.csv"
OUTPUT_PATH = REPO / "menu-data.json"

# Posición de cada columna en la hoja.
COL_SECTION, COL_GROUP, COL_NUMBER, COL_DISH = 0, 1, 2, 3
COL_FULL, COL_HALF, COL_UNIT, COL_OTHER = 4, 5, 6, 7
COL_IGIC = 8
COL_NOTES = 23

# Columnas 9..22, en el orden de la cabecera, con la clave que usa la web.
ALLERGEN_COLUMNS = [
    "gluten", "crustaceos", "huevo", "pescado", "cacahuetes", "soja", "leche",
    "frutossecos", "apio", "mostaza", "sesamo", "sulfitos", "altramuces", "moluscos",
]
FIRST_ALLERGEN_COL = 9

CATEGORY_EN = {
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
}

GROUP_EN = {
    "helados": "Ice creams",
    "aguas": "Water",
    "refrescos": "Soft drinks",
    "zumos": "Juices",
    "cervezas": "Beers",
    "vinos": "Wines",
    "cocteles": "Cocktails",
    "copas": "Spirits",
    "cafes": "Coffees",
    "infusiones": "Infusions",
}

# Etiquetas de precio: la de la columna fija y las que vienen escritas
# dentro de "Otros formatos".
LABELS_EN = {
    "1 racion": "Full portion",
    "1/2 racion": "Half portion",
    "unidad": "Each",
    "pequena": "Small",
    "grande": "Large",
    "copa": "Glass",
    "1/2 l": "½ litre",
    "1/4 l": "¼ litre",
    "botella": "Bottle",
    "rojo": "Red Label",
    "negro": "Black Label",
}
# En español se muestran así (para no repetir "Etiqueta" en la hoja).
LABELS_ES = {"rojo": "Etiqueta roja", "negro": "Etiqueta negra"}

PRICE_RE = re.compile(r"^(?P<label>.*?)\s*(?P<value>\d{1,3}(?:[.,]\d{1,2})?)\s*€?$")

MIN_ITEMS = 20


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip()


def label_key(label: str) -> str:
    """Clave para los diccionarios de etiquetas. NFD no descompone «½», así
    que las fracciones se escriben a mano antes de comparar."""
    for char, text in (("½", "1/2"), ("¼", "1/4"), ("¾", "3/4")):
        label = (label or "").replace(char, text)
    return fold(label)


def money(raw: str) -> str:
    """'4,2' o '4.20' -> '4,20'. Cadena vacía si no hay número."""
    raw = (raw or "").replace("€", "").strip()
    if not raw:
        return ""
    normalised = raw.replace(",", ".")
    try:
        return f"{float(normalised):.2f}".replace(".", ",")
    except ValueError:
        return raw


def price(label_es: str, value: str) -> dict | None:
    value = money(value)
    if not value:
        return None
    key = label_key(label_es)
    entry: dict = {"value": value}
    if label_es:
        entry["label"] = LABELS_ES.get(key, label_es)
    label_en = LABELS_EN.get(key)
    if label_en and label_en != entry.get("label"):
        entry["label_en"] = label_en
    return entry


def parse_other_formats(raw: str) -> list[dict]:
    """'Pequeña 1,20 € · Grande 1,70 €' -> dos precios, en ese orden."""
    prices = []
    for chunk in re.split(r"[·|;]", raw or ""):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = PRICE_RE.match(chunk)
        if not m:
            continue
        entry = price(m.group("label").strip(), m.group("value"))
        if entry:
            prices.append(entry)
    return prices


def read_rows(path: Path) -> tuple[list[list[str]], list[str]]:
    """Separa las filas de platos de las de la leyenda del final."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        raw = [[(c or "").strip() for c in row] for row in csv.reader(f)]
    rows, legend, in_legend = [], [], False
    for row in raw[1:]:
        if not any(row):
            continue
        first = fold(row[COL_SECTION])
        if first == "leyenda":
            in_legend = True
            continue
        if in_legend:
            legend.append(row[COL_SECTION])
            continue
        if row[COL_DISH] if len(row) > COL_DISH else "":
            rows.append(row)
    return rows, legend


def build(rows: list[list[str]]) -> tuple[list[dict], list[str]]:
    categories: list[dict] = []
    review: list[str] = []
    by_name: dict[str, dict] = {}
    current_group: dict[str, str] = {}

    def cell(row: list[str], i: int) -> str:
        return row[i] if len(row) > i else ""

    for row in rows:
        section = cell(row, COL_SECTION)
        if not section:
            continue
        if section not in by_name:
            cat: dict = {"category": section}
            en = CATEGORY_EN.get(fold(section))
            if en:
                cat["category_en"] = en
            cat["items"] = []
            by_name[section] = cat
            categories.append(cat)
        cat = by_name[section]

        # Subtítulo, solo cuando cambia dentro de la sección.
        group = cell(row, COL_GROUP)
        if group and current_group.get(section) != group:
            current_group[section] = group
            entry = {"group": group}
            en = GROUP_EN.get(fold(group))
            if en:
                entry["group_en"] = en
            cat["items"].append(entry)

        name = cell(row, COL_DISH)
        item: dict = {"name": name}
        number = cell(row, COL_NUMBER)
        if number.isdigit():
            item["number"] = int(number)

        prices = []
        for label, col in (("1 ración", COL_FULL), ("½ ración", COL_HALF), ("Unidad", COL_UNIT)):
            entry = price(label, cell(row, col))
            if entry:
                prices.append(entry)
        prices.extend(parse_other_formats(cell(row, COL_OTHER)))
        if prices:
            item["prices"] = prices
        else:
            review.append(f"{section} · {name}: sin precio en la hoja")

        certain, maybe = [], []
        for offset, key in enumerate(ALLERGEN_COLUMNS):
            mark = cell(row, FIRST_ALLERGEN_COL + offset).upper()
            if mark == "X":
                certain.append(key)
            elif mark == "?":
                maybe.append(key)
        if certain:
            item["allergens"] = certain
        if maybe:
            item["allergens_maybe"] = maybe

        note = cell(row, COL_NOTES)
        if note:
            # Nota interna de la hoja: no se publica, se avisa al terminar.
            review.append(f"{section} · {name}: {note}")

        cat["items"].append(item)

    return categories, review


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not path.exists():
        print(f"ERROR: no existe {path}", file=sys.stderr)
        return 1

    rows, legend = read_rows(path)
    categories, review = build(rows)
    total = sum(len([i for i in c["items"] if "group" not in i]) for c in categories)

    if total < MIN_ITEMS:
        print(
            f"ERROR: solo se han leído {total} platos (mínimo {MIN_ITEMS}). "
            "¿Ha cambiado el orden de las columnas de la hoja?",
            file=sys.stderr,
        )
        return 1

    payload = {
        "source": "Hoja de cálculo «Carta La Carreta del Carretón — con alérgenos»",
        "source_file": str(path.relative_to(REPO)),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "notes": ["IGIC INCLUIDO"],
        "allergen_legend": legend,
        "categories": categories,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OK: {len(categories)} categorías y {total} platos en {OUTPUT_PATH.name}")
    for cat in categories:
        dishes = len([i for i in cat["items"] if "group" not in i])
        groups = len([i for i in cat["items"] if "group" in i])
        extra = f" ({groups} subtítulos)" if groups else ""
        print(f"  · {cat['category']}: {dishes} platos{extra}")
    if review:
        print(f"\nNotas de la hoja, sin publicar ({len(review)}):", file=sys.stderr)
        for line in review:
            print(f"  - {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
