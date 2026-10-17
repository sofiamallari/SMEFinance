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

# --- Decisions: a stable, session-scoped identity per decision, with its options history ---------------------------
# Words that say what kind of cost a decision is about (meaning, not exact subject strings).
KIND_WORDS={'one_time':re.compile(r'\b(?:expan\w*|warehouse|equipment|purchas\w*|buy\w*|renovat\w*|budget|machine\w*|vehicle|van|truck|branch|shop|store|oven|invest\w*|fit-?out|refurbish\w*|kitchen|freezer|fridge|signage|website|inventory)\b',re.I),
 'recurring':re.compile(r'\b(?:hir\w*|staff|employ\w*|salar\w*|wages?|payroll|recruit\w*|headcount|workers?|rent\w*)\b',re.I)}
STEM_STOP={'what','which','with','would','could','should','about','that','this','them','then','than','instead','also','want','plan','planning','planned','financially','safer','safe','option','options','only','spend','cost','costs','will','have','around','into','from','each','month','monthly','earning','help','more','less','other','again','back','postpone','postponing','reduce','reducing','reduced','budget','now','right','away'}
# "I also want to hire…": a further commitment planned together with the current decision.
ALSO=re.compile(r'\b(?:also|as well|too|in addition|additionally|on top of)\b',re.I)

def stems(text):
 return {w[:5] for w in re.findall(r'[a-z]{4,}',(text or '').lower()) if w not in STEM_STOP}

def cost_entity(entities):
 return 'one_time_cost' if (entities.get('one_time_cost') or entities.get('expansion_cost')) else 'recurring_expense' if entities.get('recurring_expense') else None

def kind_of(entities):
 key=cost_entity(entities)
 if key:return 'one_time' if key=='one_time_cost' else 'recurring'
 subject=((entities.get('business_subject') or {}).get('value') or '')
 return next((k for k,p in KIND_WORDS.items() if p.search(subject)),None)

def new_decision(state,entities):
 state['decision_seq']=int(state.get('decision_seq') or 0)+1
 subject=((entities.get('business_subject') or {}).get('value'))
 return {'id':'d'+str(state['decision_seq']),'kind':kind_of(entities),'subject':subject,'aliases':[subject] if subject else []}

def decisions(state):
 """Every decision in this conversation: the active one first, then saved topics and the parked topic (newest first)."""
 out=[]
 if state.get('decision'):out.append({'active':True,'decision':state['decision'],'entities':state.get('entities') or {},'options':state.get('options') or [],'topic':None})
 parked=state.get('parked') or {}
 for topic in [parked]+list(reversed(state.get('topics') or [])):
  d=topic.get('decision')
  if d and all(x['decision']['id']!=d['id'] for x in out):out.append({'active':False,'decision':d,'entities':topic.get('entities') or {},'options':topic.get('options') or [],'topic':topic})
 return out

def score(item,text):
 """How clearly the message refers to this decision: shared subject stems, or words of its kind of cost."""
 d=item['decision'];words=stems(text)
 named=bool(words&set().union(*[stems(a) for a in d.get('aliases') or [d.get('subject')]])) if (d.get('aliases') or d.get('subject')) else False
 kind=bool(d.get('kind') and KIND_WORDS[d['kind']].search(text))
 return 2*named+kind

def referenced(state,text,*,saved_only=False):
 """The decision this message is about, by meaning and stored context; None when nothing refers to one."""
 ranked=sorted(((score(item,text),not item['active'],item) for item in decisions(state)),key=lambda x:(x[0],-x[1]),reverse=True)
 if not ranked or ranked[0][0]==0:return None
 best=ranked[0][2]
 if saved_only and best['active']:return None
 return best

