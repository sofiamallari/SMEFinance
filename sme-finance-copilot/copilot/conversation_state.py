"""Typed, session-only conversational context. No scenario scripts or financial formulas."""
import copy,json,re,calendar
from datetime import date,timedelta
from decimal import Decimal,InvalidOperation
from copilot.governed_claims import ClaimError,money,day,verify_response

# Extensible financial vocabulary: type and meaning, never a fixed question order.
ENTITIES={
 'business_subject':('subject','Business subject'),
 'start_date':('date','Intended start'),
 'purchase_date':('date','Intended one-time outflow date'),
 'comparison_period':('period','Comparison period'),
 'annual_interest_rate':('percent','Interest rate you supplied'),
 'one_time_cost':('money','One-time cost'),
 'recurring_expense':('money','Recurring operating expense'),
 'available_cash':('money','Cash you reported; not independently confirmed'),
 'financing_amount':('money','Financing amount you are considering'),
 'expansion_cost':('money','Expansion cost'),
 'supplier_obligations':('money','Supplier payments you reported'),
 'sales_change_percent':('percent','Assumed sales change'),
 'expense_change_percent':('percent','Assumed expense change'),
 'financing_duration':('duration','Proposed financing duration'),
 'simulation_duration':('duration','Simulation duration'),
 'payment_method':('choice','Intended funding method'),
 'costs_included':('boolean','Whether stated costs include other charges'),
 'reporting_period':('period','Requested reporting period'),
 'assessment_date':('date','Requested assessment date'),
}
INTENTS=['decision_support','sales_analysis','cash_flow','financing','payment_channels','simulation','financial_education','public_research','application_help','out_of_scope','unknown']
UPDATE={'type':'object','properties':{'entity':{'type':'string','enum':list(ENTITIES)},'quote':{'type':'string','maxLength':500}},'required':['entity','quote'],'additionalProperties':False}
CONTEXT_SCHEMA={'type':'object','properties':{
 'intent':{'type':'string','enum':INTENTS},'topic_change':{'type':'boolean'},
 'updates':{'type':'array','maxItems':14,'items':UPDATE},
 'question':{'anyOf':[{'type':'null'},{'type':'object','properties':{'entity':{'type':'string','enum':list(ENTITIES)},'text':{'type':'string','maxLength':400}},'required':['entity','text'],'additionalProperties':False}]}},
 'required':['intent','topic_change','updates','question'],'additionalProperties':False}

def fresh():return {'intent':'unknown','entities':{},'pending':None,'resolved':[],'corrections':[],'facts':{},'topics':[],'turn':0}

