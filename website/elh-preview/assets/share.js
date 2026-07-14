(function () {
  function pageUrl(btn) {
    var c = document.querySelector('link[rel="canonical"]');
    return btn.getAttribute('data-url') || (c && c.href) || location.href;
  }
  function toast(msg) {
    var t = document.getElementById('shareToast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'shareToast';
      t.className = 'share-toast';
      t.setAttribute('role', 'status');
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._tid);
    t._tid = setTimeout(function () { t.classList.remove('show'); }, 2400);
  }
  function copyLink(url) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () { toast('Link copied \u2014 ready to paste'); })
        .catch(function () { window.prompt('Copy this link:', url); });
    } else {
      window.prompt('Copy this link:', url);
    }
  }
  if (navigator.share) {
    document.querySelectorAll('.share-native').forEach(function (b) { b.hidden = false; });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('[data-share]') : null;
    if (!b) return;
    var kind = b.getAttribute('data-share');
    var url = pageUrl(b);
    if (kind === 'copy') {
      e.preventDefault();
      copyLink(url);
    } else if (kind === 'native') {
      e.preventDefault();
      if (navigator.share) {
        navigator.share({ title: document.title, url: url }).catch(function (err) {
          if (!err || err.name !== 'AbortError') copyLink(url);
        });
      } else {
        copyLink(url);
      }
    }
  });
})();
