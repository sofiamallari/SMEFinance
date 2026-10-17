/* View composition and print-only export. No financial calculations live here. */
let dashboardSnapshot=null,cashflowLoadedFor=null;
function overviewPartialPeriod(period){
 if(period.granularity!=='monthly')return '';
 const start=new Date(period.start+'T00:00:00Z'),end=new Date(period.end+'T00:00:00Z');
 if(!Number.isFinite(start.getTime())||!Number.isFinite(end.getTime()))return '';
 const lastDay=new Date(Date.UTC(end.getUTCFullYear(),end.getUTCMonth()+1,0)).getUTCDate(),notes=[];
 if(start.getUTCDate()!==1)notes.push('Partial first month: selected data starts '+period.start+'.');
 if(end.getUTCDate()!==lastDay)notes.push('Partial final month: selected data ends '+period.end+'.');
 return notes.length?notes.join(' ')+' Only records within the applied range are shown. A partial-period decline alone does not establish business deterioration.':'';
}
function positionBusinessNotifications(){
 const panel=$('#notification-popover');if(panel.hidden)return;
 const bell=$('#notification-toggle').getBoundingClientRect(),width=Math.min(340,innerWidth-24),top=bell.bottom+8;
 if(bell.bottom<=0||bell.top>=innerHeight){closeBusinessNotifications();return}
 panel.style.width=width+'px';panel.style.left=Math.max(12,Math.min(bell.right-width,innerWidth-width-12))+'px';panel.style.right='auto';panel.style.top=top+'px';panel.style.maxHeight=Math.max(40,Math.min(400,innerHeight-top-12))+'px';
}
function closeBusinessNotifications(){$('#notification-popover').hidden=true;$('#notification-toggle').setAttribute('aria-expanded','false')}
function dashboardIntegratedPane(name){
 if(name==='overview'&&dashboardSnapshot)requestAnimationFrame(()=>{if(dashboardPane==='overview'&&dashboardSnapshot?.merchant.id===M?.id){const open=$('#dashboard-trend-values')?.open;$('#drevtrend').innerHTML=financialTrend(dashboardSnapshot.trend,dashboardSnapshot.merchant.currency,trendAverages(dashboardSnapshot));renderRevenueValues(dashboardSnapshot,open)}});
 survivalState.active=name==='survival';
 if(name==='cashflow'){
  if(!can('view_forecasts')){$('#dashboard-pane-cashflow').textContent='Cash Flow is not delegated to this account.';return}
  const content=$('#tab-cashflow');if(content.children.length)$('#dashboard-pane-cashflow').replaceChildren(...content.children);
  if(cashflowLoadedFor!==M?.id){const mid=M?.id;loadCashflow().then(()=>{if(M?.id===mid)cashflowLoadedFor=mid}).catch(e=>showErr('cashflow',e))}
 }
 $('#survival-pane').hidden=name!=='survival';
 if(name==='survival'){
  const allowed=survivalAllowed();$('#dashboard-survival-access').hidden=allowed;
  $('#dashboard-survival-access').textContent='Survival Simulation is unavailable for this account or is disabled in this environment.';
  $('#survival-pane').hidden=!allowed;
  if(allowed){survivalScope();if(!survivalState.baseline&&!survivalState.loading)survivalLoad()}
 }
}
function reportFragment(selector){
 const source=$(selector);if(!source)return '';
 const copy=source.cloneNode(true);
 copy.querySelectorAll('button,input,select,textarea,script,details,[hidden]').forEach(node=>node.remove());
 for(const node of [copy,...copy.querySelectorAll('*')])for(const attribute of [...node.attributes])if(attribute.name==='id'||attribute.name.startsWith('on')||attribute.name.startsWith('data-'))node.removeAttribute(attribute.name);
 return copy.outerHTML;
}
function exportDashboardOverview(){
 const d=dashboardSnapshot,status=$('#export-status');status.classList.remove('sr-only');status.textContent='';
 if(!can('view_dashboard')||!d||d.merchant.id!==M.id&&d.merchant.merchant_id!==M.id){status.textContent='Load the current authorized merchant Overview before exporting.';return}
 const popup=window.open('about:blank','_blank');if(!popup){status.textContent='Allow the report window, then select Export PDF again.';return}
 const periodExplanation=overviewPartialPeriod(d.period);
 const heading='<header><h1>SME Finance Copilot</h1><h2>'+esc(d.merchant.name)+'</h2><p>Business Overview · '+esc(d.period.start)+' to '+esc(d.period.end)+' · '+esc(d.period.granularity)+'</p><p>Currency: CNY (RMB, ¥) · Generated '+esc(new Date().toLocaleString())+'</p>'+(periodExplanation?'<p class="note">'+esc(periodExplanation)+'</p>':'')+'</header>';
 const chart=(title,selector,note)=>'<section class="chart"><h3>'+title+'</h3><p class="note">'+note+'</p>'+reportFragment(selector)+'</section>';
 // Split the existing volume bars into printable groups without recalculating their values.
 const volume=$('#dvoltrend').cloneNode(true),barContainer=volume.querySelector('.bars');
 if(barContainer){const bars=[...barContainer.children];volume.replaceChildren();for(let i=0;i<bars.length;i+=12){const group=document.createElement('div');group.className='bars';group.append(...bars.slice(i,i+12));volume.append(group)}}
 for(const node of [volume,...volume.querySelectorAll('*')])node.removeAttribute('id');
 const styles=`:root{--brand:#08663d;--brand2:#08663d;--line:#d8e2ea;--muted:#526478}@page{size:A4;margin:15mm;@bottom-right{content:"Page " counter(page);font-size:9pt;color:#64748b}}*{box-sizing:border-box}body{font:10pt Arial,sans-serif;color:#08663d;margin:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}h1{font-size:19pt;margin:0 0 8px}h2{font-size:15pt;margin:6px 0}h3{font-size:12pt;margin:0 0 10px}header{border-bottom:2px solid #08663d;padding-bottom:12px;margin-bottom:16px}p{line-height:1.45}.note,.muted,small{color:#526478;font-size:9pt}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.card,.chart{border:1px solid #d8e2ea;border-radius:8px;padding:14px;break-inside:avoid}.kpi{font-size:18pt;font-weight:bold;margin:8px 0}.mix{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:16px}.average-rows div{display:flex;justify-content:space-between;font-size:9pt}.donutwrap{display:flex;flex-direction:column;align-items:center;gap:12px}.donut{width:135px;height:135px;border-radius:50%;display:grid;place-items:center}.hole{width:86px;height:86px;border-radius:50%;background:white;display:grid;place-items:center;text-align:center;font-weight:bold;padding:5px}.legend{width:100%;font-size:8pt}.legend div{display:flex;align-items:center;gap:6px;margin:5px 0}.sw{width:10px;height:10px;flex-shrink:0;border-radius:2px}.trends{break-before:page}.trends .chart{margin:14px 0}.bars{display:flex;align-items:flex-end;gap:5px;height:180px;border-bottom:1px solid #cbd5e1;margin:14px 0 24px;break-inside:avoid}.bcol{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end;font-size:7pt}.bcol i{display:block;min-width:12px;width:70%;background:#08663d!important}.bcol span{overflow-wrap:anywhere;font-size:6.5pt}.bcol b{font-size:7pt}svg{width:100%;height:auto;max-height:240px}svg text{font-family:Arial,sans-serif;fill:#526478;font-size:14px}.legend span[style]{flex:1}.sw{flex:0 0 10px!important}.report-tools{padding:12px;background:#edf4f7;margin-bottom:16px;color:#08663d}.report-tools button{padding:8px 12px;cursor:pointer}.highlights{break-inside:avoid}.banner{padding:12px;border:1px solid #d8e2ea}@media print{.report-tools{display:none}}.channel-performance section{margin:12px 0;break-inside:avoid}.channel-performance strong{display:block;margin-bottom:4px}.channel-bar-line{display:grid;grid-template-columns:105px minmax(100px,1fr) 55px;gap:8px;align-items:center;margin:4px 0;font-size:8pt}.channel-bar-track{background:#edf4ef;min-height:16px}.channel-bar{display:block;min-height:16px;-webkit-print-color-adjust:exact;print-color-adjust:exact}.channel-bar-line b{text-align:right;white-space:nowrap}.channel-legend{display:flex;gap:16px;font-size:9pt}.channel-legend span:first-child{color:#08663d}.channel-legend span:last-child{color:#397d53}`;
 popup.document.open();popup.document.write('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Business Overview</title><style>'+styles+'</style></head><body><div class="report-tools">Use Print / Save as PDF. Choose A4 and disable browser headers/footers.<button id="print-report">Print / Save as PDF</button></div>'+heading+reportFragment('#dkpis')+'<div class="mix">'+chart('Transaction Volume Mix','#overview-volume','Transaction counts by payment channel.')+chart('Revenue Split','#overview-revenue','Recorded channel value net of recorded refunds; gross processed split is unavailable.')+chart('Expense Split','#overview-expense','Recorded expenses by category; loan principal and other non-expense cash-out excluded.')+'</div><div class="trends">'+chart('Revenue vs Expense Trend','#drevtrend','Historical recorded net sales and expenses in CNY, with period averages; not a forecast.')+chart('Transaction Volume Trend','#dvoltrend','Transaction counts for the displayed reporting period.').replace(reportFragment('#dvoltrend'),volume.outerHTML)+'<section class="chart"><h3>Transaction Volume vs. Revenue Contribution</h3>'+reportFragment('#channel-performance')+'</section></div></body></html>');popup.document.close();
 popup.document.querySelector('#print-report').onclick=()=>popup.print();
 popup.document.fonts.ready.then(()=>{popup.focus();popup.print()});status.classList.add('sr-only');status.textContent='Report opened. Select Save as PDF in the print dialog.';
}
document.addEventListener('DOMContentLoaded',()=>{
 $('#notification-toggle').onclick=()=>{const open=$('#notification-popover').hidden;$('#notification-popover').hidden=!open;$('#notification-toggle').setAttribute('aria-expanded',String(open));if(open){positionBusinessNotifications();loadBusinessAlerts();$('#notification-close').focus()}};
 $('#notification-close').onclick=()=>{closeBusinessNotifications();$('#notification-toggle').focus()};
 document.addEventListener('click',e=>{if(!e.target.closest('.notification-anchor'))closeBusinessNotifications()});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#notification-popover').hidden){closeBusinessNotifications();$('#notification-toggle').focus()}});
 window.addEventListener('resize',positionBusinessNotifications);window.addEventListener('scroll',event=>{if(!$('#notification-popover').contains(event.target))positionBusinessNotifications()},true);
 $('#export-overview').onclick=exportDashboardOverview;
 let trendResize;window.addEventListener('resize',()=>{clearTimeout(trendResize);trendResize=setTimeout(()=>{if(dashboardSnapshot&&dashboardSnapshot.merchant.id===M?.id){const details=$('#dashboard-trend-values')?.open;$('#drevtrend').innerHTML=financialTrend(dashboardSnapshot.trend,dashboardSnapshot.merchant.currency,trendAverages(dashboardSnapshot));renderRevenueValues(dashboardSnapshot,details)}},150)});
},{once:true});
