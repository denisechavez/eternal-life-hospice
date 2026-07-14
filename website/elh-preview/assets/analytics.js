/* Eternal Life Hospice — shared analytics (GA4 + Microsoft Clarity)
   Loaded site-wide via <script async src="/assets/analytics.js"></script>
   so measurement fires on every page with a single source of truth. */
(function () {
  // ---- Google Analytics 4 ----
  var GA_ID = 'G-JRLYCRC48G';
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { dataLayer.push(arguments); };
  gtag('js', new Date());
  gtag('config', GA_ID);

  // ---- Microsoft Clarity ----
  (function (c, l, a, r, i, t, y) {
    c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
    t = l.createElement(r); t.async = 1; t.src = "https://www.clarity.ms/tag/" + i;
    y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
  })(window, document, "clarity", "script", "xddyi1rk95");
})();
