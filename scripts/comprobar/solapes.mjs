/*
 * Busca texto que se pisa con otro texto, en varias páginas y anchuras.
 *
 *   python -m http.server 8777     (desde la raíz del repositorio)
 *   node scripts/comprobar/solapes.mjs
 *
 * Existe porque en la portada se colaron las etiquetas del hero debajo del
 * indicador de scroll, que va posicionado absoluto, y no lo vio nadie hasta
 * que apareció en un móvil de verdad. El validador de HTML y axe no
 * detectan esto: hay que medir las cajas.
 *
 * Dos cosas lo hacen fiable, y las dos costaron una pasada de falsos
 * positivos: descartar lo que recorta un ancestro con overflow:hidden (la
 * historia plegada daba doce), y medir renglón a renglón con
 * getClientRects, porque a un elemento en línea partido en dos
 * getBoundingClientRect le devuelve la caja que envuelve los dos renglones.
 *
 * Necesita playwright y un Chromium; en este contenedor,
 *   PW_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
 */
import { chromium } from 'playwright';

/* Busca texto que se pisa con otro texto. Lo que lo hace fiable es
   descartar lo que no se ve de verdad: elementos ocultos por un ancestro
   (checkVisibility) y, sobre todo, lo que queda recortado por un ancestro
   con overflow:hidden — getBoundingClientRect devuelve la posición sin
   recortar, y eso daba una docena de falsos positivos en la historia
   plegada. */
const detector = () => {
  const visible = (e) =>
    e.checkVisibility
      ? e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })
      : !!e.offsetParent;

  /* Un elemento en línea que parte en varios renglones devuelve en
     getBoundingClientRect la caja que los envuelve a todos, que incluye
     hueco vacío donde sí puede haber otro texto. Hay que mirar renglón a
     renglón. */
  const recortar = (r, e) => {
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.overflow === 'visible' && cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
      const c = p.getBoundingClientRect();
      const top = Math.max(r.top, c.top), left = Math.max(r.left, c.left);
      const bottom = Math.min(r.bottom, c.bottom), right = Math.min(r.right, c.right);
      if (bottom <= top || right <= left) return null;
      r = { top, left, bottom, right, width: right - left, height: bottom - top };
    }
    return r;
  };
  const rectosDe = (e) => [...e.getClientRects()].map(r => recortar(r, e)).filter(Boolean);
  const rectoRecortadoViejo = (e) => {
    let r = e.getBoundingClientRect();
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.overflow === 'visible' && cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
      const c = p.getBoundingClientRect();
      const top = Math.max(r.top, c.top), left = Math.max(r.left, c.left);
      const bottom = Math.min(r.bottom, c.bottom), right = Math.min(r.right, c.right);
      if (bottom <= top || right <= left) return null;
      r = { top, left, bottom, right, width: right - left, height: bottom - top };
    }
    return r;
  };

  const hojas = [...document.querySelectorAll('body *')].filter(e => {
    if (!e.textContent.trim()) return false;
    if ([...e.children].some(c => c.textContent.trim())) return false;
    return visible(e);
  });
  const cajas = [];
  for (const e of hojas)
    for (const r of rectosDe(e))
      if (r.width > 2 && r.height > 2) cajas.push({ e, r });
  const nom = (n) => n.tagName.toLowerCase() +
    (typeof n.className === 'string' && n.className ? '.' + n.className.split(' ')[0] : '');
  const out = new Set();
  for (let i = 0; i < cajas.length; i++)
    for (let j = i + 1; j < cajas.length; j++) {
      const a = cajas[i], b = cajas[j];
      if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
      const x = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const y = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (x > 4 && y > 4)
        out.add(`${nom(a.e)} «${a.e.textContent.trim().slice(0,20)}» × ${nom(b.e)} «${b.e.textContent.trim().slice(0,20)}» (${Math.round(x)}×${Math.round(y)}px)`);
    }
  return [...out];
};

const BASE = process.env.BASE || 'http://localhost:8777';
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined, args: ['--no-sandbox'] });
const paginas = ['/', '/en/', '/catering.html', '/legal.html', '/novedades.html', '/404.html'];
const tamanos = [[320,650],[360,740],[390,844],[412,915],[430,932],[600,900],[768,1024],[1024,768],[1280,800],[1440,900]];
let fallos = 0;
for (const p of paginas) {
  const linea = [];
  for (const [w, h] of tamanos) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    await page.goto(BASE + p, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(250);
    const r = await page.evaluate(detector);
    if (r.length) { fallos += r.length; linea.push(`${w}px: ${r.join(' | ')}`); }
    await ctx.close();
  }
  console.log(`  ${p.padEnd(18)} ${linea.length ? 'SOLAPES\n      ' + linea.join('\n      ') : 'limpio en las 10 anchuras'}`);
}
console.log(fallos ? `\n${fallos} solapes` : '\nningún solape de texto en 6 páginas × 10 anchuras');
process.exitCode = fallos ? 1 : 0;
await browser.close();
