/* Bank Overview mirroring the SME Owner Overview and Cash Flow tabs. Survival Simulation is Owner-only.
   Presentation only: values come from /api/bank/dashboard and /api/bank/cashflow under Owner grants. */
window.BankDashboard=(()=>{const U=BankUI,COLORS=["#0b3b5c","#127a8a","#38bdf8","#94a3b8","#f59e0b","#a3a3a3"];
let state={mid:null,pane:'overview',start:'',end:'',granularity:'monthly'},request=0;
const fmt=(v,c)=>MerchantCurrency.format(v,c),short=(v,c)=>MerchantCurrency.compact(v,c),pct=v=>v==null?'n/a':(v*100).toFixed(1)+'%',esc=U.esc;
function partialPeriod(period){
 if(period.granularity!=='monthly')return '';
 const start=new Date(period.start+'T00:00:00Z'),end=new Date(period.end+'T00:00:00Z');
 if(!Number.isFinite(start.getTime())||!Number.isFinite(end.getTime()))return '';
 const lastDay=new Date(Date.UTC(end.getUTCFullYear(),end.getUTCMonth()+1,0)).getUTCDate(),notes=[];
 if(start.getUTCDate()!==1)notes.push('Partial first month: selected data starts '+period.start+'.');
 if(end.getUTCDate()!==lastDay)notes.push('Partial final month: selected data ends '+period.end+'.');
 return notes.length?notes.join(' ')+' Only records within the applied range are shown. A partial-period decline alone does not establish business deterioration.':'';
}
function donut(shares,labels,center){if(shares.some(s=>!Number.isFinite(s)||s<0)||shares.reduce((a,b)=>a+b,0)<=0)return '<div class="banner note">'+center+'<br>Net channel shares cannot be shown as a pie for zero or negative totals. Review the recorded payment-method totals.</div>';let deg=0;const parts=shares.map((s,i)=>{const a=deg,b=deg+s*360;deg=b;return COLORS[i%6]+' '+a+'deg '+b+'deg'});
 return '<div class="donutwrap"><div class="donut" style="background:conic-gradient('+parts.join(',')+')"><div class="hole">'+center+'</div></div><div class="legend">'+labels.map((l,i)=>'<div><span class="sw" style="background:'+COLORS[i%6]+'"></span><span style="flex:1">'+esc(l)+'</span><b>'+(shares[i]*100).toFixed(1)+'%</b></div>').join('')+'</div></div>'}
function bars(labels,vals){const mx=Math.max(...vals,1),lab=v=>v>=1000?(v/1000).toFixed(1)+'k':v;
 return '<div class="bars">'+vals.map((v,i)=>'<div class="bcol vol"><b>'+lab(v)+'</b><i style="height:'+Math.max(4,v/mx*80)+'%"></i><span>'+esc(labels[i])+'</span></div>').join('')+'</div>'}
function revenueTrend(rows,currency,width){
 if(!rows.length)return '<p class="muted">No recorded sales history for this reporting period.</p>';
 const W=Math.max(320,Math.min(1200,width||900)),H=300,P=48,values=rows.map(r=>r.revenue),low=Math.min(0,...values),high=Math.max(0,...values),span=high-low||1;
 const x=i=>rows.length===1?W/2:P+i*(W-2*P)/(rows.length-1),y=v=>H-P-(v-low)/span*(H-2*P);
 return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" aria-label="Recorded net sales trend in '+esc(currency)+'"><title>Historical recorded net sales</title><line x1="'+P+'" x2="'+(W-P)+'" y1="'+y(0)+'" y2="'+y(0)+'" stroke="var(--line)"/><polyline points="'+values.map((v,i)=>x(i)+','+y(v)).join(' ')+'" fill="none" stroke="var(--brand2)" stroke-width="3"/>'+rows.map((r,i)=>'<circle cx="'+x(i)+'" cy="'+y(r.revenue)+'" r="3" fill="var(--brand)"><title>'+esc(r.period)+': '+esc(fmt(r.revenue,currency))+'</title></circle>'+(i%Math.max(1,Math.ceil(rows.length/Math.max(2,Math.floor(W/140))))===0?'<text x="'+x(i)+'" y="'+(H-15)+'" text-anchor="middle">'+esc(r.period)+'</text>':'')).join('')+'<text x="'+P+'" y="20">'+esc(currency)+' · '+esc(short(high,currency))+'</text><text x="'+P+'" y="'+(H-30)+'">'+esc(short(low,currency))+'</text></svg>'+U.details('View Recorded Trend Values',U.table([['Period','period'],['Recorded Net Sales ('+currency+')','revenue',r=>esc(fmt(r.revenue,currency))]],rows));
}
function cashChart(f){
 const W=900,H=220,P=36,vals=f.path.map(p=>p.balance),mn=Math.min(0,...vals),mx=Math.max(...vals,f.opening_balance);
 const x=i=>P+i*(W-2*P)/Math.max(1,vals.length-1),y=v=>H-P-(v-mn)/((mx-mn)||1)*(H-2*P);
 return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" aria-label="Balance forecast"><line x1="'+P+'" x2="'+(W-P)+'" y1="'+y(0)+'" y2="'+y(0)+'" stroke="#dc2626" stroke-dasharray="4"/><polyline points="'+vals.map((v,i)=>x(i)+','+y(v)).join(' ')+'" fill="none" stroke="#127a8a" stroke-width="3"/>'+vals.map((v,i)=>i%5==0?'<text x="'+x(i)+'" y="'+(H-12)+'" text-anchor="middle">'+esc(f.path[i].date.slice(5))+'</text>':'').join('')+'<text x="'+(W-P)+'" y="'+(y(mx)-6)+'" text-anchor="end">max '+esc(short(mx,f.currency))+'</text><text x="'+(W-P)+'" y="'+(y(0)-4)+'" text-anchor="end" fill="#dc2626">'+esc(short(0,f.currency))+'</text>'+(mn<0?'<text x="'+(W-P)+'" y="'+(y(mn)+12)+'" text-anchor="end">min '+esc(short(mn,f.currency))+'</text>':'')+'</svg>'}
function shell(){
 return '<div class="dashboard-tabs" role="tablist" aria-label="Overview sections">'+[['overview','Overview'],['cashflow','Cash Flow']].map(([k,n])=>'<button type="button" role="tab" id="bank-dashboard-tab-'+k+'" data-bank-dashboard-tab="'+k+'" aria-controls="bank-dashboard-pane-'+k+'">'+n+'</button>').join('')+'</div>'+
 '<form class="card overview-filters" id="bank-dashboard-reporting" aria-label="Reporting period"><label>Start Date<input type="date" name="start"></label><label>End Date<input type="date" name="end"></label><label>Granularity<select name="granularity">'+['daily','weekly','monthly','quarterly'].map(g=>'<option'+(g===state.granularity?' selected':'')+'>'+g+'</option>').join('')+'</select></label><button type="submit">Apply</button><span class="muted" data-period-error role="alert"></span><small class="muted">Reporting filters apply to sales and payments, not cash-flow forecasts.</small></form>'+
 '<div id="bank-dashboard-pane-overview" role="tabpanel" aria-labelledby="bank-dashboard-tab-overview" data-bank-dashboard-pane="overview" tabindex="0"></div><div id="bank-dashboard-pane-cashflow" role="tabpanel" aria-labelledby="bank-dashboard-tab-cashflow" data-bank-dashboard-pane="cashflow" tabindex="0" hidden></div>'}
function overviewMarkup(d,width){
 const f=d.financial_metrics,c=d.merchant.currency,channels=Object.values(d.mix.by_channel),note=partialPeriod(d.period);
 return (f?.record_count===0?'<p class="banner note">No completed transaction records for this period. Actual business revenue is unknown.</p>':'')+
 '<div class="grid overview-kpis">'+[['Recorded Net Sales',fmt(f?.net_sales,c),'Canonical sales net of recorded refunds'],['Expenses',fmt(f?.expenses,c),'Recorded expenses in this reporting period'],['Net Income',fmt(f?.net_income,c),'Authoritative canonical net income'],['Digital Capture',pct(d.capture.digital_share),'Own rails '+pct(d.capture.ecosystem_share)+' · cash '+pct(d.capture.cash_share)]].map(([name,value,n])=>'<div class="card"><div class="muted">'+esc(name)+'</div><div class="kpi">'+esc(value)+'</div><p class="muted">'+esc(n)+'</p></div>').join('')+'</div>'+
 '<div class="dashboard-chart-grid overview-section"><div class="card"><h3>Transaction Volume Mix</h3><p class="muted">Transaction counts by payment channel</p>'+donut(channels.map(x=>x.volume_share),channels.map(x=>x.label),esc(d.mix.total_transactions.toLocaleString())+'<br><small>txns</small>')+'</div><div class="card"><h3>Revenue Split</h3><p class="muted">Recorded channel value, net of recorded refunds. Gross processed split is unavailable from the current API.</p>'+donut(channels.map(x=>x.revenue_share),channels.map(x=>x.label),esc(short(d.mix.gross_revenue,c))+'<br><small>net</small>')+'</div></div>'+
 '<p class="muted">'+esc(d.period.start+' to '+d.period.end+' · '+d.period.granularity+' · '+c)+'</p>'+(note?'<p class="muted partial-period-note">'+esc(note)+'</p>':'')+
 '<div class="overview-trends overview-section"><div class="card"><h3>Transaction Volume Trend</h3>'+bars(d.trend.map(t=>t.period),d.trend.map(t=>t.transactions))+'</div><div class="card"><h3>Revenue Trend</h3><p class="muted">Historical recorded net sales in merchant currency; not a forecast.</p>'+revenueTrend(d.trend,c,width)+'</div></div>'+
 '<div class="card overview-section"><h3>Transaction Volume vs. Revenue Contribution</h3>'+ChannelPerformance.render(d.channel_performance)+'</div>'}
function cashflowMarkup(r){const f=r.forecast,a=r.alerts,c=f.currency||r.currency;
 return '<div class="grid g3">'+[['Balance today',fmt(f.opening_balance,c)],['Lowest projected (30d)',fmt(f.min_balance,c)],['Cash buffer',f.buffer_days+' days'+(f.runway_days?' · negative on day '+f.runway_days:'')]].map(([k,v])=>'<div class="card"><div class="muted">'+esc(k)+'</div><div class="kpi">'+esc(v)+'</div></div>').join('')+'</div>'+
 '<div class="card overview-section"><h2>30-day balance forecast</h2><p class="muted">Method: '+esc(f.method)+'. Estimated, not a cash guarantee.</p>'+cashChart({...f,currency:c})+'</div>'+
 '<div class="card overview-section"><h2>Alerts</h2>'+(a.length?a.map(x=>'<div class="row"><span><span class="pill sev-'+esc(x.severity)+'">'+esc(x.severity)+'</span> <b>'+esc(x.message)+'</b><br><small class="muted">→ '+esc(x.recommended_action)+' <i>('+esc(x.framework_intervention)+')</i></small></span></div>').join(''):'<div class="banner ok">No alerts. Cash position looks healthy.</div>')+'</div>'}
async function loadOverview(root,api,version){
 const pane=root.querySelector('[data-bank-dashboard-pane=overview]'),form=root.querySelector('#bank-dashboard-reporting'),mid=state.mid;
 pane.textContent='Loading Overview…';
 try{const d=await api('/api/bank/dashboard?merchant='+encodeURIComponent(mid)+'&granularity='+encodeURIComponent(state.granularity)+(state.start?'&start='+state.start:'')+(state.end?'&end='+state.end:''));
  if(version!==request||!pane.isConnected)return;
  state.start=d.period.start;state.end=d.period.end;form.elements.start.value=d.period.start;form.elements.end.value=d.period.end;
  pane.innerHTML=overviewMarkup(d,pane.clientWidth)}
 catch(error){if(version===request&&pane.isConnected)pane.innerHTML=U.empty('Overview unavailable: '+error.message+'. The Owner must grant the Reports category.')}}
async function loadCashflow(root,api,version){
 const pane=root.querySelector('[data-bank-dashboard-pane=cashflow]');
 if(pane.dataset.loadedFor===state.mid)return;pane.textContent='Loading Cash Flow…';
 try{const r=await api('/api/bank/cashflow?merchant='+encodeURIComponent(state.mid));
  if(version!==request||!pane.isConnected)return;
  pane.innerHTML=cashflowMarkup(r);pane.dataset.loadedFor=state.mid}
 catch(error){if(version===request&&pane.isConnected)pane.innerHTML=U.empty('Cash Flow unavailable: '+error.message+'. The Owner must grant the Forecasts category.')}}
function select(root,api,name,version){
 state.pane=name;
 root.querySelectorAll('[data-bank-dashboard-tab]').forEach(b=>{const on=b.dataset.bankDashboardTab===name;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
 root.querySelectorAll('[data-bank-dashboard-pane]').forEach(p=>p.hidden=p.dataset.bankDashboardPane!==name);
 root.querySelector('#bank-dashboard-reporting').hidden=name!=='overview';
 if(name==='cashflow')loadCashflow(root,api,version)}
function render(root,mid,api){
 if(state.mid!==mid)state={mid,pane:'overview',start:'',end:'',granularity:'monthly'};
 const version=++request;root.innerHTML=shell();
 const form=root.querySelector('#bank-dashboard-reporting'),tabs=[...root.querySelectorAll('[data-bank-dashboard-tab]')];
 form.elements.start.value=state.start;form.elements.end.value=state.end;
 form.onsubmit=e=>{e.preventDefault();const s=form.elements.start.value,en=form.elements.end.value;form.querySelector('[data-period-error]').textContent='';
  if(s&&en&&s>en){form.querySelector('[data-period-error]').textContent='Start date must be on or before end date.';return}
  state.start=s;state.end=en;state.granularity=form.elements.granularity.value;loadOverview(root,api,version)};
 tabs.forEach((b,i)=>{b.onclick=()=>select(root,api,b.dataset.bankDashboardTab,version);b.onkeydown=e=>{let next;
  if(e.key==='ArrowRight')next=(i+1)%tabs.length;if(e.key==='ArrowLeft')next=(i+tabs.length-1)%tabs.length;if(e.key==='Home')next=0;if(e.key==='End')next=tabs.length-1;
  if(next!==undefined){e.preventDefault();tabs[next].click();tabs[next].focus()}}});
 select(root,api,state.pane,version);loadOverview(root,api,version)}
return {render};
})();
