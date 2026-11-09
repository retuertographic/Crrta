#!/usr/bin/env python3
"""Genera las imágenes de compartir (img/share/) a partir de las fotos del sitio.

Por qué existe este archivo y no lo hace build_site.py:

1. Las fotos del sitio son WebP. WhatsApp no sabe enseñar WebP en la vista
   previa de un enlace, y el rastreador de Facebook tampoco. Hasta ahora
   compartir una novedad salía sin foto por eso. Las de aquí son JPEG.

2. Las vistas previas se dibujan en 1,91:1. Con una foto cuadrada o vertical
   el recorte lo hace cada red por su cuenta y suele cortar mal, así que se
   recorta aquí, centrado, a 1200x630, que es la medida que piden todas.

3. build_site.py no depende de ninguna biblioteca externa, y eso hay que
   mantenerlo: lo ejecuta el workflow diario sin instalar nada. Esto sí
   necesita Pillow, así que va aparte y se ejecuta a mano cuando entra una
   foto nueva. build_site.py avisa si falta alguna.

Uso:  python3 scripts/build_share.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Hace falta Pillow:  pip install pillow", file=sys.stderr)
    raise SystemExit(1)

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
SALIDA = REPO / "img" / "share"

ANCHO, ALTO = 1200, 630          # 1,91:1, lo que piden WhatsApp, Facebook y X
CALIDAD = 82
LOGO = REPO / "img" / "logo-square.jpg"


def recorta(im: Image.Image) -> Image.Image:
    """Recorta al centro hasta 1200x630 sin deformar."""
    objetivo = ANCHO / ALTO
    actual = im.width / im.height
    if actual > objetivo:                      # sobra a los lados
        nuevo = round(im.height * objetivo)
        izq = (im.width - nuevo) // 2
        im = im.crop((izq, 0, izq + nuevo, im.height))
    else:                                      # sobra arriba y abajo
        nuevo = round(im.width / objetivo)
        arriba = (im.height - nuevo) // 2
        im = im.crop((0, arriba, im.width, arriba + nuevo))
    return im.resize((ANCHO, ALTO), Image.LANCZOS)


def guarda(im: Image.Image, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(destino, "JPEG", quality=CALIDAD,
                           optimize=True, progressive=True)


# Fotos que no declara ninguna página pero que sí se enlazan desde los datos
# estructurados. Sin esto, la limpieza del final se las llevaría.
EXTRAS = {"img/guachin-baile.webp"}   # las fichas Event de Guachin Salsa


def fuentes() -> set[str]:
    """Todas las fotos que alguna página declara como suya."""
    usadas: set[str] = set(EXTRAS)
    meta = json.loads((SRC / "meta.json").read_text(encoding="utf-8"))
    for pagina in meta.values():
        for idioma in pagina.values():
            if idioma.get("image"):
                usadas.add(idioma["image"])
    posts = json.loads((REPO / "novedades-data.json").read_text(encoding="utf-8"))
    for post in posts.get("posts", []):
        if post.get("image"):
            usadas.add(post["image"])
    return usadas


def main() -> int:
    hechas = []

    # La de reserva: el logotipo sobre blanco, que es el fondo sobre el que
    # está dibujado. Se usa en las páginas que no declaran foto propia.
    logo = Image.open(LOGO).convert("RGB")
    lienzo = Image.new("RGB", (ANCHO, ALTO), "white")
    lado = round(ALTO * 0.92)
    pequeno = logo.resize((round(lado * logo.width / logo.height), lado), Image.LANCZOS)
    lienzo.paste(pequeno, ((ANCHO - pequeno.width) // 2, (ALTO - pequeno.height) // 2))
    guarda(lienzo, SALIDA / "default.jpg")
    hechas.append("default.jpg")

    for rel in sorted(fuentes()):
        origen = REPO / rel
        if not origen.exists():
            print(f"  AVISO: no existe {rel}", file=sys.stderr)
            continue
        destino = SALIDA / (Path(rel).stem + ".jpg")
        guarda(recorta(Image.open(origen)), destino)
        hechas.append(destino.name)

    # Lo que sobra de fotos retiradas: se borra, que si no se queda ahí.
    validos = set(hechas)
    for f in sorted(SALIDA.glob("*.jpg")):
        if f.name not in validos:
            f.unlink()
            print(f"  retirada: img/share/{f.name}")

    total = sum((SALIDA / n).stat().st_size for n in hechas)
    print(f"OK: {len(hechas)} imágenes de compartir en img/share/ "
          f"({ANCHO}x{ALTO}, {total // 1024} KB en total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
