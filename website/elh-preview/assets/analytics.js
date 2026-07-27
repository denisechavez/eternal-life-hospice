/* Eternal Life Hospice — Cookie Consent + Analytics loader
   (GA4 + Microsoft Clarity + Brevo)
   Analytics load only after explicit visitor consent.
   Consent stored in localStorage: elh_cc = "all" | "essential"      */
(function () {
  'use strict';

  var KEY = 'elh_cc';
  var consent = null;
  try { consent = localStorage.getItem(KEY); } catch (e) {}

  /* ── Analytics init (runs after window load to protect LCP) ─────────── */
  function loadAnalytics() {
    if (document.readyState === 'complete') { bootAnalytics(); }
    else { window.addEventListener('load', bootAnalytics); }
  }

  function bootAnalytics() {
    // GA4
    var GA = 'G-JRLYCRC48G';
    var s = document.createElement('script');
    s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date()); gtag('config', GA);

    // Microsoft Clarity
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', 'xddyi1rk95');

    // Brevo visitor tracker
    window.Brevo = window.Brevo || [];
    Brevo.push(['init', { client_key: 'kejxjl4hntbbl2jnfp84s6bs' }]);
    var b = document.createElement('script');
    b.async = true; b.src = 'https://cdn.brevo.com/js/sdk-loader.js';
    document.head.appendChild(b);
  }

  /* ── Save preference + act on it ───────────────────────────────────── */
  function saveConsent(level) {
    try { localStorage.setItem(KEY, level); } catch (e) {}
    var bar = document.getElementById('elh-cc');
    var mod = document.getElementById('elh-cc-modal');
    if (bar) { bar.classList.remove('elh-cc-in'); setTimeout(function () { bar.remove(); }, 380); }
    if (mod) { mod.remove(); }
    if (level === 'all') { loadAnalytics(); }
  }

  /* ── Banner + modal (injected entirely via JS) ──────────────────────── */
  function showBanner() {
    /* --- CSS ------------------------------------------------------------ */
    var css = document.createElement('style');
    css.textContent =
      /* Banner — small floating card, bottom-left */
      '#elh-cc{position:fixed;bottom:1.4rem;left:1.4rem;z-index:99999;' +
      'background:#fff;border:1px solid #e8e3dc;border-radius:12px;' +
      'box-shadow:0 4px 24px rgba(0,0,0,.13);max-width:300px;width:calc(100vw - 2.8rem);' +
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
      'font-size:13px;line-height:1.5;' +
      'opacity:0;transform:translateY(10px);transition:opacity .3s ease,transform .3s ease}' +
      '#elh-cc.elh-cc-in{opacity:1;transform:translateY(0)}' +
      '#elh-cc-in{padding:1rem 1.1rem}' +
      '#elh-cc p{margin:0 0 .75rem;font-size:13px;color:#444;line-height:1.55}' +
      '#elh-cc a{color:#7c5cbf;text-underline-offset:2px}' +
      '#elh-cc-btns{display:flex;align-items:center;gap:.5rem}' +
      '.elh-ccb{border:none;border-radius:6px;padding:.42rem .9rem;font-size:12.5px;' +
      'font-weight:600;cursor:pointer;transition:opacity .15s;letter-spacing:.01em}' +
      '.elh-ccb:hover{opacity:.82}' +
      '.elh-cc-ok{background:#7c5cbf;color:#fff;flex:1}' +
      '.elh-cc-mg{background:transparent;color:#999;border:none;padding:.42rem .3rem;' +
      'font-size:12px;font-weight:500;text-decoration:underline;text-underline-offset:2px}' +
      /* Modal overlay */
      '#elh-cc-modal{display:none;position:fixed;inset:0;z-index:100000;' +
      'background:rgba(0,0,0,.58);align-items:center;justify-content:center;padding:1rem}' +
      '#elh-cc-modal.elh-cc-open{display:flex}' +
      /* Modal box */
      '#elh-cc-box{background:#fff;border-radius:14px;max-width:460px;width:100%;' +
      'padding:1.8rem;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
      'max-height:90vh;overflow-y:auto}' +
      '#elh-cc-box h2{font-size:1.05rem;font-weight:700;color:#1a1225;margin:0 0 .25rem}' +
      '#elh-cc-box>p{font-size:13px;color:#666;margin:0 0 1.2rem;line-height:1.6}' +
      '.elh-cc-row{display:flex;align-items:center;justify-content:space-between;' +
      'gap:.8rem;padding:.8rem 0;border-top:1px solid #f0ede8}' +
      '.elh-cc-row-lbl strong{display:block;font-size:13.5px;color:#1a1225;margin-bottom:.1rem}' +
      '.elh-cc-row-lbl span{font-size:12px;color:#888;line-height:1.45;display:block}' +
      /* Toggle switch */
      '.elh-tog{position:relative;width:40px;height:22px;flex-shrink:0}' +
      '.elh-tog input{opacity:0;width:0;height:0;position:absolute}' +
      '.elh-tog-tr{position:absolute;inset:0;background:#ccc;border-radius:22px;' +
      'cursor:pointer;transition:background .2s}' +
      '.elh-tog input:checked+.elh-tog-tr{background:#7c5cbf}' +
      '.elh-tog-tr::after{content:"";position:absolute;width:16px;height:16px;' +
      'left:3px;top:3px;background:#fff;border-radius:50%;transition:transform .2s}' +
      '.elh-tog input:checked+.elh-tog-tr::after{transform:translateX(18px)}' +
      '.elh-tog input:disabled+.elh-tog-tr{opacity:.55;cursor:default}' +
      /* Modal buttons */
      '#elh-cc-mbtns{display:flex;gap:.65rem;margin-top:1.4rem}' +
      '.elh-cc-save{flex:1;background:#7c5cbf;color:#fff;border:none;border-radius:8px;' +
      'padding:.62rem 1rem;font-size:13.5px;font-weight:600;cursor:pointer}' +
      '.elh-cc-save:hover{opacity:.88}' +
      '.elh-cc-decl{flex:1;background:#f4f1ec;color:#333;border:none;border-radius:8px;' +
      'padding:.62rem 1rem;font-size:13.5px;font-weight:600;cursor:pointer}' +
      '.elh-cc-decl:hover{background:#ebe6de}';
    document.head.appendChild(css);

    /* --- Banner ---------------------------------------------------------- */
    var bar = document.createElement('div');
    bar.id = 'elh-cc';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Cookie consent');
    bar.innerHTML =
      '<div id="elh-cc-in">' +
        '<p>We use cookies to improve your experience. <a href="/privacy-policy#cookies">Learn more</a></p>' +
        '<div id="elh-cc-btns">' +
          '<button class="elh-ccb elh-cc-ok" id="elh-cc-okbtn">Accept</button>' +
          '<button class="elh-ccb elh-cc-mg" id="elh-cc-mgbtn" aria-haspopup="dialog">Manage</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(bar);
    // Slide in after two frames so transition fires
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { bar.classList.add('elh-cc-in'); });
    });

    /* --- Modal ----------------------------------------------------------- */
    var modal = document.createElement('div');
    modal.id = 'elh-cc-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Cookie preferences');
    modal.innerHTML =
      '<div id="elh-cc-box">' +
        '<h2>Cookie Preferences</h2>' +
        '<p>Choose which cookies you allow. You can change your mind at any time by clearing your browser storage.</p>' +
        '<div class="elh-cc-row">' +
          '<div class="elh-cc-row-lbl"><strong>Essential</strong>' +
          '<span>Required for basic site functions. Always active.</span></div>' +
          '<label class="elh-tog"><input type="checkbox" checked disabled>' +
          '<span class="elh-tog-tr"></span></label>' +
        '</div>' +
        '<div class="elh-cc-row">' +
          '<div class="elh-cc-row-lbl"><strong>Analytics</strong>' +
          '<span>Google Analytics &amp; Microsoft Clarity — help us understand how the site is used.</span></div>' +
          '<label class="elh-tog"><input type="checkbox" id="elh-tog-a" checked>' +
          '<span class="elh-tog-tr"></span></label>' +
        '</div>' +
        '<div class="elh-cc-row">' +
          '<div class="elh-cc-row-lbl"><strong>Marketing</strong>' +
          '<span>Brevo visitor tracking — only active for newsletter subscribers.</span></div>' +
          '<label class="elh-tog"><input type="checkbox" id="elh-tog-m" checked>' +
          '<span class="elh-tog-tr"></span></label>' +
        '</div>' +
        '<div id="elh-cc-mbtns">' +
          '<button class="elh-cc-decl" id="elh-cc-decl">Decline All</button>' +
          '<button class="elh-cc-save" id="elh-cc-save">Save Preferences</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);

    /* --- Handlers -------------------------------------------------------- */
    document.getElementById('elh-cc-okbtn').addEventListener('click', function () {
      saveConsent('all');
    });
    document.getElementById('elh-cc-mgbtn').addEventListener('click', function () {
      modal.classList.add('elh-cc-open');
      document.getElementById('elh-cc-save').focus();
    });
    modal.addEventListener('click', function (e) {
      if (e.target === modal) { modal.classList.remove('elh-cc-open'); }
    });
    document.getElementById('elh-cc-save').addEventListener('click', function () {
      var a = document.getElementById('elh-tog-a').checked;
      var m = document.getElementById('elh-tog-m').checked;
      saveConsent((a || m) ? 'all' : 'essential');
    });
    document.getElementById('elh-cc-decl').addEventListener('click', function () {
      saveConsent('essential');
    });
  }

  /* ── Entry point ────────────────────────────────────────────────────── */
  if (consent === 'all') {
    loadAnalytics();                     // returning visitor who accepted
  } else if (!consent) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  }
  // consent === 'essential' → analytics suppressed, no banner

})();
