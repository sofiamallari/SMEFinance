/* Enhance existing controls in place: handlers, values and authorization stay owned by their modules. */
(()=>{'use strict';
const paths={trash:'M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7',view:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6',edit:'m4 16-1 5 5-1L21 7l-4-4Z M14 6l4 4',refresh:'M20 7v5h-5 M20 12a8 8 0 1 0-2 6',history:'M3 4v6h6 M3 10a9 9 0 1 1 1 8 M12 7v5l3 2',download:'M12 3v12 m-5-5 5 5 5-5 M4 16v5h16v-5'};
function enhance(root){for(const b of root.querySelectorAll('button')){const label=b.textContent.trim();if(/^(Cancel|Back|Close|Back to .+)$/i.test(label))b.classList.add('ui-secondary');if(/^(Deny|Reject|Delete)(?:$|[ ·])/i.test(label))b.classList.add('ui-danger')}for(const b of root.querySelectorAll('td button,td a')){
 if(b.dataset.uiEnhanced)continue;const text=b.textContent.trim().replace(/\s+/g,' ');let type;
 if(b.hasAttribute('data-user-remove'))type='trash';
 else if(/^(view|view details|view application|view summary)$/i.test(text))type='view';
 else if(/^edit$/i.test(text))type='edit';else if(/^refresh$/i.test(text))type='refresh';
 else if(/^(view history|authorization history|view authorization \/ history)$/i.test(text))type='history';
 else if(/^(download|download csv)$/i.test(text))type='download';
 if(type){b.dataset.uiEnhanced='icon';b.setAttribute('aria-label',b.getAttribute('aria-label')||text);b.title=b.title||text;b.classList.add('ui-icon-action');if(type==='trash'){b.classList.add('ui-trash-action');b.setAttribute('aria-label','Remove business association');b.title='Remove business association'};b.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="'+paths[type]+'"/></svg>';b.closest('td').classList.add('ui-actions')}
 else if(/^(remove|remove association|delete)$/i.test(text)&&!b.closest('.ui-more')){b.dataset.uiEnhanced='more';const d=document.createElement('details'),s=document.createElement('summary');d.className='ui-more';s.textContent='⋯';s.setAttribute('aria-label','More actions');s.title='More actions';b.before(d);d.append(s,b);b.closest('td').classList.add('ui-actions')}
 }
}
document.addEventListener('keydown',e=>{
 if(e.defaultPrevented)return;
 const tab=e.target.closest('[role=tab]'),list=tab?.closest('[role=tablist]');
 if(list&&['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){
  const tabs=[...list.querySelectorAll('[role=tab]')].filter(b=>!b.disabled),i=tabs.indexOf(tab);
  const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowLeft'?-1:1)+tabs.length)%tabs.length;
  if(tabs[next]){e.preventDefault();tabs[next].click();if(tabs[next].getAttribute('aria-selected')==='true')tabs[next].focus()}
 }
 if(e.key==='Escape'){const menu=e.target.closest('.ui-more[open]');if(menu){e.preventDefault();menu.open=false;menu.querySelector('summary').focus();e.stopPropagation()}}
});
let scheduled=false;const schedule=()=>{if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;enhance(document)})};
const start=()=>{enhance(document);new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true})};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
