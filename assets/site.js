/* Comportamiento de la web. Los textos ya vienen traducidos desde el
   generador (scripts/build_site.py), así que aquí no hay traducciones ni
   se carga nada por fetch: solo interacción. */

(function () {
  'use strict';

  /* ---- Scroll: cabecera compacta y botón de volver arriba ---- */
  const header = document.getElementById('site-header');
  const toTop = document.getElementById('toTop');
  if (header || toTop) {
    const onScroll = () => {
      if (header) header.classList.toggle('scrolled', window.scrollY > 40);
      if (toTop) toTop.classList.toggle('show', window.scrollY > 500);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
  if (toTop) toTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  /* ---- Menú móvil ---- */
  const burger = document.getElementById('burgerBtn');
  const navLinks = document.getElementById('navLinks');
  if (burger && navLinks) {
    burger.addEventListener('click', () => navLinks.classList.toggle('open'));
    navLinks.querySelectorAll('a').forEach(a =>
      a.addEventListener('click', () => navLinks.classList.remove('open')));
  }

  /* ---- Horario: resalta el día de hoy ---- */
  const hours = document.querySelector('.hours-grid');
  if (hours) {
    // getDay(): 0 = domingo … 6 = sábado. La rejilla empieza en lunes.
    const day = new Date().getDay();
    const row = day === 0 ? 6 : day - 1;
    const cells = hours.children;
    if (cells[row * 2]) cells[row * 2].classList.add('today');
    if (cells[row * 2 + 1]) cells[row * 2 + 1].classList.add('today');
  }

  /* ---- Carta: las categorías ya están en el HTML, solo se alternan ---- */
  const tabs = document.querySelectorAll('.menu-tab');
  const panels = document.querySelectorAll('.menu-panel');
  if (tabs.length && panels.length) {
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-category');
        tabs.forEach(t => {
          const on = t === tab;
          t.classList.toggle('active', on);
          t.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        panels.forEach(p => p.classList.toggle('active', p.getAttribute('data-category') === target));
      });
    });
  }

  /* ---- Galería con lightbox ---- */
  const lightbox = document.getElementById('lightbox');
  if (lightbox) {
    const img = document.getElementById('lightboxImg');
    document.querySelectorAll('#galleryGrid a').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        img.src = a.getAttribute('href');
        img.alt = a.querySelector('img') ? a.querySelector('img').alt : '';
        lightbox.classList.add('open');
      });
    });
    const close = () => lightbox.classList.remove('open');
    const closeBtn = document.getElementById('lightboxClose');
    if (closeBtn) closeBtn.addEventListener('click', close);
    lightbox.addEventListener('click', e => { if (e.target === lightbox) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  }

  /* ---- Compartir. Las etiquetas vienen del HTML, en su idioma. ---- */
  const shareBox = document.getElementById('shareBox');
  if (shareBox) {
    const url = encodeURIComponent(window.location.href);
    const title = encodeURIComponent(document.title);
    shareBox.querySelectorAll('a[data-share]').forEach(a => {
      const targets = {
        whatsapp: `https://wa.me/?text=${title}%20${url}`,
        facebook: `https://www.facebook.com/sharer/sharer.php?u=${url}`,
        x: `https://twitter.com/intent/tweet?url=${url}&text=${title}`,
      };
      const href = targets[a.getAttribute('data-share')];
      if (href) a.setAttribute('href', href);
    });
    const copyBtn = shareBox.querySelector('.share-copy');
    if (copyBtn) {
      copyBtn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(window.location.href);
          copyBtn.classList.add('copied');
          setTimeout(() => copyBtn.classList.remove('copied'), 1800);
        } catch (e) { /* silencioso: sin portapapeles no pasa nada */ }
      });
    }
  }

  /* ---- Cambio de idioma: conserva el ancla ----
     Los identificadores de sección son los mismos en los dos idiomas, así
     que quien está leyendo #privacidad en español sigue ahí al pasar a
     inglés, en vez de volver al principio de la página. */
  if (window.location.hash) {
    document.querySelectorAll('.lang-link').forEach(function (link) {
      link.setAttribute('href', link.getAttribute('href') + window.location.hash);
    });
  }

  /* ---- Año del pie ---- */
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
