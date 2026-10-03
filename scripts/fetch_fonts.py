#!/usr/bin/env python3
"""
Descarga las fuentes a assets/fonts/ y escribe sus @font-face.

    python scripts/fetch_fonts.py

Están alojadas aquí y no en Google por dos motivos. Uno legal: la petición
a fonts.googleapis.com salía en cuanto se abría la página, antes de que
nadie aceptara nada, y con ella la IP del visitante. Y uno de velocidad:
eran dos conexiones más y una hoja de estilo de terceros bloqueando el
render.

Solo se baja el subconjunto «latin»: cubre el español y el inglés enteros
—tildes, ñ, ¿ ¡, ½— y es lo mismo que servía Google. Los caracteres de
fuera (la flecha →, el icono ☰) caen en la fuente del sistema, igual que
antes.

Las tres familias son SIL Open Font License: alojarlas está permitido.

Si cambian las familias o los pesos, se tocan aquí, se ejecuta esto y se
revisan las precargas de src/partials/head.html.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent
FONTS = REPO / "assets" / "fonts"
CSS = REPO / "assets" / "site.css"

# Con una UA de navegador moderno la API devuelve woff2, y la versión
# variable de Playfair cuando se le pide un rango de pesos.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")
URL = ("https://fonts.googleapis.com/css2"
       "?family=Yellowtail"
       "&family=Playfair+Display:wght@400..900"
       "&family=Poppins:wght@400;500;600;700"
       "&display=swap")

INICIO = "/* === fuentes: lo escribe scripts/fetch_fonts.py, no editar a mano === */"
FIN = "/* === fin de las fuentes === */"

# Fuentes de reserva con las métricas ajustadas. Sin esto, el texto se pinta
# primero con la fuente del sistema y al llegar la definitiva cambia de altura:
# en el titular de la portada eso valía 0,22 de CLS. Con size-adjust y los
# ascent/descent calculados, la reserva ocupa lo mismo y no se mueve nada.
# Liberation Sans y Liberation Serif son métricamente iguales a Arial y a
# Times New Roman, así que sirven para medir.
RESERVAS = {
    "Poppins": ("Arial", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    "Playfair Display": ("Times New Roman", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
    "Yellowtail": ("Times New Roman", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
}

# Medidas por si no están las Liberation en la máquina: son las de Arial y
# Times New Roman, que no cambian.
MEDIDAS_CONOCIDAS = {
    "Arial": {"ancho": 0.4895},
    "Times New Roman": {"ancho": 0.4593},
}


def medidas(ruta: str | Path) -> dict:
    """unitsPerEm, ascenso, descenso y anchura media de las minúsculas."""
    f = TTFont(ruta)
    upm = f["head"].unitsPerEm
    h = f["hhea"]
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    anchos = [hmtx[cmap[ord(c)]][0] for c in "abcdefghijklmnopqrstuvwxyz" if ord(c) in cmap]
    return {"upm": upm, "asc": h.ascent, "desc": h.descent, "gap": h.lineGap,
            "ancho": (sum(anchos) / len(anchos)) / upm}


def reserva(familia: str, archivo: Path) -> str | None:
    """@font-face de la fuente de reserva, ajustada a la de verdad."""
    if familia not in RESERVAS:
        return None
    nombre_local, ruta_local = RESERVAS[familia]
    if Path(ruta_local).exists():
        base = medidas(ruta_local)
    elif nombre_local in MEDIDAS_CONOCIDAS:
        base = MEDIDAS_CONOCIDAS[nombre_local]
    else:
        print(f"  aviso: sin métricas de {nombre_local}, {familia} se queda sin reserva",
              file=sys.stderr)
        return None

    w = medidas(archivo)
    ajuste = w["ancho"] / base["ancho"]
    return (f"@font-face {{\n"
            f"  font-family: '{familia} reserva';\n"
            f"  src: local('{nombre_local}'), local('Liberation {'Serif' if 'Times' in nombre_local else 'Sans'}');\n"
            f"  size-adjust: {ajuste * 100:.2f}%;\n"
            f"  ascent-override: {w['asc'] / w['upm'] / ajuste * 100:.2f}%;\n"
            f"  descent-override: {abs(w['desc']) / w['upm'] / ajuste * 100:.2f}%;\n"
            f"  line-gap-override: {w['gap'] / w['upm'] / ajuste * 100:.2f}%;\n"
            f"}}")


CABECERA = """/* Las fuentes van alojadas aquí, no en Google. Dos motivos: la petición a
   fonts.googleapis.com salía antes de que nadie aceptara nada, y con ella la
   IP del visitante; y eran dos conexiones más y una hoja de estilo de
   terceros bloqueando el render. Solo el subconjunto latin: cubre el español
   y el inglés enteros, tildes, ñ, ¿ ¡ y ½.

   Se regeneran con scripts/fetch_fonts.py. Yellowtail, Playfair Display y
   Poppins son SIL Open Font License: alojarlas está permitido. */