def restore(state,item,carry=None,previous=None):
 """Make a saved decision the active one again; the current one is saved with its identity and options.
 carry: this turn's new values (e.g. a quantity), applied to the restored decision. previous: the state before this
 message; the current decision is saved as it was then, since this message is about the other decision."""
 from copilot.conversation_state import topic_entry
 topic=item['topic'];target=item['decision']['id']
 same=previous and (previous.get('decision') or {}).get('id')==(state.get('decision') or {}).get('id')
 current=topic_entry(previous if same else state) if (state.get('decision') or state.get('entities')) else None
 state['topics']=[t for t in state['topics'] if t is not topic and (t.get('decision') or {}).get('id')!=target]
 if current:
  # The snapshot from before this message is already correct; only a snapshot taken now sheds this turn's values.
  if not same:
   for k in list(carry or {}):current['entities'].pop(k,None)
  if current['entities'] or current['decision']:state['topics']=(state['topics']+[current])[-5:]
 if (state.get('parked') or {}).get('decision') and state['parked']['decision']['id']==target:state['parked']=None
 shared={k:copy.deepcopy(v) for k,v in state['entities'].items() if k in SHARED_KEYS}
 state.update(entities=copy.deepcopy(topic.get('entities') or {}),resolved=list(topic.get('resolved') or []),pending=copy.deepcopy(topic.get('pending')),
  decision=copy.deepcopy(topic['decision']),options=copy.deepcopy(topic.get('options') or []),scenarios=copy.deepcopy(topic.get('scenarios') or []))
 # Business-wide assumptions (an assumed sales or expense change) stay in force across decisions.
 for k,v in shared.items():
  if k not in state['entities']:state['entities'][k]={**v,'carried':True};state['resolved'].append(k)
 for k,v in (carry or {}).items():
  state['entities'][k]=copy.deepcopy(v)
  if k not in state['resolved']:state['resolved'].append(k)
 return state

def maybe_restore(previous,updated,text):
 """A message about an earlier decision ("reducing the expansion budget", "the hires") makes it active again."""
 if updated.get('intent') not in ('decision_support','simulation','cash_flow','unknown'):return False
 turn=updated['turn'];incoming={k:v for k,v in updated['entities'].items() if v.get('turn')==turn}
 if any(k in incoming for k in ('one_time_cost','recurring_expense','expansion_cost')):return False
 item=referenced(updated,text,saved_only=True)
 if not item:return False
 restore(updated,item,carry={k:v for k,v in incoming.items() if k not in ('business_subject',)},previous=previous)
 updated['intent']='decision_support'
 return True

# Assumptions about the whole business, not one decision.
SHARED_KEYS=('sales_change_percent','expense_change_percent')

