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
})();
