/* Eternal Life Hospice — Cookie Consent + Analytics loader
   (GA4 + Google Ads + Microsoft Clarity + Brevo + Thryv)
   Analytics load only after explicit visitor consent.
   Consent stored in localStorage: elh_cc = "all" | "essential"
   Global: window.elhCookieSettings() — re-opens preferences at any time  */


(function () {
  'use strict';

  if (window.__elhAnalyticsInitialized) { return; }
  window.__elhAnalyticsInitialized = true;
  var KEY = 'elh_cc';
  var consent = null;
  try { consent = localStorage.getItem(KEY); } catch (e) {}

  /* ── Replit custom events (privacy-safe and consent-aware) ───────────── */
  function analyticsConsentGranted() {
    try { return localStorage.getItem(KEY) === 'all'; }
    catch (e) { return false; }
  }

  function trackEvent(name, data) {
    if (!analyticsConsentGranted()) { return false; }
    // Mirror only the approved funnel events. Each destination fails independently.
    trackGAOutcome(name, data);
    try {
      if (window.umami && typeof window.umami.track === 'function') {
        var result = window.umami.track(name, data);
        if (result && typeof result.catch === 'function') {
          result.catch(function () {
            // Network failures must not produce unhandled rejections.
          });
        }
        return true;
      }
    } catch (e) {
      // Analytics must never interrupt care-seeking or site navigation.
    }
    return false;
  }

  // Shared, safe hook for form and chat code. Never pass visitor-entered text.
  window.elhTrackEvent = trackEvent;

  function trackGAEvent(name, data) {
    if (!analyticsConsentGranted()) { return; }
    try {
      if (typeof window.gtag === 'function') {
        // Care-related custom events belong in GA4, not the Ads destination.
        var result = window.gtag('event', name, Object.assign({}, data, {
          send_to: 'G-WTMEYKXW8H'
        }));
        if (result && typeof result.catch === 'function') {
          result.catch(function () {});
        }
      }
    } catch (e) {
      // Never interrupt navigation or submission confirmation.
    }
  }
  function trackGAOutcome(name, data) {
    if (!data || ['request_care_click', 'referral_cta_click', 'form_success'].indexOf(name) === -1) { return; }
    var source = outcomePage(data.page);
    if (!source) { return; }
    var params = { source_page: source };
    if (name === 'form_success') {
      // These are authored form names, never values from submitted fields.
      var kinds = {
        'elh-family': 'care',
        'elh-physician': 'referral',
        'elh-casemanager': 'referral',
        'elh-coordinator': 'professional_contact',
        'elh-voice': 'team_contact'
      };
      if (!Object.prototype.hasOwnProperty.call(kinds, data.form)) { return; }
      params.form = data.form;
      params.submission_type = kinds[data.form];
    } else {
      params.destination_page = name === 'request_care_click' ? '/' : '/refer';
      if (['chat', 'header', 'footer', 'hero', 'form', 'content'].indexOf(data.placement) !== -1) {
        params.placement = data.placement;
      }
    }
    // No spread/copy of caller metadata: exclude entered text, receipts and URLs.
    trackGAEvent(name, params);
  }

  function outcomePage(value) {
    if (typeof value !== 'string' || value.length > 150) { return null; }
    // Canonical editorial paths only: no query, fragment or arbitrary URL.
    value = value.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
    return /^\/(?:[a-z0-9-]+\/)*[a-z0-9-]*$/.test(value) ? value : null;
  }

  function trackRelatedReading(link) {
    if (!analyticsConsentGranted() ||
        !(link.closest('.elh-related') || link.classList.contains('elh-inline-link'))) { return; }
    // These attributes are emitted by the curated-link renderer. Do not read
    // labels, the current URL (which may contain queries), or form values.
    var source = link.getAttribute('data-reading-source');
    var destination = link.getAttribute('data-reading-destination');
    var topic = link.getAttribute('data-reading-topic');
    var route = /^\/(?:[a-z0-9-]+\/)*[a-z0-9-]*$/;
    var topics = ['care', 'services', 'family', 'local', 'journal', 'coverage',
      'comfort', 'choosing', 'starting', 'whole', 'referral', 'support'];
    if (!source || !destination || source.length > 150 || destination.length > 150 ||
        !route.test(source) || !route.test(destination) || topics.indexOf(topic) === -1) { return; }
    trackGAEvent('related_reading_click', {
      source_page: source,
      destination_page: destination,
      topic: topic
    });
  }

  function pagePath() {
    return window.location.pathname || '/';
  }

  function placementFor(el) {
    if (el.closest('.elhc')) { return 'chat'; }
    if (el.closest('header')) { return 'header'; }
    if (el.closest('footer')) { return 'footer'; }
    if (el.closest('.hero')) { return 'hero'; }
    if (el.closest('form')) { return 'form'; }
    return 'content';
  }

  function safeFormName(form) {
    var field = form.querySelector('input[name="form-name"]');
    var value = form.getAttribute('name') || (field && field.value) || 'unknown';
    return /^[a-z0-9_-]{1,50}$/i.test(value) ? value : 'unknown';
  }

  function resourceName(url) {
    var parts = url.pathname.split('/');
    var name = parts[parts.length - 1] || 'download';
    return name.toLowerCase().replace(/[^a-z0-9._-]/g, '').slice(0, 80) || 'download';
  }

  function socialNetwork(url) {
    var host = url.hostname.toLowerCase();
    if (host.indexOf('linkedin.com') > -1) { return 'linkedin'; }
    if (host.indexOf('facebook.com') > -1) { return 'facebook'; }
    if (host.indexOf('instagram.com') > -1) { return 'instagram'; }
    if (host.indexOf('twitter.com') > -1 || host === 'x.com') { return 'x'; }
    if (host.indexOf('pinterest.com') > -1) { return 'pinterest'; }
    return '';
  }

  function bindCustomEvents() {
    if (window.__elhCustomEventsBound) { return; }
    window.__elhCustomEventsBound = true;

    document.addEventListener('click', function (event) {
      var target = event.target;
      var category = target && target.closest ? target.closest('.lead-cat[data-cat]') : null;
      if (category) {
        var leadType = category.getAttribute('data-cat');
        if (['family', 'physician', 'casemanager', 'coordinator', 'voice'].indexOf(leadType) !== -1) {
          trackEvent('lead_type_selected', { page: pagePath(), lead_type: leadType });
        }
        return;
      }
      var link = target && target.closest ? target.closest('a[href]') : null;
      if (!link) { return; }

      trackRelatedReading(link);
      // Continue through the existing care/referral conversion handlers.
      var rawHref = link.getAttribute('href') || '';
      var data = { page: pagePath(), placement: placementFor(link) };

      if (rawHref.indexOf('tel:') === 0) {
        trackEvent('phone_click', data);
        return;
      }
      if (rawHref.indexOf('mailto:?') === 0) {
        trackEvent('email_share_click', data);
        return;
      }
      if (rawHref.indexOf('mailto:') === 0) {
        trackEvent('email_click', data);
        return;
      }

      var url;
      try { url = new URL(rawHref, window.location.href); }
      catch (e) { return; }

      if (link.classList.contains('search-result')) {
        trackEvent('site_search_result_click', {
          page: pagePath(),
          destination: url.pathname.slice(0, 100)
        });
        return;
      }

      if (url.hostname === 'maps.google.com' || url.hostname === 'www.google.com' && url.pathname.indexOf('/maps') === 0) {
        trackEvent('map_click', data);
        return;
      }

      if (link.hasAttribute('download') || /\.(pdf|vcf)$/i.test(url.pathname)) {
        trackEvent('resource_download', {
          page: pagePath(),
          placement: data.placement,
          resource: resourceName(url)
        });
        return;
      }

      var network = socialNetwork(url);
      if (network) {
        trackEvent('social_link_click', {
          page: pagePath(),
          placement: data.placement,
          network: network
        });
        return;
      }

      if (url.origin === window.location.origin && (url.pathname === '/refer' || url.pathname === '/refer/')) {
        trackEvent('referral_cta_click', data);
        return;
      }

      if (
        url.origin === window.location.origin &&
        (url.searchParams.get('lead') === 'family' ||
          url.searchParams.get('lead') === 'voice' || url.hash === '#leadcap')
      ) {
        var lead = url.searchParams.get('lead');
        trackEvent(lead === 'family' ? 'request_care_click' :
          lead === 'voice' ? 'contact_team_click' : 'contact_cta_click', data);
      }
    });

    document.addEventListener('focusin', function (event) {
      var target = event.target;
      var form = target && target.closest ? target.closest('form') : null;
      if (!form || form.getAttribute('data-analytics-started') === 'true') { return; }
      if (trackEvent('form_start', {
        page: pagePath(),
        form: safeFormName(form)
      })) {
        form.setAttribute('data-analytics-started', 'true');
      }
    });

    document.addEventListener('submit', function (event) {
      var form = event.target;
      if (!form || form.tagName !== 'FORM') { return; }
      trackEvent('form_submit', {
        page: pagePath(),
        form: safeFormName(form)
      });
    });
  }

  /* ── Analytics init (runs after window load to protect LCP) ─────────── */
  function loadAnalytics() {
    if (document.readyState === 'complete') { bootAnalytics(); }
    else { window.addEventListener('load', bootAnalytics); }
  }

  function bootAnalytics() {
    if (!analyticsConsentGranted() || window.__elhAnalyticsBooted) { return; }
    window.__elhAnalyticsBooted = true;
    // Inject preconnect hints now that consent is confirmed
    var preconnects = [
      'https://www.googletagmanager.com',
      'https://www.google-analytics.com',
      'https://www.clarity.ms',
      'https://cdn.brevo.com',
      'https://tags.tiqcdn.com'
    ];
    preconnects.forEach(function (origin) {
      var l = document.createElement('link');
      l.rel = 'preconnect'; l.href = origin; l.crossOrigin = 'anonymous';
      document.head.appendChild(l);
    });

    // One Google tag loader for GA4 and Google Ads, after visitor consent.
    var GA = 'G-WTMEYKXW8H';
    var s = document.createElement('script');
    s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date()); gtag('config', GA);
    gtag('config', 'AW-18384023405');

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

    // Thryv Marketing Center website analytics and heatmap
    window.utag_data = window.utag_data || {};
    window.Parameters = window.Parameters || { ExternalUid: 'cii463' };
    var thryv = document.createElement('script');
    thryv.async = true;
    thryv.src = 'https://tags.tiqcdn.com/utag/marketingcenter/common/prod/utag.js';
    document.head.appendChild(thryv);

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
    var previous = null;
    try { previous = localStorage.getItem(KEY); } catch (e) {}
    try { localStorage.setItem(KEY, level); } catch (e) {}
    var bar = document.getElementById('elh-cc');
    if (bar) { bar.remove(); }
    if (cookieReturnFocus && cookieReturnFocus.isConnected) { cookieReturnFocus.focus(); }
    // Already-loaded third-party scripts cannot be unloaded reliably. A fresh
    // document applies an essential-only choice before any optional boot.
    if (previous === 'all' && level === 'essential') { window.location.reload(); return; }
    if (level === 'all') { loadAnalytics(); }
  }

  var cookieReturnFocus = null;

  /* ── Inject CSS (idempotent) ─────────────────────────────────────────── */
  function ensureCSS() {
    if (document.getElementById('elh-cc-css')) { return; }
    var css = document.createElement('style');
    css.id = 'elh-cc-css';
    css.textContent = `
      #elh-cc{position:fixed;bottom:20px;left:20px;z-index:2147483001;box-sizing:border-box;
        width:540px;max-width:calc(100vw - 40px);max-height:calc(100dvh - 40px);overflow-y:auto;
        background:#fffdf8;border:1px solid #d8cebd;border-top:3px solid #b5a279;border-radius:3px;
        padding:27px 30px 20px;box-shadow:0 12px 34px #43244018;color:#484442;
        font-family:'Jost ELH','Jost',Arial,sans-serif;text-align:left;line-height:1.5}
      #elh-cc *{box-sizing:border-box}
      #elh-cc [hidden]{display:none!important}
      #elh-cc :focus-visible{outline:2px solid #6a4268;outline-offset:4px}
      #elh-cc .privacy-eyebrow{display:flex;align-items:center;gap:9px;color:#655b60;
        text-transform:uppercase;font-size:10px;letter-spacing:.14em;font-weight:500}
      #elh-cc .privacy-mark{color:#9a855c;font:24px Georgia,serif;line-height:1}
      #elh-cc h2{font:400 31px/1.15 Georgia,'Times New Roman',serif;
        letter-spacing:-.7px;color:#432440;margin:16px 0 13px;text-transform:none}
      #elh-cc .privacy-copy{color:#585359;font-size:14px;line-height:1.65;margin:0 0 11px}
      #elh-cc .privacy-policy{color:#62475e;text-decoration:underline;text-underline-offset:4px;
        font-size:12px;display:inline-flex;align-items:center;gap:6px}
      #elh-cc .privacy-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:23px 0 17px}
      #elh-cc button{cursor:pointer}
      #elh-cc .privacy-actions button,#elh-cc .privacy-save{font:500 14px 'Jost ELH','Jost',Arial,sans-serif;
        border:1px solid #6e5369;min-height:46px;padding:10px 14px;border-radius:2px;
        transition:background .15s,color .15s;letter-spacing:normal;text-transform:none}
      #elh-cc .privacy-actions button:first-child{background:transparent;color:#432440}
      #elh-cc .privacy-actions button:last-child,#elh-cc .privacy-save{background:#432440;color:#fffdf8}
      #elh-cc .privacy-actions button:first-child:hover{background:#f2ece7}
      #elh-cc .privacy-actions button:last-child:hover,#elh-cc .privacy-save:hover{background:#5c3958}
      #elh-cc .privacy-bottom{border-top:1px solid #e4ddd1;padding-top:14px;display:flex;
        align-items:center;justify-content:space-between;gap:12px}
      #elh-cc .privacy-bottom button{color:#584752;background:none;border:0;padding:3px 0;min-height:28px;
        font:400 12px 'Jost ELH','Jost',Arial,sans-serif;text-decoration:underline;text-underline-offset:4px}
      #elh-cc .privacy-bottom button span{margin-left:7px;text-decoration:none;display:inline-block}
      #elh-cc .privacy-bottom>span{font-size:10px;color:#70666a}
      #elh-cc .privacy-preferences{border-top:1px solid #ded6c9;margin-top:20px;padding-top:13px}
      #elh-cc .privacy-pref-heading{display:flex;align-items:center;justify-content:space-between}
      #elh-cc .privacy-pref-heading h3{margin:0;color:#432440;font:400 21px Georgia,serif;letter-spacing:normal;text-transform:none}
      #elh-cc .privacy-pref-heading button{border:0;background:none;color:#432440;font-size:25px;min-width:40px;min-height:40px}
      #elh-cc .privacy-pref-row{display:flex;align-items:center;justify-content:space-between;gap:16px;
        padding:15px 0;border-bottom:1px solid #e4ddd1;font-size:14px}
      #elh-cc .privacy-pref-row strong{font-weight:500;color:#484442}
      #elh-cc .privacy-pref-row p{font-size:12px;line-height:1.5;color:#655d61;margin:5px 0 0;max-width:330px}
      #elh-cc .privacy-always{font-size:11px;color:#70666a;white-space:nowrap}
      #elh-cc .privacy-optional{cursor:pointer}
      #elh-cc .privacy-pref-row input{width:22px;height:22px;flex-shrink:0;accent-color:#432440;cursor:pointer;margin:0}
      #elh-cc .privacy-save{width:100%;margin-top:16px}
      @media(max-width:460px){
        #elh-cc{bottom:14px;left:14px;max-width:calc(100vw - 28px);max-height:calc(100dvh - 28px);padding:23px 21px 18px}
        #elh-cc h2{font-size:28px}#elh-cc .privacy-break{display:none}
        #elh-cc .privacy-bottom{align-items:flex-start;flex-direction:column;gap:7px}
        #elh-cc .privacy-actions{gap:8px}#elh-cc .privacy-actions button{font-size:13px;padding:10px}
      }
      @media(prefers-reduced-motion:reduce){#elh-cc *{transition:none!important}}
    `;
    document.head.appendChild(css);
  }

  /* ── Approved Refined Privacy panel; preferences expand in place ───── */
  function showBanner() {
    if (document.getElementById('elh-cc')) { return; }
    ensureCSS();

    /* --- Banner ---------------------------------------------------------- */
    var bar = document.createElement('div');
    bar.id = 'elh-cc';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Cookie consent');
    bar.innerHTML =
      '<div class="privacy-eyebrow"><span aria-hidden="true" class="privacy-mark">✧</span>Your privacy, your choice</div>' +
      '<h2>A thoughtful approach<br class="privacy-break"> to your privacy.</h2>' +
      '<p class="privacy-copy">We use essential cookies to keep this website working. With your permission, we also use analytics and tracking to understand visits and how people find us.</p>' +
      '<a class="privacy-policy" href="/privacy-policy#cookies">Read our cookie policy <span aria-hidden="true">↗</span></a>' +
      '<div class="privacy-preferences" id="elh-cc-preferences" hidden>' +
        '<div class="privacy-pref-heading"><h3>Cookie preferences</h3><button type="button" id="elh-cc-close" aria-label="Close preferences">×</button></div>' +
        '<div class="privacy-pref-row"><div><strong>Essential</strong><p>Needed for site features and security.</p></div><span class="privacy-always">Always on</span></div>' +
        '<label class="privacy-pref-row privacy-optional"><div><strong>Analytics &amp; tracking</strong><p>Google Analytics and Ads, Clarity, Brevo and other non-essential site and call tracking. Enabled or disabled together.</p></div>' +
          '<input type="checkbox" id="elh-tog-all" aria-label="Allow analytics and tracking"></label>' +
        '<button type="button" class="privacy-save" id="elh-cc-save">Save preferences</button>' +
      '</div>' +
      '<div class="privacy-actions"><button type="button" id="elh-cc-decl">Essential only</button><button type="button" id="elh-cc-okbtn">Accept all</button></div>' +
      '<div class="privacy-bottom"><button type="button" id="elh-cc-mgbtn" aria-expanded="false" aria-controls="elh-cc-preferences">Manage preferences <span aria-hidden="true">+</span></button><span>Change your choice anytime.</span></div>';
    document.body.appendChild(bar);
    /* --- Handlers -------------------------------------------------------- */
    document.getElementById('elh-cc-okbtn').addEventListener('click', function () {
      saveConsent('all');
    });
    document.getElementById('elh-cc-mgbtn').addEventListener('click', function () {
      var opening = document.getElementById('elh-cc-preferences').hidden;
      setCookiePreferences(opening);
    });
    document.getElementById('elh-cc-close').addEventListener('click', function () { setCookiePreferences(false); });
    document.getElementById('elh-cc-decl').addEventListener('click', function () { saveConsent('essential'); });
    document.getElementById('elh-cc-save').addEventListener('click', function () {
      saveConsent(document.getElementById('elh-tog-all').checked ? 'all' : 'essential');
    });
    bar.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !document.getElementById('elh-cc-preferences').hidden) {
        event.preventDefault(); setCookiePreferences(false);
      }
    });
  }

  function setCookiePreferences(open) {
    var prefs = document.getElementById('elh-cc-preferences');
    var button = document.getElementById('elh-cc-mgbtn');
    prefs.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
    button.querySelector('span').textContent = open ? '−' : '+';
    if (open) {
      var current = null;
      try { current = localStorage.getItem(KEY); } catch (e) {}
      document.getElementById('elh-tog-all').checked = current === 'all';
      document.getElementById('elh-tog-all').focus();
    } else { button.focus(); }
  }

  /* ── Public API — called by "Cookie Settings" footer link ───────────── */
  window.elhCookieSettings = function () {
    cookieReturnFocus = document.activeElement;
    showBanner();
    setCookiePreferences(true);
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

  bindCustomEvents();

  // UserWay is an accessibility tool — load it unconditionally on every page
  loadUserWay();

})();