def scalar(key,quote,*,currency,today,previous=None,question=''):
 kind,label=ENTITIES[key];text=quote.strip();low=text.lower()
 if kind=='subject':
  if low in ('business','purchase','financing','hiring') or re.search(r'\b(?:my|our|your|you|can|could|would|should|afford|buying|worth|costs|plan|summary)\b',low):raise ClaimError('invalid_subject')
  if not text or len(text)>90 or len(text.split())>6 or re.search(r'[%@<>]|https?://|\b(?:RMB|CNY|USD|PHP)\b',text,re.I):raise ClaimError('invalid_subject')
  return {'value':text}
 if kind=='money':
  values=re.findall(r'(?:RMB|CNY|USD|PHP|[\u00a5\uffe5])?\s*([+-]?\d[\d,]*(?:\.\d{1,2})?)',text,re.I)
  if len(values)!=1 or '%' in text:raise ClaimError('ambiguous_entity_value')
  value=Decimal(values[0].replace(',',''))
  if not value.is_finite() or value<0 or value>Decimal('1000000000000'):raise ClaimError('invalid_entity_value')
  code=next((c for c in ('USD','PHP','CNY','RMB') if re.search(r'\b'+c+r'\b',text,re.I)),None)
  code='CNY' if code=='RMB' or re.search(r'[\u00a5\uffe5]',text) else code or (previous or {}).get('currency') or currency
  return {'value':format(value,'.2f'),'currency':code}
 if kind=='percent':
  if low in ('unchanged','same','no change'):return {'value':'0'}
  values=re.findall(r'[+-]?\d+(?:\.\d+)?',text)
  if len(values)!=1:raise ClaimError('ambiguous_entity_value')
  value=Decimal(values[0]);context=text+' '+question
  if not values[0].startswith(('+','-')):
   directions=re.findall(r'\b(?:decreas\w*|declin\w*|drop\w*|fall\w*|reduc\w*|increas\w*|ris\w*|grow\w*)',context,re.I)
   if directions:value=-abs(value) if re.match(r'decreas|declin|drop|fall|reduc',directions[-1],re.I) else abs(value)
   elif previous and Decimal(previous['value'])<0:value=-abs(value)
  if not value.is_finite() or abs(value)>100:raise ClaimError('invalid_entity_value')
  return {'value':str(value)}
 if kind=='duration':
  match=re.fullmatch(r'\s*(\d+)\s*(months?|years?)\s*[.!]?\s*',text,re.I)
  if not match:raise ClaimError('ambiguous_entity_value')
  months=int(match[1])*(12 if match[2].lower().startswith('year') else 1)
  if not 1<=months<=600:raise ClaimError('invalid_entity_value')
  return {'value':str(months),'unit':'months'}
 if kind=='choice':
  # Values belong to the pending entity's type, not keyword-to-field routing.
  choices={'cash':'cash','in cash':'cash','financing':'financing','finance':'financing','through financing':'financing','mixed':'mixed'}
  if low.rstrip('.!?') not in choices:raise ClaimError('ambiguous_entity_value')
  return {'value':choices[low.rstrip('.!?')]}
 if kind=='boolean':
  if low.rstrip('.!?') not in ('yes','no','true','false','all','none'):raise ClaimError('ambiguous_entity_value')
  return {'value':low.rstrip('.!?') in ('yes','true','all')}
 if kind=='date':
  if low in ('next month','starting next month'):
   start=(today.replace(day=28)+timedelta(days=4)).replace(day=1)
   return {'value':start.isoformat(),'precision':'month'}
  if low in ('today','tomorrow'):return {'value':(today+timedelta(days=1 if low=='tomorrow' else 0)).isoformat()}
  try:return {'value':date.fromisoformat(text).isoformat()}
  except ValueError:raise ClaimError('invalid_entity_value')
 if kind=='period':
  rolling=re.search(r'\blast\s+(\d+)\s+days\b',low)
  if rolling:
   days=int(rolling[1])
   if not 1<=days<=366:raise ClaimError('invalid_entity_value')
   end=today;start=end-timedelta(days=days-1)
  elif low=='previous comparable period' and previous and isinstance(previous.get('value'),dict):
   prior=previous['value'];end=date.fromisoformat(prior['start'])-timedelta(days=1);start=end-timedelta(days=(date.fromisoformat(prior['end'])-date.fromisoformat(prior['start'])).days)
  elif low in ('last month','previous month'):
   end=today.replace(day=1)-timedelta(days=1);start=end.replace(day=1)
  elif low in ('this month','current month'):start=today.replace(day=1);end=today
  elif re.fullmatch(r'(?:q[1-4](?:\s+\d{4})?|last quarter)',low):
   if low=='last quarter':
    q=(today.month-1)//3-1;year=today.year
    if q<0:q=3;year-=1
   else:
    q=int(low[1])-1;year=int(low.split()[-1]) if len(low.split())>1 else today.year
   start=date(year,q*3+1,1);end=date(year,q*3+3,calendar.monthrange(year,q*3+3)[1])
  elif re.fullmatch(r'(?:'+ '|'.join(calendar.month_name[1:])+r')(?:\s+\d{4})?',text,re.I):
   parts=text.split();month=next(i for i,n in enumerate(calendar.month_name) if n.lower()==parts[0].lower())
   year=int(parts[1]) if len(parts)>1 else today.year
   start=date(year,month,1);end=date(year,month,calendar.monthrange(year,month)[1])
  else:
   dates=re.findall(r'\d{4}-\d{2}-\d{2}',text)
   if len(dates)!=2:raise ClaimError('ambiguous_entity_value')
   start,end=map(date.fromisoformat,dates)
  if start>end or (end-start).days>366:raise ClaimError('invalid_entity_value')
  return {'value':{'start':start.isoformat(),'end':end.isoformat()}}
 raise ClaimError('unknown_entity')

def put(state,key,value,quote):
 old=state['entities'].get(key)
 record={**value,'kind':'user_assumption','quote':quote,'turn':state['turn']}
 if old and any(old.get(k)!=v for k,v in value.items()):
  state['corrections']=(state['corrections']+[{'entity':key,'previous':old,'replacement':record}])[-20:]
 state['entities'][key]=record
 if key not in state['resolved']:state['resolved'].append(key)
 if state.get('pending',{} ) and state['pending']['entity']==key:state['pending']=None

def answer_pending(state,text,*,currency,today):
 """Only an unambiguous value of the already requested type is auto-applied."""
 state['turn']+=1
 pending=state.get('pending')
 if not pending:return False
 key=pending['entity'];kind=ENTITIES[key][0]
 # Full statements, corrections and topic changes are left for structured interpretation.
 if re.search(r'\b(?:actually|meant|make|not|instead|rather|referring|about)\b',text,re.I):return False
 if kind=='money' and not re.fullmatch(r'\s*(?:RMB|CNY|USD|PHP|[\u00a5\uffe5])?\s*\d[\d,]*(?:\.\d{1,2})?\s*',text,re.I):return False
 short=bool(re.fullmatch(r'[\s\w,.%+\-\u00a5\uffe5!?]+',text)) and len(text.split())<=5
 if not short:return False
 try:value=scalar(key,text,currency=currency,today=today,previous=state['entities'].get(key),question=pending['text'])
 except (ClaimError,ValueError,InvalidOperation):return False
 put(state,key,value,text)
 state['last_answer']={'entity':key,'text':text,'turn':state['turn']}
 return True

