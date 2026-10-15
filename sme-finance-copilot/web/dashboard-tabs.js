/* POC dashboard composition. Existing services and chart renderers remain authoritative. */
let dashboardRequest=0,growthRequest=0,alertRequest=0,dashboardAssessment=null,dashboardAssessmentPromise=null;
let dashboardPane='overview',businessAlertsLoaded=false;
const maturityStages=['Survival Borrower','Striving Amateur','Steady Upgrader','Opportunity Seizer','Expanding Proprietor','Heir Seeker'];
const dimensionLabel=name=>name.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
function resetDashboardContext(){
 dashboardRequest++;growthRequest++;alertRequest++;dashboardAssessment=null;dashboardAssessmentPromise=null;businessAlertsLoaded=false;businessAlertRows=[];businessAlertsRetrieved=null;businessAlertState={page:1,size:3,severity:'all'};revenueTableState={page:1,size:10,context:''};
 for(const id of ['dkpis','dvol','drev','overview-volume','overview-revenue','dvoltrend','drevtrend','business-growth','business-alerts','financing-readiness','dashboard-insights','dashboard-incentive','dashboard-provenance','dashboard-limitations','matches','rbfelig','rbfsummary','rbfdays','rbfcmp'])$('#'+id)?.replaceChildren();
 $('#business-growth').textContent='Open Business Growth to load the current assessment.';$('#business-alerts').textContent='Open Alerts to load the available business alerts.';
}
function selectDashboardPane(name){
 if(!['overview','sales','growth','alerts'].includes(name))name='overview';dashboardPane=name;
 $$('[data-dashboard-tab]').forEach(b=>{const selected=b.dataset.dashboardTab===name;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;b.classList.toggle('active',selected)});
 $$('[data-dashboard-pane]').forEach(panel=>panel.hidden=panel.dataset.dashboardPane!==name);
 $('#dashboard-reporting').hidden=!['overview','sales'].includes(name);
 if(name==='growth')loadBusinessGrowth();if(name==='alerts')loadBusinessAlerts();
}
async function assessmentForMerchant(){
 const mid=M.id;
 if(dashboardAssessment?.merchant_id===mid)return dashboardAssessment;
 if(dashboardAssessmentPromise?.mid===mid)return dashboardAssessmentPromise.promise;
 const promise=api('/mcp',{method:'POST',body:JSON.stringify({jsonrpc:'2.0',id:'owner-maturity',method:'tools/call',params:{name:'assess_business',arguments:{merchant_id:mid}}})}).then(r=>{
  if(r.error||r.result?.isError||!r.result?.structuredContent)throw Error('The current assessment is unavailable or not authorized.');
  const assessment=r.result.structuredContent;if(M?.id!==mid||assessment.merchant_id!==mid)throw Error('Merchant changed.');
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
 const mid=M.id,request=++alertRequest,box=$('#business-alerts');box.textContent='Loading business alerts…';
 if(!can('view_forecasts')){box.textContent='Business alerts are not delegated to this account.';return}
 try{const response=await api('/mcp',{method:'POST',body:JSON.stringify({jsonrpc:'2.0',id:'owner-alerts',method:'tools/call',params:{name:'cashflow_alerts',arguments:{merchant_id:mid}}})});
  if(M.id!==mid||request!==alertRequest)return;if(response.error||response.result?.isError)throw Error('Alerts unavailable');
  businessAlertRows=response.result.structuredContent.items;businessAlertsRetrieved=new Date();
  if(!businessAlertRows.some(a=>a.severity===businessAlertState.severity))businessAlertState.severity='all';
  businessAlertState.page=1;businessAlertsLoaded=true;renderCompactBusinessAlerts();
 }catch(error){if(M.id===mid&&request===alertRequest)box.textContent='Business alerts could not be loaded. Use Refresh alerts to retry.'}
}
async function loadDashboard(){
 const mid=M.id,request=++dashboardRequest,s=$('#dstart').value,e=$('#dend').value;$('#derr').textContent='';
 if(s&&e&&s>e){$('#derr').textContent='Start date must be on or before end date.';return}
 const d=await api('/api/dashboard'+q('&granularity='+$('#dgran').value+(s?'&start='+s:'')+(e?'&end='+e:'')));
 if(M.id!==mid||request!==dashboardRequest)return;
 if(!s){$('#dstart').value=d.period.start;$('#dend').value=d.period.end}
 const f=d.financial_metrics,inc=d.incentive;
 $('#dashboard-empty').hidden=f?.record_count!==0;$('#dashboard-empty').textContent='No completed transaction records for this period. Actual business revenue is unknown.';
 $('#dkpis').innerHTML=[['Recorded Net Sales',fmt(f?.net_sales),'Canonical sales net of recorded refunds'],['Expenses',fmt(f?.expenses),'Recorded expenses in this reporting period'],['Net Income',fmt(f?.net_income),'Authoritative canonical net income'],['Digital Capture',pct(d.capture.digital_share),'Own rails '+pct(d.capture.ecosystem_share)+' · cash '+pct(d.capture.cash_share)]].map(([name,value,note])=>'<div class="card"><div class="muted">'+name+'</div><div class="kpi">'+value+'</div><p class="muted">'+esc(note)+'</p></div>').join('');
 const channels=Object.values(d.mix.by_channel),volume=donut(channels.map(c=>c.volume_share),channels.map(c=>c.label),d.mix.total_transactions.toLocaleString()+'<br><small>txns</small>'),revenue=donut(channels.map(c=>c.revenue_share),channels.map(c=>c.label),short(d.mix.gross_revenue)+'<br><small>net</small>');
 for(const id of ['dvol','overview-volume'])$('#'+id).innerHTML=volume;for(const id of ['drev','overview-revenue'])$('#'+id).innerHTML=revenue;
 const trendOpen=$('#dashboard-trend-values')?.open;$('#dvoltrend').innerHTML=bars(d.trend.map(t=>t.period),d.trend.map(t=>t.transactions),'vol');$('#drevtrend').innerHTML=financialTrend(d.trend,d.merchant.currency);renderRevenueValues(d,trendOpen);
 $('#dashboard-trend-period').textContent=d.period.start+' to '+d.period.end+' · '+d.period.granularity+' · '+d.merchant.currency;
 $('#dashboard-insights').innerHTML='<p><b>Receivables:</b> '+esc(d.receivables.explanation)+'</p>';
 $('#dashboard-incentive').innerHTML='<p><b>Incentive milestone:</b> '+esc(inc.tier_name||'No milestone yet')+(inc.mom_growth==null?'':' · '+pct(inc.mom_growth)+' month-on-month own-rail growth')+'</p><small class="muted">Provisional sandbox milestone, not a guaranteed reward. Review Alerts for current business warnings.</small>';

}
const existingLoadFinancing=loadFinancing;
loadFinancing=async function(){const mid=M.id;const promise=existingLoadFinancing();if(can('view_assessment'))assessmentForMerchant().then(a=>{if(M.id===mid)$('#financing-readiness').textContent='Business maturity: '+a.stage_name+' · Composite '+a.composite_score+'/100 · Credit readiness '+a.scores.credit_readiness+'/100 · as of '+a.as_of+'. Indicative business assessment, not credit eligibility or approval.'}).catch(()=>{if(M.id===mid)$('#financing-readiness').textContent='Maturity summary unavailable for this account or data.'});else $('#financing-readiness').textContent='Maturity summary is not delegated to this account.';return promise};
document.addEventListener('DOMContentLoaded',()=>{
 $$('[data-dashboard-tab]').forEach(button=>{button.onclick=()=>selectDashboardPane(button.dataset.dashboardTab);button.onkeydown=event=>{const buttons=$$('[data-dashboard-tab]'),index=buttons.indexOf(button);let next;if(event.key==='ArrowRight')next=(index+1)%buttons.length;if(event.key==='ArrowLeft')next=(index+buttons.length-1)%buttons.length;if(event.key==='Home')next=0;if(event.key==='End')next=buttons.length-1;if(next!==undefined){event.preventDefault();buttons[next].click();buttons[next].focus()}}});
 $('#refresh-growth').onclick=()=>{dashboardAssessment=null;dashboardAssessmentPromise=null;loadBusinessGrowth()};$('#refresh-business-alerts').onclick=()=>{businessAlertsLoaded=false;loadBusinessAlerts()};
 selectDashboardPane('overview');
},{once:true});

let revenueTableState={page:1,size:10,context:''};
let businessAlertRows=[],businessAlertState={page:1,size:3,severity:'all'},businessAlertsRetrieved=null;
function nextMaturityCard(a){
 const gap=a.next_stage;if(!gap)return '<section class="growth-next-card"><h3>Next Maturity Stage</h3><p>'+esc(a.stage>=6?'Highest maturity stage reached.':'No numeric next-stage target supplied by this assessment.')+'</p><small>'+esc(a.graduation_trigger||'Assessment data is unavailable.')+'</small></section>';
 const gates=Object.entries(gap.dimension_gaps||{}).sort((a,b)=>b[1]-a[1]),gate=gates[0];
 return '<section class="growth-next-card"><h3>Next Maturity Stage</h3><p class="growth-stage-transition">Stage '+esc(a.stage)+' → Stage '+esc(gap.target_stage)+'</p><strong>'+esc(gap.target_name)+'</strong><div class="growth-target-grid"><div><small>Composite threshold</small><b>'+esc(gap.composite_needed)+'/100</b></div><div><small>Composite gap</small><b>'+esc(gap.composite_gap)+' points needed</b></div></div>'+(gate?'<div class="growth-gate"><small>Largest unmet dimension gate</small><strong>'+esc(dimensionLabel(gate[0]))+'</strong><span>Current: '+esc(a.scores[gate[0]])+'/100 · '+esc(gate[1])+' points below the required gate</span></div>':'<p class="muted">No unmet dimension gate returned.</p>')+'<small class="muted">Composite threshold and all required gates apply together; threshold alone does not guarantee advancement.</small></section>';
}
function growthPriorityCard(a){const priorities=a.constraints||[],primary=priorities[0];const item=c=>'<strong>'+esc(dimensionLabel(c.constraint))+'</strong><p>'+esc(c.evidence)+'</p>'+(c.intervention?'<p><b>Explore:</b> '+esc(c.intervention)+'</p>':'');return '<section class="growth-priority"><h3>Recommended Next Step</h3>'+(primary?item(primary):'<p class="muted">No actionable priority returned by the available assessment.</p>')+(priorities.length>1?'<details><summary>View Other Priorities</summary>'+priorities.slice(1).map(c=>'<div class="growth-other-priority">'+item(c)+'</div>').join('')+'</details>':'')+'<small class="muted">Existing assessment recommendation; indicative, not a guaranteed financing offer.</small></section>'}
function renderRevenueValues(d,open){
 const context=[M.id,d.period.start,d.period.end,d.period.granularity].join('|');if(revenueTableState.context!==context){revenueTableState.context=context;revenueTableState.page=1;open=false}
 const target=$('#dashboard-trend-table');if(!target)return;
 ownerPagedTable(target,d.trend,[['Period',row=>esc(row.period)],['Recorded Net Sales ('+d.merchant.currency+')',row=>esc(fmt(row.revenue,d.merchant.currency))]],revenueTableState,'records');
 target.closest('details').open=Boolean(open);
}
const businessAlertTitles={BUFFER_THIN:'Low Cash Buffer',RECEIVABLES_OVERDUE:'Overdue Customer Invoices',RUNWAY_CRITICAL:'Critical Cash Runway',RUNWAY_LOW:'Low Cash Runway',RUNWAY_WATCH:'Cash Runway Watch',SALES_DROP:'Recorded Sales Decrease',OBLIGATIONS_DUE:'Upcoming Supplier Bills',FUNDS_MIXING:'Business and Household Funds',CASH_DEPENDENCE:'Cash Dependence'};
const businessSeverityLabels={critical:'Critical',warning:'Warning',info:'Info'};
function renderCompactBusinessAlerts(){
 const box=$('#business-alerts'),state=businessAlertState,all=businessAlertRows,filtered=state.severity==='all'?all:all.filter(a=>a.severity===state.severity),pages=Math.max(1,Math.ceil(filtered.length/state.size));state.page=Math.max(1,Math.min(state.page,pages));const start=(state.page-1)*state.size,visible=filtered.slice(start,start+state.size),critical=all.filter(a=>a.severity==='critical').length;
 box.innerHTML='<div class="business-alert-filters" role="group" aria-label="Business alert severity">'+['all',...Object.keys(businessSeverityLabels).filter(severity=>all.some(a=>a.severity===severity))].map(severity=>'<button type="button" class="btn ghost sm" data-business-severity="'+severity+'" aria-pressed="'+String(state.severity===severity)+'">'+(severity==='all'?'All':businessSeverityLabels[severity])+' ('+(severity==='all'?all.length:all.filter(a=>a.severity===severity).length)+')</button>').join('')+'</div>'+(critical?'<p class="critical-alert-count">Critical alerts in this snapshot: '+critical+'</p>':'')+'<div class="compact-business-alerts">'+(visible.length?visible.map(a=>'<article class="business-alert-card"><div class="business-alert-heading"><h4>'+esc(businessAlertTitles[a.code]||dimensionLabel(a.code))+'</h4><span class="pill sev-'+esc(a.severity)+'">'+esc(businessSeverityLabels[a.severity]||a.severity)+'</span></div><p>'+esc(a.message)+'</p>'+(a.recommended_action?'<p class="business-alert-action"><b>Suggested action:</b> '+esc(a.recommended_action)+'</p>':'')+'<div class="business-alert-tools">'+(can('view_forecasts')?'<button class="btn ghost sm" data-alert-source="cashflow">Review Cash Flow</button>':'')+'<details><summary>View Details</summary><p>Source: existing Cash Flow business rules.</p>'+(a.framework_intervention?'<p>'+esc(a.framework_intervention)+'</p>':'')+(a.as_of?'<p>As of '+esc(a.as_of)+'</p>':'')+'</details></div></article>').join(''):all.length?'<p>No business alerts match this severity filter.</p>':'<p>No business alerts for the available assessment.</p>')+'</div><div class="owner-pagination" aria-label="Business alerts pagination"><span>Showing '+(filtered.length?start+1:0)+'–'+Math.min(start+state.size,filtered.length)+' of '+filtered.length+' alerts</span><label>Per page <select data-business-alert-size>'+[3,5,10].map(size=>'<option '+(state.size===size?'selected':'')+'>'+size+'</option>').join('')+'</select></label><button class="btn ghost sm" data-business-alert-prev '+(state.page===1?'disabled':'')+'>Previous</button><span>Page '+state.page+' of '+pages+'</span><button class="btn ghost sm" data-business-alert-next '+(state.page===pages?'disabled':'')+'>Next</button></div><small class="muted">Retrieved on demand '+esc(businessAlertsRetrieved?.toLocaleString()||'')+'; independent of reporting-period filters.</small>';
 box.querySelectorAll('[data-business-severity]').forEach(button=>button.onclick=()=>{state.severity=button.dataset.businessSeverity;state.page=1;renderCompactBusinessAlerts()});
 box.querySelector('[data-business-alert-size]').onchange=event=>{state.size=Number(event.target.value);state.page=1;renderCompactBusinessAlerts()};box.querySelector('[data-business-alert-prev]').onclick=()=>{state.page--;renderCompactBusinessAlerts()};box.querySelector('[data-business-alert-next]').onclick=()=>{state.page++;renderCompactBusinessAlerts()};box.querySelectorAll('[data-alert-source]').forEach(button=>button.onclick=()=>navigate(button.dataset.alertSource));
}
