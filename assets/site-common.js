/* Comportamiento compartido: carga header/footer, scroll, menú móvil,
   modal legal, selector de idioma, horario del día y compartir. */

(async function () {
  const prefix = window.SITE_PREFIX || '';

  async function injectPartial(slotId, file) {
    const slot = document.getElementById(slotId);
    if (!slot) return;
    try {
      const res = await fetch(prefix + file, { cache: 'no-store' });
      let html = await res.text();
      html = html.split('{{PREFIX}}').join(prefix);
      slot.outerHTML = html;
    } catch (err) {
      console.error('No se pudo cargar ' + file, err);
    }
  }

  await injectPartial('site-header-slot', 'partials/header.html');
  await injectPartial('site-footer-slot', 'partials/footer.html');

  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ---- Scroll: header compacto + botón "volver arriba" ---- */
  const siteHeader = document.getElementById('site-header');
  const siteToTop = document.getElementById('toTop');
  if (siteHeader && siteToTop) {
    const onScroll = () => {
      siteHeader.classList.toggle('scrolled', window.scrollY > 40);
      siteToTop.classList.toggle('show', window.scrollY > 500);
    };
    window.addEventListener('scroll', onScroll);
    onScroll();
    siteToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  /* ---- Menú móvil ---- */
  const siteBurger = document.getElementById('burgerBtn');
  const siteNavLinks = document.getElementById('navLinks');
  if (siteBurger && siteNavLinks) {
    siteBurger.addEventListener('click', () => siteNavLinks.classList.toggle('open'));
    siteNavLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => siteNavLinks.classList.remove('open')));
  }

  /* ---- Modal legal ---- */
  const siteLegalModal = document.getElementById('legalModal');
  if (siteLegalModal) {
    const legalTabs = document.querySelectorAll('.legal-tab');
    const legalPanels = {
      aviso: document.getElementById('legalPanelAviso'),
      privacidad: document.getElementById('legalPanelPrivacidad'),
      cookies: document.getElementById('legalPanelCookies'),
    };
    function openLegal(tab) {
      siteLegalModal.classList.add('open');
      legalTabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-legal-panel') === tab));
      Object.entries(legalPanels).forEach(([key, el]) => el && el.classList.toggle('active', key === tab));
    }
    document.querySelectorAll('[data-legal-tab]').forEach(btn => {
      btn.addEventListener('click', () => openLegal(btn.getAttribute('data-legal-tab')));
    });
    legalTabs.forEach(btn => {
      btn.addEventListener('click', () => openLegal(btn.getAttribute('data-legal-panel')));
    });
    document.getElementById('legalClose').addEventListener('click', () => siteLegalModal.classList.remove('open'));
    siteLegalModal.addEventListener('click', (e) => { if (e.target === siteLegalModal) siteLegalModal.classList.remove('open'); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') siteLegalModal.classList.remove('open'); });
  }

  /* ---- Horario: resalta el día de hoy ---- */
  const hoursGrid = document.querySelector('.hours-grid');
  if (hoursGrid) {
    // getDay(): 0 = domingo … 6 = sábado. La rejilla empieza en lunes.
    const jsDay = new Date().getDay();
    const rowIndex = jsDay === 0 ? 6 : jsDay - 1;
    const cells = hoursGrid.children;
    if (cells[rowIndex * 2]) cells[rowIndex * 2].classList.add('today');
    if (cells[rowIndex * 2 + 1]) cells[rowIndex * 2 + 1].classList.add('today');
  }

  /* ---- Selector de idioma (usa window.I18N, de assets/i18n.js) ---- */
  const FLAGS = { es: '🇪🇸', en: '🇬🇧' };
  let currentLang = localStorage.getItem('carreton_lang') || 'es';

  function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('carreton_lang', lang);
    document.documentElement.lang = lang;
    const langFlag = document.getElementById('langFlag');
    const langCode = document.getElementById('langCode');
    if (langFlag) langFlag.textContent = FLAGS[lang];
    if (langCode) langCode.textContent = lang.toUpperCase();
    document.querySelectorAll('[data-lang]').forEach(b => b.classList.toggle('active', b.getAttribute('data-lang') === lang));
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (window.I18N && I18N[lang] && I18N[lang][key] !== undefined) el.innerHTML = I18N[lang][key];
    });
    if (typeof window.onLanguageChange === 'function') window.onLanguageChange(lang);
  }
  window.applyTranslations = setLanguage;
  window.getCurrentLang = () => currentLang;

  const siteLangSwitch = document.getElementById('langSwitch');
  const siteLangBtn = document.getElementById('langBtn');
  if (siteLangSwitch && siteLangBtn) {
    siteLangBtn.addEventListener('click', (e) => { e.stopPropagation(); siteLangSwitch.classList.toggle('open'); });
    document.querySelectorAll('[data-lang]').forEach(b => {
      b.addEventListener('click', () => { setLanguage(b.getAttribute('data-lang')); siteLangSwitch.classList.remove('open'); });
    });
    document.addEventListener('click', () => siteLangSwitch.classList.remove('open'));
  }

  /* ---- Compartir (WhatsApp, Facebook, X, copiar enlace) ---- */
  window.CarretonShare = {
    render(containerId, url, title) {
      const el = document.getElementById(containerId);
      if (!el) return;
      const u = encodeURIComponent(url);
      const t = encodeURIComponent(title);
      const icons = {
        whatsapp: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.5 2 2 6.5 2 12c0 1.8.5 3.5 1.4 5L2 22l5.2-1.4c1.4.8 3.1 1.2 4.8 1.2 5.5 0 10-4.5 10-10S17.5 2 12 2zm0 18.2c-1.6 0-3.1-.4-4.4-1.2l-.3-.2-3.1.8.8-3-.2-.3C4 14 3.5 13 3.5 12c0-4.7 3.8-8.5 8.5-8.5s8.5 3.8 8.5 8.5-3.8 8.5-8.5 8.5z"/><path d="M17.1 14.4c-.3-.1-1.6-.8-1.9-.9-.2-.1-.4-.1-.6.1-.2.3-.7.9-.9 1.1-.2.2-.3.2-.6.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.6-2.1-.2-.3 0-.5.1-.6.1-.1.3-.4.4-.5.1-.2.2-.3.2-.5.1-.2 0-.4 0-.5-.1-.1-.6-1.5-.9-2.1-.2-.5-.5-.5-.6-.5h-.6c-.2 0-.5.1-.7.4-.3.3-1 1-1 2.4s1 2.8 1.2 3c.1.2 2.1 3.3 5.2 4.6.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.6-.7 1.9-1.3.2-.6.2-1.2.2-1.3-.1-.1-.3-.2-.6-.4z"/></svg>',
        facebook: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 13.5h2.5l1-4H14v-2c0-1.03 0-2 2-2h1.5V2.14c-.326-.043-1.557-.14-2.857-.14C11.928 2 10 3.657 10 6.7v2.8H7v4h3V22h4v-8.5z"/></svg>',
        x: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 2H22l-7.6 8.7L23.3 22h-6.9l-5.4-6.9L4.8 22H1.7l8.1-9.3L1 2h7l4.9 6.3L18.9 2zm-1.2 18h1.9L7.4 4H5.4l12.3 16z"/></svg>',
        link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.5-1.5"/></svg>',
      };
      const links = [
        { href: `https://wa.me/?text=${t}%20${u}`, label: 'WhatsApp', icon: icons.whatsapp },
        { href: `https://www.facebook.com/sharer/sharer.php?u=${u}`, label: 'Facebook', icon: icons.facebook },
        { href: `https://twitter.com/intent/tweet?url=${u}&text=${t}`, label: 'X', icon: icons.x },
      ];
      el.innerHTML = links.map(l =>
        `<a href="${l.href}" target="_blank" rel="noopener noreferrer" aria-label="${l.label}">${l.icon}</a>`
      ).join('') + `<button type="button" class="share-copy" aria-label="Copiar enlace">${icons.link}</button>`;

      const copyBtn = el.querySelector('.share-copy');
      copyBtn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(url);
          copyBtn.classList.add('copied');
          setTimeout(() => copyBtn.classList.remove('copied'), 1800);
        } catch (e) { /* silencioso */ }
      });
    }
  };

  setLanguage(currentLang);
})();