"""


def baja(url: str, destino: Path) -> int:
    subprocess.run(["curl", "-sS", "--fail", "--max-time", "60", "-o", str(destino), url],
                   check=True)
    return destino.stat().st_size


def main() -> int:
    FONTS.mkdir(parents=True, exist_ok=True)
    css = subprocess.run(["curl", "-sS", "--fail", "--max-time", "30", "-A", UA, URL],
                         capture_output=True, text=True, check=True).stdout

    bloques = re.findall(r"/\* (?P<sub>[\w-]+) \*/\s*(?P<face>@font-face \{.*?\})", css, re.S)
    latin = [face for sub, face in bloques if sub == "latin"]
    if not latin:
        print("ERROR: la respuesta de Google Fonts no trae el subconjunto latin",
              file=sys.stderr)
        return 1

    caras, total = [], 0
    reservas_hechas: set[str] = set()
    for face in latin:
        familia = re.search(r"font-family: '([^']+)'", face).group(1)
        peso = re.search(r"font-weight: ([\d ]+);", face).group(1).strip()
        url = re.search(r"url\((https://fonts\.gstatic\.com[^)]+)\)", face).group(1)
        rango = re.search(r"unicode-range: ([^;]+);", face).group(1)
        variable = " " in peso
        nombre = f"{familia.lower().replace(' ', '-')}-{'variable' if variable else peso}.woff2"
        total += baja(url, FONTS / nombre)
        print(f"  · {nombre} ({(FONTS / nombre).stat().st_size / 1024:.1f} KB)")
        if familia not in reservas_hechas:
            r = reserva(familia, FONTS / nombre)
            if r:
                caras.append(r)
                reservas_hechas.add(familia)
        caras.append(
            "@font-face {\n"
            f"  font-family: '{familia}';\n"
            "  font-style: normal;\n"
            f"  font-weight: {peso};\n"
            "  font-display: swap;\n"
            f"  src: url('fonts/{nombre}') format('woff2');\n"
            f"  unicode-range: {rango};\n"
            "}"
        )

    bloque = "\n".join([INICIO, CABECERA.rstrip(), "", "\n".join(caras), FIN])
    texto = CSS.read_text(encoding="utf-8")

    # El bloque va entre marcas: así esto reemplaza solo lo que escribió la
    # vez anterior y no se lleva por delante nada del resto de la hoja.
    desde, hasta = texto.find(INICIO), texto.find(FIN)
    if desde != -1 and hasta != -1:
        texto = texto[:desde] + bloque + texto[hasta + len(FIN):]
    else:
        # Primera vez: después del comentario de cabecera del archivo.
        corte = texto.find("  :root{")
        if corte == -1:
            print("ERROR: no encuentro :root en assets/site.css", file=sys.stderr)
            return 1
        texto = texto[:corte] + bloque + "\n\n" + texto[corte:]
    CSS.write_text(texto, encoding="utf-8")
    print(f"OK: {len(caras)} fuentes, {total / 1024:.1f} KB · @font-face escritos en assets/site.css")
    return 0


if __name__ == "__main__":
    sys.exit(main())
