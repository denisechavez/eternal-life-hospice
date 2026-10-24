(function(){
  var nav=document.getElementById('site-nav');
  var service=nav&&nav.querySelector('.nav-group[data-section="services"]');
  if(!service)return;
  var toggles=Array.prototype.slice.call(service.querySelectorAll('.sp-group-toggle'));
  if(!toggles.length)return;
  var mobile=window.matchMedia('(max-width: 999px)');
  var panel=service.querySelector('.sp-mega');
  function positionPanel(){
    if(!panel||mobile.matches){if(panel)panel.style.left='';return;}
    var anchor=service.getBoundingClientRect();
    var width=panel.getBoundingClientRect().width;
    var min=16-anchor.left;
    var max=window.innerWidth-16-width-anchor.left;
    var centered=(window.innerWidth-width)/2-anchor.left;
    panel.style.left=Math.max(min,Math.min(max,centered))+'px';
  }
  function setOpen(button,open){
    var panel=document.getElementById(button.getAttribute('aria-controls'));
    button.setAttribute('aria-expanded',open?'true':'false');
    if(panel)panel.classList.toggle('is-open',open&&mobile.matches);
  }
  function reset(){
    toggles.forEach(function(button){setOpen(button,false);});
    positionPanel();
  }
  toggles.forEach(function(button){
    button.addEventListener('click',function(event){
      event.preventDefault();
      event.stopPropagation();
      if(!mobile.matches)return;
      var wasOpen=button.getAttribute('aria-expanded')==='true';
      reset();
      if(!wasOpen)setOpen(button,true);
    });
    button.addEventListener('keydown',function(event){
      if(event.key==='Escape'&&button.getAttribute('aria-expanded')==='true'){
        event.preventDefault();event.stopPropagation();setOpen(button,false);button.focus();
      }
    });
  });
  if(mobile.addEventListener)mobile.addEventListener('change',reset);
  else if(mobile.addListener)mobile.addListener(reset);
  reset();
  window.addEventListener('resize',positionPanel,{passive:true});
})();
