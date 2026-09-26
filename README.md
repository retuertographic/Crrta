# La Carreta del Carretón — web del restaurante

Sitio estático (HTML, CSS y un poco de JavaScript, sin framework ni build)
para el restaurante **La Carreta del Carretón**, en Arafo (Tenerife).
Está montado con la misma estructura que la web de El Capricho: páginas
sueltas, cabecera y pie compartidos como *partials*, textos en dos idiomas
y la carta separada del diseño en un JSON que se actualiza solo.

## Qué contiene

```
index.html                  portada: hero, nosotros, especialidades, carta,
                            galería y contacto
novedades.html              listado de novedades
novedades/                  una página por cada novedad publicada
novedades-data.json         el índice de novedades (título, fecha, imagen)
menu-data.json              la carta: categorías, platos y precios
partials/header.html        cabecera compartida por todas las páginas
partials/footer.html        pie + modal de textos legales
assets/site.css             todo el diseño
assets/site-common.js       cabecera/pie, menú móvil, idioma, modal legal
assets/i18n.js              los textos en español e inglés
img/                        logotipo y fotografías
carta/carta-hoja.csv        la hoja de la carta, exportada a CSV (fuente de verdad)
scripts/build_menu.py       convierte ese CSV en menu-data.json
```

## Publicar en GitHub Pages

1. En el repositorio, `Settings → Pages`.
2. En *Source*, elige la rama `main` y la carpeta `/ (root)`. Guarda.
3. A los pocos minutos la web estará en
   `https://retuertographic.github.io/Crrta/`.

Para usar un dominio propio, añade un archivo `CNAME` en la raíz con el
dominio (una sola línea, sin `https://`) y apunta el DNS a GitHub Pages.

> Nota: las páginas cargan la cabecera y el pie con `fetch()`, así que hay
> que abrirlas desde un servidor web, no con doble clic sobre el archivo.
> En local: `python3 -m http.server` dentro de esta carpeta.

## La carta

La fuente de verdad es la hoja de cálculo **«Carta La Carreta del Carretón —
con alérgenos»** de Google Sheets. En el repositorio vive una copia
exportada a CSV en `carta/carta-hoja.csv`, para que la carta publicada se
pueda reconstruir sin depender de tener acceso a la hoja.

### Actualizar la carta

1. Edita la hoja en Google Sheets.
2. `Archivo → Descargar → Valores separados por comas (.csv)`.
3. Sustituye `carta/carta-hoja.csv` por el archivo descargado.
4. `python scripts/build_menu.py` y haz commit de los dos archivos.

El script imprime cuántos platos ha leído por categoría, y al final, por
stderr, las notas de la columna «Notas alérgenos / transcripción» — que
**no se publican** en la web, son apuntes internos («Receta desconocida:
confirmar»). Si lee menos de 20 platos falla a propósito, en vez de
publicar una carta a medias: querrá decir que han cambiado de sitio las
columnas de la hoja.

Las columnas deben mantener este orden: Sección · Subcategoría · Nº ·
Plato · Ración (€) · Media ración (€) · Precio unidad (€) · Otros formatos
/ precios · IGIC · los catorce alérgenos · Notas.

### Alérgenos

La hoja distingue dos cosas y la web también, a propósito:

| En la hoja | En la web |
| --- | --- |
| `X` — lo lleva según la receta habitual | etiqueta con fondo: **Gluten** |
| `?` — podría llevarlo, por confirmar | etiqueta punteada: **Gluten ?** |
| vacío | no aparece |

Mezclarlas daría por seguro algo que no lo es. Bajo la carta va siempre el
aviso de que son estimaciones y de que hay que preguntar en sala. **Ni
siquiera las `X` son una analítica**: la propia hoja las define como
estimación según la receta habitual del plato.

### Formato de menu-data.json

```json
{
  "source": "Hoja de cálculo «Carta La Carreta del Carretón — con alérgenos»",
  "source_file": "carta/carta-hoja.csv",
  "scraped_at": "2026-09-26T14:00:00+00:00",
  "notes": ["IGIC INCLUIDO"],
  "allergen_legend": ["X = contiene el alérgeno (…)", "…"],
  "categories": [
    {
      "category": "Aperitivos",
      "category_en": "Starters",
      "items": [
        { "group": "Helados", "group_en": "Ice creams" },
        {
          "number": 2,
          "name": "Tostones Rellenos",
          "prices": [
            { "label": "1 ración", "label_en": "Full portion", "value": "7,00" },
            { "label": "½ ración", "label_en": "Half portion", "value": "4,80" }
          ],
          "allergens": ["gluten"],
          "allergens_maybe": ["leche"]
        }
      ]
    }
  ]
}
```

