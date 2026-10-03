# La Carreta del Carretón — web del restaurante

Sitio estático generado: las plantillas viven en `src/`, un script escribe
una versión por idioma con su propia URL, y GitHub Pages publica el
resultado desde la raíz. Sin framework ni dependencias de JavaScript.
La estructura sigue la de la web de El Capricho: nada que salga en más
de una página se escribe dos veces, y la carta va separada del diseño en
un JSON.

## Qué contiene

La web **se genera**: se editan las plantillas de `src/` y un script escribe
las páginas de cada idioma. Lo que hay en la raíz es el resultado, y es lo
que publica GitHub Pages.

```
src/pages/                  las plantillas de cada página (lo que se edita)
src/partials/               los elementos comunes, una sola copia de cada uno
            head.html         el <head>: fuentes, CSS, favicon y el SEO
            header.html       cabecera y menú
            footer.html       pie y enlaces legales
            form.html         plantilla de los formularios del CRM
            form-contacto.html  el formulario de contacto con su titular
            consent-banner.html banner de cookies
            consent-prefs.html  botón de preferencias del pie
            schema.html       ficha del restaurante para Google (NAP)
            scripts.html      el <script> del final
src/i18n.json               todos los textos, en español e inglés
src/meta.json               título y descripción de cada página, por idioma
carta/carta-hoja.csv        la hoja de la carta, exportada a CSV
carta/descripciones.json    las descripciones de los platos, en los dos idiomas
scripts/build_menu.py       CSV + descripciones -> menu-data.json
scripts/build_site.py       plantillas + traducciones + carta -> la web
scripts/fetch_fonts.py      descarga las fuentes y escribe sus @font-face
assets/site.css             el diseño
assets/fonts/               las fuentes, alojadas aquí y no en Google
assets/site.js              interacción (pestañas, menú, galería, compartir)
assets/consent.js           banner de cookies y carga de la medición
src/analytics.json          IDs de GA4 y Hotjar (vacíos = desactivados)
src/forms.json              IDs de los formularios del CRM
img/                        logotipo y fotografías

_config.yml                 lo que GitHub Pages NO publica (src/, scripts/, carta/)

index.html, 404.html, novedades.html, novedades/, en/, sitemap.xml, robots.txt
                            GENERADOS: no se editan a mano
```

`_config.yml` importa: sin él, GitHub Pages publica el repositorio entero y
las plantillas de `src/` quedan accesibles y rastreables, con `{{LANG}}` en
el atributo `lang` y sin canonical. Si alguna vez se renombra una carpeta
de código, hay que añadirla ahí.

La página de error es `404.html` **en la raíz**: GitHub Pages solo usa esa,
también para las rutas bajo `/en/`, así que lleva los dos idiomas. No entra
en el sitemap.

## Elementos comunes (`src/partials/`)

Lo que sale en más de una página vive en un solo archivo. Las plantillas
de `src/pages/` solo ponen el marcador y el generador lo sustituye:

```html
<head>
<!--{{HEAD}}-->
</head>
<body>
<!--{{HEADER}}-->
  ...
<!--{{FOOTER}}-->
<!--{{SCRIPTS}}-->
```

**Cada archivo de `src/partials/` es un marcador**, con el nombre en
mayúsculas y los guiones como subrayados: `consent-banner.html` se inserta
donde ponga `<!--{{CONSENT_BANNER}}-->`. Para añadir un elemento común no
hay que tocar el generador: se deja el archivo ahí y se pone su marcador.

Un partial puede contener el marcador de otro. Así es como `head.html`
trae dentro el bloque de SEO, y el bloque de contacto trae el formulario.

Los marcadores que el generador rellena con datos:

| Marcador | Qué pone |
|---|---|
| `<!--{{SEO}}-->` | title, description, **canonical**, `og:` y `hreflang` |
| `<!--{{CARTA_TABS}}-->`, `<!--{{CARTA_PANELS}}-->`, `<!--{{CARTA_NOTES}}-->` | la carta |
| `<!--{{NOVEDADES}}-->` | las tarjetas de novedades |
| `<!--{{FORM_CATERING}}-->`, `<!--{{FORM_CONTACTO}}-->` | los formularios, con el ID de cada idioma |
| `<!--{{LANG_SWITCH}}-->` | los enlaces entre idiomas |
| `<!--{{ANALYTICS}}-->`, `<!--{{CONSENT_BANNER}}-->`, `<!--{{CONSENT_PREFS}}-->` | medición y consentimiento (vacíos si no hay IDs) |

