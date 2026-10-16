"""REAL-PROVIDER acceptance run (not mocked). Skipped unless explicitly enabled.

Enable with COPILOT_LIVE_LLM_TESTS=1 and the allowlisted provider settings in .env.
Only the disposable synthetic test fixture is sent to the provider. Each turn's
safe diagnostics (no prompts, keys or full financial records) are written to the
JSON file named by COPILOT_LIVE_REPORT, when set.
"""
import json,os,unittest
from copilot.conversation_review import sentences
from tests.test_ai_reasoning_regression import Base

ENABLED=os.environ.get('COPILOT_LIVE_LLM_TESTS')=='1'

CONVERSATIONS={
 'financial_understanding':['How is my business performing this month?','Is that better or worse than last month?','What is causing the difference?','What should I focus on improving?'],
 'warehouse_expansion':['Can I afford a warehouse expansion?','20k','I plan to pay for it next month.','How would that affect my cash flow?','What if the cost increases to 30k?','Which option is less risky?'],
}

@unittest.skipUnless(ENABLED,'Live provider test disabled; set COPILOT_LIVE_LLM_TESTS=1 to run it')
class LiveGemini(Base):
 def setUp(self):
  # tests/__init__.py strips provider keys; this explicitly opted-in test restores only the
  # allowlisted provider settings from .env, for this test alone.
  from unittest.mock import patch
  from copilot.llm_config import load_llm_env
  settings={};load_llm_env(environ=settings)
  provider={k:settings[k] for k in ('COPILOT_LLM_BASE_URL','COPILOT_LLM_API_KEY','COPILOT_LLM_MODEL') if k in settings}
  scope=patch.dict(os.environ,{**provider,'COPILOT_GOVERNED_LIVE':'yes','COPILOT_AGENT_MODE':'auto'});scope.start();self.addCleanup(scope.stop)
  from copilot.governed_partner import live_configured
  if not live_configured():self.skipTest('Provider settings are not configured')
  super().setUp()
 def run_conversation(self,name):
  self.ref=self.p.create(self.token,'M002')['conversation'];turns=[]
  for text in CONVERSATIONS[name]:
   r=self.ask(text);state=self.state();pending=(state.get('pending') or {}).get('text')
   body=r['reply'].replace(pending,'').strip() if pending else r['reply']
   turns.append({'question':text,'reply':r['reply'],'connection_status':r.get('connection_status'),'response_path':r.get('response_path'),'verification':r.get('verification'),
    'failure_stage':r.get('failure_stage'),'failure_category':r.get('failure_category'),'reason_code':r.get('reason_code'),'provider_status':r.get('provider_status'),
    'validation_retry':r.get('validation_retry'),'tools_used':r.get('tools_used'),'request_id':r.get('request_id'),'answer_sentences':sentences(body) if body else 0,
    'pending_question':pending,'entities':{k:v.get('value') for k,v in state['entities'].items()},'remembered_options':[s['one_time_cost']['value'] for s in state.get('scenarios',[])]})
  return turns
 def test_both_observed_conversations(self):
  report={name:self.run_conversation(name) for name in CONVERSATIONS}
  if os.environ.get('COPILOT_LIVE_REPORT'):
   with open(os.environ['COPILOT_LIVE_REPORT'],'w',encoding='utf-8') as handle:json.dump(report,handle,indent=1,ensure_ascii=False)
  problems=[]
  for name,turns in report.items():
   for index,turn in enumerate(turns,1):
    if turn['failure_category'] in ('provider_unavailable','provider_timeout'):problems.append(f'{name} turn {index}: provider {turn["provider_status"] or turn["failure_category"]}')
    elif turn['verification']!='passed':problems.append(f'{name} turn {index}: {turn["failure_category"]}/{turn["reason_code"]}')
    limit=4 if 'option' in turn['question'] else 2
    if turn['verification']=='passed' and turn['answer_sentences']>limit:problems.append(f'{name} turn {index}: {turn["answer_sentences"]} sentences')
  warehouse=report['warehouse_expansion']
  if warehouse[1]['entities'].get('one_time_cost')!='20000.00':problems.append('20k was not normalized to 20000.00')
  if warehouse[2]['entities'].get('purchase_date')!='2026-11-01':problems.append('next month was not resolved to 2026-11-01')
  if warehouse[4]['entities'].get('one_time_cost')!='30000.00':problems.append('30k was not normalized to 30000.00')
  if warehouse[5]['tools_used']!=['run_cash_impact_scenario']*2:problems.append('options were not both recalculated')
  asked=[t['pending_question'] for t in warehouse if t['pending_question']]
  if len(asked)!=len(set(asked)):problems.append('a question was repeated')
  self.assertEqual(problems,[],json.dumps(report,indent=1,ensure_ascii=False))