- Una entrada `{ "group": … }` dentro de `items` es un subtítulo dentro de
  la categoría (Refrescos, Cervezas, Helados…), no un plato.
- `value` es el número sin el símbolo del euro; la web le añade el ` €`.
- Los sufijos `_en` son traducciones; si faltan, la web enseña el español.
- Los nombres de alérgeno que se ven en pantalla están en
  `assets/i18n.js`, en `allergens`.

El archivo se puede editar a mano si hace falta un arreglo rápido, pero el
siguiente `build_menu.py` lo sobrescribe: los cambios de verdad van en la
hoja.

## Añadir una novedad

1. Añade una entrada al principio del array `posts` de `novedades-data.json`
   (`slug`, `date` en formato `AAAA-MM-DD`, `image`, títulos y extractos).
2. Copia `novedades/abrimos-nuestra-web.html` a `novedades/<slug>.html` y
   cambia el texto. Los textos largos del post viven en el propio archivo,
   en el bloque `I18N.es.postN_*` / `I18N.en.postN_*`.

## Cambiar textos e idiomas

Todo lo traducible lleva `data-i18n="clave"` en el HTML, y la clave vive en
`assets/i18n.js` con su versión `es` y `en`. Si añades texto nuevo, añade la
clave en los dos idiomas. El idioma elegido se guarda en el navegador
(`localStorage`, clave `carreton_lang`).

## Pendiente antes de publicar

- [ ] **Datos del titular en los textos legales.** `partials/footer.html` y
      `assets/i18n.js` llevan `[PENDIENTE: nombre del titular]` y
      `[PENDIENTE: NIF]`. Son obligatorios según el artículo 10 de la
      LSSICE.
- [ ] **Notas de la hoja.** Diecisiete filas llevan apuntes pendientes en
      la columna de notas («Receta desconocida: confirmar» en las cinco
      ensaladas, «Confirmar tipo de gofio», «Pata asada: en la carta
      aparecen dos precios»…). No se publican, pero cerrarlas mejoraría
      los alérgenos. `build_menu.py` las lista al ejecutarse.
- [ ] **Descripciones de los platos.** La hoja no tiene columna de
      descripción, así que la carta va solo con nombre y precio. Si se
      añade una columna, el script puede publicarlas.
- [ ] **Traducciones de los platos.** Por el mismo motivo, en inglés se
      traducen las categorías, los subtítulos y las raciones, pero los
      nombres de los platos se quedan en español.
- [ ] **Redes sociales.** Los enlaces de Facebook, TripAdvisor y Google del
      pie de contacto se tomaron de resultados públicos de búsqueda;
      conviene comprobar que son las fichas correctas del local.
- [ ] **Fotografías.** Ahora mismo hay tres (salón, carne a la brasa y
      postre Teide). Con más fotos la galería gana mucho.

## Datos del local

- Dirección: C. el Carretón, 4-7, 38550 Arafo, Santa Cruz de Tenerife
- Teléfono: 922 51 50 66
- Horario: lunes y martes cerrado · miércoles a viernes 12:30–16:00 ·
  sábados y domingos 12:00–16:00 (solo mediodía)

### Correos

| Para qué | Dirección |
| --- | --- |
| Reservas (ES) | `reservas@lacarretadelcarreton.com` |
| Reservas (EN) | `bookings@lacarretadelcarreton.com` |
| Atención al cliente (ES) | `atencionalcliente@lacarretadelcarreton.com` |
| Atención al cliente (EN) | `customercare@lacarretadelcarreton.com` |
| Información general | `info@lacarretadelcarreton.com` |
| Protección de datos | `protecciondedatos@lacarretadelcarreton.com` |

Los dos primeros pares cambian solos con el idioma que elija el visitante:
la lógica está en `MAILBOXES`, al final de `index.html`, y se aplica a
cualquier elemento con `data-mailbox="bookings"` o `data-mailbox="care"`
(el texto va en el propio enlace, o en el hijo con `data-mailbox-text` si
el enlace lleva más cosas dentro). Los otros dos son iguales en los dos
idiomas. El de protección de datos es además el que aparece en el aviso
legal y en la política de privacidad, y el de información general va en el
JSON-LD.

La tarjeta de reservas presenta el teléfono y el correo como dos opciones
con el mismo peso (`.reserve-ways` en `assets/site.css`), y los botones
«Reservar mesa» de la cabecera, el pie y la galería llevan a la sección de
contacto en vez de abrir el marcador del teléfono.
