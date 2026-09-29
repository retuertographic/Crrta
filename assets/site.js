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

  /* ---- Modal de textos legales ---- */
  const legalModal = document.getElementById('legalModal');
  if (legalModal) {
    const tabs = document.querySelectorAll('.legal-tab');
    const panels = {
      aviso: document.getElementById('legalPanelAviso'),
      privacidad: document.getElementById('legalPanelPrivacidad'),
      cookies: document.getElementById('legalPanelCookies'),
    };
    const open = (which) => {
      legalModal.classList.add('open');
      tabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-legal-panel') === which));
      Object.entries(panels).forEach(([k, el]) => el && el.classList.toggle('active', k === which));
    };
    document.querySelectorAll('[data-legal-tab]').forEach(b =>
      b.addEventListener('click', () => open(b.getAttribute('data-legal-tab'))));
    tabs.forEach(b => b.addEventListener('click', () => open(b.getAttribute('data-legal-panel'))));
    const close = () => legalModal.classList.remove('open');
    const closeBtn = document.getElementById('legalClose');
    if (closeBtn) closeBtn.addEventListener('click', close);
    legalModal.addEventListener('click', e => { if (e.target === legalModal) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
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

  /* ---- Formulario de presupuesto del catering ----
     La web es estática y no tiene a dónde enviar un formulario, así que
     compone un correo con los datos y abre el programa de correo. Nada
     sale de aquí sin que la persona lo envíe ella misma. Si no hay cliente
     de correo (webmail), se enseña el texto para copiarlo. */
  var cateringForm = document.getElementById('cateringForm');
  if (cateringForm) {
    var CATERING_EMAIL = 'info@lacarretadelcarreton.com';
    var fallback = document.getElementById('cateringFallback');
    var summaryBox = document.getElementById('cateringSummary');
    var copyBtn = document.getElementById('cateringCopy');

    function labelFor(field) {
      var label = field.closest('label');
      var span = label && label.querySelector('span');
      return span ? span.textContent.trim() : field.name;
    }

    function buildSummary() {
      var lines = [];
      cateringForm.querySelectorAll('input, textarea').forEach(function (field) {
        var value = field.value.trim();
        if (value) lines.push(labelFor(field) + ': ' + value);
      });
      // El formato de servicio es siempre el mismo; va escrito para que
      // quien lo reciba no tenga que suponerlo.
      lines.push(cateringForm.getAttribute('data-service-line') || 'Buffet');
      return lines.join('\n');
    }

    cateringForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!cateringForm.reportValidity()) return;

      var summary = buildSummary();
      var name = (cateringForm.elements.nombre.value || '').trim();
      var subject = 'Catering Habana Express' + (name ? ' — ' + name : '');

      if (summaryBox) summaryBox.textContent = summary;
      if (fallback) fallback.hidden = false;

      // Un enlace que se pulsa, en vez de reasignar location: es el patrón
      // que mejor aguanta entre navegadores para esquemas externos.
      var link = document.createElement('a');
      link.href = 'mailto:' + CATERING_EMAIL +
        '?subject=' + encodeURIComponent(subject) +
        '&body=' + encodeURIComponent(summary);
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      link.remove();
    });

    if (copyBtn) {
      copyBtn.addEventListener('click', async function () {
        try {
          await navigator.clipboard.writeText(summaryBox ? summaryBox.textContent : '');
          var done = copyBtn.getAttribute('data-copied-label');
          var idle = copyBtn.getAttribute('data-copy-label');
          copyBtn.textContent = done;
          setTimeout(function () { copyBtn.textContent = idle; }, 1800);
        } catch (err) { /* sin portapapeles: el texto ya está a la vista */ }
      });
    }
  }

  /* ---- Año del pie ---- */
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
