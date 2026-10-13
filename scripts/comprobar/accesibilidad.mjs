/*
 * Pasa axe-core por todas las páginas, en móvil y en escritorio.
 *
 *   python -m http.server 8777     (desde la raíz del repositorio)
 *   node scripts/comprobar/accesibilidad.mjs
 *
 * Mide las dos anchuras porque hay fallos que solo existen en una: el menú
 * de móvil no está en el DOM en escritorio, y el contraste cambia cuando
 * una tarjeta pasa de fondo oscuro a fondo claro al apilarse. Así se coló
 * una vez: treinta y cuatro incumplimientos de contraste que en escritorio
 * no aparecían.
 *
 * Reglas: WCAG 2.0/2.1/2.2 hasta AA, más las de buenas prácticas de axe.
 *
 * Necesita playwright y un Chromium; en este contenedor,
 *   PW_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
 */
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const axe = readFileSync(fileURLToPath(new URL('../../node_modules/axe-core/axe.min.js', import.meta.url)), 'utf8');
const BASE = process.env.BASE || 'http://localhost:8777';
const paginas = ['/', '/catering.html', '/legal.html', '/novedades.html', '/404.html',
                 '/en/', '/en/catering.html', '/en/legal.html', '/en/novedades.html'];
const tamanos = [[390, 844], [1280, 800]];
const reglas = { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] } };

const navegador = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined, args: ['--no-sandbox'] });
let fallos = 0;

for (const ruta of paginas) {
  const malos = [];
  for (const [ancho, alto] of tamanos) {
    const pagina = await navegador.newPage({ viewport: { width: ancho, height: alto } });
    await pagina.goto(BASE + ruta, { waitUntil: 'networkidle' });
    await pagina.addScriptTag({ content: axe });
    const { violations } = await pagina.evaluate(r => axe.run(document, r), reglas);
    for (const v of violations)
      for (const n of v.nodes)
        malos.push(`${ancho}px · [${v.impact}] ${v.id}: ${n.target.join(' ')}`);
    await pagina.close();
  }
  fallos += malos.length;
  if (malos.length) {
    console.log(`\n  ${ruta}`);
    malos.forEach(m => console.log(`    ${m}`));
  } else {
    console.log(`  ${ruta.padEnd(22)} limpia en ${tamanos.length} anchuras`);
  }
}

await navegador.close();
console.log(fallos
  ? `\n${fallos} incumplimientos en ${paginas.length} páginas`
  : `\nningún incumplimiento en ${paginas.length} páginas × ${tamanos.length} anchuras`);
process.exit(fallos ? 1 : 0);
