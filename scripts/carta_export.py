#!/usr/bin/env python3
"""
Lee la carta exportada como página única ("carta-…-carta.html").

Ese archivo lleva toda la carta dentro de un `const D={…}` en JavaScript,
en tres idiomas (español, inglés y alemán), con grupos dentro de algunas
categorías, alérgenos, precios con etiqueta y un campo `note` que marca las
filas cuya traducción hay que revisar.

Ese `note` es justo lo que nos interesa: no publicamos una traducción que
la propia exportación marca como dudosa. Si la fila lleva `note` "en" (o
"sintrad"), se descarta el inglés y la web enseña el español; igual con el
alemán y `note` "de". Mejor un nombre en español que un nombre en inglés
que no corresponde al plato.
"""

from __future__ import annotations

import json
import re

# Cómo se muestra cada etiqueta de precio en español y en inglés.
PRICE_LABELS = {
    "½ ración": ("½ ración", "Half portion"),
    "1 ración": ("1 ración", "Full portion"),
    "Precio unidad": ("Unidad", "Each"),
    "Grande": ("Grande", "Large"),
    "Pequeña": ("Pequeña", "Small"),
    "Copa": ("Copa", "Glass"),
    "¼ litro": ("¼ litro", "¼ litre"),
    "½ litro": ("½ litro", "½ litre"),
    "Botella": ("Botella", "Bottle"),
    "Negro": ("Etiqueta negra", "Black Label"),
    "Rojo": ("Etiqueta roja", "Red Label"),
}

# `note` que invalida la traducción de ese idioma.
BAD_EN = {"en", "sintrad"}
BAD_DE = {"de", "sintrad"}

# `note` que avisa de algo raro en el precio; no cambia lo que publicamos,
# pero lo listamos al final para que alguien lo mire.
PRICE_FLAG = "precio"

DATA_RE = re.compile(r"\bconst\s+D\s*=\s*(\{.*?\})\s*;", re.S)
PRICE_RE = re.compile(r"^(?P<value>[\d.,\s/]+?)\s*€?$")


def clean_price(raw: str) -> str:
    """'4,20 €' -> '4,20'. '10,00 € / 10,50 €' -> '10,00 / 10,50'."""
    value = raw.replace("€", " ").strip()
    return re.sub(r"\s+", " ", value).strip(" /") if "/" in value else value.strip()


def extract_data(html: str) -> dict:
    m = DATA_RE.search(html)
    if not m:
        raise ValueError("no se encontró el bloque `const D={…}` en el archivo")
    return json.loads(m.group(1))


def convert(html: str) -> tuple[list[dict], list[str]]:
    """Devuelve (categorías en formato menu-data.json, avisos para revisar)."""
    data = extract_data(html)
    categories: list[dict] = []
    review: list[str] = []

    for cat in data.get("cats", []):
        titles = cat.get("t") or []
        name_es = titles[0] if titles else cat.get("id", "Carta")
        name_en = titles[1] if len(titles) > 1 else ""

        out_cat: dict = {"category": name_es}
        if name_en and name_en != name_es:
            out_cat["category_en"] = name_en
        items: list[dict] = []

        for raw in cat.get("items", []):
            group = raw.get("group")
            if group:
                entry = {"group": group.get("es", "")}
                if group.get("en") and group["en"] != group["es"]:
                    entry["group_en"] = group["en"]
                items.append(entry)
                continue

            es = raw.get("es") or ["", ""]
            en = raw.get("en") or ["", ""]
            de = raw.get("de") or ["", ""]
            note = raw.get("note")

            name = (es[0] or "").strip()
            if not name:
                continue
            item: dict = {"name": name}

            desc = (es[1] or "").strip() if len(es) > 1 else ""
            if desc:
                item["description"] = desc

            # Traducciones, solo si la exportación no las marca como dudosas.
            if note not in BAD_EN:
                if en[0] and en[0].strip() != name:
                    item["name_en"] = en[0].strip()
                if len(en) > 1 and en[1] and en[1].strip() != desc:
                    item["description_en"] = en[1].strip()
            elif note in BAD_EN:
                review.append(f"{name_es} · {name}: traducción al inglés marcada para revisar")

            if note not in BAD_DE:
                if de[0] and de[0].strip() != name:
                    item["name_de"] = de[0].strip()
                if len(de) > 1 and de[1] and de[1].strip() != desc:
                    item["description_de"] = de[1].strip()
            elif note == "de":
                review.append(f"{name_es} · {name}: traducción al alemán marcada para revisar")

            prices = []
            for label, raw_value in raw.get("p", []):
                value = clean_price(raw_value)
                if not value:
                    continue
                price: dict = {"value": value}
                label_es, label_en = PRICE_LABELS.get(label, (label, label))
                if label_es:
                    price["label"] = label_es
                if label_en and label_en != label_es:
                    price["label_en"] = label_en
                prices.append(price)
                if "/" in value:
                    review.append(f"{name_es} · {name}: dos precios en el mismo campo ({raw_value})")
            if prices:
                item["prices"] = prices

            allergens = [a for a in raw.get("al", []) if a]
            if allergens:
                item["allergens"] = sorted(set(allergens))

            if note == PRICE_FLAG:
                review.append(f"{name_es} · {name}: precio marcado para revisar en el origen")

            items.append(item)

        if items:
            out_cat["items"] = items
            categories.append(out_cat)

    # Sin duplicados y conservando el orden.
    seen: set[str] = set()
    unique_review = [r for r in review if not (r in seen or seen.add(r))]
    return categories, unique_review
