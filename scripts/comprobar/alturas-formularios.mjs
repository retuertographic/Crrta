/*
 * Mide cuánto ocupan de verdad los formularios del CRM y lo compara con las
 * alturas fijas de assets/site.css.
 *
 *   node scripts/comprobar/alturas-formularios.mjs
 *
 * Los formularios van en iframe porque el CRM no manda cabeceras CORS, y
 * tampoco comunica su altura: dentro, su página tiene html{overflow:hidden}
 * y un contenedor con overflow:auto, así que en cuanto el contenido pasa de
 * la altura del marco aparece una barra de scroll dentro del formulario.
 * Por eso la altura va fija por tramos de anchura.
 *
 * Y por eso existe esta comprobación: el formulario vive en el CRM y puede
 * crecer sin que nadie toque este repositorio. Pasó: al de contacto le
 * añadieron fecha, hora y número de personas y se quedó con 170px de scroll
 * dentro, sin que fallara nada más.
 *
 * Necesita playwright y un Chromium; en este contenedor,
 *   PW_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
 * y, como la salida va por un proxy con su propio certificado, también
 *   PW_ARGS='--ignore-certificate-errors-spki-list=...'
 */
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const CSS = fileURLToPath(new URL('../../assets/site.css', import.meta.url));
const FORMS = JSON.parse(readFileSync(fileURLToPath(new URL('../../src/forms.json', import.meta.url)), 'utf8'));
const MARGEN = 30;     // holgura mínima que se exige por debajo de la altura fija

/* Anchura real del iframe en cada tramo del CSS. La columna son 760px como
   mucho; en móvil, la anchura de la ventana menos los márgenes del .wrap.
   El tramo se mide en su punto más estrecho, que es donde más crece el
   formulario: las etiquetas largas pasan a más líneas. */
const TRAMOS = [
  { nombre: 'por defecto', consulta: null,            anchoIframe: 572 },
  { nombre: 'max-width:620', consulta: 'max-width:620px', anchoIframe: 382 },
  { nombre: 'max-width:430', consulta: 'max-width:430px', anchoIframe: 312 },
  { nombre: 'max-width:360', consulta: 'max-width:360px', anchoIframe: 272 },
];

const css = readFileSync(CSS, 'utf8');

/** Altura declarada en el CSS para ese formulario y ese tramo. */
function alturaDeclarada(tipo, consulta) {
  const regla = new RegExp(`\\.crm-form--${tipo} iframe\\{height:(\\d+)px;?\\}`, 'g');
  if (!consulta) {           // la primera, la que está fuera de toda media query
    const m = regla.exec(css);
    return m ? Number(m[1]) : null;
  }
  const i = css.indexOf(`@media (${consulta})`);
  if (i < 0) return null;
  const bloque = css.slice(i, css.indexOf('}\n', css.indexOf('{', i) + 1) + 400);
  const m = new RegExp(`\\.crm-form--${tipo} iframe\\{height:(\\d+)px`).exec(bloque);
  return m ? Number(m[1]) : null;
}

const navegador = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined, args: ['--no-sandbox', ...(process.env.PW_ARGS ? process.env.PW_ARGS.split(' ') : [])] });
let fallos = 0;

for (const tipo of ['contacto', 'catering']) {
  for (const [idioma, id] of Object.entries(FORMS[tipo] || {})) {
    if (!id) continue;
    for (const tramo of TRAMOS) {
      const pagina = await navegador.newPage({ viewport: { width: tramo.anchoIframe, height: 2200 } });
      let alto = -1, motivo = '';
      try {
        await pagina.goto(FORMS.base_url + id, { waitUntil: 'networkidle', timeout: 45000 });
        await pagina.waitForTimeout(900);
        // el bloque con alto propio dentro del contenedor que hace scroll
        alto = await pagina.evaluate(() => {
          const caja = document.querySelector('body > div > div > div');
          return caja ? Math.ceil(caja.getBoundingClientRect().height) : -1;
        });
      } catch (e) { motivo = e.message.split('\n')[0]; }
      await pagina.close();

      const declarada = alturaDeclarada(tipo, tramo.consulta);
      const etiqueta = `${tipo} ${idioma} · ${tramo.nombre} (iframe ${tramo.anchoIframe}px)`;
      if (alto < 0 || declarada === null) {
        console.log(`  ${etiqueta.padEnd(52)} NO SE PUDO MEDIR ${motivo || '(¿falta la regla en el CSS?)'}`);
        fallos++;
      } else if (alto + MARGEN > declarada) {
        console.log(`  ${etiqueta.padEnd(52)} contenido ${alto} > alto ${declarada} → SCROLL DENTRO`);
        fallos++;
      } else {
        console.log(`  ${etiqueta.padEnd(52)} contenido ${alto} · alto ${declarada} · holgura ${declarada - alto}`);
      }
    }
  }
}

await navegador.close();
console.log(fallos
  ? `\n${fallos} tramos se quedan cortos: sube esas alturas en assets/site.css`
  : '\ntodos los tramos tienen sitio de sobra: ningún formulario saca scroll');
process.exit(fallos ? 1 : 0);
