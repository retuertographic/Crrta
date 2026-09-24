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
scripts/carta_export.py     lee la carta exportada como página única
scripts/totem_parser.py     entiende el HTML de la carta digital de mdtotem
scripts/build_menu.py       genera menu-data.json a partir de cualquiera de las dos
.github/workflows/update-menu.yml   la tarea diaria que lo ejecuta
```

## Publicar en GitHub Pages

1. En el repositorio, `Settings → Pages`.
2. En *Source*, elige la rama `main` y la carpeta `/ (root)`. Guarda.
3. A los pocos minutos la web estará en
   `https://retuertographicdesign.github.io/crrtn/`.

Para usar un dominio propio, añade un archivo `CNAME` en la raíz con el
dominio (una sola línea, sin `https://`) y apunta el DNS a GitHub Pages.

> Nota: las páginas cargan la cabecera y el pie con `fetch()`, así que hay
> que abrirlas desde un servidor web, no con doble clic sobre el archivo.
> En local: `python3 -m http.server` dentro de esta carpeta.

## La carta

`index.html` lee `menu-data.json` y pinta las pestañas de categorías y la
lista de platos, con su descripción, los alérgenos y uno o varios precios
(media ración / ración entera). El formato es:

```json
{
  "source": "https://mdtotem.com/directorio/lacarretadelcarreton/index.php",
  "scraped_at": "2026-09-24T06:00:00+00:00",
  "notes": ["IGIC INCLUIDO"],
  "categories": [
    {
      "category": "Aperitivos",
      "category_en": "Starters",
      "items": [
        { "group": "Refrescos", "group_en": "Refreshments" },
        {
          "name": "Tostones rellenos",
          "name_en": "Stuffed Tostones",
          "description": "Plátano verde frito, montadito con ropa vieja a la cubana",
          "description_en": "Fried green plantain, slice with Cuban-style old rust",
          "prices": [
            { "label": "½ ración", "label_en": "Half portion", "value": "4,80" },
            { "label": "1 ración", "label_en": "Full portion", "value": "7,00" }
          ],
          "allergens": ["gluten", "huevo"]
        }
      ]
    }
  ]
}
```

- Todo lo que no sea `name` es opcional. Los sufijos `_en` y `_de` son
  traducciones: si faltan, la web enseña el español. Eso es deliberado —
  es mejor el nombre en español que uno en inglés que no corresponde al
  plato.
- Una entrada `{ "group": … }` dentro de `items` es un subtítulo dentro de
  la categoría (Refrescos, Cervezas, Helados…), no un plato.
- `value` es el número sin el símbolo del euro; la web le añade el ` €`.
- `label` se traduce con `label_en` si viene en los datos; si no, con el
  diccionario `portions` de `assets/i18n.js`; si tampoco, se muestra tal
  cual.
- `allergens` usa los nombres de los iconos de la carta digital (`gluten`,
  `huevo`, `leche`, `frutossecos`, `altramuces`, `pescado`…). Los nombres
  que se ven en pantalla están en `assets/i18n.js`, en `allergens`.
- También se admite el formato simple `"price": "4,20"` en vez de `prices`.
- Si `categories` está vacío, la web muestra un aviso invitando a llamar,
  en vez de una sección en blanco.

Se puede mantener a mano perfectamente: es un archivo de texto.

### Cómo se genera

La fuente más completa es **la carta exportada como página única** (el
archivo `carta-…-carta.html`, que lleva toda la carta dentro de un
`const D={…}`: los tres idiomas, los grupos, los alérgenos y un campo
`note` que marca las filas con la traducción o el precio dudosos):

```bash
python scripts/build_menu.py --from-carta-html carta-la-carreta-del-carreton-carta.html
```

`scripts/carta_export.py` respeta ese campo `note`: si una fila viene
marcada, esa traducción **no se publica** y la web cae al español. Al
terminar, el script imprime por stderr la lista de filas marcadas, para
poder arreglarlas en el origen.

La otra fuente es la carta digital de mdtotem, que tiene una página por
categoría, todas con la
misma forma: el título en `.encabezadoTexto`, y dentro de `#eventos` un
`.numeroPlato` por plato, seguido del nombre, la descripción, los
`.preciosTexto` y una tabla con los iconos de alérgenos.
`scripts/totem_parser.py` es quien entiende eso; `scripts/build_menu.py`
lo usa de dos maneras:

```bash
pip install requests beautifulsoup4

# Descargando de mdtotem (así lo hace el workflow diario;
# ojo: sobrescribe la carta con lo que haya en mdtotem):
python scripts/build_menu.py --fetch

# Desde páginas guardadas a mano (botón derecho → guardar, o copiar el HTML):
python scripts/build_menu.py --from-files carta/*.html

# Añadiendo categorías sueltas sin perder las que ya estaban:
python scripts/build_menu.py --from-files carta/postres.html --merge
```

Con `--fetch` parte de `index.php`, sigue los enlaces de esa misma carpeta
y se queda con las páginas que tienen pinta de categoría. El orden de las
pestañas lo fija `CATEGORY_ORDER` en `build_menu.py`.

Si el resultado no llega a los mínimos, **el script falla a propósito** en
vez de publicar una carta vacía o a medias: verás la ❌ en Actions y sabrás
que hay que revisarlo.

### Actualización automática

El workflow `update-menu.yml` ejecuta `build_menu.py --fetch` **cada día a
las 06:00 UTC** y hace commit solo si algo ha cambiado. También puede
lanzarse a mano desde `Actions → Actualizar carta → Run workflow`.

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
- [ ] **Filas marcadas para revisar en la carta de origen** (la web ya las
      enseña en español, así que no hay nada roto publicado, pero conviene
      arreglarlas en mdtotem):
      - Traducción al inglés cruzada o vacía: *Ensalada especial*,
        *¼ pollo* (decía «Chicken nuggets»), *Nuggets de pollo*,
        *Secreto a la brasa*, *Victoria* (decía «Mahou Clásica»).
      - Traducción al alemán cruzada: *Huevos rotos*, *Papas rellenas*,
        *Croquetas de gofio con carne de costilla*, *Tamal cubano*.
      - Precios: *Pata asada* trae «10,00 € / 10,50 €» en un solo campo;
        *Garbanzos* venía marcado en el origen.
- [ ] **Alemán.** Los datos ya traen las traducciones al alemán
      (`name_de`, `description_de`), pero la web solo tiene ES/EN. Añadir
      el tercer idioma es cuestión de traducir los textos de
      `assets/i18n.js` y añadir el botón en `partials/header.html`.
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
