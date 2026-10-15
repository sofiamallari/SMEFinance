/* Persistent, merchant-scoped UI. Backend evidence and permissions remain authoritative. */
let partnerBusy=false,partnerMerchant=null,partnerPinned=true;

const partnerSuggestions=[...CHIPS,'How do I import my Excel report?','How do I record an expense?','How do I configure transaction currency?','How do I authorize a bank?','How do I create a financing application?','How do I import transactions?','How do I manage staff permissions?'];
function partnerEmpty(){const empty=!$('#chatlog .msg');$('#partner-welcome').hidden=!empty}
function partnerScroll(force=false){if(force||partnerPinned)requestAnimationFrame(()=>{$('#partner-conversation').scrollTop=$('#partner-conversation').scrollHeight})}
function partnerComposerState(){$('#chatform button').disabled=partnerBusy||!$('#chatinput').value.trim()}
function partnerOpen(open){
 document.body.classList.toggle('ai-collapsed',!open);$('#ai-toggle').setAttribute('aria-expanded',String(open));
 const narrow=matchMedia('(max-width:1100px)').matches;
 $('#partner-panel').setAttribute('role',narrow&&open?'dialog':'complementary');
 if(narrow&&open){$('#partner-panel').setAttribute('aria-modal','true');$('#chatinput').focus()}else $('#partner-panel').removeAttribute('aria-modal');
 $('#ai-backdrop').hidden=!(narrow&&open);
}
function partnerScope(){
 if(!M||!SESSION)return;
 if(typeof survivalScope==='function')survivalScope();
 const key=(SESSION.user?.user_id||SESSION.user?.username||'demo')+'|'+M.id;
 if(partnerMerchant===key)return;
 partnerMerchant=key;partnerPinned=true;$('#partner-suggestions').open=true;$('#chatinput').value='';partnerComposerState();
 $('#chatlog').replaceChildren();
 {
  const restoreKey=key;
  api('/api/partner/conversation?merchant='+encodeURIComponent(M.id)).then(result=>{
   if(partnerMerchant!==restoreKey||$('#chatlog .msg'))return;
   for(const message of result.messages||[])addMsg(message.content,message.role==='user'?'user':'bot');
   if(result.messages?.length){addMsg('Earlier conversation restored. Ask again to refresh financial findings and current permissions.','bot');$('#partner-suggestions').open=false}partnerEmpty();partnerScroll(true);
  }).catch(()=>{});
 }
 partnerEmpty();
}
function partnerModule(tab){
 partnerScope();
 $('#chips').replaceChildren();
 for(const question of partnerSuggestions){const button=document.createElement('button');button.type='button';button.className='chip';button.textContent=question;
  // Same explain/read request path as typed questions; never action confirmation.
  button.onclick=()=>{if(partnerBusy)return;$('#chatinput').value='';partnerSend(question)};$('#chips').appendChild(button)}
 partnerEmpty();
}
function partnerEvidence(container,r){
 if(r.classification==='APPLICATION_GUIDANCE'){const note=document.createElement('small');note.textContent='Application guide · maintained help content';container.appendChild(document.createElement('br'));container.appendChild(note)}
 if(r.connection_status==='fallback'){const note=document.createElement('p');note.textContent='Live assistance is unavailable. Showing verified backend results where available.';container.appendChild(note)}
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
 }catch(error){addMsg('The action could not be completed. Review it in the source module before trying again.','bot');button.disabled=false}
}
async function partnerSend(text,token){
 if(!text.trim()||partnerBusy||!M)return;
 if(!token&&typeof survivalOffer==='function'&&survivalOffer(text))return;
 partnerOpen(true);partnerScope();const mid=M.id,scope=partnerMerchant;
 $('#partner-suggestions').open=false;partnerPinned=true;if(!token)addMsg(text,'user');partnerScroll(true);partnerBusy=true;partnerComposerState();
 const pending=addMsg('Retrieving authorized evidence and checking financial claims…','bot');pending.dataset.partnerPending='true';
 try{const r=await api('/api/chat',{method:'POST',body:JSON.stringify({merchant:mid,message:text,module:active(),explain_actions:true,approval_token:token})});pending.remove();if(M.id!==mid||partnerMerchant!==scope)return;
  const node=addMsg(r.reply,'bot');partnerEvidence(node,r);
  if(r.data?.action){const action=r.data.action;const p=document.createElement('p');p.textContent='Review: '+action.kind.replace(/_/g,' ')+' · '+fmt(action.parameters.amount,M.currency)+' · '+(action.parameters.method||action.parameters.product_id)+' · expires '+new Date(action.expires_at*1000).toLocaleTimeString();node.appendChild(p);const b=document.createElement('button');b.className='btn sm';b.textContent='Confirm exact simulated action';b.onclick=()=>partnerConfirm(action,b);node.appendChild(b)}
  }catch(error){pending.remove();if(M.id===mid&&partnerMerchant===scope){const node=addMsg('Unable to retrieve this answer. Check your access and connection, then try again.','bot');const retry=document.createElement('button');retry.type='button';retry.className='btn ghost sm';retry.textContent='Retry question';retry.onclick=()=>{retry.disabled=true;partnerSend(text)};if(!token)node.appendChild(retry)}}
 finally{partnerBusy=false;partnerComposerState();partnerScroll()}
}
document.addEventListener('DOMContentLoaded',()=>{
 send=partnerSend;$('#chatform').onsubmit=e=>{e.preventDefault();const value=$('#chatinput').value;if(partnerBusy||!value.trim())return;$('#chatinput').value='';send(value)};
 $('#chatinput').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('#chatform').requestSubmit()}});
 $('#partner-suggestions').addEventListener('toggle',()=>{if($('#partner-suggestions').open)$('#chips').scrollTop=0});
 $('#chatinput').addEventListener('input',partnerComposerState);
 $('#partner-conversation').addEventListener('scroll',()=>{const box=$('#partner-conversation');partnerPinned=box.scrollHeight-box.scrollTop-box.clientHeight<60},{passive:true});
 const fitViewport=()=>{const viewport=window.visualViewport;$('#partner-panel').style.height=(viewport?viewport.height:innerHeight)+'px';$('#partner-panel').style.top=(viewport?viewport.offsetTop:0)+'px'};fitViewport();window.addEventListener('resize',fitViewport);window.visualViewport?.addEventListener('resize',fitViewport);window.visualViewport?.addEventListener('scroll',fitViewport);partnerComposerState();
 const originalApi=api;let automaticPeriod=true;
 $('#dstart').addEventListener('input',()=>automaticPeriod=false);$('#dend').addEventListener('input',()=>automaticPeriod=false);
 api=async(path,options={})=>{const result=await originalApi(path,options);if(options.method==='POST'&&result.ok!==false&&result.valid!==false&&(/\/api\/(?:pos-import\/.*\/commit|merchant-transactions\/entry|transactions\/(?:entry|import|manage)|payments\/pay)$/.test(path)||path==='/api/partner/actions/confirm')){
   const changedMerchant=JSON.parse(options.body||'{}').merchant;if(!M||changedMerchant!==M.id)return result;
   if(typeof survivalInvalidate==='function')survivalInvalidate();
   if(automaticPeriod){$('#dstart').value='';$('#dend').value=''}
   if(M&&active()==='dashboard')loadDashboard();
   if(!$('#chatlog [data-stale-notice]')){const notice=addMsg('Business data changed. Ask again to refresh earlier financial findings.','bot');notice.dataset.staleNotice='true'}
  }return result};
 $('#ai-toggle').onclick=()=>{partnerOpen(true);$('#chatinput').focus()};$('#ai-close').onclick=()=>{partnerOpen(false);$('#ai-toggle').focus()};$('#ai-backdrop').onclick=()=>partnerOpen(false);
 $('#financing-parent').onclick=()=>{ownerNavigation.expandDesktop();const open=$('#financing-submenu').hidden;$('#financing-submenu').hidden=!open;$('#financing-parent').setAttribute('aria-expanded',String(open))};
 document.addEventListener('keydown',event=>{if(document.querySelector('dialog[open]'))return;if(event.key==='Tab'&&matchMedia('(max-width:1100px)').matches&&!document.body.classList.contains('ai-collapsed')){const nodes=[...$('#partner-panel').querySelectorAll('button:not(:disabled),input,textarea,summary')].filter(node=>node.offsetParent!==null);if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes.at(-1).focus()}else if(!event.shiftKey&&document.activeElement===nodes.at(-1)){event.preventDefault();nodes[0].focus()}}if(event.key==='Escape'&&!document.body.classList.contains('ai-collapsed')){partnerOpen(false);$('#ai-toggle').focus()}});
 partnerOpen(!matchMedia('(max-width:1100px)').matches);
 const drawerMedia=matchMedia('(max-width:1100px)');drawerMedia.addEventListener('change',event=>partnerOpen(!event.matches));

},{once:true});
