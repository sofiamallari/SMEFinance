"""Bounded evidence planning inside the existing generalized conversation engine."""
import calendar,copy,re
from datetime import date,timedelta
from copilot.governed_claims import ClaimError
from copilot.security import AccessDenied

LABELS={'get_financial_summary':'recorded sales summaries and period comparisons',
 'get_transaction_trends':'transaction trends and highest recorded sales periods',
 'get_payment_channel_mix':'payment-channel transaction mix',
 'get_cash_flow':'cash-flow projections with synthetic opening-balance limitations',
 'get_business_highlights':'recorded incentive and receivables highlights',
 'get_financing_status':'a specific authorized financing application status',
 'get_financing_details':'a specific authorized financing application requested amount',
 'run_survival_simulation':'hypothetical operating-result simulations',
 'run_cash_impact_scenario':'hypothetical purchase and incremental hiring cash-impact scenarios'}

def capability_answer(definitions):
 names={d['function']['name'] for d in definitions}
 supported=[label for name,label in LABELS.items() if name in names]
 return 'Welcome! I can help with financial education and permitted application guidance'+('. For your current account, I can also help with '+ '; '.join(supported) if supported else '')+'. I cannot execute payments, change business records or approve financing.'

def default_period(c,mid,today):
 from copilot.cash_impact import latest_data
 latest=latest_data(c,mid);anchor=min(date.fromisoformat(latest),today) if latest else today
 if anchor.day!=calendar.monthrange(anchor.year,anchor.month)[1]:anchor=anchor.replace(day=1)-timedelta(days=1)
 return {'start':anchor.replace(day=1).isoformat(),'end':anchor.isoformat()}

def prepare_state(previous,updated,text):
 """Different cost types are separate unless the user explicitly combines them."""
 combine=bool(re.search(r'\b(?:both|combine|together)\b',text,re.I))
 incoming={k for k,v in updated['entities'].items() if v.get('turn')==updated['turn']}
 old=previous['entities']
 separate=(('recurring_expense' in incoming and 'one_time_cost' in old) or ('one_time_cost' in incoming and 'recurring_expense' in old))
 if separate and not combine and not any(t.get('entities')==old for t in updated['topics']):
  updated['topics']=(updated['topics']+[{'intent':previous['intent'],'entities':copy.deepcopy(old),'pending':None,'resolved':previous['resolved']}])[-3:]
  updated['entities']={k:v for k,v in updated['entities'].items() if k in incoming}
  updated['resolved']=list(updated['entities']);updated['pending']=None
 if combine:
  for topic in reversed(updated['topics']):
   for key in ('one_time_cost','recurring_expense','payment_method','costs_included','start_date'):
    if key not in updated['entities'] and key in topic['entities']:updated['entities'][key]=copy.deepcopy(topic['entities'][key])
  updated['resolved']=list(updated['entities'])
 return updated

def scenario_args(state,today):
 entities=state['entities'];get=lambda key:entities.get(key,{}).get('value')
 args={'assessment_date':get('assessment_date') or today.isoformat(),'horizon_days':90}
 if get('one_time_cost') is not None:
  # A financing-funded purchase needs financing terms; never model it as cash.
  if get('payment_method')!='cash':return None
  args.update(one_time_cost=float(get('one_time_cost')),purchase_date=get('purchase_date') or args['assessment_date'])
 if get('recurring_expense') is not None:
  if not get('start_date'):return None
  args.update(monthly_cost=float(get('recurring_expense')),start_date=get('start_date'))
 if not any(k in args for k in ('one_time_cost','monthly_cost')):return None
 for key in ('one_time_cost','recurring_expense','available_cash'):
  if key in entities and entities[key].get('currency')!='CNY':raise ClaimError('scenario_currency_mismatch')
 if get('available_cash') is not None:args['user_cash']=float(get('available_cash'))
 return args

