/* Banner de cookies y carga de las herramientas de medición.
   Nada de terceros se descarga hasta que la persona acepta: ni Google
   Analytics ni Hotjar existen en la página mientras no haya consentimiento.
   Rechazar es tan fácil como aceptar, que es lo que exige la AEPD. */

(function () {
  'use strict';

  var cfg = window.SITE_ANALYTICS || {};
  var STORAGE_KEY = 'carreton_consent';
  var banner = document.getElementById('cookieBanner');

  function readChoice() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }
  function saveChoice(value) {
    try { localStorage.setItem(STORAGE_KEY, value); } catch (e) { /* modo privado */ }
  }

  function loadGA4(id) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id);
  }

  function loadHotjar(id) {
    window.hj = window.hj || function () { (window.hj.q = window.hj.q || []).push(arguments); };
    window._hjSettings = { hjid: Number(id), hjsv: 6 };
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://static.hotjar.com/c/hotjar-' + window._hjSettings.hjid + '.js?sv=6';
    document.head.appendChild(s);
  }

  /* Clics en el teléfono y en los correos: es la conversión que importa
     en esta web, porque no hay formulario de reserva. */
  function trackContactClicks() {
    document.addEventListener('click', function (e) {
      var link = e.target.closest && e.target.closest('a[href^="tel:"], a[href^="mailto:"]');
      if (!link || typeof window.gtag !== 'function') return;
      var href = link.getAttribute('href');
      window.gtag('event', 'contact_click', {
        method: href.indexOf('tel:') === 0 ? 'telefono' : 'correo',
        link_url: href,
        page_language: document.documentElement.lang || 'es'
      });
    });
  }

  function enableTracking() {
    if (cfg.ga4Id) loadGA4(cfg.ga4Id);
    if (cfg.hotjarId) loadHotjar(cfg.hotjarId);
    if (cfg.trackContactClicks && cfg.ga4Id) trackContactClicks();
  }

  function hideBanner() {
    if (banner) banner.classList.remove('open');
  }
  function showBanner() {
    if (banner) banner.classList.add('open');
  }

  if (banner) {
    var accept = banner.querySelector('[data-consent="accept"]');
    var reject = banner.querySelector('[data-consent="reject"]');
    if (accept) accept.addEventListener('click', function () {
      saveChoice('accepted');
      hideBanner();
      enableTracking();
    });
    if (reject) reject.addEventListener('click', function () {
      saveChoice('rejected');
      hideBanner();
    });
  }

  /* Poder cambiar de idea después es obligatorio: el enlace del pie
     vuelve a abrir el banner. */
  document.querySelectorAll('[data-consent="reopen"]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      showBanner();
    });
  });

  var choice = readChoice();
  if (choice === 'accepted') {
    enableTracking();
  } else if (choice !== 'rejected') {
    showBanner();
  }
})();
