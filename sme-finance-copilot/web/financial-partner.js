/* Persistent, merchant-scoped UI. Backend evidence and permissions remain authoritative. */
let partnerBusy=false,partnerMerchant=null;
const partnerThreads=new Map();
const moduleQuestions={dashboard:['Show recorded sales this month','Why did revenue change?'],transactions:['How do I upload a POS file?','Show recorded expenses'],'pos-import':['How do I upload a POS file?','Are there duplicate or unreconciled records?'],'transaction-history':['Show recorded sales this month','Show recorded refunds'],'data-quality':['Are there duplicate or unreconciled records?'],payments:['What happened to my latest simulated payment?','Explain cash balance versus revenue'],cashflow:['Show cash flow forecast','What is my cash buffer?'],financing:['What financing fits my business?','Quote RBF advance 10000000'],rbf:['How much can I borrow with RBF?','Explain revenue-based financing'],applications:['What is the status of my simulated application?']};
function partnerOpen(open){
 document.body.classList.toggle('ai-collapsed',!open);$('#ai-toggle').setAttribute('aria-expanded',String(open));
 const narrow=matchMedia('(max-width:1100px)').matches;
 $('#partner-panel').setAttribute('role',narrow&&open?'dialog':'complementary');
 if(narrow&&open){$('#partner-panel').setAttribute('aria-modal','true');$('#chatinput').focus()}else $('#partner-panel').removeAttribute('aria-modal');
 $('#ai-backdrop').hidden=!(narrow&&open);
}
function partnerScope(){
 if(!M||!SESSION)return;
 const key=(SESSION.user?.user_id||SESSION.user?.username||'demo')+'|'+M.id;
 if(partnerMerchant===key)return;
 if(partnerMerchant){const copy=$('#chatlog').cloneNode(true);copy.querySelectorAll('[data-partner-pending]').forEach(node=>node.remove());copy.querySelectorAll('button').forEach(button=>{button.disabled=true;button.textContent='Request a fresh action proposal'});partnerThreads.set(partnerMerchant,copy)}
 partnerMerchant=key;
 const saved=partnerThreads.get(key);$('#chatlog').replaceChildren();
 if(saved)for(const child of [...saved.childNodes])$('#chatlog').appendChild(child);
 else addMsg('Ask about '+M.name+'\'s recorded transactions, payments, cash flow or financing. Financial amounts are verified by the backend.','bot');
 $('#modebadge').textContent=AGENT==='ai_agent'?'Gemini configured · not yet verified':'Deterministic mode';
}
function partnerModule(tab){
 partnerScope();
 let questions=moduleQuestions[tab]||moduleQuestions.dashboard;
 if(['financing','rbf','applications'].includes(tab)&&!can('view_financing'))questions=moduleQuestions.dashboard;
 $('#chips').replaceChildren();
 for(const question of questions){const b=document.createElement('button');b.className='chip';b.textContent=question;b.onclick=()=>send(question);$('#chips').appendChild(b)}
 $('#partner-module').textContent=({payments:'Digital Payments','pos-import':'Bulk POS Import',rbf:'RBF Calculator',cashflow:'Cash Flow','transaction-history':'Transaction History','data-quality':'Data Quality & Monitoring'}[tab]||tab.replace(/-/g,' '));
}
function partnerEvidence(container,r){
 const trace=document.createElement('span');trace.className='trace';
 trace.textContent=(r.classification||'Advisory')+' · '+(r.connection_status==='connected'?'Gemini response validated':r.connection_status==='fallback'?'Deterministic fallback':'Backend response')+' · Tools: '+((r.tools_used||r.data?.tools_used||[]).join(', ')||'none');container.appendChild(trace);
 if(r.evidence?.length){
  const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Evidence, period and limitations';details.appendChild(summary);
  for(const f of r.evidence){const line=document.createElement('p');line.className='muted';line.textContent=f.metric.replace(/_/g,' ')+': '+f.value+(f.currency?' '+f.currency:'')+' · '+f.status+' · '+f.provenance.replace(/_/g,' ')+' · '+f.period_start+' to '+f.period_end+' · '+f.source.replace(/_/g,' ')+' · retrieved '+new Date(f.as_of).toLocaleString();details.appendChild(line)}
  const limits=[...new Set(r.evidence.flatMap(f=>[...(f.limitations||[]),...(f.assumptions||[])]))];
  for(const limit of limits){const p=document.createElement('p');p.className='muted';p.textContent=limit;details.appendChild(p)}
  container.appendChild(details);
 }
}
async function partnerConfirm(action,button){
 const mid=M.id;button.disabled=true;
 try{const result=await api('/api/partner/actions/confirm',{method:'POST',body:JSON.stringify({merchant:mid,action_id:action.action_id,confirmed:true})});
  if(M.id!==mid)return;
  addMsg('Confirmed simulated action: '+(result.result?.ref||result.result?.application_id||result.action_id)+' · '+(result.result?.status||result.state)+'. No real funds moved and no lender approval was granted.','bot');
  if(active()==='applications')loadApplications();if(active()==='payments')loadPayments();
 }catch(error){addMsg(error.message,'bot');button.disabled=false}
}
async function partnerSend(text,token){
 if(!text.trim()||partnerBusy||!M)return;
 partnerOpen(true);partnerScope();const mid=M.id;
 if(!token)addMsg(text,'user');partnerBusy=true;$('#chatform button').disabled=true;
 const pending=addMsg('Retrieving authorized evidence and checking financial claims…','bot');pending.dataset.partnerPending='true';
 try{const r=await api('/api/chat',{method:'POST',body:JSON.stringify({merchant:mid,message:text,module:active(),approval_token:token})});pending.remove();if(M.id!==mid)return;
  const node=addMsg(r.reply,'bot');partnerEvidence(node,r);
  $('#modebadge').textContent=r.connection_status==='connected'?'Gemini verified':r.connection_status==='fallback'?'Fallback · verified backend data':r.mode==='ai_agent'?'Gemini verified':'Deterministic mode';
  if(r.data?.action){const action=r.data.action;const p=document.createElement('p');p.textContent='Review: '+action.kind.replace(/_/g,' ')+' · '+action.parameters.amount+' '+M.currency+' · '+(action.parameters.method||action.parameters.product_id)+' · expires '+new Date(action.expires_at*1000).toLocaleTimeString();node.appendChild(p);const b=document.createElement('button');b.className='btn sm';b.textContent='Confirm exact simulated action';b.onclick=()=>partnerConfirm(action,b);node.appendChild(b)}
 }catch(error){pending.remove();if(M.id===mid)addMsg(error.message,'bot')}
 finally{partnerBusy=false;$('#chatform button').disabled=false;$('#chatlog').scrollTop=1e9}
}
document.addEventListener('DOMContentLoaded',()=>{
 send=partnerSend;$('#chatform').onsubmit=e=>{e.preventDefault();const value=$('#chatinput').value;$('#chatinput').value='';send(value)};
 const originalApi=api;let automaticPeriod=true;
 $('#dstart').addEventListener('input',()=>automaticPeriod=false);$('#dend').addEventListener('input',()=>automaticPeriod=false);
 api=async(path,options={})=>{const result=await originalApi(path,options);if(options.method==='POST'&&result.ok!==false&&result.valid!==false&&(/\/api\/(?:pos-import\/.*\/commit|merchant-transactions\/entry|transactions\/(?:entry|import|manage)|payments\/pay)$/.test(path)||path==='/api/partner/actions/confirm')){
   const changedMerchant=JSON.parse(options.body||'{}').merchant;if(!M||changedMerchant!==M.id)return result;
   if(automaticPeriod){$('#dstart').value='';$('#dend').value=''}
   if(M&&active()==='dashboard')loadDashboard();
   if(!$('#chatlog [data-stale-notice]')){const notice=addMsg('Business data changed. Ask again to refresh earlier financial findings.','bot');notice.dataset.staleNotice='true'}
  }return result};
 $('#ai-toggle').onclick=()=>partnerOpen(document.body.classList.contains('ai-collapsed'));$('#ai-close').onclick=()=>{partnerOpen(false);$('#ai-toggle').focus()};$('#ai-backdrop').onclick=()=>partnerOpen(false);
 $('#financing-parent').onclick=()=>{const open=$('#financing-submenu').hidden;$('#financing-submenu').hidden=!open;$('#financing-parent').setAttribute('aria-expanded',String(open))};
 document.addEventListener('keydown',event=>{if(event.key==='Tab'&&matchMedia('(max-width:1100px)').matches&&!document.body.classList.contains('ai-collapsed')){const nodes=[...$('#partner-panel').querySelectorAll('button:not(:disabled),input,summary')].filter(node=>node.offsetParent!==null);if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes.at(-1).focus()}else if(!event.shiftKey&&document.activeElement===nodes.at(-1)){event.preventDefault();nodes[0].focus()}}if(event.key==='Escape'&&!document.body.classList.contains('ai-collapsed')){partnerOpen(false);$('#ai-toggle').focus()}});
 partnerOpen(!matchMedia('(max-width:1100px)').matches);
 const drawerMedia=matchMedia('(max-width:1100px)');drawerMedia.addEventListener('change',event=>partnerOpen(!event.matches));
 window.addEventListener('resize',()=>partnerOpen(!document.body.classList.contains('ai-collapsed')));
},{once:true});