def bind_dates(updated,text,previous=None):
 """A date belongs to the event the user described: a hiring start never becomes a purchase payment date, the start of
 an assumed sales change is not the assessment date, and a postponement date is not the planned payment date."""
 entities=updated['entities'];turn=updated['turn'];old=(previous or {}).get('entities') or {}
 now={k for k,v in entities.items() if v.get('turn')==turn}
 def undo(key):
  # Put back the value the decision had before this message (or nothing).
  if key in old and (updated.get('decision') or {}).get('id')==((previous or {}).get('decision') or {}).get('id'):entities[key]=copy.deepcopy(old[key])
  else:
   entities.pop(key,None);updated['resolved']=[k for k in updated['resolved'] if k!=key]
 # "Sales decrease by 20% starting November": the change starts then; the projection still starts today.
 changing=any(k in now for k in SHARED_KEYS) or (any(k in entities for k in SHARED_KEYS) and re.search(r'\b(?:sales|revenue|expenses?|costs?)\b',text,re.I))
 if 'assessment_date' in now and changing:
  entities['change_start_date']={**entities['assessment_date'],'kind':'user_assumption'};undo('assessment_date')
  if 'change_start_date' not in updated['resolved']:updated['resolved'].append('change_start_date')
 # "Postponing the investment until April 2027": that date belongs to the postponed alternative only.
 for key in ('purchase_date','start_date'):
  entry=entities.get(key)
  if key in now and entry and POSTPONE.search(text[:max(0,text.lower().find(entry.get('quote','').lower()))][-60:] or '') and updated.get('decision'):
   updated['decision']['postponed_date']=entry['value'];undo(key);now.discard(key)
 recurring_now='recurring_expense' in now or ('one_time_cost' not in now and kind_of(entities)=='recurring')
 one_time_now='one_time_cost' in now or ('recurring_expense' not in now and kind_of(entities)=='one_time')
 move=lambda a,b:(entities.__setitem__(b,entities.pop(a)),updated.__setitem__('resolved',list(dict.fromkeys(b if k==a else k for k in updated['resolved']))))
 if 'purchase_date' in now and recurring_now and not one_time_now:
  if 'start_date' in now:entities.pop('purchase_date') # the same date offered twice: it is the start of the recurring cost
  else:move('purchase_date','start_date')
 elif 'start_date' in now and one_time_now and not recurring_now and 'purchase_date' not in now:move('start_date','purchase_date')
 # A recurring-only decision has no one-time payment metadata.
 if 'recurring_expense' in entities and 'one_time_cost' not in entities and 'expansion_cost' not in entities:
  for key in ('purchase_date',):
   if key in entities:entities.pop(key)
 updated['resolved']=[k for k in updated['resolved'] if k in entities or k==(updated.get('pending') or {}).get('entity')]
 if (updated.get('pending') or {}).get('entity')=='purchase_date' and 'one_time_cost' not in entities and 'recurring_expense' in entities:updated['pending']=None

def record_options(updated):
 """Every proposed or revised cost stays available for this decision, even before all inputs are complete."""
 entities=updated['entities'];key=cost_entity(entities)
 if not key or not updated.get('decision'):return
 entry=entities[key]
 options=updated.setdefault('options',[])
 option={'entity':key,'value':entry['value'],'currency':entry.get('currency','CNY'),'quote':entry.get('quote',''),'turn':entry.get('turn')}
 if key=='recurring_expense' and entities.get('quantity'):option['quantity']=entities['quantity']['value']
 same=lambda o:(o['entity'],o['value'],o.get('quantity'))==(option['entity'],option['value'],option.get('quantity'))
 if not any(same(o) for o in options):
  option['label']='proposed' if not any(o['entity']==key for o in options) else 'revised'
  updated['options']=(options+[option])[-6:]

def stabilize_subject(previous,updated):
 """A paraphrase ("expansion", "expansion budget") keeps the decision's first subject; it is kept as an alias."""
 d=updated.get('decision');new=(updated['entities'].get('business_subject') or {})
 if not d or not new:return
 if not d.get('subject'):d['subject']=new['value'];d['aliases']=[new['value']];return
 if new.get('value')==d['subject']:return
 if new.get('turn')==updated['turn'] and (stems(new['value'])&stems(d['subject']) or not stems(new['value'])):
  d['aliases']=list(dict.fromkeys((d.get('aliases') or [])+[new['value']]))[-6:]
  updated['entities']['business_subject']={**new,'value':d['subject']}

def prepare_state(previous,updated,text):
 """Different cost types are separate decisions unless the user combines them; each decision keeps its identity."""
 updated.setdefault('options',[]);updated.setdefault('links',[])
 # An expansion cost is a one-time outflow for the existing scenario contract.
 if 'expansion_cost' in updated['entities']:
  updated['entities']['one_time_cost']=updated['entities'].pop('expansion_cost')
  updated['resolved']=list(dict.fromkeys('one_time_cost' if k=='expansion_cost' else k for k in updated['resolved']))
  if (updated.get('pending') or {}).get('entity')=='expansion_cost':updated['pending']=None
 before=(updated.get('decision') or {}).get('id')
 updated=separate_costs(previous,updated,text)
 if (updated.get('decision') or {}).get('id')==before:maybe_restore(previous,updated,text)
 bind_dates(updated,text,previous)
 # Identity: a decision gets an id the first time it has a subject or a cost; paraphrases keep it.
 if not updated.get('decision') and updated.get('intent')=='decision_support' and (cost_entity(updated['entities']) or updated['entities'].get('business_subject')):
  updated['decision']=new_decision(updated,updated['entities'])
 if updated.get('decision') and not updated['decision'].get('kind'):updated['decision']['kind']=kind_of(updated['entities'])
 stabilize_subject(previous,updated)
 record_options(updated)
 return updated

