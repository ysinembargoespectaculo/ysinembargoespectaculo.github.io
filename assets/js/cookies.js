/* ── Aviso de cookies + Google Analytics (solo si el usuario acepta) ──
   Lo cargan index.html y legal.html.
   Mientras GA_ID esté vacío no se muestra ningún aviso ni se carga nada. */
(function () {
  var GA_ID = 'G-8QE7S6MWLC'; // ← ID de medición de Google Analytics 4, p. ej. 'G-XXXXXXXXXX'
  var CLAVE = 'ysCookies'; // 'si' | 'no'

  var botones = document.querySelectorAll('[data-cookies-config]');
  if (!GA_ID) return;
  botones.forEach(function (b) { b.hidden = false; });

  function leer() { try { return localStorage.getItem(CLAVE); } catch (e) { return null; } }
  function guardar(v) { try { localStorage.setItem(CLAVE, v); } catch (e) {} }

  var cargado = false;
  function cargarGA() {
    if (cargado) return;
    cargado = true;
    window['ga-disable-' + GA_ID] = false;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', GA_ID, { anonymize_ip: true });
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
  }

  function borrarGA() {
    window['ga-disable-' + GA_ID] = true;
    var host = location.hostname.replace(/^www\./, '');
    document.cookie.split(';').forEach(function (c) {
      var n = c.split('=')[0].trim();
      if (n.indexOf('_ga') !== 0) return;
      ['', '; domain=' + host, '; domain=.' + host].forEach(function (d) {
        document.cookie = n + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/' + d;
      });
    });
  }

  var aviso = null;
  function mostrar() {
    if (aviso) { aviso.hidden = false; return; }
    var st = document.createElement('style');
    st.textContent =
      '.ck{position:fixed;left:1rem;right:1rem;bottom:1rem;z-index:2000;max-width:560px;margin:0 auto;' +
      'background:#0d1420;border:1px solid rgba(255,184,73,.45);padding:1.1rem 1.25rem;color:#fff8e7;' +
      'font-family:Raleway,sans-serif;font-size:.9rem;line-height:1.55;box-shadow:0 10px 40px rgba(0,0,0,.6)}' +
      '.ck a{color:#ffb849}.ck-b{display:flex;gap:.75rem;margin-top:.9rem;flex-wrap:wrap}' +
      '.ck button{flex:1;min-width:120px;padding:.7rem 1rem;font:inherit;font-weight:700;cursor:pointer;' +
      'border:1px solid #ffb849;background:transparent;color:#ffb849}' +
      '.ck button.ck-si{background:#ffb849;color:#0a0806}' +
      '.ck[hidden]{display:none}';
    document.head.appendChild(st);
    aviso = document.createElement('div');
    aviso.className = 'ck';
    aviso.setAttribute('role', 'dialog');
    aviso.setAttribute('aria-label', 'Aviso de cookies');
    aviso.innerHTML =
      '<p>Usamos cookies de Google Analytics solo para saber cuántas visitas tiene la web. ' +
      'No se activan si no las aceptas. <a href="legal.html#cookies">Más información</a></p>' +
      '<div class="ck-b"><button type="button" class="ck-no">Rechazar</button>' +
      '<button type="button" class="ck-si">Aceptar</button></div>';
    document.body.appendChild(aviso);
    aviso.querySelector('.ck-si').addEventListener('click', function () {
      guardar('si'); aviso.hidden = true; cargarGA();
    });
    aviso.querySelector('.ck-no').addEventListener('click', function () {
      guardar('no'); aviso.hidden = true; borrarGA();
    });
  }

  botones.forEach(function (b) { b.addEventListener('click', mostrar); });

  var eleccion = leer();
  if (eleccion === 'si') cargarGA();
  else if (eleccion !== 'no') mostrar();
})();
