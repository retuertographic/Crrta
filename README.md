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
scripts/scrape_menu.py      lee la carta digital y genera menu-data.json
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
lista de platos. El formato es:

```json
{
  "source": "https://mdtotem.com/directorio/lacarretadelcarreton/index.php",
  "scraped_at": "2026-09-21T06:00:00+00:00",
  "categories": [
    {
      "category": "Entrantes",
      "category_en": "Starters",
      "items": [
        { "name": "Croquetas de jamón", "description": "Seis unidades", "price": "6,50" }
      ]
    }
  ]
}
```

- `category_en`, `name_en` y `description` son opcionales.
- `price` es el número sin el símbolo del euro (`"12,50"` o `"12.50"`); la
  web le añade el ` €`.
- Si `categories` está vacío, la web muestra un aviso invitando a llamar,
  en vez de una sección en blanco.

Se puede mantener a mano perfectamente: es un archivo de texto.

### Actualización automática

`scripts/scrape_menu.py` descarga la carta digital de mdtotem y regenera
`menu-data.json`. El workflow `update-menu.yml` lo ejecuta **cada día a las
06:00 UTC** y hace commit solo si algo ha cambiado. También puede lanzarse
a mano desde la pestaña `Actions → Actualizar carta → Run workflow`.

El extractor prueba dos estrategias (contenedores con clases del tipo
`categoria`/`plato`/`precio`, y si eso no cuaja, un recorrido lineal
tratando los encabezados como categorías y las líneas que acaban en precio
como platos). Si ninguna da un resultado creíble, **el script falla a
propósito** en vez de publicar una carta vacía o equivocada: verás la ❌ en
Actions y sabrás que hay que revisarlo.

Para depurar los selectores contra el HTML real:

```bash
pip install requests beautifulsoup4
python scripts/scrape_menu.py --dump-html /tmp/carta.html
```

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
      `assets/i18n.js` llevan `[PENDIENTE: nombre del titular]`,
      `[PENDIENTE: NIF]` y `[PENDIENTE: correo de contacto]`. Son
      obligatorios según el artículo 10 de la LSSICE.
- [ ] **Correo de contacto** en el bloque "Otros contactos" de
      `index.html` (mismo marcador).
- [ ] **La carta.** `menu-data.json` está vacío a la espera de la primera
      sincronización (o de que se rellene a mano).
- [ ] **Redes sociales.** Los enlaces de Facebook, TripAdvisor y Google del
      pie de contacto se tomaron de resultados públicos de búsqueda;
      conviene comprobar que son las fichas correctas del local.
- [ ] **Fotografías.** Ahora mismo hay tres (salón, carne a la brasa y
      postre Teide). Con más fotos la galería gana mucho.

## Datos del local

- Dirección: C. el Carretón, 4-7, 38550 Arafo, Santa Cruz de Tenerife
- Teléfono: 922 51 50 66
- Horario: lunes y martes cerrado · miércoles a viernes 12:00–16:00 ·
  sábados y domingos 12:30–16:00