def separate_costs(previous,updated,text):
 # Any material change to a complete scenario ("what if it is 30k?", "hire two instead", "and sales drop 20%")
 # keeps the earlier complete version for comparison; the active scenario is recalculated from the new inputs.
 from datetime import date as _date
 complete=lambda entities:scenario_args({'entities':entities},_date.today()) is not None
 changed=[k for k in MATERIAL_KEYS if k in updated['entities'] and updated['entities'][k].get('turn')==updated['turn']
          and (previous['entities'].get(k) or {}).get('value')!=updated['entities'][k].get('value')]
 if changed and previous.get('intent')==updated.get('intent') and complete(previous['entities']):
  prior=snapshot(previous);prior.pop('expansion_cost',None)
  if 'expansion_cost' in previous['entities'] and 'one_time_cost' not in prior:prior['one_time_cost']=previous['entities']['expansion_cost']
  value=lambda s:{k:(v or {}).get('value') for k,v in s.items()}
  kept=[s for s in updated.get('scenarios',[]) if value(s)!=value(prior)]
  updated['scenarios']=(kept+[prior])[-3:]
 combine=bool(re.search(r'\b(?:both|combine|together)\b',text,re.I))
 incoming={k for k,v in updated['entities'].items() if v.get('turn')==updated['turn']}
 old=previous['entities']
 separate=(('recurring_expense' in incoming and 'one_time_cost' in old and 'one_time_cost' not in incoming) or ('one_time_cost' in incoming and 'recurring_expense' in old and 'recurring_expense' not in incoming))
 if separate and not combine:
  from copilot.conversation_state import topic_entry
  prior=previous.get('decision')
  saved=any((t.get('decision') or {}).get('id')==prior['id'] for t in updated['topics']) if prior else any(t.get('entities')==old for t in updated['topics'])
  if not saved:
   entry=topic_entry(previous);entry['pending']=None
   if not entry['decision']:entry['decision']=new_decision(updated,old)
   prior=entry['decision'];updated['topics']=(updated['topics']+[entry])[-5:]
  elif not prior:prior=next((t.get('decision') for t in updated['topics'] if t.get('entities')==old and t.get('decision')),None)
  fresh_values={k:v for k,v in updated['entities'].items() if k in incoming}
  kind=kind_of(fresh_values);match=referenced({**updated,'decision':None},text)
  if match and match['decision'].get('kind')==kind and not match['active']:
   # A new value for an earlier decision of this kind ("make the expansion 100k") goes back to that decision.
   updated['entities']={};updated['decision']=None
   restore(updated,match,carry=fresh_values);updated['pending']=None
   return updated
  updated['entities']=fresh_values
  # A separate decision starts its own history; scenario versions of the other decision are not reused.
  updated['resolved']=list(updated['entities']);updated['pending']=None;updated['scenarios']=[]
  updated['decision']=new_decision(updated,updated['entities']);updated['options']=[]
  if updated.get('parked') and prior and (updated['parked'].get('decision') or {}).get('id')==prior['id']:updated['parked']['pending']=None
  # "I also want to hire…": the new decision is planned together with the earlier one (a shared base in comparisons).
  if prior and ALSO.search(text):updated['links']=(updated.get('links',[])+[[prior['id'],updated['decision']['id']]])[-6:]
 if combine:
  for topic in reversed(updated['topics']):
   for key in ('one_time_cost','recurring_expense','payment_method','costs_included','start_date'):
    if key not in updated['entities'] and key in topic['entities']:updated['entities'][key]=copy.deepcopy(topic['entities'][key])
  updated['resolved']=list(updated['entities'])
 return updated

