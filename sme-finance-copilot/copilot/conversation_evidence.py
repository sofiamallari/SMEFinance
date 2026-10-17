"""Bounded evidence planning inside the existing generalized conversation engine."""
import calendar,copy,re
from datetime import date,timedelta
from copilot.governed_claims import ClaimError
from copilot.security import AccessDenied

LABELS={'get_financial_summary':'recorded sales summaries and period comparisons',
 'get_transaction_trends':'transaction trends and highest recorded sales periods',
 'get_payment_channel_mix':'payment-channel transaction mix',
 'get_cash_flow':'cash-flow forecasts (estimates, not reconciled with your bank)',
 'get_cash_flow_alerts':'cash-flow alerts and recommended actions',
 'get_income_summary':'expenses, net income, average revenue and expense, and the expense split for a period',
 'get_cashflow_book':'your uploaded cash-flow workbook: who owes you, overdue invoices, bills due and your 7-day runway',
 'get_transaction_details':'looking up a recorded transaction by its TX- reference',
 'get_recent_transactions':'your most recent recorded transactions',
 'get_data_quality':'data-quality rates and alerts',
 'get_import_summary':'whether your latest upload was saved and how many imported and manual records you have',
 'get_financing_matches':'indicative financing matches',
 'get_rbf_quote':'indicative revenue-based financing quotes',
 'get_business_maturity':'your business maturity stage and next-stage gap',
 'get_business_highlights':'recorded incentive and receivables highlights',
 'get_financing_status':'a specific authorized financing application status',
 'get_financing_details':'a specific authorized financing application requested amount',
 'run_survival_simulation':'hypothetical operating-result simulations',
 'run_cash_impact_scenario':'hypothetical purchase and incremental hiring cash-impact scenarios',
 'calculate_loan_repayment':'loan repayment estimates from the amount, rate and term you give'}

def capability_answer(definitions):
 names={d['function']['name'] for d in definitions}
 supported=[label for name,label in LABELS.items() if name in names]
 return 'Welcome! I can help with financial education and permitted application guidance'+('. For your current account, I can also help with '+ '; '.join(supported) if supported else '')+'. I cannot execute payments, change business records or approve financing.'

def default_period(c,mid,today):
 from copilot.cash_impact import latest_data
 latest=latest_data(c,mid);anchor=min(date.fromisoformat(latest),today) if latest else today
 if anchor.day!=calendar.monthrange(anchor.year,anchor.month)[1]:anchor=anchor.replace(day=1)-timedelta(days=1)
 return {'start':anchor.replace(day=1).isoformat(),'end':anchor.isoformat()}

def snapshot(state):
 return {k:copy.deepcopy(v) for k,v in state['entities'].items() if k in SCENARIO_KEYS}

def prepare_state(previous,updated,text):
 """Different cost types are separate unless the user explicitly combines them."""
 # An expansion cost is a one-time outflow for the existing scenario contract.
 if 'expansion_cost' in updated['entities']:
  updated['entities']['one_time_cost']=updated['entities'].pop('expansion_cost')
  updated['resolved']=list(dict.fromkeys('one_time_cost' if k=='expansion_cost' else k for k in updated['resolved']))
  if (updated.get('pending') or {}).get('entity')=='expansion_cost':updated['pending']=None
 # A changed one-time cost ("what if it is 30k?") keeps the earlier option for comparison.
 old_cost=previous['entities'].get('one_time_cost') or previous['entities'].get('expansion_cost')
 new_cost=updated['entities'].get('one_time_cost')
 if old_cost and new_cost and new_cost.get('turn')==updated['turn'] and old_cost['value']!=new_cost['value']:
  prior={**snapshot(previous)};prior.pop('expansion_cost',None);prior['one_time_cost']=old_cost
  kept=[s for s in updated.get('scenarios',[]) if s['one_time_cost']['value']!=old_cost['value']]
  updated['scenarios']=(kept+[prior])[-2:]
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

