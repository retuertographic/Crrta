# La Carreta del Carretón — web del restaurante

Sitio estático generado: las plantillas viven en `src/`, un script escribe
una versión por idioma con su propia URL, y GitHub Pages publica el
resultado desde la raíz. Sin framework ni dependencias de JavaScript.
La estructura sigue la de la web de El Capricho: cabecera y pie
compartidos, y la carta separada del diseño en un JSON.

## Qué contiene

La web **se genera**: se editan las plantillas de `src/` y un script escribe
las páginas de cada idioma. Lo que hay en la raíz es el resultado, y es lo
que publica GitHub Pages.

```
src/pages/                  las plantillas (lo que se edita)
src/partials/header.html    cabecera compartida
src/partials/footer.html    pie + modal de textos legales
src/i18n.json               todos los textos, en español e inglés
src/meta.json               título y descripción de cada página, por idioma
carta/carta-hoja.csv        la hoja de la carta, exportada a CSV
carta/descripciones.json    las descripciones de los platos, en los dos idiomas
scripts/build_menu.py       CSV + descripciones -> menu-data.json
scripts/build_site.py       plantillas + traducciones + carta -> la web
assets/site.css             el diseño
assets/site.js              interacción (pestañas, menú, modal, galería)
assets/consent.js           banner de cookies y carga de la medición
src/analytics.json          IDs de GA4 y Hotjar (vacíos = desactivados)
img/                        logotipo y fotografías

index.html, novedades.html, novedades/, en/, sitemap.xml, robots.txt
                            GENERADOS: no se editan a mano
```

## Cómo se publica

```bash
python scripts/build_menu.py    # solo si ha cambiado la carta
python scripts/build_site.py    # siempre
git add -A && git commit && git push
```

GitHub Pages publica la rama `main` desde la raíz, así que **los archivos
generados van al repositorio**. Si editas una plantilla y olvidas ejecutar
`build_site.py`, el cambio no se publica.

En local: `python3 -m http.server` en la raíz.

## Un idioma por URL

El español vive en la raíz y el inglés en `/en/`:

| | Español | Inglés |
| --- | --- | --- |
| Portada | `/` | `/en/` |
| Catering | `/catering.html` | `/en/catering.html` |
| Novedades | `/novedades.html` | `/en/novedades.html` |
| Una novedad | `/novedades/<slug>.html` | `/en/novedades/<slug>.html` |

Cada página declara su `canonical` y las etiquetas `hreflang` de todas sus
versiones, y el `sitemap.xml` las lista con sus alternativas. El selector
de idioma son **enlaces de verdad**, no un botón de JavaScript.

Esto es a propósito y es la razón de que haya un generador. Con el idioma
resuelto en el navegador, Google solo veía la versión española: el resto
del contenido no existía hasta que alguien pulsaba un botón. Por el mismo
motivo **la carta se escribe entera en el HTML** en lugar de pedirse con
`fetch`: los 88 platos con sus descripciones son justo lo que la gente
busca, y así están en el código fuente de la página.

### Añadir un idioma

1. Añádelo a `LANGUAGES` en `scripts/build_site.py` (código, carpeta,
   etiqueta hreflang y locale de fechas).
2. Traduce `src/i18n.json` y `src/meta.json`.
3. Añade `name_XX` / `description_XX` donde haga falta en
   `carta/descripciones.json`, y los mapas de categorías en
   `scripts/build_menu.py`.
4. Ejecuta el build. Si falta alguna clave, el script avisa por stderr y
   usa el español mientras tanto — no rompe la página.

## Catering (Habana Express)

Página propia, `src/pages/catering.html`, con su entrada en el menú y un
resumen en la portada que enlaza a ella (`.cat-teaser` en `index.html`).

**El formulario de presupuesto no envía nada a ningún servidor**, porque
esta web no tiene backend. Al pulsar «Pedir presupuesto» se compone un
correo con los datos y se abre el programa de correo de quien lo rellena,
con todo escrito. Si no se abre —típico en webmail—, aparece debajo el
texto ya montado y un botón para copiarlo.

Efecto secundario bueno: como los datos nunca pasan por la web, no hay
tratamiento de datos que declarar por esta vía ni casilla de
consentimiento que añadir.

Si algún día quieres que las solicitudes lleguen solas a un buzón o a un
CRM (como el formulario de El Capricho), hace falta un endpoint externo;
dímelo y cambio el envío sin tocar el resto de la página.

El destinatario es `info@lacarretadelcarreton.com`, en el `CATERING_EMAIL`
de `assets/site.js`. La línea «Servicio: buffet» se añade sola al resumen,
porque el formato es siempre el mismo.

## Analíticas y mapas de calor

Están montados pero **apagados**: `src/analytics.json` tiene los IDs
vacíos, así que hoy la web no carga ningún tercero y no aparece ningún
banner. Para encenderlos:

```jsonc
{
  "ga4_id": "G-XXXXXXXXXX",     // Google Analytics 4
  "hotjar_id": "1234567",       // Hotjar Site ID
  "track_contact_clicks": true
}
```

y `python scripts/build_site.py`. Cada herramienta se activa por separado:
deja un campo vacío y esa no se carga. Si los dos están vacíos, el banner
ni se genera.

