/* Shared presentation/controller only. Backend authorization remains authoritative. */
window.PortalNavigation={
 roleLabel(role){return ({owner:'SME Owner',SME_OWNER:'SME Owner',staff:'SME Staff',SME_STAFF:'SME Staff',lender_analyst:'Bank',BANK:'Bank',security_admin:'System Admin',SYSTEM_ADMIN:'System Admin'})[role]||'Authenticated account'},
 create({button,sidebar,menu,storageKey}){
  const mobile=matchMedia('(max-width:850px)');
  function saved(){try{return localStorage.getItem(storageKey)!=='false'}catch{return true}}
  function setOpen(open){document.body.classList.toggle('nav-collapsed',!open);button.setAttribute('aria-expanded',String(open));button.setAttribute('aria-label',(open?'Collapse':'Expand')+' navigation');button.title=(open?'Collapse':'Expand')+' navigation';menu.inert=mobile.matches&&!open;if(!mobile.matches)try{localStorage.setItem(storageKey,String(open))}catch{}}
  button.onclick=()=>setOpen(document.body.classList.contains('nav-collapsed'));
  menu.addEventListener('click',e=>{if(mobile.matches&&e.target.closest('a[href],button[data-tab]'))setOpen(false)});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&mobile.matches&&!document.body.classList.contains('nav-collapsed')){setOpen(false);button.focus()}});
  document.addEventListener('click',e=>{if(mobile.matches&&!sidebar.contains(e.target)&&!document.body.classList.contains('nav-collapsed'))setOpen(false)});
  mobile.addEventListener('change',()=>setOpen(mobile.matches?false:saved()));
  setOpen(mobile.matches?false:saved());
  return {setOpen,closeMobile(){if(mobile.matches)setOpen(false)},expandDesktop(){if(!mobile.matches)setOpen(true)}};
 }
};