COMPARE=re.compile(r'\b(?:less|more|least|most)\s+risky\b|\briskier\b|\bsafer\b|\bcompare\b|\bcomparison\b|\bwhich (?:option|one|scenario|is better)\b|\bbetter option\b',re.I)
SCENARIO_KEYS=('business_subject','one_time_cost','expansion_cost','purchase_date','payment_method','recurring_expense','start_date','available_cash','assessment_date')

def one_time(state):
 entities=state['entities']
 return entities.get('one_time_cost') or entities.get('expansion_cost')

def assumed_cash(state):
 """A dated one-time cost with no stated funding is modeled as a cash outflow, and labeled."""
 entities=state['entities']
 return bool(one_time(state)) and 'payment_method' not in entities and 'purchase_date' in entities

def scenario_args(state,today):
 entities=state['entities'];get=lambda key:entities.get(key,{}).get('value')
 args={'assessment_date':get('assessment_date') or today.isoformat(),'horizon_days':90}
 cost=one_time(state)
 if cost is not None:
  # A financing-funded purchase needs financing terms; never model it as cash.
  method=get('payment_method')
  if method in ('financing','mixed'):return None
  if method is None and not get('purchase_date'):return None
  args.update(one_time_cost=float(cost['value']),purchase_date=get('purchase_date') or args['assessment_date'])
 if get('recurring_expense') is not None:
  if not get('start_date'):return None
  args.update(monthly_cost=float(get('recurring_expense')),start_date=get('start_date'))
 if not any(k in args for k in ('one_time_cost','monthly_cost')):return None
 for key in ('one_time_cost','expansion_cost','recurring_expense','available_cash'):
  if key in entities and entities[key].get('currency')!='CNY':raise ClaimError('scenario_currency_mismatch')
 if get('available_cash') is not None:args['user_cash']=float(get('available_cash'))
 # Combined change (C8): the user's % change to recent sales/expenses travels with the cost.
 for key in ('sales_change_percent','expense_change_percent'):
  if get(key) is not None and float(get(key)):args[key]=float(get(key))
 return args

TX_REF=r'\bTX-[A-Za-z0-9-]{4,120}\b'
# Which tools each intent may use; extra proposals outside this map are skipped, not executed.
RELEVANT={
 'sales_analysis':{'get_financial_summary','get_transaction_trends','get_payment_channel_mix','get_income_summary','get_data_quality'},
 'cash_flow':{'get_cash_flow','get_business_highlights','get_cash_flow_alerts','get_income_summary','get_cashflow_book'},
 'decision_support':{'get_cashflow_book','get_cash_flow','run_cash_impact_scenario','get_financial_summary','get_business_highlights','get_cash_flow_alerts','get_income_summary','get_business_maturity','get_financing_matches'},
 'financing':{'get_financing_status','get_financing_details','get_financing_matches','get_rbf_quote','get_business_maturity'},
 'payment_channels':{'get_payment_channel_mix','get_financial_summary'},
 'simulation':{'run_survival_simulation','get_financial_summary','get_cash_flow'},
 'transactions':{'get_transaction_details','get_recent_transactions','get_data_quality','get_import_summary'},
 'data_quality':{'get_data_quality','get_recent_transactions','get_import_summary'},
 'business_growth':{'get_business_maturity','get_income_summary','get_financing_matches'},
 'loan_calculation':{'calculate_loan_repayment'},
 'past_what_if':{'get_income_summary'}}
KEYWORD_TOOLS=[(r'\balerts?\b|\bwarnings?\b','get_cash_flow_alerts'),(r'\bexpenses?\b|\bnet income\b|\bprofit\b|\baverages?\b','get_income_summary'),
 (r'\btrends?\b|\bover time\b|\bmonth by month\b|\bmonthly (?:sales|revenue)\b','get_transaction_trends'),
 (r'\bfinancing (?:options|matches)\b|\bwhich (?:loan|financing)\b','get_financing_matches'),(r'\brbf\b|\brevenue[- ]based\b','get_rbf_quote')]
