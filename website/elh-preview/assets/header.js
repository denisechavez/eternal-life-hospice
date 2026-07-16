(function () {
  var hdr = document.getElementById('hdr');
  if (!hdr) return;

  function onScroll() {
    hdr.classList.toggle('scrolled', window.scrollY > 60);
  }
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  var mb = hdr.querySelector('.menu-btn');
  var nav = hdr.querySelector('nav');

  function closeMenu() {
    hdr.classList.remove('nav-open');
    if (mb) mb.setAttribute('aria-expanded', 'false');
  }
  function toggleMenu() {
    var open = hdr.classList.toggle('nav-open');
    if (mb) mb.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  if (mb) {
    mb.addEventListener('click', function (e) {
      e.stopPropagation();
      toggleMenu();
    });
  }

  document.addEventListener('click', function (e) {
    if (
      hdr.classList.contains('nav-open') &&
      mb && !mb.contains(e.target) &&
      nav && !nav.contains(e.target)
    ) {
      closeMenu();
    }
  });

  if (nav) {
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeMenu);
    });
  }

  var ctaPill = hdr.querySelector('.hdr-cta');
  if (ctaPill) {
    var ctaHues = ['cta-hue1', 'cta-hue2', 'cta-hue3'], ctaIdx = 0;
    ctaPill.addEventListener('mouseenter', function () {
      ctaPill.classList.remove('cta-hue1', 'cta-hue2', 'cta-hue3');
      ctaPill.classList.add(ctaHues[ctaIdx % 3]);
      ctaIdx++;
    });
    ctaPill.addEventListener('mouseleave', function () {
      ctaPill.classList.remove('cta-hue1', 'cta-hue2', 'cta-hue3');
    });
  }

  // SEARCH
  var so = document.getElementById('searchOverlay');
  var si = document.getElementById('searchInput');
  var sr = document.getElementById('searchResults');
  var sb = document.getElementById('searchBtn');
  var sc = document.getElementById('searchClose');
  var idx = null, q = '', fetching = false, lastFocus = null;

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function openSearch() {
    if (!so) return;
    lastFocus = document.activeElement;
    so.classList.add('open');
    so.setAttribute('aria-hidden', 'false');
    so.setAttribute('aria-modal', 'true');
    if (si) { si.focus(); si.value = ''; }
    if (sr) sr.innerHTML = '';
  }
  function closeSearch() {
    if (!so) return;
    so.classList.remove('open');
    so.setAttribute('aria-hidden', 'true');
    so.removeAttribute('aria-modal');
    if (si) si.blur();
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  if (sb) sb.addEventListener('click', openSearch);
  if (sc) sc.addEventListener('click', closeSearch);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && so && so.classList.contains('open')) { e.preventDefault(); closeSearch(); }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openSearch(); }
  });

  function doSearch(val) {
    q = val.toLowerCase().trim();
    if (!q) { if (sr) sr.innerHTML = ''; return; }
    if (!idx) {
      if (fetching) return;
      if (sr) sr.innerHTML = '<div class="search-empty">Loading search index...</div>';
      fetching = true;
      fetch('/assets/search-index.json').then(function (r) { return r.json(); }).then(function (data) { idx = data; fetching = false; render(); }).catch(function () { fetching = false; if (sr) sr.innerHTML = '<div class="search-empty">Unable to load search. Try again.</div>'; });
      return;
    }
    render();
  }

  function render() {
    var hits = [];
    for (var i = 0; i < idx.length; i++) {
      var it = idx[i];
      var txt = ((it.title || '') + ' ' + (it.desc || '') + ' ' + (it.kw || '')).toLowerCase();
      if (txt.indexOf(q) > -1) hits.push(it);
    }
    if (!sr) return;
    sr.innerHTML = '';
    if (!hits.length) { sr.innerHTML = '<div class="search-empty">No results for "' + esc(q) + '"</div>'; return; }

    var count = document.createElement('div');
    count.style.cssText = 'color:rgba(245,240,235,.4);font-size:13px;margin-bottom:.6rem;';
    count.textContent = hits.length + ' result' + (hits.length > 1 ? 's' : '');
    sr.appendChild(count);

    for (var j = 0; j < hits.length; j++) {
      var r = hits[j];
      var a = document.createElement('a');
      a.className = 'search-result';
      a.href = r.url || '#';
      if (r.cat) {
        var c = document.createElement('div');
        c.className = 'search-result-cat';
        c.textContent = r.cat;
        a.appendChild(c);
      }
      var t = document.createElement('div');
      t.className = 'search-result-title';
      t.textContent = r.title || '';
      a.appendChild(t);
      var d = document.createElement('div');
      d.className = 'search-result-desc';
      d.textContent = r.desc || '';
      a.appendChild(d);
      sr.appendChild(a);
    }
  }

  if (si) {
    si.addEventListener('input', function () { doSearch(si.value); });
    si.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var first = sr ? sr.querySelector('.search-result') : null;
        if (first) { e.preventDefault(); window.location.href = first.getAttribute('href'); }
      }
    });
  }
  if (so) so.addEventListener('click', function (e) { if (e.target === so) closeSearch(); });
})();