Si un marcador está mal escrito, el generador avisa por pantalla en vez de
dejar la página sin ese trozo.

### Dos rutas, para dos cosas distintas

| Token | Apunta a | Para qué |
|---|---|---|
| `{{PREFIX}}` | la raíz del sitio | `assets/`, `img/` — no se duplican por idioma |
| `{{HOME}}` | la raíz **de ese idioma** | los enlaces entre páginas |

Importa: desde `/en/legal.html`, `{{HOME}}index.html` lleva a
`/en/index.html` y no a la portada en español. Con un solo token, el menú
y el pie de las páginas en inglés devolvían al visitante al español.

### Comentarios que no se publican

Un comentario que empiece por `<!--#` es una nota para quien edita `src/`
y el generador la quita al publicar. Los comentarios normales (`<!-- -->`)
sí salen en el HTML.

### Textos en atributos

`data-i18n` cambia el contenido de un elemento, pero no sirve para un
`aria-label` o un `title`. Para eso está `data-i18n-attr`:

```html
<button data-i18n-attr="aria-label=aria_menu" aria-label="Abrir menú">
<a data-i18n-attr="aria-label=aria_reviews_g;title=aria_reviews_g" ...>
```

## Accesibilidad

Lo que hay montado y conviene no deshacer sin pensarlo:

- **`<main id="contenido">`** envuelve el cuerpo de cada página, y el primer
  elemento enfocable es un enlace «Saltar al contenido» que apunta ahí. Sin
  él, quien navega con teclado se come los nueve enlaces del menú en cada
  página.
- **Las pestañas de la carta** siguen el patrón de la WAI: solo una entra en
  el tabulador (`tabindex="0"`) y las demás se recorren con las flechas,
  Inicio y Fin. Si tocas `activar()` en `assets/site.js`, el `tabindex`
  tiene que seguir moviéndose con la pestaña activa: si no, las otras
  categorías dejan de alcanzarse con el teclado.
- **La hamburguesa** mantiene `aria-expanded`, cambia su `aria-label` entre
  «Abrir menú» y «Cerrar menú» (los dos textos vienen resueltos desde
  `i18n.json` en `data-label-open` y `data-label-close`), y el cajón se
  cierra con Escape —devolviendo el foco al botón— y tocando fuera.
- **Foco visible** con `:focus-visible`, en dorado claro sobre fondo claro y
  en blanco sobre la cabecera y el pie.
- **Objetivos táctiles** de 44 px en la hamburguesa y el cierre de la
  galería, y de 26 px en los enlaces del pie. Los enlaces que van dentro de
  una línea de texto (teléfono, correos, «Cómo llegar») se quedan como están:
  WCAG 2.5.8 los exceptúa.

Pendiente: el dorado de la marca (`--gold: #A9833F`) no llega a 4,5:1 sobre
los fondos claros. `#826430` sí, con el mismo tono.

## Las fuentes

Están en `assets/fonts/`, no en Google. Dos motivos: la petición a
`fonts.googleapis.com` salía nada más abrir la página —antes de que nadie
aceptara nada, y con ella la IP del visitante—, y eran dos conexiones más y
una hoja de estilo de terceros bloqueando el render.

```bash
python scripts/fetch_fonts.py    # solo si cambian las familias o los pesos
```

Baja el subconjunto `latin` (cubre el español y el inglés enteros: tildes, ñ,
¿ ¡ y ½), escribe los `@font-face` entre marcas al principio de
`assets/site.css` y **calcula las fuentes de reserva**. Esto último importa:
sin ellas el texto se pinta primero con la fuente del sistema y al llegar la
definitiva cambia de altura — en el titular de la portada eso valía 0,22 de
CLS, por encima del umbral de Google. Con `size-adjust` y los
`ascent-override` calculados a partir de las métricas reales, la reserva
ocupa exactamente lo mismo y no se mueve nada.

Si añades una familia o un peso, tócalo en `scripts/fetch_fonts.py`,
ejecútalo, y revisa las precargas de `src/partials/head.html`: ahí van las
tres que se ven sin bajar (Playfair, Yellowtail y Poppins 400).

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
| Información legal | `/legal.html` | `/en/legal.html` |
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

## Textos legales