from copilot.conversation_routes import BOOK,OWN_AVERAGE
KEYWORD_TOOLS.append((BOOK.pattern,'get_cashflow_book'))
from copilot.conversation_routes import IMPORTS,QUALITY,DASHBOARD_DIFF
KEYWORD_TOOLS.append((IMPORTS.pattern,'get_import_summary'))
# A dependable default tool per intent when the model proposes none.
DEFAULT_TOOL={'transactions':'get_recent_transactions','data_quality':'get_data_quality','business_growth':'get_business_maturity','loan_calculation':'calculate_loan_repayment','past_what_if':'get_income_summary'}
# Values each backend calculation needs before it runs; a missing one becomes one question.
NEEDS={'loan_calculation':[('financing_amount','How much do you plan to borrow?'),('annual_interest_rate','What annual interest rate should I use for the loan?'),('financing_duration','Over how many months or years would you repay it?')],
 'past_what_if':[('past_expense','How much was the cost you want to leave out?'),('reporting_period','Which month was that cost in?')],
 'simulation':[('sales_change_percent','By what percentage would sales change?'),('expense_change_percent','Should expenses stay the same, or change by a percentage?'),('simulation_duration','How many months should I simulate: one, three or six?')]}

def loan_args(entities):
 get=lambda k:(entities.get(k) or {}).get('value')
 if not all(get(k) is not None for k in ('financing_amount','annual_interest_rate','financing_duration')):return None
 args={'principal':float(get('financing_amount')),'annual_rate_percent':float(get('annual_interest_rate')),'months':int(get('financing_duration'))}
 if get('interest_rate_change'):args['rate_change_percent']=float(get('interest_rate_change'))
 return args

MONTH_NAMES=r'(?P<m>jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?'

def lookup_day(text,today):
 """A past calendar day the user names ("oct2", "October 2nd", "2 Oct", "2026-10-02", "yesterday"); never a future date."""
 from copilot.conversation_state import MONTHS
 if re.search(r'\byesterday\b',text,re.I):return (today-timedelta(days=1)).isoformat()
 iso=re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b',text)
 match=re.search(r'\b'+MONTH_NAMES+r'\s*(?P<d>\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s*(?P<y>\d{4}))?|\b(?P<d2>\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m2>jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b(?:,?\s*(?P<y2>\d{4}))?',text,re.I)
 try:
  if iso:value=date(int(iso[1]),int(iso[2]),int(iso[3]))
  elif match:
   month=MONTHS[(match['m'] or match['m2']).lower()];number=int(match['d'] or match['d2']);year=match['y'] or match['y2']
   value=date(int(year) if year else today.year,month,number)
   if not year and value>today:value=value.replace(year=value.year-1)
  else:return None
 except ValueError:return None
 return value.isoformat() if value<=today else None

NOT_NAMES={'my','the','a','an','that','this','last','latest','recent','single','manual','one','each','every','your','new','first','sale','sales','expense','which','what','any','no','of','for','is'}

def transaction_name(text):
 """The user's own label for a transaction ("my test3 transaction", 'transaction "test3"'); never a TX- reference."""
 quoted=re.search(r'["“]([A-Za-z0-9 _.-]{2,40})["”]',text)
 if quoted:return quoted.group(1).strip()
 called=re.search(r'\btrans\w*ction\s+(?:called|named|labell?ed|ref(?:erence)?)\s+([A-Za-z0-9_.-]{2,40})',text,re.I)
 if called and called.group(1).lower() not in NOT_NAMES:return called.group(1)
 for match in re.finditer(r'\btrans\w*ction\s+(?:called|named|labell?ed|ref(?:erence)?)\s+([A-Za-z0-9_.-]{2,40})|\b([A-Za-z0-9_.-]{2,40})\s+trans\w*ction\b',text,re.I):
  word=match.group(1) or match.group(2)
  if word.lower() in NOT_NAMES or word.upper().startswith('TX-'):continue
  if match.group(1) or re.search(r'\d',word):return word
 return None

def comparison_args(state,today,text):
 """Up to three remembered option sets, each bound only to this conversation's validated inputs."""
 if not COMPARE.search(text) or not state.get('scenarios'):return []
 options=[]
 for entities in state['scenarios']+[snapshot(state)]:
  args=scenario_args({'entities':entities},today)
  if args and args not in options:options.append(args)
 return options[-3:] if len(options)>=2 else []

