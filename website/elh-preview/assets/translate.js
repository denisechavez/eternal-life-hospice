document.querySelectorAll('.ft-lang').forEach(function(a){
  a.href='https://translate.google.com/translate?sl=en&tl='+a.dataset.lang+'&u='+encodeURIComponent(location.href);
  a.target='_blank';a.rel='noopener';
});
