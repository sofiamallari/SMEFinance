"""AI-only regression scenarios; synthetic identities and disposable storage."""
import copy,json,unittest
from datetime import date,timedelta
from unittest.mock import patch
from decimal import Decimal
from copilot import conversation_state as cs
from copilot import conversation_evidence as ev
from copilot.governed_claims import verify_response,ClaimError,analytical_claims,scenario_claims
from copilot.modules.cashflow import forecast
from copilot.governed_partner import Partner
from copilot.pos_import import POSImportService
from copilot.security import AccessDenied,RateLimiter
from tests.auth_support import setup_identity
from tests.conversation_support import script

TODAY=date(2026,10,16)
class Stabilization(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=unittest.TestCase();setup_identity(cls.fixture,all_merchants=True)
 @classmethod
 def tearDownClass(cls):cls.fixture.doCleanups()
 def setUp(self):
  f=self.fixture;self.c,self.auth,self.tokens=f.c,f.auth,f.tokens
  self.p=Partner(self.c,self.auth,POSImportService(self.auth,f.store));self.g=self.p.gateway
  self.token=self.tokens['owner'];self.ref=self.p.create(self.token,'M002')['conversation'];self.c.limiter=RateLimiter(per_minute=1000)
 def ask(self,text):return self.p.reply(self.token,'M002',self.ref,text)
 def state(self):return self.p.context(self.token,'M002',self.ref)[1]['conversation_state']
 def put(self,s,key,text):
  s['turn']+=1;cs.put(s,key,cs.scalar(key,text,currency='CNY',today=TODAY),text)
 def args(self,**kw):return {'assessment_date':'2026-10-16','horizon_days':90,'one_time_cost':15000,**kw}
 def run_scenario(self,**kw):return self.g.execute(self.token,'M002','run_cash_impact_scenario',self.args(**kw),simulation_requested=True)
 def test_capabilities_are_role_filtered_without_provider(self):
  with patch('copilot.conversation_review.provider',side_effect=AssertionError('No provider')):
   r=self.ask('What can you help me with as a business owner?')
  self.assertEqual(r['classification'],'CAPABILITIES');self.assertIn('cash-impact',r['reply']);self.assertNotIn('expense analysis',r['reply'])
  definitions=self.g.definitions(self.tokens['staff'],'M002');self.assertNotIn('cash-impact',ev.capability_answer(definitions))
 def test_policy_and_field_class_contract(self):
  from copilot.governed_tools import OUTPUTS
  from copilot.governance_policy import FIELD_CLASSES,Policy
  self.assertTrue(Policy().available);self.assertEqual(self.p.policy.version,'0.6.0')
  for name,spec in self.p.policy.section('tools').items():
   self.assertFalse(set(spec['output_field_allowlist'])-set(OUTPUTS[name]));self.assertFalse(set(spec['output_field_allowlist'])-set(FIELD_CLASSES[name]))
 def test_month_quarter_and_equal_comparison_period(self):
  for text,start,end in [('September','2026-09-01','2026-09-30'),('August','2026-08-01','2026-08-31'),('Q3','2026-07-01','2026-09-30'),('last quarter','2026-07-01','2026-09-30'),('last 30 days','2026-09-17','2026-10-16')]:
   self.assertEqual(cs.scalar('reporting_period',text,currency='CNY',today=TODAY)['value'],{'start':start,'end':end})
  v=cs.scalar('comparison_period','previous comparable period',currency='CNY',today=TODAY,previous={'value':{'start':'2026-09-01','end':'2026-09-30'}})['value'];self.assertEqual(v,{'start':'2026-08-02','end':'2026-08-31'})
 def test_sales_comparison_uses_backend_decimal_inputs(self):
  results=[]
  for i,(start,end) in enumerate([('2026-09-01','2026-09-30'),('2026-08-01','2026-08-31')]):results.append(('fact'+str(i),'get_financial_summary',self.g.execute(self.token,'M002','get_financial_summary',{'start':start,'end':end})))
  record=analytical_claims(results)['analysis.comparison'];self.assertEqual(Decimal(record['value']),Decimal(results[0][2]['recorded_net_sales'])-Decimal(results[1][2]['recorded_net_sales']));self.assertEqual(record['kind'],'derived_calculation')
 def test_comparison_zero_denominator(self):
  a={'period':{'start':'2026-09-01','end':'2026-09-30'},'currency':'CNY','recorded_net_sales':'12','transaction_count':1}
  b={**a,'recorded_net_sales':'0'};r=analytical_claims([('f0','get_financial_summary',a),('f1','get_financial_summary',b)])
  self.assertIn('undefined',r['analysis.comparison']['display'])
 def test_best_period_retains_ties(self):
  rows=[{'period':m,'recorded_net_sales':'20','granularity':'monthly','transaction_count':1} for m in ['2026-08','2026-09']]
  r=analytical_claims([('f','get_transaction_trends',rows)])['analysis.best_period'];self.assertIn('2026-08',r['display']);self.assertIn('2026-09',r['display'])
 def test_synthetic_opening_distinct_from_latest_data(self):
  v=self.g.execute(self.token,'M002','get_cash_flow',{});self.assertEqual(v['opening_balance_date'],self.c.as_of.isoformat());self.assertIsNone(v['available_cash_if_verified']);self.assertIn('other',str(v['limitations']))
 def test_purchase_cost_adjusts_path_without_mutation(self):
  before=repr(self.c.financial_data.project('M002'));ledger=copy.deepcopy(self.fixture.store.journal.read()[0])
  r=self.run_scenario();delta=Decimal(r['baseline']['closing_balance'])-Decimal(r['adjusted']['closing_balance'])
  self.assertEqual(delta,Decimal('15000'));self.assertEqual(before,repr(self.c.financial_data.project('M002')));self.assertEqual(ledger,self.fixture.store.journal.read()[0])
  self.assertIn('Synthetic demo opening',scenario_claims(r,'f')['f.opening']['display'])
 def test_hiring_incremental_start_and_no_purchase(self):
  r=self.g.execute(self.token,'M002','run_cash_impact_scenario',{'assessment_date':'2026-10-16','horizon_days':90,'monthly_cost':6000,'start_date':'2026-11-01'},simulation_requested=True)
  self.assertTrue(all(s['date']>='2026-11-01' for s in r['schedule']));self.assertEqual(len(r['schedule']),3)
  self.assertEqual(Decimal(r['baseline']['closing_balance'])-Decimal(r['adjusted']['closing_balance']),Decimal('18000'))
 def test_user_cash_is_separate(self):
  r=self.run_scenario(user_cash=40000);self.assertIsNotNone(r['user_cash_adjusted']);self.assertEqual(r['synthetic_opening_balance'],'19800.00');self.assertNotEqual(r['baseline'],r['user_cash_baseline'])
 def test_no_scheduled_obligation_double_count(self):
  m=self.c.financial_data.project('M002');asof=TODAY
  normal=forecast(m,asof,90);adjusted=forecast(m,asof,90,extra_outflows=[{'date':'2026-10-17','amount':'15000'}])
  self.assertEqual(Decimal(str(normal['closing_balance']))-Decimal(str(adjusted['closing_balance'])),Decimal('15000.00'))
  self.assertEqual(normal,forecast(m,asof,90,extra_outflows=[]))
 def test_invalid_schedule_and_outside_horizon(self):
  for kw in [{'one_time_cost':-1},{'horizon_days':181},{'purchase_date':'2026-01-01'},{'user_cash':-1}]:
   with self.subTest(kw=kw),self.assertRaises(Exception):self.run_scenario(**kw)
  with self.assertRaises(AccessDenied):self.g.execute(self.token,'M002','run_cash_impact_scenario',self.args())
 def test_role_and_merchant_scenario_denials(self):
  for role in ('staff','lender_analyst','security_admin'):
   with self.subTest(role=role),self.assertRaises(AccessDenied):self.g.execute(self.tokens[role],'M002','run_cash_impact_scenario',self.args(),simulation_requested=True)
  with self.assertRaises(AccessDenied):self.p.reply(self.token,'M001',self.ref,'Show sales')
 def test_qualitative_and_numeric_unsupported_claims_rejected(self):
  for text in ['After the purchase you would still have some cash left.','Your remaining balance would be positive.','Your cash balance is 100000.','Historical data is missing.']:
   with self.subTest(text=text),self.assertRaises(ClaimError):verify_response(json.dumps({'segments':[{'text':text}]}),{})
  self.assertIn('explain',verify_response(json.dumps({'segments':[{'text':'I can explain how your cash flow forecast works.'}]}),{})[0])
 def test_short_cash_correction_and_independent_hiring(self):
  s=cs.fresh();self.put(s,'one_time_cost','CNY 15000');s['pending']={'entity':'payment_method','text':'Will you pay cash or use financing?'}
  cs.answer_pending(s,'cash',currency='CNY',today=TODAY);self.assertEqual(s['entities']['payment_method']['value'],'cash');self.assertNotIn('available_cash',s['entities'])
  self.put(s,'one_time_cost','CNY 18000');self.assertEqual(ev.scenario_args(s,TODAY)['one_time_cost'],18000)
  newer=copy.deepcopy(s);self.put(newer,'recurring_expense','CNY 6000');newer=ev.prepare_state(s,newer,'Hire someone at CNY 6000 monthly')
  self.assertNotIn('one_time_cost',newer['entities']);combined=ev.prepare_state(newer,copy.deepcopy(newer),'Assess both together');self.assertEqual(combined['entities']['one_time_cost']['value'],'18000.00')
 def test_topic_restoration_and_session_reset(self):
  s=cs.fresh();s['intent']='sales_analysis';self.put(s,'reporting_period','September')
  proposal={'intent':'cash_flow','topic_change':True,'updates':[],'question':None};s=cs.apply_proposal(s,proposal,'Review cash flow',currency='CNY',today=TODAY)
  s=cs.apply_proposal(s,{**proposal,'intent':'sales_analysis'},'Return to sales',currency='CNY',today=TODAY)
  self.assertEqual(s['entities']['reporting_period']['value']['start'],'2026-09-01')
  self.p.close(self.token,'M002',self.ref);self.ref=self.p.create(self.token,'M002')['conversation'];self.assertFalse(self.state()['entities'])
 def test_bounded_tool_selection_and_amount_binding(self):
  definitions=self.g.definitions(self.token,'M002');s=cs.fresh();s['intent']='sales_analysis'
  with self.assertRaises(ClaimError):ev.requests({'tool_requests':[{'name':'get_financial_summary','arguments':{}}]*4},s,self.c,'M002',TODAY,definitions,'Show sales')
  with self.assertRaises(ClaimError):ev.requests({'tool_requests':[{'name':'get_financial_summary','arguments':{'start':'2000-01-01','end':'2000-02-01'}}]},s,self.c,'M002',TODAY,definitions,'Show sales')
 def test_provider_failure_safe_and_actions_denied(self):
  script(self.p,[{'intent':'sales_analysis'}],[TimeoutError('SECRET_CANARY')]);r=self.ask('Show sales');self.assertEqual(r['connection_status'],'fallback');self.assertNotIn('SECRET_CANARY',str(r))
  r=self.ask('Approve my loan now');self.assertEqual(r['classification'],'DENIED')
 def test_verified_double_sources_and_sales_default(self):
  script(self.p,[{'intent':'sales_analysis'}],[{'segments':[{'claim':'fact0.net_sales','kind':'backend_fact'}]}]);r=self.ask('Show sales')
  self.assertEqual(r['verification'],'passed');self.assertEqual(r['connection_status'],'test_double')
  source=self.ask('Where did you get those numbers?');self.assertEqual(source['classification'],'SOURCES');self.assertIn('get_financial_summary',source['reply'])
  self.assertEqual(ev.default_period(self.c,'M002',TODAY),{'start':'2026-09-01','end':'2026-09-30'})
 def test_purchase_multi_turn_pipeline_and_hiring_isolation(self):
  plans=[{'intent':'decision_support','updates':[('one_time_cost','CNY 15000')],'question':{'entity':'payment_method','text':'Will you pay cash or use financing?'}},
   {'intent':'decision_support'},{'intent':'decision_support','updates':[('one_time_cost','CNY 18000')]},
   {'intent':'decision_support','topic_change':True,'updates':[('recurring_expense','CNY 6000'),('start_date','next month')]}]
  narrations=[{'segments':[{'claim':'user.one_time_cost','kind':'user_assumption'}]},
   {'segments':[{'claim':'fact0.adjusted','kind':'simulation_result'},{'claim':'fact0.scenario_basis','kind':'data_limitation'}]},
   {'segments':[{'claim':'fact0.adjusted','kind':'simulation_result'},{'claim':'fact0.scenario_basis','kind':'data_limitation'}]},
   {'segments':[{'claim':'fact0.schedule','kind':'simulation_result'}]}]
  script(self.p,plans,narrations)
  for question in ['Can I buy equipment for CNY 15000?','cash','Actually it costs CNY 18000.','Can I hire someone at CNY 6000 monthly starting next month?']:
   r=self.ask(question);self.assertEqual(r.get('verification'),'passed',r)
  self.assertNotIn('one_time_cost',self.state()['entities']);self.assertNotIn('18000',r['reply']);self.assertIn('6000',r['reply'].replace(',',''))
 def test_model_proposed_two_tools_full_pipeline(self):
  from copilot.conversation_review import sources
  q='Compare September with August.';spans=sources(q)
  updates=[{'entity':key,'source':next(k for k,v in spans.items() if v==value)} for key,value in [('reporting_period','September'),('comparison_period','August')]]
  sequence=iter([{'intent':'sales_analysis','topic_change':False,'updates':updates,'question':None,'tool_requests':[{'name':'get_financial_summary','arguments':{'start':'2026-09-01','end':'2026-09-30'}},{'name':'get_financial_summary','arguments':{'start':'2026-08-01','end':'2026-08-31'}}]}, {'segments':[{'claim':'analysis.comparison','kind':'derived_calculation'}]}])
  self.p.conversation_request=lambda *a:{'content':json.dumps(next(sequence))}
  r=self.ask(q);self.assertEqual(r.get('verification'),'passed',r);self.assertEqual(r['tools_used'],['get_financial_summary']*2);self.assertIn('0.56% higher than August 2026',r['reply']);self.assertIn('Difference:',json.dumps(r['evidence']))
 def test_outflow_outside_horizon_is_not_applied(self):
  m=self.c.financial_data.project('M002');base=forecast(m,TODAY,30)
  self.assertEqual(base,forecast(m,TODAY,30,extra_outflows=[{'date':'2027-01-01','amount':'1000'}]))
 def test_unrequested_simulation_and_missing_data(self):
  v=self.g.execute(self.token,'M002','get_financial_summary',{'start':'2026-01-01','end':'2026-01-31'});self.assertEqual(v['recorded_net_sales'],'0.00');self.assertIsNone(v['coverage'])
  s=cs.fresh();s['intent']='decision_support';self.put(s,'recurring_expense','CNY 6000');self.assertIsNone(ev.scenario_args(s,TODAY))