COMPARE=re.compile(r'\b(?:less|more|least|most)\s+risky\b|\briskier\b|\bsafer\b|\bcompare\b|\bcomparison\b|\bwhich (?:option|one|scenario|is better)\b|\bbetter option\b',re.I)
SCENARIO_KEYS=('business_subject','one_time_cost','expansion_cost','purchase_date','payment_method','recurring_expense','start_date','available_cash','assessment_date','quantity','sales_change_percent','expense_change_percent')
# Inputs whose change makes a new scenario version (the previous complete version is kept for comparison).
MATERIAL_KEYS=('one_time_cost','recurring_expense','quantity','purchase_date','start_date','sales_change_percent','expense_change_percent','available_cash')

def one_time(state):
 entities=state['entities']
 return entities.get('one_time_cost') or entities.get('expansion_cost')

def assumed_cash(state):
 """A dated one-time cost with no stated funding is modeled as a cash outflow, and labeled."""
 entities=state['entities']
 return bool(one_time(state)) and 'payment_method' not in entities and 'purchase_date' in entities

def total(unit_cost,quantity):
 """Deterministic total for the scenario: the stated cost is per unit, multiplied by the stated quantity (default 1)."""
 from decimal import Decimal
 return float((Decimal(str(unit_cost))*int(quantity or 1)).quantize(Decimal('.01')))

def horizon(args):
 """90 days by default, extended (up to the tool's 180) so that every stated date falls inside the projection."""
 start=date.fromisoformat(args['assessment_date'])
 dates=[date.fromisoformat(args[k]) for k in ('purchase_date','start_date','change_start_date') if args.get(k)]
 latest=max([(d-start).days for d in dates],default=0)
 args['horizon_days']=90 if latest<=90 else min(latest+15,180)
 return args

def scenario_args(state,today):
 entities=state['entities'];get=lambda key:entities.get(key,{}).get('value')
 args={'assessment_date':get('assessment_date') or today.isoformat(),'horizon_days':90}
 cost=one_time(state)
 if cost is not None:
  # A financing-funded purchase needs financing terms; never model it as cash.
  method=get('payment_method')
  if method in ('financing','mixed'):return None
  if method is None and not get('purchase_date'):return None
  args.update(one_time_cost=total(cost['value'],get('quantity')),purchase_date=get('purchase_date') or args['assessment_date'])
 if get('recurring_expense') is not None:
  if not get('start_date'):return None
  args.update(monthly_cost=total(get('recurring_expense'),get('quantity')),start_date=get('start_date'))
 if not any(k in args for k in ('one_time_cost','monthly_cost')):return None
 for key in ('one_time_cost','expansion_cost','recurring_expense','available_cash'):
  if key in entities and entities[key].get('currency')!='CNY':raise ClaimError('scenario_currency_mismatch')
 if get('available_cash') is not None:args['user_cash']=float(get('available_cash'))
 # Combined change (C8): the user's % change to recent sales/expenses travels with the cost.
 for key in ('sales_change_percent','expense_change_percent'):
  if get(key) is not None and float(get(key)):args[key]=float(get(key))
 if get('change_start_date') and any(k in args for k in SHARED_KEYS) and get('change_start_date')>args['assessment_date']:args['change_start_date']=get('change_start_date')
 # Costs planned together with this decision ("I also want to…") are part of the same projection when they are complete.
 if state.get('decision'):
  for item in base_costs(state,state['decision']['id'],today)[0]:
   if item['kind']=='recurring' and 'monthly_cost' not in args:args.update(monthly_cost=item['amount'],start_date=item['date'])
   elif item['kind']=='one_time' and 'one_time_cost' not in args:args.update(one_time_cost=item['amount'],purchase_date=item['date'])
 horizon(args)
 # A date beyond the longest projection cannot be modelled; the cost is shown as not applied instead of failing the turn.
 end=(date.fromisoformat(args['assessment_date'])+timedelta(days=args['horizon_days'])).isoformat()
 if any(args.get(k) and args[k]>end for k in ('purchase_date','start_date')):return None
 return args