Están en `/legal.html` (y `/en/legal.html`), en tres secciones con ancla,
para poder enlazar directamente a cada una:

    /legal.html#aviso-legal
    /legal.html#privacidad
    /legal.html#cookies

Antes vivían en un modal del pie, que no se podía enlazar. El pie apunta
ahora a esas anclas, y al cambiar de idioma se conserva el ancla, porque
los identificadores son los mismos en los dos idiomas.

El contenido sigue saliendo de `src/i18n.json` (claves `aviso_*`,
`priv_*`, `cook_*`): se edita ahí, no en la página.

## Formularios del CRM

Los cuatro formularios viven en el CRM y se incrustan en un iframe. Sus
identificadores están en `src/forms.json`; deja uno vacío y esa sección
deja de mostrar formulario.

| Dónde | Español | Inglés |
| --- | --- | --- |
| Presupuesto de catering | `/catering.html` | `/en/catering.html` |
| Contacto | portada, sección de contacto | ídem |

### Por qué iframe y no un formulario propio

El CRM **no manda cabeceras CORS**: un formulario con nuestro marcado que
enviara a `POST /form/<guid>/submit` lo bloquearía el navegador. Se
comprobó con una petición de prueba a un guid inexistente. Si algún día se
habilita CORS en el CRM, se podría montar el formulario con el diseño del
sitio y desaparecería todo lo que viene a continuación.

### Por qué la altura va fija

El CRM tampoco comunica su altura al contenedor (el único `postMessage`
de su bundle es interno de React), y al ser otro dominio la página no
puede medir el iframe. Así que la altura va fija por tramos de ancho, en
`assets/site.css`, bajo `.crm-form`.

Los valores salen de **medir cada formulario en un navegador real** a los
anchos que realmente ocupa. El contenido crece al estrecharse, porque la
etiqueta del consentimiento pasa a más líneas:

| Ancho del iframe | Catering | Contacto |
| --- | --- | --- |
| 760 px | 858 | 558 |
| 512 px | 882 | 558 |
| 382 px | 906 | 582 |
| 272 px | 930 | 630 |
| 252 px | 978 | — |

**Pasarse de alto no se ve** (el formulario tiene fondo transparente);
quedarse corto saca una barra de scroll dentro del marco. Por eso cada
tramo lleva 40-70 px de margen. Comprobado de 280 a 1440 px: la holgura
mínima es de +15 px y no hay scroll interno en ningún ancho.

Si se añade o quita un campo en el CRM, hay que volver a medir. El script
está en el scratchpad de la sesión (`measure.mjs`); en esencia: abrir
`https://crmapi.retuertographicdesign.com/form/<guid>` a cada ancho y leer
la altura de `#root > div > div`.

### Pendiente en el CRM

- La casilla de consentimiento: **Catering ES ya apunta bien**. Los otros
  tres (Catering EN, Contacto ES y Contacto EN) siguen enlazando a la
  política de privacidad de **otra web** (`retuertographic.github.io/rya`).
  Deben apuntar a `https://retuertographic.github.io/Crrta/legal.html#privacidad`
  y, los de inglés, a `.../en/legal.html#privacidad`.
- Los cuatro están **sin captcha**.
- El botón del formulario de contacto sale en azul de Material, mientras
  que el de catering sale dorado: cada formulario tiene su propio CSS en
  el CRM y conviene igualarlos al dorado del sitio (`#A9833F`).

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

- [ ] **Enlace de la casilla de consentimiento en el CRM**, que apunta a
      la política de privacidad de otra web (ver arriba).
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

Los dos primeros pares se resuelven al generar el sitio: `MAILBOXES` en
`scripts/build_site.py` se aplica a cualquier elemento con
`data-mailbox="bookings"` o `data-mailbox="care"` (el texto va en el
propio enlace, o en el hijo con `data-mailbox-text` si el enlace lleva
más cosas dentro). Los otros dos son iguales en los dos
idiomas. El de protección de datos es además el que aparece en el aviso
legal y en la política de privacidad, y el de información general va en el
JSON-LD.

La tarjeta de reservas presenta las cuatro vías con el mismo peso —
teléfono, WhatsApp (+34 661 72 78 26), correo y el formulario del CRM que
está más abajo en la misma página (`.reserve-ways` en `assets/site.css`), y los botones
«Reservar mesa» de la cabecera, el pie y la galería llevan a la sección de
contacto en vez de abrir el marcador del teléfono.