def apply_proposal(state,proposal,text,*,currency,today):
 from jsonschema import Draft202012Validator
 Draft202012Validator(CONTEXT_SCHEMA).validate(proposal)
 new=copy.deepcopy(state)
 if proposal['topic_change'] and state.get('pending') and len(text.split())<=3:raise ClaimError('ambiguous_topic_change')
 restore=bool(re.search(r'\b(?:return|back|resume|revisit)\b',text,re.I))
 candidates=[t for t in new['topics'] if t['intent']==proposal['intent']]
 restored=copy.deepcopy(candidates[-1]) if restore and candidates else None
 if proposal['topic_change']:
  new['topics']=(new['topics']+[{'intent':new['intent'],'entities':new['entities'],'pending':new['pending'],'resolved':new['resolved']}])[-3:]
  new.update(entities={},pending=None,resolved=[],facts={})
  new.pop('research_scope',None)
 if restored:
  new.update(entities=restored['entities'],pending=None,resolved=restored['resolved'])
 new['intent']=proposal['intent']
 for update in proposal['updates']:
  key,quote=update['entity'],update['quote']
  if not quote or quote.casefold() not in text.casefold():raise ClaimError('entity_without_user_source')
  offset=text.casefold().find(quote.casefold());before=text[max(0,offset-25):offset]
  if re.search(r'\bnot\s*$',before,re.I):raise ClaimError('negated_entity_source')
  old=new['entities'].get(key)
  answered=state.get('last_answer',{})
  if answered.get('turn')==state['turn'] and answered.get('text')==text and key!=answered['entity']:raise ClaimError('entity_pending_mismatch')
  # A short answer can only update the requested entity; ambiguity never creates cash.
  if len(text.split())<=3 and state.get('pending') and key!=state['pending']['entity'] and ENTITIES[key][0] not in ('choice','date'):raise ClaimError('entity_pending_mismatch')
  if key=='available_cash' and not re.search(r'cash|balance|funds',quote,re.I) and not (state.get('pending') and state['pending']['entity']==key and re.search(r'\b(?:I|we)\s+have\b.*\bavailable\b',quote,re.I) and not re.search(r'cost|price|salary|worth|credit',quote,re.I)):
   bare=bool(re.fullmatch(r'\s*(?:RMB|CNY|USD|PHP|[\u00a5\uffe5])?\s*\d[\d,]*(?:\.\d{1,2})?\s*',text,re.I))
   pending_cash=state.get('pending') and state['pending']['entity']==key
   already_answered=old and old.get('turn')==state['turn'] and old.get('quote')==text
   if not bare or not (pending_cash or already_answered):raise ClaimError('cash_without_explicit_source')
  anchor=today
  if key=='comparison_period' and 'previous month' in quote.lower() and new['entities'].get('reporting_period'):
   anchor=date.fromisoformat(new['entities']['reporting_period']['value']['start'])
  meaning=(state.get('pending') or {}).get('text','')
  if ENTITIES[key][0]=='percent':meaning+=' '+text[:offset+len(quote)]
  value=scalar(key,quote,currency=currency,today=anchor,previous=(new['entities'].get('reporting_period') if key=='comparison_period' and quote.lower()=='previous comparable period' else old),question=meaning)
  put(new,key,value,quote)
 if any(u['entity']=='reporting_period' for u in proposal['updates']) and not any(u['entity']=='comparison_period' for u in proposal['updates']):
  new['entities'].pop('comparison_period',None)
  new['resolved']=[k for k in new['resolved'] if k!='comparison_period']
 question=proposal['question']
 if question:
  if question['entity'] in new['resolved']:raise ClaimError('repeated_resolved_question')
  if question['text'].count('?')!=1:raise ClaimError('invalid_clarification_question')
  verify_response(json.dumps({'segments':[{'text':question['text']}]}),{})
  new['pending']=question
 return new

def claim_records(state):
 records={}
 for key,entry in state['entities'].items():
  kind,label=ENTITIES[key];value=entry['value']
  if kind=='money':display=label+': '+money(value,entry['currency'])+'.'
  elif kind=='percent':display=label+': '+value+'% (your assumption).'
  elif kind=='duration':display=label+': '+value+' months (your assumption).'
  elif kind=='period':display=label+': '+day(value['start'])+' to '+day(value['end'])+'.'
  elif kind=='date':display=label+': '+(date.fromisoformat(value).strftime('%B %Y') if entry.get('precision')=='month' else day(value))+'.'
  else:display=label+': '+str(value).lower()+' (as you stated).'
  records['user.'+key]={'kind':'user_assumption','metric':key,'value':value,'display':display,**{k:entry[k] for k in ('currency',) if k in entry}}
 return records

def safe_fallback(state):
 """No scenario sequence, guessed values, financial verdict, or repeated question."""
 pending=state.get('pending')
 if pending and pending['entity'] not in state['resolved']:
  return "I can't reach a verified live answer right now. "+pending['text']
 return "I've kept the information you provided for this conversation, but I can't safely complete this assessment right now. Please try again or review the relevant financial module."
