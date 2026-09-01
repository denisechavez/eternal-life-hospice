(function () {
  var hdr = document.getElementById('hdr');
  if (!hdr) return;

  var isHome = (location.pathname === '/' || location.pathname === '/index.html');
  var scrollScheduled = false;
  var lastScrolled = null;
  function updateHeaderState() {
    scrollScheduled = false;
    var nextScrolled = isHome && window.scrollY > 60;
    if (nextScrolled === lastScrolled) return;
    hdr.classList.toggle('scrolled', nextScrolled);
    lastScrolled = nextScrolled;
  }
  function onScroll() {
    if (scrollScheduled) return;
    scrollScheduled = true;
    window.requestAnimationFrame(updateHeaderState);
  }
  updateHeaderState();
  if (isHome) window.addEventListener('scroll', onScroll, { passive: true });

  var mb = hdr.querySelector('.menu-btn');
  var nav = hdr.querySelector('nav');
  var groups = nav ? nav.querySelectorAll('.nav-group') : [];

  if (nav && !nav.id) nav.id = 'site-nav';
  if (mb && nav) mb.setAttribute('aria-controls', nav.id);

  Array.prototype.forEach.call(groups, function (group, index) {
    var parent = group.querySelector('.nav-parent');
    var submenu = group.querySelector('.nav-sub');
    if (!parent || !submenu) return;

    var submenuId = submenu.id || 'site-nav-submenu-' + (index + 1);
    submenu.id = submenuId;

    var toggle = group.querySelector('.nav-toggle');
    if (!toggle) {
      toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'nav-toggle';
      toggle.innerHTML = '<span class="sr-only">Show submenu for ' + parent.textContent.trim() + '</span><span class="nav-chevron" aria-hidden="true"></span>';
      parent.insertAdjacentElement('afterend', toggle);
    }
    toggle.setAttribute('aria-controls', submenuId);
    toggle.setAttribute('aria-expanded', 'false');
  });

  function normalizePath(value) {
    var path = (value || '/').split('?')[0].split('#')[0];
    if (path.length > 1) path = path.replace(/\/+$/, '');
    return path || '/';
  }

  function markCurrentSection() {
    if (!nav) return;
    var path = normalizePath(location.pathname);
    var section = '';
    if (path === '/hospice-care') section = 'hospice-care';
    else if (
      path === '/services' || path === '/sound-bath' ||
      path === '/resources/comfort-therapies' ||
      path === '/resources/pain-symptom-management'
    ) section = 'services';
    else if (
      path === '/resources' || path === '/family-guide' ||
      path === '/blog' || path.indexOf('/blog/') === 0 ||
      path === '/care-brief' || path.indexOf('/care-brief/') === 0 ||
      path === '/volunteer' || path === '/media-kit' || path === '/careers'
    ) section = 'resources';
    else if (path.indexOf('/hospice-') === 0) section = 'service-areas';
    else if (path.indexOf('/about/') === 0) section = 'about';
    else if (path === '/refer') section = 'contact';

    if (!section) return;
    var current = nav.querySelector('[data-section="' + section + '"] > .nav-parent');
    if (current) current.setAttribute('aria-current', 'page');
  }
  markCurrentSection();

  // Request Care pill — cycle through the three accent colors on each hover pass.
  var ctaPill = hdr.querySelector('.nav-group--contact > .nav-parent');
  if (ctaPill) {
    var ctaHues = ['cta-hue1', 'cta-hue2', 'cta-hue3'];
    var ctaIdx = 0;
    ctaPill.addEventListener('mouseenter', function () {
      ctaPill.classList.remove('cta-hue1', 'cta-hue2', 'cta-hue3');
      ctaPill.classList.add(ctaHues[ctaIdx % ctaHues.length]);
      ctaIdx++;
    });
    ctaPill.addEventListener('mouseleave', function () {
      ctaPill.classList.remove('cta-hue1', 'cta-hue2', 'cta-hue3');
    });
  }

  function closeMenu() {
    hdr.classList.remove('nav-open');
    if (mb) mb.setAttribute('aria-expanded', 'false');
    collapseAllGroups();
  }
  function collapseAllGroups() {
    Array.prototype.forEach.call(groups, function (group) {
      group.classList.remove('expanded');
      var toggle = group.querySelector('.nav-toggle');
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
    });
  }
  function toggleMenu() {
    var open = hdr.classList.toggle('nav-open');
    if (mb) mb.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) collapseAllGroups(); // always open with sections collapsed
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
      return;
    }
    if (nav && !nav.contains(e.target)) collapseAllGroups();
  });

  if (nav) {
    // Every link remains navigable, including top-level landing pages.
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeMenu);
    });

    nav.querySelectorAll('.nav-toggle').forEach(function (toggle) {
      toggle.addEventListener('click', function () {
        var group = toggle.parentElement;
        var wasExpanded = group.classList.contains('expanded');
        collapseAllGroups();
        if (!wasExpanded) {
          group.classList.add('expanded');
          toggle.setAttribute('aria-expanded', 'true');
        }
      });
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var mobileOpen = hdr.classList.contains('nav-open');
    var expanded = nav && nav.querySelector('.nav-group.expanded');
    if (!mobileOpen && !expanded) return;
    e.preventDefault();
    closeMenu();
    if (mobileOpen && mb) mb.focus();
  });

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

  function searchFocusables() {
    if (!so) return [];
    var nodes = so.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])');
    return Array.prototype.filter.call(nodes, function (el) {
      return el.getAttribute('aria-hidden') !== 'true' &&
        (el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    });
  }

  function openSearch() {
    if (!so || so.classList.contains('open')) return;
    if (typeof window.elhTrackEvent === 'function') {
      window.elhTrackEvent('site_search_open', { page: location.pathname || '/' });
    }
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
    if (!so || !so.classList.contains('open')) return;
    if (e.key === 'Escape') { e.preventDefault(); closeSearch(); return; }
    if (e.key === 'Tab') {
      var focusables = searchFocusables();
      if (!focusables.length) { e.preventDefault(); return; }
      var first = focusables[0], last = focusables[focusables.length - 1];
      var active = document.activeElement;
      if (!so.contains(active)) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      } else if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });
  document.addEventListener('keydown', function (e) {
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

  // Tokenize a string into lowercase alphanumeric words
  function tokenize(s) {
    return (s || '').toLowerCase().split(/[^a-z0-9]+/).filter(function (t) { return t.length > 0; });
  }

  // Levenshtein distance, capped early at 2 for speed
  function editDist(a, b) {
    if (a === b) return 0;
    if (Math.abs(a.length - b.length) > 2) return 99;
    var m = a.length, n = b.length;
    var row = [], prev = [];
    for (var j = 0; j <= n; j++) prev[j] = j;
    for (var i = 1; i <= m; i++) {
      row[0] = i;
      for (var j = 1; j <= n; j++) {
        row[j] = a[i - 1] === b[j - 1]
          ? prev[j - 1]
          : 1 + Math.min(prev[j], row[j - 1], prev[j - 1]);
      }
      var tmp = prev; prev = row; row = tmp;
    }
    return prev[n];
  }

  // Returns true if a query token matches any token in the document token list.
  // Rules: exact, prefix (queryTok is prefix of docTok), abbreviation
  // (queryTok ≥ 3 chars is prefix of docTok), or 1-edit fuzzy for len ≥ 5.
  function tokenMatches(qt, docToks) {
    for (var k = 0; k < docToks.length; k++) {
      var dt = docToks[k];
      if (dt === qt) return true;                            // exact
      if (dt.indexOf(qt) === 0 && qt.length >= 3) return true; // prefix
      if (qt.indexOf(dt) === 0 && dt.length >= 3) return true; // query is longer prefix of doc word (abbreviation)
      if (qt.length >= 5 && dt.length >= 4 && editDist(qt, dt) <= 1) return true; // fuzzy
    }
    return false;
  }

  // Score: fraction of query tokens that match something in the document.
  // Exact whole-string match gets a bonus so it still floats to the top.
  function scoreEntry(entry, queryToks, rawQ) {
    var txt = ((entry.title || '') + ' ' + (entry.desc || '') + ' ' + (entry.kw || '')).toLowerCase();
    // Fast path: exact substring match → top score
    if (txt.indexOf(rawQ) > -1) return 1 + queryToks.length;
    var docToks = tokenize(txt);
    if (!queryToks.length) return 0;
    var matched = 0;
    for (var i = 0; i < queryToks.length; i++) {
      if (tokenMatches(queryToks[i], docToks)) matched++;
    }
    return matched / queryToks.length; // 0–1
  }

  function render() {
    var queryToks = tokenize(q);
    var scored = [];
    for (var i = 0; i < idx.length; i++) {
      var sc = scoreEntry(idx[i], queryToks, q);
      if (sc > 0) scored.push({ item: idx[i], score: sc });
    }
    scored.sort(function (a, b) { return b.score - a.score; });
    var hits = scored.map(function (s) { return s.item; });
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