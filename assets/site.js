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
    const setMenu = (open) => {
      navLinks.classList.toggle('open', open);
      // aria-expanded es lo que anuncia al lector de pantalla si el cajón
      // está abierto; sin él, el botón no dice nada de su estado.
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      const label = open ? burger.dataset.labelClose : burger.dataset.labelOpen;
      if (label) burger.setAttribute('aria-label', label);
    };
    burger.addEventListener('click', () => setMenu(!navLinks.classList.contains('open')));
    navLinks.querySelectorAll('a').forEach(a =>
      a.addEventListener('click', () => setMenu(false)));
    // Salir sin tener que acertarle otra vez al botón: con Escape, y
    // tocando fuera del cajón.
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && navLinks.classList.contains('open')) {
        setMenu(false);
        burger.focus();
      }
    });
    document.addEventListener('click', (e) => {
      if (!navLinks.classList.contains('open')) return;
      if (navLinks.contains(e.target) || burger.contains(e.target)) return;
      setMenu(false);
    });
  }

  /* ---- Nuestra historia: plegada en pantallas estrechas ----
     El texto entero está en el HTML y se ve por defecto. Esto lo pliega
     solo cuando la pantalla es estrecha y el texto es largo de verdad, así
     que sin JavaScript no se pierde nada. */
  const story = document.getElementById('historia-texto');
  const storyMore = document.getElementById('storyMore');
  if (story && storyMore) {
    const estrecha = window.matchMedia('(max-width: 900px)');
    const plegar = (si) => {
      story.classList.toggle('is-clamped', si);
      storyMore.setAttribute('aria-expanded', si ? 'false' : 'true');
      storyMore.textContent = si ? storyMore.dataset.labelMore : storyMore.dataset.labelLess;
    };
    const revisar = () => {
      // 900 px de texto son unas dos pantallas y media de móvil: a partir de
      // ahí compensa plegar.
      const largo = story.scrollHeight > 900;
      const aplica = estrecha.matches && largo;
      storyMore.hidden = !aplica;
      plegar(aplica);
    };
    storyMore.addEventListener('click', () => {
      const plegado = story.classList.contains('is-clamped');
      plegar(!plegado);
      if (plegado === false) story.scrollIntoView({ block: 'start', behavior: 'smooth' });
    });
    estrecha.addEventListener('change', revisar);
    revisar();
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
  const tabs = Array.prototype.slice.call(document.querySelectorAll('.menu-tab'));
  const panels = document.querySelectorAll('.menu-panel');
  if (tabs.length && panels.length) {
    // Con role="tab" solo una pestaña entra en el tabulador y las demás se
    // recorren con las flechas (patrón de pestañas de la WAI). Por eso aquí
    // hay que mover también el tabindex: si no, las otras categorías no se
    // alcanzan con el teclado.
    const activar = (tab, mueveFoco) => {
      const target = tab.getAttribute('data-category');
      tabs.forEach(t => {
        const on = t === tab;
        t.classList.toggle('active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.setAttribute('tabindex', on ? '0' : '-1');
      });
      panels.forEach(p => p.classList.toggle('active', p.getAttribute('data-category') === target));
      if (mueveFoco) tab.focus();
    };
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => activar(tab, false));
      tab.addEventListener('keydown', (e) => {
        const salto = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        let destino = null;
        if (salto) destino = tabs[(i + salto + tabs.length) % tabs.length];
        else if (e.key === 'Home') destino = tabs[0];
        else if (e.key === 'End') destino = tabs[tabs.length - 1];
        if (!destino) return;
        e.preventDefault();
        activar(destino, true);
      });
    });
  }

  /* ---- Galería con lightbox (fotos y vídeos) ----
     Sirve a la galería de la casa y a la de fuera de carta. Las piezas
     con data-tipo="video" se abren en el <video> del lightbox. */
  const lightbox = document.getElementById('lightbox');
  if (lightbox) {
    const img = document.getElementById('lightboxImg');
    const vid = document.getElementById('lightboxVideo');
    const closeBtn = document.getElementById('lightboxClose');
    let origen = null;
    const abrir = (a) => {
      origen = a;
      if (a.dataset.tipo === 'video' && vid) {
        img.hidden = true;
        vid.hidden = false;
        vid.poster = a.dataset.poster || '';
        vid.src = a.getAttribute('href');
        vid.play().catch(() => {});
      } else {
        if (vid) { vid.pause(); vid.hidden = true; vid.removeAttribute('src'); }
        img.hidden = false;
        img.src = a.getAttribute('href');
        const i = a.querySelector('img');
        img.alt = i ? i.alt : (a.getAttribute('aria-label') || '');
      }
      lightbox.classList.add('open');
      if (closeBtn) closeBtn.focus();
    };
    document.querySelectorAll('#galleryGrid a, #fdcGaleria a').forEach(a => {
      a.addEventListener('click', e => { e.preventDefault(); abrir(a); });
    });
    const close = () => {
      if (!lightbox.classList.contains('open')) return;
      lightbox.classList.remove('open');
      if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
      if (origen) origen.focus();
    };
    if (closeBtn) closeBtn.addEventListener('click', close);
    lightbox.addEventListener('click', e => { if (e.target === lightbox) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  }

  /* ---- Vídeos de fuera de carta: solo se reproducen mientras se ven.
     preload="none" en el HTML, así que no se descargan hasta llegar. */
  const fdcVideos = document.querySelectorAll('#fdcGaleria video');
  const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (fdcVideos.length && 'IntersectionObserver' in window && !quieto) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (en.isIntersecting) en.target.play().catch(() => {});
        else en.target.pause();
      });
    }, { threshold: 0.4 });
    fdcVideos.forEach(v => io.observe(v));
  }

  /* ---- Aviso emergente de fuera de carta ----
     Sale una vez por visitante y por tanda (la clave guarda la fecha de
     caducidad, así que una tanda nueva vuelve a salir). Pasado el día de
     data-hasta no sale aunque el HTML siga sin regenerar. */
  const aviso = document.getElementById('fdcAviso');
  if (aviso) {
    const hasta = aviso.dataset.hasta;
    const clave = 'carreton_fdc_visto';
    let visto = null;
    try { visto = localStorage.getItem(clave); } catch (e) {}
    // Fin del día en Canarias (UTC+0 en invierno, UTC+1 en verano): se
    // toma UTC+0, que es el más tardío de los dos.
    const caduca = hasta ? new Date(hasta + 'T23:59:59Z') : null;
    const vigente = caduca && Date.now() <= caduca.getTime();
    if (vigente && visto !== hasta && !location.hash) {
      let previo = null;
      const cerrar = (devolver) => {
        aviso.hidden = true;
        document.body.classList.remove('fdc-aviso-abierto');
        try { localStorage.setItem(clave, hasta); } catch (e) {}
        document.removeEventListener('keydown', teclas);
        if (devolver !== false && previo && previo.focus) previo.focus();
      };
      const teclas = (e) => {
        if (e.key === 'Escape') cerrar();
        if (e.key === 'Tab') {
          const f = aviso.querySelectorAll('a, button');
          const primero = f[0], ultimo = f[f.length - 1];
          if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
          else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
        }
      };
      // Si el aviso de cookies está abierto, se espera a que lo cierren:
      // los dos a la vez se tapan y el de cookies va primero.
      const cookiesAbierto = () => {
        const ov = document.getElementById('biscotti-banner-overlay');
        return ov && ov.classList.contains('visible');
      };
      const mostrar = () => {
        if (cookiesAbierto()) { setTimeout(mostrar, 800); return; }
        previo = document.activeElement;
        aviso.hidden = false;
        document.body.classList.add('fdc-aviso-abierto');
        document.addEventListener('keydown', teclas);
        const btn = document.getElementById('fdcAvisoCerrar');
        if (btn) btn.focus();
      };
      setTimeout(mostrar, 2500);
      aviso.addEventListener('click', e => { if (e.target === aviso) cerrar(); });
      const btnCerrar = document.getElementById('fdcAvisoCerrar');
      if (btnCerrar) btnCerrar.addEventListener('click', () => cerrar());
      aviso.querySelectorAll('#fdcAvisoVer, #fdcAvisoReservar')
        .forEach(el => el.addEventListener('click', () => cerrar(false)));
    }
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