# --- Costs planned together, alternatives and funding needs ------------------------------------------------------------
def linked_ids(state,decision_id):
 return {b if a==decision_id else a for a,b in state.get('links') or [] if decision_id in (a,b)}

def base_costs(state,decision_id,today):
 """Complete costs of the decisions planned together with this one, and the linked decisions that are incomplete."""
 linked=linked_ids(state,decision_id);end=today+timedelta(days=180);included=[];missing=[]
 for item in decisions(state):
  if item['decision']['id'] not in linked:continue
  e=item['entities'];get=lambda k:(e.get(k) or {}).get('value');subject=item['decision'].get('subject') or ('hiring' if item['decision'].get('kind')=='recurring' else 'purchase')
  if get('recurring_expense') and get('start_date') and today.isoformat()<=get('start_date')<=end.isoformat():
   included.append({'kind':'recurring','amount':total(get('recurring_expense'),get('quantity')),'unit':get('recurring_expense'),'quantity':int(get('quantity') or 1),'date':get('start_date'),'subject':subject,'currency':e['recurring_expense'].get('currency','CNY'),'id':item['decision']['id']})
  elif get('one_time_cost') and get('purchase_date') and today.isoformat()<=get('purchase_date')<=end.isoformat() and get('payment_method') not in ('financing','mixed'):
   included.append({'kind':'one_time','amount':total(get('one_time_cost'),get('quantity')),'unit':get('one_time_cost'),'quantity':int(get('quantity') or 1),'date':get('purchase_date'),'subject':subject,'currency':e['one_time_cost'].get('currency','CNY'),'id':item['decision']['id']})
  else:missing.append({'subject':subject,'id':item['decision']['id'],'kind':item['decision'].get('kind'),'options':[o for o in item['options']],'reason':'start date' if item['decision'].get('kind')=='recurring' else 'payment date'})
 return included,missing

def linked_quantities(state,today):
 return {item['quantity'] for item in base_costs(state,state['decision']['id'],today)[0]} if state.get('decision') else set()

NOW=re.compile(r'\b(?:now|today|immediately|right away|straight away)\b',re.I)
REDUCE=re.compile(r'\b(?:reduc\w*|smaller|cut\w*|cheaper|trim\w*|downsiz\w*|scal\w* (?:it )?back|lower (?:budget|cost|amount|spend\w*))\b',re.I)
POSTPONE=re.compile(r'\b(?:postpon\w*|delay\w*|defer\w*|wait\w*|later|hold(?:ing)? off|put(?:ting)? (?:it )?off)\b',re.I)
ORIGINAL=re.compile(r'\b(?:original\w*|full|as planned|go(?:ing)? ahead|proceed\w*|expand\w* (?:now|as)|the plan)\b',re.I)
# "Based on everything we discussed, what would you recommend?": the decision's alternatives, compared again.
RECOMMEND=re.compile(r'\b(?:recommend\w*|advise|advice|what should (?:i|we) do|best (?:option|choice|plan)|which (?:option|one) should)\b',re.I)
LABELS_BY_KIND={'one_time':{'now':'Paying the full {s} cost now','original':'The original {s} plan','reduced':'Reducing the {s} budget','postponed':'Postponing the {s}'},
 'recurring':{'now':'Starting the {s} now','original':'The original {s} plan','reduced':'A lower {s} cost','postponed':'Postponing the {s}'}}

def shared_changes(state):
 out={k:float(state['entities'][k]['value']) for k in SHARED_KEYS if k in state['entities'] and float(state['entities'][k]['value'])}
 start=(state['entities'].get('change_start_date') or {}).get('value')
 if out and start:out['change_start_date']=start
 return out

