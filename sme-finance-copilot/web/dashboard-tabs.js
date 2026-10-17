/* POC dashboard composition. Existing services and chart renderers remain authoritative. */
let dashboardRequest=0,growthRequest=0,alertRequest=0,dashboardAssessment=null,dashboardAssessmentPromise=null;
let dashboardPane='overview',businessAlertsLoaded=false;
const maturityStages=['Survival Borrower','Striving Amateur','Steady Upgrader','Opportunity Seizer','Expanding Proprietor','Heir Seeker'];
const dimensionLabel=name=>name.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
function resetDashboardContext(){
 dashboardSnapshot=null;$('#export-overview').disabled=true;$('#export-status').textContent='';$('#dashboard-partial-period').hidden=true;$('#dashboard-partial-period').textContent='';closeBusinessNotifications();['cf-kpis','cf-chart','cf-ar-buckets','cf-ar-table','cf-ap-buckets','cf-ap-table'].forEach(id=>$('#'+id)?.replaceChildren());if($('#cf-status'))$('#cf-status').textContent='';cashflowLoadedFor=null;dashboardRequest++;growthRequest++;alertRequest++;dashboardAssessment=null;dashboardAssessmentPromise=null;businessAlertsLoaded=false;businessAlertRows=[];dismissedBusinessAlerts.clear();businessAlertsRetrieved=null;businessAlertState={page:1,size:3,severity:'all'};revenueTableState={page:1,size:10,context:''};
 for(const id of ['dkpis','dvol','drev','overview-volume','overview-revenue','dvoltrend','drevtrend','business-growth','business-alerts','financing-readiness','channel-performance','dashboard-provenance','dashboard-limitations','matches','rbfelig','rbfsummary','rbfdays','rbfcmp'])$('#'+id)?.replaceChildren();
 $('#business-growth').textContent='Open Business Growth to load the current assessment.';$('#business-alerts').textContent='Open Alerts to load the available business alerts.';
}
function selectDashboardPane(name){
 if(!['overview','cashflow','survival'].includes(name))name='overview';dashboardPane=name;
 $$('[data-dashboard-tab]').forEach(b=>{const selected=b.dataset.dashboardTab===name;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;b.classList.toggle('active',selected)});
 $$('[data-dashboard-pane]').forEach(panel=>panel.hidden=panel.dataset.dashboardPane!==name);
 $('#dashboard-reporting').hidden=name!=='overview';$('#overview-export-row').hidden=name!=='overview';
 dashboardIntegratedPane(name);
}
async function assessmentForMerchant(){
 const mid=M.id;
 if(dashboardAssessment?.merchant_id===mid)return dashboardAssessment;
 if(dashboardAssessmentPromise?.mid===mid)return dashboardAssessmentPromise.promise;
 const promise=api('/api/assessment?merchant='+encodeURIComponent(mid)).then(r=>{
  const assessment=r;if(M?.id!==mid||assessment.merchant_id!==mid)throw Error('Merchant changed.');
  dashboardAssessment=assessment;return assessment;
 }).finally(()=>{if(dashboardAssessmentPromise?.mid===mid)dashboardAssessmentPromise=null});
 dashboardAssessmentPromise={mid,promise};return promise;
}
async function loadBusinessGrowth(){
 const mid=M.id,request=++growthRequest,box=$('#business-growth');box.textContent='Loading current maturity assessment…';
 if(!can('view_assessment')){box.textContent='Business maturity assessment is not delegated to this account.';return}
 try{const a=await assessmentForMerchant();if(M.id!==mid||request!==growthRequest)return;
  const gap=a.next_stage;
  box.innerHTML='<p><b>Stage '+a.stage+': '+esc(a.stage_name)+'</b> <span class="pill">Composite '+esc(a.composite_score)+'/100</span></p><div class="stages" aria-label="Six business maturity stages">'+maturityStages.map((name,i)=>'<div class="stage '+(i+1===a.stage?'on':i+1<a.stage?'done':'')+'" '+(i+1===a.stage?'aria-current="step"':'')+'>'+String(i+1)+'. '+esc(name)+'</div>').join('')+'</div><div class="maturity-dimensions">'+Object.entries(a.scores).map(([name,value])=>'<div class="maturity-dimension"><div class="row"><span>'+esc(dimensionLabel(name))+'</span><b>'+esc(value)+'/100</b></div><div class="bar" role="progressbar" aria-label="'+esc(dimensionLabel(name))+'" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+esc(value)+'"><span style="width:'+Number(value)+'%"></span></div></div>').join('')+'</div>'+nextMaturityCard(a)+growthPriorityCard(a)+'<details><summary>Assessment Details</summary><p>Source: canonical assess_business service · as of '+esc(a.as_of)+'. Independent of the historical reporting-period filter.</p><p>'+esc(a.note)+'</p><p>Inputs include configured synthetic business attributes and canonical recorded transactions. Maturity weights and thresholds remain provisional POC rules; this is not credit approval.</p><p>Advancement guidance: '+esc(a.graduation_trigger)+'</p></details>';
 }catch(error){if(M.id===mid&&request===growthRequest)box.textContent='Maturity assessment could not be loaded. Retry by selecting Business Growth.'}
}
async function loadBusinessAlerts(){
 if(businessAlertsLoaded)return;
 const mid=M.id,request=++alertRequest,box=$('#business-alerts');box.textContent='Loading notifications…';
 if(!can('view_forecasts')){box.textContent='Business alerts are not delegated to this account.';return}
 try{const response=await api('/api/business-alerts?merchant='+encodeURIComponent(mid));
  if(M.id!==mid||request!==alertRequest)return;
  businessAlertRows=response.items;dismissedBusinessAlerts.clear();businessAlertsRetrieved=new Date();
  if(!businessAlertRows.some(a=>a.severity===businessAlertState.severity))businessAlertState.severity='all';
  businessAlertState.page=1;businessAlertsLoaded=true;renderCompactBusinessAlerts();
 }catch(error){if(M.id===mid&&request===alertRequest)box.textContent='Notifications could not be loaded. Close and reopen to try again.'}
}
// Dashboard cache: the last result for each business and period is kept for this browser tab (sessionStorage, cleared
// on sign-out or when the tab closes). It is shown at once, then refreshed quietly; imports and new entries clear it.
const DASH_CACHE='dash-cache:';
function dashboardCacheKey(mid,s,e,g){return DASH_CACHE+mid+'|'+s+'|'+e+'|'+g}
function dashboardCacheGet(key){try{return JSON.parse(sessionStorage.getItem(key)||'null')}catch{return null}}
function dashboardCachePut(key,d){try{sessionStorage.setItem(key,JSON.stringify(d))}catch{}}
function invalidateDashboardCache(){dashboardSnapshot=null;try{Object.keys(sessionStorage).filter(k=>k.startsWith(DASH_CACHE)).forEach(k=>sessionStorage.removeItem(k))}catch{}}
async function loadDashboard(){
 $('#export-overview').disabled=true;const mid=M.id,request=++dashboardRequest,s=$('#dstart').value,e=$('#dend').value,g=$('#dgran').value;$('#derr').textContent='';
 if(dashboardSnapshot&&dashboardSnapshot.merchant.id===mid&&dashboardSnapshot.period.start===s&&dashboardSnapshot.period.end===e&&dashboardSnapshot.period.granularity===g){$('#export-overview').disabled=false;return}
 if(s&&e&&s>e){$('#derr').textContent='Start date must be on or before end date.';return}
 const key=dashboardCacheKey(mid,s,e,g),cached=dashboardCacheGet(key);
 if(cached?.merchant?.id===mid)renderDashboardData(cached,s);
 const d=await api('/api/dashboard'+q('&granularity='+g+(s?'&start='+s:'')+(e?'&end='+e:'')),cached?{quiet:true}:{});
 if(M.id!==mid||request!==dashboardRequest)return;
 dashboardCachePut(key,d);if(!s)dashboardCachePut(dashboardCacheKey(mid,d.period.start,d.period.end,g),d);
 if(cached&&JSON.stringify(cached)===JSON.stringify(d)){dashboardSnapshot=d;return}
 renderDashboardData(d,s);
}
function renderDashboardData(d,s){
 if(!s&&!$('#dstart').value){$('#dstart').value=d.period.start;$('#dend').value=d.period.end}
 dashboardSnapshot=d;const f=d.financial_metrics,inc=d.incentive;
 $('#dashboard-empty').hidden=f?.record_count!==0;$('#dashboard-empty').textContent='No completed transaction records for this period. Actual business revenue is unknown.';
 $('#dkpis').innerHTML=averageCard('Average Revenue',f?.net_sales,d.period_length,'Recorded net sales ÷ months, weeks or days in the period')+averageCard('Average Expense',f?.expenses,d.period_length,'Recorded expenses ÷ months, weeks or days in the period')+[['Net Income',fmt(f?.net_income),'Authoritative canonical net income'],['Digital Capture',pct(d.capture.digital_share),'Own rails '+pct(d.capture.ecosystem_share)+' · cash '+pct(d.capture.cash_share)]].map(([name,value,note])=>'<div class="card"><div class="muted">'+name+'</div><div class="kpi">'+value+'</div><p class="muted">'+esc(note)+'</p></div>').join('');
 const channels=Object.values(d.mix.by_channel),volume=donut(channels.map(c=>c.volume_share),channels.map(c=>c.label),d.mix.total_transactions.toLocaleString()+'<br><small>txns</small>'),revenue=donut(channels.map(c=>c.revenue_share),channels.map(c=>c.label),short(d.mix.gross_revenue)+'<br><small>net</small>');
 for(const id of ['overview-volume'])$('#'+id).innerHTML=volume;for(const id of ['overview-revenue'])$('#'+id).innerHTML=revenue;
 $('#channel-performance').innerHTML=ChannelPerformance.render(d.channel_performance);
 const trendOpen=$('#dashboard-trend-values')?.open;$('#dvoltrend').innerHTML=bars(d.trend.map(t=>t.period),d.trend.map(t=>t.transactions),'vol');$('#drevtrend').innerHTML=financialTrend(d.trend,d.merchant.currency,trendAverages(d));renderExpenseSplit(d);renderRevenueValues(d,trendOpen);
 $('#dashboard-trend-period').textContent=d.period.start+' to '+d.period.end+' · '+d.period.granularity+' · '+d.merchant.currency;
 const periodNote=overviewPartialPeriod(d.period);$('#dashboard-partial-period').textContent=periodNote;$('#dashboard-partial-period').hidden=!periodNote;
 $('#export-overview').disabled=false;
}
const existingLoadFinancing=loadFinancing;
loadFinancing=async function(){const mid=M.id;const promise=existingLoadFinancing();if(can('view_assessment'))assessmentForMerchant().then(a=>{if(M.id===mid)$('#financing-readiness').textContent='Business maturity: '+a.stage_name+' · Composite '+a.composite_score+'/100 · Credit readiness '+a.scores.credit_readiness+'/100 · as of '+a.as_of+'. Indicative business assessment, not credit eligibility or approval.'}).catch(()=>{if(M.id===mid)$('#financing-readiness').textContent='Maturity summary unavailable for this account or data.'});else $('#financing-readiness').textContent='Maturity summary is not delegated to this account.';return promise};
document.addEventListener('DOMContentLoaded',()=>{
 $$('[data-dashboard-tab]').forEach(button=>{button.onclick=()=>selectDashboardPane(button.dataset.dashboardTab);button.onkeydown=event=>{const buttons=$$('[data-dashboard-tab]'),index=buttons.indexOf(button);let next;if(event.key==='ArrowRight')next=(index+1)%buttons.length;if(event.key==='ArrowLeft')next=(index+buttons.length-1)%buttons.length;if(event.key==='Home')next=0;if(event.key==='End')next=buttons.length-1;if(next!==undefined){event.preventDefault();buttons[next].click();buttons[next].focus()}}});
 $('#refresh-growth').onclick=()=>{dashboardAssessment=null;dashboardAssessmentPromise=null;loadBusinessGrowth()};
 selectDashboardPane('overview');
},{once:true});

let revenueTableState={page:1,size:10,context:''};
const dismissedBusinessAlerts=new Set();
let businessAlertRows=[],businessAlertState={page:1,size:3,severity:'all'},businessAlertsRetrieved=null;
function nextMaturityCard(a){
 const gap=a.next_stage;if(!gap)return '<section class="growth-next-card"><h3>Next Maturity Stage</h3><p>'+esc(a.stage>=6?'Highest maturity stage reached.':'No numeric next-stage target supplied by this assessment.')+'</p><small>'+esc(a.graduation_trigger||'Assessment data is unavailable.')+'</small></section>';
 const gates=Object.entries(gap.dimension_gaps||{}).sort((a,b)=>b[1]-a[1]),gate=gates[0];
 return '<section class="growth-next-card"><h3>Next Maturity Stage</h3><p class="growth-stage-transition">Stage '+esc(a.stage)+' → Stage '+esc(gap.target_stage)+'</p><strong>'+esc(gap.target_name)+'</strong><div class="growth-target-grid"><div><small>Composite threshold</small><b>'+esc(gap.composite_needed)+'/100</b></div><div><small>Composite gap</small><b>'+esc(gap.composite_gap)+' points needed</b></div></div>'+(gate?'<div class="growth-gate"><small>Largest unmet dimension gate</small><strong>'+esc(dimensionLabel(gate[0]))+'</strong><span>Current: '+esc(a.scores[gate[0]])+'/100 · '+esc(gate[1])+' points below the required gate</span></div>':'<p class="muted">No unmet dimension gate returned.</p>')+'<small class="muted">Composite threshold and all required gates apply together; threshold alone does not guarantee advancement.</small></section>';
}
function growthPriorityCard(a){const priorities=a.constraints||[],primary=priorities[0];const item=c=>'<strong>'+esc(dimensionLabel(c.constraint))+'</strong><p>'+esc(c.evidence)+'</p>'+(c.intervention?'<p><b>Explore:</b> '+esc(c.intervention)+'</p>':'');return '<section class="growth-priority"><h3>Recommended Next Step</h3>'+(primary?item(primary):'<p class="muted">No actionable priority returned by the available assessment.</p>')+(priorities.length>1?'<details><summary>View Other Priorities</summary>'+priorities.slice(1).map(c=>'<div class="growth-other-priority">'+item(c)+'</div>').join('')+'</details>':'')+'<small class="muted">Existing assessment recommendation; indicative, not a guaranteed financing offer.</small></section>'}
// Averages use the exact period length: days, days ÷ 7 weeks, and calendar months (a partial month counts by its days).
function averageCard(name,total,length,note){
 const value=Number(total),per=n=>Number.isFinite(value)&&n>0?fmt(value/n):'—';
 return '<div class="card average-card"><div class="muted">'+esc(name)+'</div><div class="kpi">'+per(length?.months)+' <small class="muted">/ month</small></div><div class="average-rows"><div><span>Weekly</span><b>'+per(length?.weeks)+'</b></div><div><span>Daily</span><b>'+per(length?.days)+'</b></div><div><span>Total</span><b>'+(Number.isFinite(value)?fmt(value):'—')+'</b></div></div><p class="muted">'+esc(note)+'</p></div>';
}
function trendAverages(d){
 const L=d.period_length||{},n={monthly:L.months,weekly:L.weeks,daily:L.days,quarterly:L.months/3}[d.period.granularity],m=d.financial_metrics||{};
 return n>0?{revenue:Number(m.net_sales)/n,expenses:Number(m.expenses)/n,label:{monthly:'month',weekly:'week',daily:'day',quarterly:'quarter'}[d.period.granularity]}:null;
}
const EXPENSE_COLORS=['#993C1D','#D85A30','#F0997B','#BA7517','#888780'];
function expenseLabel(c){return /[A-Z ]/.test(c)?c:String(c).replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase())}
function renderExpenseSplit(d){
 const target=$('#overview-expense');if(!target)return;const split=(d.expense_split||[]).filter(c=>c.amount>0);
 if(!split.length){target.innerHTML='<p class="muted">No recorded expenses in this reporting period.</p>';return}
 const top=split.slice(0,4),rest=split.slice(4),other=rest.reduce((a,c)=>a+c.share,0),shares=[...top.map(c=>c.share),...(other>0?[other]:[])],labels=[...top.map(c=>expenseLabel(c.category)),...(other>0?['Other ('+rest.length+')']:[])];
 let deg=0;const parts=shares.map((s,i)=>{const a=deg,b=deg+s*360;deg=b;return EXPENSE_COLORS[i]+' '+a+'deg '+b+'deg'});
 target.innerHTML='<div class="donutwrap"><div class="donut" style="background:conic-gradient('+parts.join(',')+')"><div class="hole">'+short(d.financial_metrics?.expenses??d.expenses)+'<br><small>expenses</small></div></div><div class="legend">'+labels.map((l,i)=>'<div><span class="sw" style="background:'+EXPENSE_COLORS[i]+'"></span><span style="flex:1">'+esc(l)+'</span><b>'+(shares[i]*100).toFixed(1)+'%</b></div>').join('')+'</div></div>';
}
function renderRevenueValues(d,open){
 const context=[M.id,d.period.start,d.period.end,d.period.granularity].join('|');if(revenueTableState.context!==context){revenueTableState.context=context;revenueTableState.page=1;open=false}
 const target=$('#dashboard-trend-table');if(!target)return;
 ownerPagedTable(target,d.trend,[['Period',row=>esc(row.period)],['Recorded Net Sales ('+d.merchant.currency+')',row=>esc(fmt(row.revenue,d.merchant.currency))],['Recorded Expenses ('+d.merchant.currency+')',row=>esc(fmt(row.expenses||0,d.merchant.currency))]],revenueTableState,'records');
 target.closest('details').open=Boolean(open);
}
const businessAlertTitles={BUFFER_THIN:'Low Cash Buffer',RECEIVABLES_OVERDUE:'Overdue Customer Invoices',RUNWAY_CRITICAL:'Critical Cash Runway',RUNWAY_LOW:'Low Cash Runway',RUNWAY_WATCH:'Cash Runway Watch',SALES_DROP:'Recorded Sales Decrease',OBLIGATIONS_DUE:'Upcoming Supplier Bills',FUNDS_MIXING:'Business and Household Funds',CASH_DEPENDENCE:'Cash Dependence'};
const businessSeverityLabels={critical:'Critical',warning:'Warning',info:'Info'};
function notificationDestination(alert){
 const value=alert.destination||alert.route||alert.action?.path;
 if(typeof value!=='string'||!value.startsWith('/')||value.startsWith('//'))return null;
 const tab=Object.keys(routes).find(key=>routes[key]===value);
 if(!tab||!can(routePermissions[tab]))return null;
 const labels={cashflow:'Review Cash Flow',dashboard:'View Overview',financing:'View Financing',applications:'View Applications',rbf:'View RBF Calculator'};
 return labels[tab]?{tab,path:value,label:labels[tab]}:null;
}
function renderCompactBusinessAlerts(){
 const box=$('#business-alerts'),visible=businessAlertRows.map((alert,index)=>({alert,index})).filter(row=>!dismissedBusinessAlerts.has(row.index));box.innerHTML=visible.length?visible.map(({alert:a,index})=>{
  const severity=Object.hasOwn(businessSeverityLabels,a.severity)?a.severity:'unknown',label=businessSeverityLabels[severity]||'Notification',destination=notificationDestination(a),message=String(a.message||'');
  const symbol=severity==='info'?'<circle cx="8" cy="8" r="6"/><path d="M8 7v4M8 4v1"/>':'<path d="M8 2 15 14H1Z M8 6v4M8 11v1"/>';
  return '<article class="notification-bubble severity-'+severity+'"><button type="button" class="notification-dismiss" data-dismiss-notification="'+index+'" aria-label="Dismiss '+esc(label)+' notification" title="Hide until page reload; this does not resolve the alert">&#215;</button><div class="notification-severity severity-'+severity+'"><svg aria-hidden="true" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">'+symbol+'</svg><span>'+esc(label)+'</span></div><p class="notification-message" id="notification-message-'+index+'">'+esc(message)+'</p><button type="button" class="notification-more" aria-controls="notification-message-'+index+'" aria-expanded="false" hidden>Show full message</button>'+(a.recommended_action?'<details class="notification-guidance"><summary>Suggested action</summary><p>'+esc(a.recommended_action)+'</p></details>':'')+(destination?'<a class="notification-action" data-notification-tab="'+destination.tab+'" href="'+esc(destination.path)+'">'+esc(destination.label)+' <span aria-hidden="true">↗</span></a>':'')+'</article>';
 }).join(''):'<p class="notification-empty">No notifications right now.</p>';
 for(const bubble of box.querySelectorAll('.notification-bubble')){const message=bubble.querySelector('.notification-message'),more=bubble.querySelector('.notification-more');requestAnimationFrame(()=>{more.hidden=message.scrollHeight<=message.clientHeight+1});more.onclick=()=>{const expanded=more.getAttribute('aria-expanded')!=='true';more.setAttribute('aria-expanded',String(expanded));message.classList.toggle('expanded',expanded);more.textContent=expanded?'Show less':'Show full message'}}
 box.querySelectorAll('[data-dismiss-notification]').forEach(button=>button.onclick=event=>{event.stopPropagation();dismissedBusinessAlerts.add(Number(button.dataset.dismissNotification));renderCompactBusinessAlerts();(box.querySelector('[data-dismiss-notification]')||$('#notification-close')).focus()});
 box.querySelectorAll('[data-notification-tab]').forEach(link=>link.onclick=event=>{event.preventDefault();closeBusinessNotifications();navigate(link.dataset.notificationTab)});
 positionBusinessNotifications();
}
