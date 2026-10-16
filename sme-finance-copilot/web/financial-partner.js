/* Page-session chat; no transcript or approval is saved in browser storage. */
let partnerBusy=false,partnerMerchant=null,partnerPinned=true,partnerEpoch=0,partnerConversation=null,partnerStarting=null;
const partnerSuggestions=['How am I doing?','Show my sales trends','Show my payment channel mix','Any cash-flow insights?','What is revenue-based financing?','Can I afford a warehouse expansion?','Simulate sales decreasing by 20%, expenses unchanged for 3 months','Search current public SME lending rates','How do I import my Excel report?','How do I create a financing application?'];
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
function partnerForget(reference){
 if(reference)fetch('/api/partner/v2/close',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json','X-CSRF-Token':SESSION?.csrf_token||''},body:JSON.stringify({conversation:reference})}).catch(()=>{});
}
function partnerReset(){
 partnerForget(partnerConversation);partnerEpoch++;partnerConversation=null;partnerStarting=null;partnerBusy=false;partnerPinned=true;
 $('#chatlog').replaceChildren();$('#chatinput').value='';$('#partner-suggestions').open=true;partnerEmpty();partnerComposerState();
}
async function partnerStart(){
 if(partnerConversation)return partnerConversation;
 if(partnerStarting)return partnerStarting;
 const epoch=partnerEpoch,mid=M.id;
 const starting=api('/api/partner/v2/conversations',{method:'POST',body:JSON.stringify({merchant:mid})}).then(r=>{
  if(epoch!==partnerEpoch||M?.id!==mid){partnerForget(r.conversation);throw Error('Conversation changed')}
  partnerConversation=r.conversation;return r.conversation;
 }).finally(()=>{if(partnerStarting===starting)partnerStarting=null});
 partnerStarting=starting;return starting;
}
function partnerScope(){
 if(!M||!SESSION)return;
 if(typeof survivalScope==='function')survivalScope();
 const key=SESSION.user.user_id+'|'+M.id;
 if(partnerMerchant===key)return;
 partnerMerchant=key;partnerReset();
 if(can('use_copilot'))partnerStart().catch(()=>{});
}
function partnerModule(){
 partnerScope();$('#chips').replaceChildren();
 for(const question of partnerSuggestions){const button=document.createElement('button');button.type='button';button.className='chip';button.textContent=question;
  button.onclick=()=>{if(partnerBusy)return;$('#chatinput').value='';partnerSend(question)};$('#chips').appendChild(button)}
 partnerEmpty();
}
function partnerEvidence(container,r){
 const note=document.createElement('small');note.className='muted';
 note.textContent=r.connection_status==='live'?'Live provider · authorized backend tools':r.connection_status==='test_double'?'Test double · not live AI':r.connection_status==='fallback'?(r.provider_status==='temporarily_busy'?'AI service temporarily busy · deterministic guidance':r.fallback_reason==='timeout'?'Live request timed out · deterministic fallback':r.fallback_reason==='response_validation'?'Response could not be verified · deterministic fallback':'Live request failed · deterministic fallback'):'Deterministic guidance and backend results · not live AI';container.appendChild(document.createElement('br'));container.appendChild(note);
 if(r.tools_used?.length){const details=document.createElement('details'),summary=document.createElement('summary'),tools=document.createElement('p');details.className='muted';summary.textContent='Sources & tools';tools.textContent=r.tools_used.map(t=>t.replace(/_/g,' ')).join(', ');details.append(summary,tools);container.appendChild(details)}
 for(const source of r.sources||[]){
  const section=document.createElement('blockquote'),link=document.createElement('a');
  try{const u=new URL(source.source_url);if(u.protocol!=='https:')continue;link.href=u.href}catch{continue}
  link.textContent=source.source_title;link.target='_blank';link.rel='noopener noreferrer';section.appendChild(link);
  const date=document.createElement('p');date.textContent='Published: '+(source.publication_date||'Not supplied')+' · retrieved '+source.retrieved_at;section.appendChild(date);
  const quote=document.createElement('p');quote.textContent=source.excerpt;section.appendChild(quote);container.appendChild(section);
 }
 if(r.research?.available)partnerResearch(container,r.research);
}
function partnerResearch(container,proposal){
 const section=document.createElement('section');section.setAttribute('aria-label','Public research approval');
 for(const text of [proposal.purpose,'Exact query: '+proposal.exact_query,proposal.information_type,proposal.private_data_notice,'Single use · expires in '+proposal.expires_in_seconds+' seconds.']){const p=document.createElement('p');p.textContent=text;section.appendChild(p)}
 const epoch=partnerEpoch,mid=M.id,conversation=partnerConversation;
 for(const decision of ['approve','decline']){const button=document.createElement('button');button.type='button';button.className='btn ghost sm';button.textContent=decision==='approve'?'Approve exact search':'Decline';button.onclick=async()=>{
  if(epoch!==partnerEpoch||partnerBusy)return;
  section.querySelectorAll('button').forEach(b=>b.disabled=true);partnerBusy=true;partnerComposerState();
  try{const r=await api('/api/partner/v2/research',{method:'POST',body:JSON.stringify({merchant:mid,conversation,approval_reference:proposal.approval_reference,exact_query:proposal.exact_query,decision})});if(epoch!==partnerEpoch)return;partnerEvidence(addMsg(r.reply,'bot'),r)}
  catch{if(epoch===partnerEpoch)addMsg('Search approval is unavailable, expired or already used. No automatic retry was made.','bot')}
  finally{if(epoch===partnerEpoch){partnerBusy=false;partnerComposerState();partnerScroll(true)}}
 };section.appendChild(button)}container.appendChild(section);
}
function partnerRetry(node,text){
 if(!$('#chatinput').value.trim())$('#chatinput').value=text;
 const retry=document.createElement('button');retry.type='button';retry.className='btn ghost sm';retry.textContent='Retry question';
 retry.onclick=()=>{if(partnerBusy)return;$('#chatinput').value=text;partnerComposerState();$('#chatinput').focus()};node.appendChild(retry);
}
async function partnerSend(text){
 if(!text.trim()||partnerBusy||!M)return;
 partnerOpen(true);partnerScope();const mid=M.id,epoch=partnerEpoch;
 $('#partner-suggestions').open=false;partnerPinned=true;addMsg(text,'user');partnerScroll(true);partnerBusy=true;partnerComposerState();
 const pending=addMsg('Checking access and authorized sources…','bot');pending.dataset.partnerPending='true';
 const waiting=setTimeout(()=>{if(epoch===partnerEpoch&&pending.isConnected)pending.textContent='Still analyzing… You can keep this question open while I check authorized sources.'},10000);
 try{const conversation=await partnerStart();if(epoch!==partnerEpoch)return;
  const r=await api('/api/chat',{method:'POST',body:JSON.stringify({merchant:mid,conversation,message:text})});pending.remove();if(epoch!==partnerEpoch||M.id!==mid)return;
  const node=addMsg(r.reply,'bot');partnerEvidence(node,r);if(r.retry_available)partnerRetry(node,text);
 }catch{pending.remove();if(epoch===partnerEpoch)partnerRetry(addMsg('This answer is unavailable. Your question is kept below so you can retry.','bot'),text)}
 finally{clearTimeout(waiting);if(epoch===partnerEpoch){partnerBusy=false;partnerComposerState();partnerScroll()}}
}
window.addEventListener('pagehide',()=>{partnerForget(partnerConversation);partnerConversation=null;partnerEpoch++;$('#chatlog').replaceChildren()});
window.addEventListener('pageshow',event=>{if(event.persisted){partnerMerchant=null;partnerScope()}});

document.addEventListener('DOMContentLoaded',()=>{
 $('#ai-new').onclick=()=>{partnerReset();partnerStart().catch(()=>{});$('#chatinput').focus()};
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
