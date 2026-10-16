"""Synthetic source-ID/narration fixtures for the active two-stage contract."""
import json

def script(partner,plans,narrations):
 plans=iter(plans);narrations=iter(narrations);calls=[]
 def request(messages,schema):
  calls.append((messages,schema))
  if 'intent' in schema.get('properties',{}):
   p=next(plans)
   if isinstance(p,Exception):raise p
   data=json.loads(messages[-1]['content']);spans=data['source_spans']
   updates=[{'entity':entity,'source':next(key for key,value in spans.items() if value==quote)} for entity,quote in p.get('updates',[])]
   value={'intent':p.get('intent','sales_analysis'),'topic_change':p.get('topic_change',False),'updates':updates,'question':p.get('question')}
   if 'tool_requests' in p:value['tool_requests']=p['tool_requests']
  else:
   value=next(narrations)
   if isinstance(value,Exception):raise value
   if callable(value):value=value(messages,schema)
  return {'content':json.dumps(value)}
 partner.conversation_request=request
 return calls
