const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let identity;
function message(text,error=false){const el=$('#message');el.textContent=text;el.className='message'+(error?' error':'')}
async function api(path,body,method){const r=await fetch(path,{method:method||(body?'POST':'GET'),headers:{'Content-Type':'application/json','X-CSRF-Token':identity?.csrf_token||''},...(body?{body:JSON.stringify(body)}:{})});if(r.status===401){location.href='/login';throw Error('Sign in required')}const data=await r.json();if(!r.ok)throw Error(data.error);return data}
async function reauthenticate(){
  return new Promise(resolve=>{const d=document.createElement('dialog');d.innerHTML='<h2>Confirm your identity</h2><form><label>Password<input id="reauth-password" type="password" autocomplete="current-password" required maxlength="256"></label><p role="alert" id="reauth-error"></p><button>Confirm</button><button type="button" id="reauth-cancel">Cancel</button></form>';document.body.appendChild(d);const done=ok=>{d.close();d.remove();resolve(ok)};d.querySelector('#reauth-cancel').onclick=()=>done(false);d.oncancel=e=>{e.preventDefault();done(false)};d.querySelector('form').onsubmit=async e=>{e.preventDefault();try{await api('/api/auth/reauthenticate',{password:d.querySelector('input').value});d.querySelector('input').value='';done(true)}catch(e){d.querySelector('#reauth-error').textContent=e.message}};d.showModal();d.querySelector('input').focus()})
}
async function start(){identity=await api('/api/auth/me');if(identity.user.must_change_password){location.href='/login';return}if($('#admin-profile')){
 $('#profile-username').textContent=identity.user.username;
 const role=identity.user.effective_role||identity.user.role;
 $('#profile-role').textContent=({SYSTEM_ADMIN:'System Admin',security_admin:'System Admin'}[role]||'Authenticated account');
 document.querySelectorAll('[data-admin-permission]').forEach(link=>{link.hidden=!link.dataset.adminPermission.split(' ').every(p=>identity.permissions.includes(p));const target=new URL(link.href,location.origin);const active=target.pathname===location.pathname&&(target.pathname==='/admin/users'||target.hash===(location.hash||'#overview'));if(active&&!link.hidden)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current')});
 $('#admin-profile').addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();$('#admin-profile').open=false;$('#admin-profile summary').focus()}});
 document.addEventListener('click',e=>{if(!$('#admin-profile').contains(e.target))$('#admin-profile').open=false});
 $('#admin-nav-toggle').onclick=()=>{const open=$('#admin-sidebar').classList.toggle('mobile-open');$('#admin-nav-toggle').setAttribute('aria-expanded',String(open))};
}else if($('#who'))$('#who').textContent=identity.user.display_name+' · '+identity.user.role;$('#logout').onclick=async()=>{await api('/api/auth/logout',{});location.href='/login'};const security=$('#security-link');if(security)security.hidden=!identity.permissions.includes('manage_security');await load()}
const begin=()=>start().catch(e=>message(e.message,true));
if(document.readyState==='complete')begin();else document.addEventListener('DOMContentLoaded',begin,{once:true});