def alternatives(state,text,today):
 """'Expanding now, reducing the budget or postponing it?': each alternative for the decision the user means, with the
 same 90-day horizon, the costs planned together with it and any assumed sales change. Never re-asks a supplied amount.
 Dates: 'now' is the date of this message; a reduced budget follows the same timing; postponing moves the payment
 beyond the projection (deferred, not cancelled)."""
 recommend=bool(RECOMMEND.search(text))
 if not (COMPARE.search(text) or re.search(r'\bsafest\b',text,re.I) or recommend):return None
 asked=[name for name,pattern in (('now',NOW),('original',ORIGINAL),('reduced',REDUCE),('postponed',POSTPONE)) if pattern.search(text)]
 if 'now' in asked and 'original' in asked:asked.remove('original')
 item=referenced(state,text) or next((d for d in decisions(state) if d['options']),None)
 if not item or not item['options']:return None
 d=item['decision']
 if recommend and len(asked)<2:
  # A recommendation follow-up compares what was compared before (or the decision's own options).
  asked=list(d.get('compared') or ['original','reduced']+(['postponed'] if d.get('postponed_date') else []))
 if len(asked)<2:return None
 if 'now' not in asked and 'original' not in asked and 'reduced' in asked:asked.insert(0,'original')
 kind=d.get('kind') or 'one_time';entity='one_time_cost' if kind=='one_time' else 'recurring_expense'
 opts=[o for o in item['options'] if o['entity']==entity]
 if not opts:return None
 from decimal import Decimal
 subject=d.get('subject') or ('expansion' if kind=='one_time' else 'hiring')
 original=opts[0];reduced=next((o for o in reversed(opts[1:]) if Decimal(o['value'])<Decimal(original['value'])),None)
 # A date the user gave earlier for this decision; "now" in this message is not a stored date.
 entry=item['entities'].get('purchase_date' if kind=='one_time' else 'start_date') or {}
 stored=entry.get('value') if entry.get('turn')!=state.get('turn') or not NOW.search(entry.get('quote','')) else None
 when=today.isoformat() if NOW.search(text) else stored
 date_key='purchase_date' if kind=='one_time' else 'start_date'
 later=d.get('postponed_date') if 'postponed' in asked else None
 if not when and any(n in asked for n in ('now','original','reduced')):
  return {'ask':{'entity':date_key,'text':'When would you pay for the '+subject+' if you go ahead? Timing matters for the comparison.'}}
 if 'reduced' in asked and not reduced:
  return {'ask':{'entity':entity,'text':'How much would the reduced '+subject+' budget be?'}}
 base,missing=base_costs(state,d['id'],today);changes=shared_changes(state)
 # Every option shares one horizon, long enough for the latest stated date (at most 180 days).
 span=horizon({'assessment_date':today.isoformat(),**({'purchase_date':max(x for x in (when,later) if x)} if (when or later) else {}),**({'change_start_date':changes['change_start_date']} if changes.get('change_start_date') else {})})['horizon_days']
 end=(today+timedelta(days=span)).isoformat()
 if later and later>end:later=None # still beyond the longest projection: deferred past it
 def args_for(option,on):
  args={'assessment_date':today.isoformat(),'horizon_days':span}
  for b in base:
   if b['date']>end:continue
   if b['kind']=='recurring':args.update(monthly_cost=b['amount'],start_date=b['date'])
   else:args.update(one_time_cost=b['amount'],purchase_date=b['date'])
  if option and on:
   amount=total(option['value'],option.get('quantity'))
   if kind=='one_time':args.update(one_time_cost=amount,purchase_date=on)
   else:args.update(monthly_cost=amount,start_date=on)
  args.update({k:v for k,v in changes.items() if k!='change_start_date' or v>args['assessment_date']})
  return args if any(k in args for k in ('one_time_cost','monthly_cost','sales_change_percent','expense_change_percent')) else None
 labels=LABELS_BY_KIND[kind];chosen=[]
 for name in ('now','original','reduced','postponed'):
  if name not in asked:continue
  option={'now':original,'original':original,'reduced':reduced,'postponed':original if later else None}[name]
  on=later if name=='postponed' else when
  chosen.append({'name':name,'label':labels[name].format(s=subject),'value':option['value'] if option else None,'quantity':(option or {}).get('quantity'),
   'currency':(option or original).get('currency','CNY'),'date':on if option else None,'args':args_for(option,on)})
 d['compared']=[c['name'] for c in chosen]
 return {'decision':d['id'],'subject':subject,'kind':kind,'options':chosen,'base':base,'missing':[m for m in missing],'changes':changes,'now_assumed':bool(NOW.search(text)) and not stored,
  'deferred':[] if later else [o['value'] for o in opts],'currency':original.get('currency','CNY'),'assessment_date':today.isoformat(),'recommend':recommend}

