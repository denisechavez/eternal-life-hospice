/* Eternal Life Hospice — Cookie Consent + Analytics loader
   (GA4 + Microsoft Clarity + Brevo)
   Analytics load only after explicit visitor consent.
   Consent stored in localStorage: elh_cc = "all" | "essential"
   Global: window.elhCookieSettings() — re-opens preferences at any time  */


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
    // Inject preconnect hints now that consent is confirmed
    var preconnects = [
      'https://www.googletagmanager.com',
      'https://www.google-analytics.com',
      'https://www.clarity.ms',
      'https://cdn.brevo.com'
    ];
    preconnects.forEach(function (origin) {
      var l = document.createElement('link');
      l.rel = 'preconnect'; l.href = origin; l.crossOrigin = 'anonymous';
      document.head.appendChild(l);
    });

    // GA4
    var GA = 'G-JRLYCRC48G';
    var s = document.createElement('script');
    s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date()); gtag('config', GA);

    // Microsoft Clarity — excluded on pages that set window.__noClarity = true
    // (currently: /refer — referral intake form collects provider & patient data)
    if (!window.__noClarity) {
      (function (c, l, a, r, i, t, y) {
        c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
        t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
        y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
      })(window, document, 'clarity', 'script', 'xddyi1rk95');
    }

    // Brevo visitor tracker
    window.Brevo = window.Brevo || [];
    Brevo.push(['init', { client_key: 'kejxjl4hntbbl2jnfp84s6bs' }]);
    var b = document.createElement('script');
    b.async = true; b.src = 'https://cdn.brevo.com/js/sdk-loader.js';
    document.head.appendChild(b);

    // Metricool
    var mc = document.createElement('script');
    mc.type = 'text/javascript';
    mc.src = 'https://tracker.metricool.com/resources/be.js';
    mc.onreadystatechange = mc.onload = function () {
      beTracker.t({ hash: '6737811bcbdf68de28bffe4886ee6695' });
    };
    document.head.appendChild(mc);

    // WhatConverts call-tracking (marketing consent required)
    // bootAnalytics() only runs after window load, so inject directly — no listener needed.
    (function () {
      var f = function (a) { return JSON.parse(JSON.stringify(a)); };
      window.$wc_leads = window.$wc_leads || { doc: { url: f(document.URL), ref: f(document.referrer), search: f(location.search), hash: f(location.hash) } };
      var wc = document.createElement('script');
      wc.src = '//s.ksrndkehqnwntyxlhgto.com/172406.js';
      document.body.appendChild(wc);
    }());

  }

  /* ── UserWay accessibility widget (essential — always loads) ─────────── */
  function loadUserWay() {
    var load = function () {
      var s = document.createElement('script');
      s.setAttribute('data-color', '#6793AC');
      s.setAttribute('data-trigger', 'elh-ada-trigger');
      s.setAttribute('data-account', 'puHleOAe1C');
      s.src = 'https://cdn.userway.org/widget.js';
      document.body.appendChild(s);
    };
    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(load);
    } else {
      window.addEventListener('load', load);
    }
  }

  /* ── Save preference + act on it ───────────────────────────────────── */
  function saveConsent(level) {
    try { localStorage.setItem(KEY, level); } catch (e) {}
    var bar = document.getElementById('elh-cc');
    var mod = document.getElementById('elh-cc-modal');
    if (bar) { bar.classList.remove('elh-cc-in'); setTimeout(function () { bar.remove(); }, 380); }
    if (mod) { mod.classList.remove('elh-cc-open'); }
    if (level === 'all') { loadAnalytics(); }
  }

  /* ── Inject CSS (idempotent) ─────────────────────────────────────────── */
  function ensureCSS() {
    if (document.getElementById('elh-cc-css')) { return; }
    var css = document.createElement('style');
    css.id = 'elh-cc-css';
    css.textContent =
      /* Banner — ultra-minimal pill, bottom-right */
      '#elh-cc{position:fixed;bottom:1.2rem;left:1.2rem;z-index:99999;' +
      'background:rgba(255,255,255,.92);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);' +
      'border:1px solid rgba(0,0,0,.08);border-radius:99px;' +
      'box-shadow:0 2px 12px rgba(0,0,0,.10);' +
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
      'font-size:12px;line-height:1;' +
      'opacity:0;transform:translateY(6px);transition:opacity .28s ease,transform .28s ease}' +
      '#elh-cc.elh-cc-in{opacity:1;transform:translateY(0)}' +
      '#elh-cc-in{padding:.45rem .55rem .45rem .85rem;display:flex;align-items:center;gap:.5rem}' +
      '#elh-cc p{margin:0;font-size:11.5px;color:#666;white-space:nowrap}' +
      '#elh-cc a{color:#7c5cbf}' +
      '#elh-cc-btns{display:flex;align-items:center;gap:.3rem;flex-shrink:0}' +
      '.elh-ccb{border:none;border-radius:99px;font-size:11.5px;' +
      'font-weight:600;cursor:pointer;transition:opacity .15s;white-space:nowrap}' +
      '.elh-ccb:hover{opacity:.78}' +
      '.elh-cc-ok{background:#7c5cbf;color:#fff;padding:.35rem .75rem}' +
      '.elh-cc-mg{background:transparent;color:#aaa;border:none;padding:.35rem .4rem;' +
      'font-size:11px;font-weight:500;text-decoration:underline;text-underline-offset:2px}' +
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
  }

  /* ── Inject modal only (for returning visitors opening Cookie Settings) ── */
  function ensureModal() {
    if (document.getElementById('elh-cc-modal')) { return; }
    ensureCSS();

    var currentConsent = null;
    try { currentConsent = localStorage.getItem(KEY); } catch (e) {}
    var analyticsOn = currentConsent === 'all';

    var modal = document.createElement('div');
    modal.id = 'elh-cc-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Cookie preferences');
    modal.innerHTML =
      '<div id="elh-cc-box">' +
        '<h2>Cookie Preferences</h2>' +
        '<p>Choose which cookies you allow. You can update your choice at any time using the Cookie Settings link in the footer.</p>' +
        '<div class="elh-cc-row">' +
          '<div class="elh-cc-row-lbl"><strong>Essential</strong>' +
          '<span>Required for basic site functions. Always active.</span></div>' +
          '<label class="elh-tog"><input type="checkbox" checked disabled>' +
          '<span class="elh-tog-tr"></span></label>' +
        '</div>' +
        '<div class="elh-cc-row">' +
          '<div class="elh-cc-row-lbl"><strong>Analytics &amp; Tracking</strong>' +
          '<span>Google Analytics, Microsoft Clarity, Brevo, and call-tracking — ' +
          'help us understand how the site is used and how visitors find us. ' +
          'All non-essential tracking is enabled or disabled together.</span></div>' +
          '<label class="elh-tog"><input type="checkbox" id="elh-tog-all"' + (analyticsOn ? ' checked' : '') + '>' +
          '<span class="elh-tog-tr"></span></label>' +
        '</div>' +
        '<div id="elh-cc-mbtns">' +
          '<button class="elh-cc-decl" id="elh-cc-decl">Decline All</button>' +
          '<button class="elh-cc-save" id="elh-cc-save">Save Preferences</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);

    modal.addEventListener('click', function (e) {
      if (e.target === modal) { modal.classList.remove('elh-cc-open'); }
    });
    document.getElementById('elh-cc-save').addEventListener('click', function () {
      var all = document.getElementById('elh-tog-all').checked;
      saveConsent(all ? 'all' : 'essential');
    });
    document.getElementById('elh-cc-decl').addEventListener('click', function () {
      saveConsent('essential');
    });
  }

  /* ── Banner + modal (injected for first-time visitors) ──────────────── */
  function showBanner() {
    ensureCSS();

    /* --- Banner ---------------------------------------------------------- */
    var bar = document.createElement('div');
    bar.id = 'elh-cc';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Cookie consent');
    bar.innerHTML =
      '<div id="elh-cc-in">' +
        '<p>We use <a href="/privacy-policy#cookies">cookies</a></p>' +
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

    ensureModal();

    /* --- Handlers -------------------------------------------------------- */
    document.getElementById('elh-cc-okbtn').addEventListener('click', function () {
      saveConsent('all');
    });
    document.getElementById('elh-cc-mgbtn').addEventListener('click', function () {
      var mod = document.getElementById('elh-cc-modal');
      mod.classList.add('elh-cc-open');
      document.getElementById('elh-cc-save').focus();
    });
  }

  /* ── Public API — called by "Cookie Settings" footer link ───────────── */
  window.elhCookieSettings = function () {
    ensureModal();
    var mod = document.getElementById('elh-cc-modal');
    mod.classList.add('elh-cc-open');
    document.getElementById('elh-cc-save').focus();
  };

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

  // UserWay is an accessibility tool — load it unconditionally on every page
  loadUserWay();

})();
