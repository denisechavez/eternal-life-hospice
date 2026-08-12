/**
 * translate.js — ELH language pills
 *
 * STATIC_PAGES lists slugs that have pre-built translated HTML files at
 * /<lang>/<slug>.  It is written by website/tools/deepl-translate.py when pages
 * are generated.  Until then the array stays empty and every pill falls back
 * to a Google Translate redirect — no broken links are ever served.
 *
 * Supports translated pages too: if the visitor is already on /es/hospice-torrance-ca,
 * the pill for Spanish is marked active and other pills are computed from the
 * English base path.
 */
(function () {
  /* AUTO-UPDATED by website/tools/deepl-translate.py — do not edit by hand */
  var STATIC_PAGES = [
    /* translated slugs appear here after the build script runs */
  ];

  /* Languages served as static files; the three below always use Google */
  /* hy (Armenian), tl (Filipino), fa (Persian): not supported by DeepL  */
  var STATIC_LANGS = ['es', 'ru', 'uk', 'ko', 'vi', 'zh-CN', 'ar'];

  /* Detect current language from the URL path segment */
  var parts   = location.pathname.replace(/^\//, '').split('/');
  var curLang = STATIC_LANGS.indexOf(parts[0]) !== -1 ? parts[0] : 'en';

  /* basePath = the equivalent English path, e.g. /hospice-torrance-ca */
  var basePath = curLang !== 'en' ? '/' + parts.slice(1).join('/') : location.pathname;
  basePath = basePath.replace(/\.html$/, '').replace(/\/$/, '') || '/';

  /* slug without leading slash, e.g. 'hospice-torrance-ca' */
  var slug = basePath.replace(/^\//, '');

  document.querySelectorAll('.ft-lang').forEach(function (btn) {
    var lang = btn.dataset.lang;
    if (!lang) return;

    var isStatic = STATIC_LANGS.indexOf(lang) !== -1 && STATIC_PAGES.indexOf(slug) !== -1;
    var url, openBlank;

    if (isStatic) {
      /* Static pre-translated page */
      url = '/' + lang + basePath;
      openBlank = false;
    } else {
      /* Google Translate fallback — always a working link */
      var englishUrl = location.origin + basePath;
      url = 'https://translate.google.com/translate?sl=en&tl=' +
            encodeURIComponent(lang) + '&u=' + encodeURIComponent(englishUrl);
      openBlank = true;
    }

    btn.addEventListener('click', function () {
      if (openBlank) {
        window.open(url, '_blank', 'noopener');
      } else {
        window.location.href = url;
      }
    });

    /* Highlight the pill that matches the current page language */
    if (lang === curLang) {
      btn.classList.add('ft-lang--active');
      btn.setAttribute('aria-current', 'true');
    }
  });
}());