FUNDING=re.compile(r'\b(?:rbf|revenue[- ]based|financ\w*|loans?|borrow\w*|credit line|advance)\b',re.I)
DECIDE=re.compile(r'\b(?:could|would|can|should|will|might|does|do|is)\b.{0,80}\b(?:help|fund\w*|financ\w*|pay for|cover|bridge|work|make sense|worth|enough|instead)\b',re.I)
NAVIGATE=re.compile(r"\bhow (?:do|can|to|should) (?:i|we)\s+(?:open|use|find|get to|access|go to|navigate|start|create|submit|apply|enter|see|view|run|check)\b|\bwhere (?:is|are|do|can)\b|\b(?:open|show me) the\b.{0,30}\b(?:calculator|page|screen|tab)\b|\bsteps\b|\bguide\b",re.I)

def funding_question(text):
 """'Could revenue-based financing help fund my expansion?' is a decision question, not navigation."""
 return bool(FUNDING.search(text) and DECIDE.search(text) and not NAVIGATE.search(text))

def funding(state,text,today):
 """The funding need for a financing question about a decision: its full cost (the first amount the user gave), and the
 scenario that pays it now from business cash, with the costs planned together with it and any assumed sales change."""
 if not funding_question(text):return None
 item=referenced(state,text) or next((d for d in decisions(state) if d['decision'].get('kind')=='one_time' and d['options']),None)
 if not item:return None
 d=item['decision'];opts=[o for o in item['options'] if o['entity']==('one_time_cost' if d.get('kind')=='one_time' else 'recurring_expense')]
 if not opts:return None
 need=opts[0];subject=d.get('subject') or 'purchase'
 base,missing=base_costs(state,d['id'],today);changes=shared_changes(state)
 args={'assessment_date':today.isoformat(),'horizon_days':90}
 for b in base:
  if b['kind']=='recurring':args.update(monthly_cost=b['amount'],start_date=b['date'])
  else:args.update(one_time_cost=b['amount'],purchase_date=b['date'])
 amount=total(need['value'],need.get('quantity'))
 # The cost is paid on the date the user planned (if any, and modellable), otherwise now.
 planned=(item['entities'].get('purchase_date' if d.get('kind')=='one_time' else 'start_date') or {}).get('value')
 on=planned if planned and today.isoformat()<=planned<=(today+timedelta(days=180)).isoformat() else today.isoformat()
 if d.get('kind')=='one_time':args.update(one_time_cost=amount,purchase_date=on)
 else:args.update(monthly_cost=amount,start_date=on)
 args.update({k:v for k,v in changes.items() if k!='change_start_date' or v>args['assessment_date']})
 horizon(args)
 return {'decision':d['id'],'subject':subject,'kind':d.get('kind'),'need':amount,'currency':need.get('currency','CNY'),'options':[o['value'] for o in opts],'args':args,'base':base,'missing':missing,'changes':changes,'date':on}

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