### Nada se carga antes del consentimiento

`assets/consent.js` no incrusta las etiquetas de Google ni de Hotjar en el
HTML: las **crea al vuelo solo cuando alguien pulsa «Aceptar»**. Mientras
tanto no se descarga nada de esos dominios, que es lo que exige la AEPD —
no basta con cargar el script y no poner la cookie.

- La decisión se guarda en `localStorage` (`carreton_consent`), y hasta que
  se toma, el banner vuelve a salir.
- **Rechazar tiene el mismo peso visual que aceptar**, mismo tamaño y misma
  fila. También es un requisito, no una cuestión de gusto.
- El pie lleva «Preferencias de cookies», que reabre el banner: poder
  cambiar de idea es obligatorio.
- El banner cerrado queda `visibility:hidden`, así que no se queda en el
  tabulador ni lo lee un lector de pantalla.

### La política de cookies se ajusta sola

Los párrafos de la política llevan `data-if="analytics"` y
`data-unless="analytics"`, y el generador publica solo los que
correspondan. Con los IDs vacíos la web dice que no instala cookies de
análisis; al ponerlos, pasa a explicar GA4 y Hotjar y el consentimiento.
Así la política nunca contradice a lo que la web hace de verdad.

### Clics de contacto como conversión

Con `track_contact_clicks` activo, cualquier clic en un `tel:` o un
`mailto:` manda a GA4 un evento `contact_click` con `method`
(teléfono/correo), `link_url` y `page_language`. Como esta web no tiene
formulario de reserva, ese evento **es** la conversión: conviene marcarlo
como tal en GA4 (Administrar → Eventos → marcar como conversión).

### Lo que queda fuera

- Los **textos legales de RGPD** (aviso legal y privacidad) no se han
  tocado para esto; van por otra vía.
- El **enmascarado de texto de Hotjar** se configura en el panel de Hotjar,
  no en el código. Conviene revisarlo antes de grabar sesiones.

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

### Las descripciones

La hoja no tiene columna de descripción, así que viven aparte en
`carta/descripciones.json`, y `build_menu.py` las mezcla al generar la
carta. La clave es el nombre del plato tal como aparece en la hoja (no
distingue mayúsculas ni acentos), y cada entrada lleva `es` y `en`:

```json
"Costillas BBQ": {
  "es": "Plato estrella, tiernas y jugosas costillas…",
  "en": "Our signature dish: tender, juicy ribs…"
}
```

Si una entrada no casa con ningún plato de la hoja, el script lo avisa al
terminar — así un plato que se renombre en la hoja no se queda con la
descripción colgando en silencio. Ahora mismo hay 29 entradas, que cubren
31 platos (*Tostones* y *Yuca con mojo* salen en dos secciones).

El inglés está traducido a mano. La traducción automática que traía la
carta digital anterior tenía errores que en una carta son graves
(«entraña» como *entrails*, «ropa vieja» como *old rust*, «pata asada»
como *pig's foot*), así que no se reutilizó. Los nombres de plato cubanos
y canarios se dejan en español y se explican entre paréntesis.

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

1. Añade una entrada al principio del array `posts` de
   `novedades-data.json` (`slug`, `date` en `AAAA-MM-DD`, `image`, títulos
   y extractos en los dos idiomas).
2. Copia `src/pages/novedades/abrimos-nuestra-web.html` a
   `src/pages/novedades/<slug>.html` y cambia el texto.
3. Añade la página a `PAGES` y sus textos a `src/meta.json`.
4. Ejecuta `build_site.py`.


## Cambiar textos

Todo lo traducible lleva `data-i18n="clave"` en las plantillas, y la clave
vive en `src/i18n.json` con su versión `es` y `en`. El generador sustituye
el contenido del elemento por el texto del idioma que toque, así que lo que
se ve en la plantilla es solo el original en español.


## Pendiente antes de publicar

- [ ] **IDs de medición.** `src/analytics.json` está vacío: GA4 y Hotjar
      no se cargan hasta que se rellene y se vuelva a generar la web.
- [ ] **Datos del titular en los textos legales.** `partials/footer.html` y
      `assets/i18n.js` llevan `[PENDIENTE: nombre del titular]` y
      `[PENDIENTE: NIF]`. Son obligatorios según el artículo 10 de la
      LSSICE.
- [ ] **Notas de la hoja.** Diecisiete filas llevan apuntes pendientes en
      la columna de notas («Receta desconocida: confirmar» en las cinco
      ensaladas, «Confirmar tipo de gofio», «Pata asada: en la carta
      aparecen dos precios»…). No se publican, pero cerrarlas mejoraría
      los alérgenos. `build_menu.py` las lista al ejecutarse.
- [ ] **Descripciones que faltan.** 31 de los 88 platos tienen
      descripción; el resto son bebidas y platos sencillos que tampoco la
      tenían en la carta anterior. Si quieres más, se añaden a
      `carta/descripciones.json`.
- [ ] **Nombres de los platos en inglés.** Las descripciones sí están
      traducidas, pero los nombres se quedan en español (*Tostones
      Rellenos*, *Pata Asada*…). En muchos casos es lo correcto para un
      plato cubano; si se quieren traducir, harían falta campos `name_en`.
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