def requests(plan,state,c,mid,today,definitions,text):
 """Three executions max. All arguments remain schema-checked by the gateway."""
 allowed={d['function']['name'] for d in definitions};intent=state['intent'];entities=state['entities']
 period=entities.get('reporting_period',{}).get('value') or default_period(c,mid,today)
 comparison=entities.get('comparison_period',{}).get('value')
 if not comparison and state['intent']=='sales_analysis':
  end=date.fromisoformat(period['start'])-timedelta(days=1);last=date.fromisoformat(period['end']);first=date.fromisoformat(period['start'])
  whole_month=first.day==1 and first.month==last.month and first.year==last.year and last.day==calendar.monthrange(last.year,last.month)[1]
  start=end.replace(day=1) if whole_month else end-timedelta(days=(last-first).days)
  comparison={'start':start.isoformat(),'end':end.isoformat()}
 scenario=scenario_args(state,today) if intent=='decision_support' else None
 proposals=plan.get('tool_requests')
 if proposals is None:
  # Backward-compatible provider contract. New real-provider plans use tool_requests.
  from copilot.conversation_review import TOOLS
  name=TOOLS.get(intent);proposals=[{'name':name,'arguments':{}}] if name else []
  if scenario:proposals=[{'name':'run_cash_impact_scenario','arguments':{}}]
  if name=='get_financial_summary' and 'comparison_period' in entities:proposals.append({'name':name,'arguments':comparison})
 if len(proposals)>3:raise ClaimError('tool_count_exceeded')
 result=[]
 for proposal in proposals:
  name=proposal['name'];args=proposal['arguments']
  if name not in allowed:raise AccessDenied('Tool is not authorized for this account')
  relevant={
   'sales_analysis':{'get_financial_summary','get_transaction_trends','get_payment_channel_mix'},
   'cash_flow':{'get_cash_flow','get_business_highlights'},
   'decision_support':{'get_cash_flow','run_cash_impact_scenario','get_financial_summary','get_business_highlights'},
   'financing':{'get_financing_status','get_financing_details'},
   'payment_channels':{'get_payment_channel_mix','get_financial_summary'},
   'simulation':{'run_survival_simulation','get_financial_summary','get_cash_flow'}}
  if name not in relevant.get(intent,set()):raise ClaimError('tool_not_relevant_to_intent')
  if name=='search_public_financial_information':raise ClaimError('research_approval_required')
  if name=='run_cash_impact_scenario':
   if not scenario:continue
   if any(k not in scenario or v!=scenario[k] for k,v in args.items()):raise ClaimError('scenario_inputs_not_conversation_bound')
   args=scenario
  elif name in ('get_financial_summary','get_transaction_trends','get_payment_channel_mix','get_business_highlights'):
   requested={k:v for k,v in args.items() if k!='granularity'}
   if name=='get_transaction_trends' and re.search(r'best|highest',text,re.I):
    m=c.financial_data.project(mid);available=[date.fromisoformat(r['date']) for r in m.transactions]
    end=max(available) if available else today;start=max(min(available),end-timedelta(days=365)) if available else end
    target={'start':start.isoformat(),'end':end.isoformat()}
   else:target=comparison if comparison and ((requested and requested==comparison) or (not requested and any(n=='get_financial_summary' for n,a in result) and name=='get_financial_summary')) else period
   if requested and requested!=target:raise ClaimError('unrequested_reporting_period')
   args={**target,**({'granularity':args.get('granularity','monthly')} if name=='get_transaction_trends' else {})}
  elif name in ('get_financing_status','get_financing_details'):
   refs=re.findall(r'\bAPP-[A-Za-z0-9-]{1,80}\b',text)
   if len(refs)!=1:continue
   if args and args.get('application_reference')!=refs[0]:raise ClaimError('unrequested_application')
   args={'application_reference':refs[0]}
  elif name=='run_survival_simulation':
   required=('sales_change_percent','expense_change_percent','simulation_duration')
   if intent!='simulation' or not all(k in entities for k in required):continue
   expected={'sales_change_percent':float(entities[required[0]]['value']),'expense_change_percent':float(entities[required[1]]['value']),'months':int(entities[required[2]]['value'])}
   if args and args!=expected:raise ClaimError('simulation_inputs_not_conversation_bound')
   args=expected
  result.append((name,args))
 return result