MAX_TOOL_CALLS=5 # per message (orchestrator design); the whole-turn deadline still applies

def requests(plan,state,c,mid,today,definitions,text,notes=None):
 """At most MAX_TOOL_CALLS executions per message. All arguments remain schema-checked by the gateway."""
 notes=[] if notes is None else notes
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
 if len(proposals)>MAX_TOOL_CALLS:raise ClaimError('tool_count_exceeded')
 if scenario and 'run_cash_impact_scenario' in allowed and not any(p['name']=='run_cash_impact_scenario' for p in proposals):
  # Complete scenario inputs are always modeled; the backend binds every argument.
  notes.append('scenario_added_by_backend');proposals=[{'name':'run_cash_impact_scenario','arguments':{}},*proposals][:MAX_TOOL_CALLS]
 # Workbook questions (who owes me, overdue, bills due, 7-day runway) are answered from the Cash Flow tab workbook, not the forecast.
 book=bool(BOOK.search(text)) and 'get_cashflow_book' in allowed and intent in ('cash_flow','decision_support') and not scenario
 if book:proposals=[p for p in proposals if p['name']!='get_cash_flow']
 if not scenario and not book and intent in ('decision_support','cash_flow') and 'get_cash_flow' in allowed and not any(p['name']=='get_cash_flow' for p in proposals):
  # Affordability and cash-flow questions always show the existing forecast figures the app already has.
  notes.append('cash_flow_added_by_backend');proposals=[{'name':'get_cash_flow','arguments':{}},*proposals][:MAX_TOOL_CALLS]
 if re.search(TX_REF,text) and intent=='transactions' and 'get_transaction_details' in allowed and not any(p['name']=='get_transaction_details' for p in proposals):
  notes.append('transaction_lookup_added_by_backend');proposals=[{'name':'get_transaction_details','arguments':{}},*proposals][:MAX_TOOL_CALLS]
 elif not proposals and DEFAULT_TOOL.get(intent) in allowed:
  notes.append('default_tool_added_by_backend');proposals=[{'name':DEFAULT_TOOL[intent],'arguments':{}}]
 # Explicit module words ("alerts", "expenses", "net income") always fetch that module's data when relevant.
 for pattern,tool in KEYWORD_TOOLS:
  if re.search(pattern,text,re.I) and tool in allowed and tool in RELEVANT.get(intent,set()) and not any(p['name']==tool for p in proposals):
   notes.append('keyword_tool_added:'+tool);proposals=[{'name':tool,'arguments':{}},*proposals][:MAX_TOOL_CALLS]
 if DASHBOARD_DIFF.search(text) and 'get_financial_summary' in allowed and intent=='sales_analysis':
  # The Dashboard opens on the last 90 days of records; fetch that window next to the period the chat used.
  end=c.financial_data.as_of(mid);dash={'start':(end-timedelta(days=89)).isoformat(),'end':end.isoformat()}
  notes.append('dashboard_period_added_by_backend')
  planned=[('get_financial_summary',dict(period)),('get_financial_summary',dash)]
  if 'get_income_summary' in allowed:planned.append(('get_income_summary',dash))
  return planned
 options=comparison_args(state,today,text) if intent=='decision_support' else []
 if options:
  # Every compared option is recalculated now; earlier projections are never reused.
  if 'run_cash_impact_scenario' not in allowed:raise AccessDenied('Tool is not authorized for this account')
  return [('run_cash_impact_scenario',args) for args in options]
 result=[]
 for proposal in proposals:
  name=proposal['name'];args=proposal['arguments']
  if name not in allowed:raise AccessDenied('Tool is not authorized for this account')
  if name not in RELEVANT.get(intent,set()):
   # An extra, irrelevant proposal is skipped (and recorded) instead of aborting the whole turn.
   notes.append('tool_not_relevant_to_intent:'+name);continue
  if name=='search_public_financial_information':raise ClaimError('research_approval_required')
  if name=='get_data_quality' and IMPORTS.search(text) and not QUALITY.search(text) and any(p['name']=='get_import_summary' for p in proposals):
   # "How many records were in my import" is answered from the import itself, not data-quality rates.
   notes.append('data_quality_replaced_by_import_summary');continue
  if name=='run_cash_impact_scenario':
   if not scenario:continue
   if any(k not in scenario or v!=scenario[k] for k,v in args.items()):raise ClaimError('scenario_inputs_not_conversation_bound')
   args=scenario
  elif name in ('get_financial_summary','get_transaction_trends','get_payment_channel_mix','get_business_highlights'):
   requested={k:v for k,v in args.items() if k!='granularity'}
   if name=='get_transaction_trends' and re.search(r'best|highest|trend|over time|month by month|monthly',text,re.I):
    # Trends and best periods look across recorded months, not only the reporting month.
    m=c.financial_data.project(mid);available=[date.fromisoformat(r['date']) for r in m.transactions]
    end=max(available) if available else today;start=max(min(available),end-timedelta(days=365 if re.search(r'best|highest',text,re.I) else 182)) if available else end
    target={'start':start.isoformat(),'end':end.isoformat()}
   else:target=comparison if comparison and ((requested and requested==comparison) or (not requested and any(n=='get_financial_summary' for n,a in result) and name=='get_financial_summary')) else period
   # The backend owns reporting periods: a mismatched model range is replaced by the resolved one, never executed.
   if requested and requested!=target:notes.append('model_period_replaced:'+name)
   args={**target,**({'granularity':args.get('granularity','monthly')} if name=='get_transaction_trends' else {})}
  elif name=='get_transaction_details':
   # The reference must be one the user actually typed; the model can never choose another transaction.
   refs=re.findall(TX_REF,text)
   if len(refs)!=1:continue
   args={'reference':refs[0]}
  elif name=='get_recent_transactions':
   singular=re.search(r'\b(?:latest|last|most recent|newest)\s+(?:single\s+|manual\s+)?(?:trans\w*ction|sale|expense|entry)\b(?!s)',text,re.I)
   bound={'limit':1 if singular else min(int(args.get('limit') or 10),20)}
   on=lookup_day(text,today)
   if on:bound.update(start=on,end=on,limit=20) # "my transaction on Oct 2": that day's records
   elif re.search(r'\btoday\b',text,re.I):bound.update(start=today.isoformat(),end=today.isoformat())
   # Only a period named in this message narrows the list; an earlier question's period never does.
   elif entities.get('reporting_period') and entities['reporting_period'].get('turn')==state['turn']:bound.update(entities['reporting_period']['value'])
   if re.search(r'\b(?:single|manual(?:ly)?|entered|typed)\b',text,re.I):bound['source']='manual'
   named=transaction_name(text)
   if named:bound.update(match=named,limit=5)
   args=bound
  elif name=='get_income_summary':
   if intent=='past_what_if' and not entities.get('reporting_period'):continue # asked for, never defaulted
   args=dict(comparison if comparison and args and {k:args.get(k) for k in ('start','end')}==comparison else period)
   if OWN_AVERAGE.search(text) and not entities.get('reporting_period'):
    # Averages with no named period use the last three complete months, so a month's average is not just its total.
    end=date.fromisoformat(args['end']);first=end.replace(day=1)
    for _ in range(2):first=(first-timedelta(days=1)).replace(day=1)
    args={'start':first.isoformat(),'end':end.isoformat()}
  elif name=='get_cashflow_book':args={'reference_date':today.isoformat()} # the backend binds the reference date (business today)
  elif name=='calculate_loan_repayment':
   expected=loan_args(entities)
   if expected is None:continue
   if args and args!=expected:raise ClaimError('loan_inputs_not_conversation_bound')
   args=expected
  elif name=='get_rbf_quote':
   amount=(entities.get('financing_amount') or {}).get('value')
   args={'advance':float(amount)} if amount else {}
  elif name in ('get_data_quality','get_cash_flow_alerts','get_financing_matches','get_business_maturity','get_import_summary'):args={}
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
