#!/usr/bin/env python3
"""
Construye menu-data.json a partir de las páginas de la carta digital.

Dos formas de darle las páginas:

  # Desde archivos HTML guardados a mano (copiar/pegar del navegador):
  python scripts/build_menu.py --from-files carta/*.html

  # Descargándolas de mdtotem (así lo hace el workflow diario):
  python scripts/build_menu.py --fetch

Con --fetch parte de index.php, sigue los enlaces de la misma carpeta y se
queda con las páginas que tienen pinta de categoría de la carta.

Si el resultado no llega a los mínimos (MIN_CATEGORIES / MIN_ITEMS) el script
falla en vez de escribir una carta vacía o a medias: preferimos ver la ❌ en
Actions antes que publicar precios equivocados.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from totem_parser import fold, parse_page, to_category

MENU_URL = "https://mdtotem.com/directorio/lacarretadelcarreton/index.php"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "menu-data.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; CarretonMenuBot/1.0; "
    "+https://github.com/retuertographicdesign/crrtn)"
)

# Orden en que queremos las pestañas en la web. Lo que no esté aquí va detrás,
# en el orden en que aparezca.
CATEGORY_ORDER = [
    "fuera de carta",
    "aperitivos",
    "ensaladas",
    "vegetariano",
    "sopas",
    "pollo",
    "res",
    "carne de cochino",
    "pescado y marisco",
    "postres",
]

# Secciones de la carta digital que no son comida.
SKIP_CATEGORIES = {"contacto", "inicio", "horario", "horarios"}

MIN_CATEGORIES = 1
MIN_ITEMS = 5


def sort_key(category_name: str):
    key = fold(category_name)
    return (CATEGORY_ORDER.index(key) if key in CATEGORY_ORDER else len(CATEGORY_ORDER), key)


def fetch_pages() -> list[str]:
    """Descarga index.php y las páginas de categoría enlazadas desde ella."""
    import requests

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    def get(url: str) -> str:
        res = session.get(url, timeout=30)
        res.raise_for_status()
        res.encoding = res.apparent_encoding or res.encoding
        return res.text

    index_html = get(MENU_URL)
    base_dir = MENU_URL.rsplit("/", 1)[0] + "/"

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(index_html, "html.parser")
    seen: set[str] = set()
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        url = urldefrag(urljoin(MENU_URL, a["href"]))[0]
        if not url.startswith(base_dir) or url in seen:
            continue
        if urlparse(url).path.rsplit(".", 1)[-1].lower() not in ("php", "html", "htm", ""):
            continue
        seen.add(url)
        urls.append(url)

    pages = [index_html]
    for url in urls:
        try:
            pages.append(get(url))
        except Exception as exc:  # una categoría caída no debe tumbar el resto
            print(f"AVISO: no se pudo leer {url}: {exc}", file=sys.stderr)
    return pages


def build(pages: list[str]) -> tuple[list[dict], list[str]]:
    categories: list[dict] = []
    notes: list[str] = []
    seen: set[str] = set()

    for html in pages:
        page = parse_page(html)
        if not page or not page["items"]:
            continue
        key = fold(page["category"])
        if key in SKIP_CATEGORIES or key in seen:
            continue
        seen.add(key)
        categories.append(to_category(page))
        for n in page["notes"]:
            if n not in notes:
                notes.append(n)

    categories.sort(key=lambda c: sort_key(c["category"]))
    return categories, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fetch", action="store_true", help="Descarga las páginas de mdtotem.")
    group.add_argument("--from-files", nargs="+", metavar="HTML", help="Lee páginas ya guardadas.")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Conserva las categorías que ya hay en menu-data.json y no vengan en esta pasada.",
    )
    args = parser.parse_args()

    if args.fetch:
        try:
            pages = fetch_pages()
        except Exception as exc:
            print(f"ERROR: no se pudo descargar la carta: {exc}", file=sys.stderr)
            return 1
    else:
        pages = [Path(f).read_text(encoding="utf-8") for f in args.from_files]

    categories, notes = build(pages)

    if args.merge and OUTPUT_PATH.exists():
        try:
            previous = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
        fresh = {fold(c["category"]) for c in categories}
        for cat in previous.get("categories", []):
            if fold(cat.get("category", "")) not in fresh:
                categories.append(cat)
        notes = notes or previous.get("notes", [])
        categories.sort(key=lambda c: sort_key(c["category"]))

    total = sum(len(c["items"]) for c in categories)
    if len(categories) < MIN_CATEGORIES or total < MIN_ITEMS:
        print(
            f"ERROR: la extracción no dio un resultado creíble ({len(categories)} "
            f"categorías, {total} platos; mínimo {MIN_CATEGORIES} y {MIN_ITEMS}).\n"
            "Puede que la carta digital haya cambiado de estructura.",
            file=sys.stderr,
        )
        return 1

    payload = {
        "source": MENU_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
        "categories": categories,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OK: {len(categories)} categorías y {total} platos en {OUTPUT_PATH.name}")
    for cat in categories:
        print(f"  · {cat['category']}: {len(cat['items'])} platos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
