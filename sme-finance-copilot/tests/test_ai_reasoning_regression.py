"""MOCKED-PROVIDER regressions for the observed financial-reasoning failures.

Every test here uses a scripted model (tests.conversation_support.script); no request
leaves the process. Real-provider checks live in tests/test_ai_live_gemini.py and are
skipped unless explicitly enabled. Expected figures are derived from the controlled
fixtures and the backend calculations, never from previously observed screenshots.
"""
import json,unittest
from datetime import date,datetime,timezone
from decimal import Decimal
from unittest.mock import patch
from urllib.error import HTTPError
from copilot import conversation_state as cs
from copilot import conversation_evidence as ev
from copilot.cash_impact import run as cash_impact
from copilot.conversation_review import sentences
from copilot.currency_policy import format_money
from copilot.governed_claims import ClaimError,tool_claims,analytical_claims,recommendation_claims,verify_response
from copilot.governed_partner import Partner
from copilot.modules.cashflow import forecast
from copilot.pos_import import POSImportService
from copilot.security import AccessDenied,RateLimiter
from tests.auth_support import setup_identity
from tests.conversation_support import script

TODAY=date(2026,10,16)
NOON=datetime(2026,10,16,5,0,tzinfo=timezone.utc).timestamp() # midday in the merchant timezone
OCTOBER={'start':'2026-10-01','end':'2026-10-16'};SEPTEMBER={'start':'2026-09-01','end':'2026-09-30'}
# Controlled sales fixture reproducing the observed coverage: one October record date, a full September.
SALES={('2026-10-01','2026-10-16'):{'coverage':{'start':'2026-10-16','end':'2026-10-16'},'recorded_net_sales':'11000.00','transaction_count':2},
       ('2026-09-01','2026-09-30'):{'coverage':{'start':'2026-09-01','end':'2026-09-30'},'recorded_net_sales':'181755.62','transaction_count':2918}}

def claims(*keys,kinds=None):
 return {'segments':[{'claim':k,'kind':(kinds or {}).get(k,'derived_calculation')} for k in keys]}

class Base(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=unittest.TestCase();setup_identity(cls.fixture,all_merchants=True)
 @classmethod
 def tearDownClass(cls):cls.fixture.doCleanups()
 def setUp(self):
  f=self.fixture;self.c,self.auth,self.tokens=f.c,f.auth,f.tokens
  self.p=Partner(self.c,self.auth,POSImportService(self.auth,f.store),clock=lambda:NOON);self.g=self.p.gateway
  self.token=self.tokens['owner'];self.ref=self.p.create(self.token,'M002')['conversation'];self.c.limiter=RateLimiter(per_minute=1000)
  original=self.g._read
  def read(token,p,mid,name,args):
   key=(args.get('start'),args.get('end'))
   if name=='get_financial_summary' and key in SALES:
    return {**SALES[key],'period':{'start':key[0],'end':key[1]},'currency':'CNY','source_timestamp':'2026-10-16T05:00:00+00:00'}
   return original(token,p,mid,name,args)
  patcher=patch.object(self.g,'_read',side_effect=read);patcher.start();self.addCleanup(patcher.stop)
 def ask(self,text):return self.p.reply(self.token,'M002',self.ref,text)
 def state(self):return self.p.context(self.token,'M002',self.ref)[1]['conversation_state']
 def kinds(self,result):return {e['claim']:e['kind'] for e in result.get('evidence',[])}
 def answer(self,result):
  """The reply without the backend-appended pending question."""
  pending=self.state().get('pending')
  return result['reply'].replace(pending['text'],'').strip() if pending else result['reply']


class FinancialUnderstanding(Base):
 """Observed Test Case 1: performance -> comparison -> cause -> focus."""
 def test_four_turn_conversation(self):
  current=Decimal(SALES[('2026-10-01','2026-10-16')]['recorded_net_sales']);prior=Decimal(SALES[('2026-09-01','2026-09-30')]['recorded_net_sales'])
  percent=str(abs(((current-prior)/prior*100).quantize(Decimal('.01'))))
  summary=lambda p:{'name':'get_financial_summary','arguments':p}
  plans=[{'intent':'sales_analysis','updates':[('reporting_period','this month')],'tool_requests':[summary(OCTOBER)]},
   {'intent':'sales_analysis','updates':[('comparison_period','last month')],'tool_requests':[summary(OCTOBER),summary(SEPTEMBER)]},
   {'intent':'sales_analysis','tool_requests':[]},
   # The observed failure: an irrelevant tool for the chosen intent used to abort the whole turn.
   {'intent':'decision_support','tool_requests':[{'name':'get_payment_channel_mix','arguments':{}}]}]
  narrations=[
   claims('fact0.net_sales',kinds={'fact0.net_sales':'backend_fact'}), # omits the coverage qualification -> rejected and retried once
   claims('fact0.net_sales','fact0.coverage_gap',kinds={'fact0.net_sales':'backend_fact','fact0.coverage_gap':'data_limitation'}),
   claims('analysis.comparison','analysis.comparison_caveat',kinds={'analysis.comparison_caveat':'data_limitation'}),
   claims('analysis.comparison_caveat','advice.check_imports',kinds={'analysis.comparison_caveat':'data_limitation','advice.check_imports':'recommendation'}),
   claims('advice.check_imports',kinds={'advice.check_imports':'recommendation'})]
  script(self.p,plans,narrations)
  first=self.ask('How is my business performing this month?')
  self.assertEqual(first['verification'],'passed',first);self.assertEqual(first['validation_retry'],'missing_required_qualification')
  self.assertIn(format_money('11000.00'),first['reply']);self.assertIn('only cover October 16, 2026',first['reply']);self.assertLessEqual(sentences(first['reply']),2)
  second=self.ask('Is that better or worse than last month?')
  self.assertEqual(second['verification'],'passed',second);self.assertEqual(second['tools_used'],['get_financial_summary']*2)
  self.assertIn(percent+'% lower than September 2026',second['reply']);self.assertIn('does not show a verified change in business performance',second['reply'])
  self.assertIn('the periods differ in length (16 vs 30 days)',second['reply']);self.assertLessEqual(sentences(second['reply']),2)
  third=self.ask('What is causing the difference?')
  self.assertEqual(third['verification'],'passed',third);self.assertEqual(third['tools_used'],['get_financial_summary']*2) # refreshed, not reused
  self.assertIn('have been imported',third['reply']);self.assertNotRegex(third['reply'],r'(?i)because|due to|customers|season')
  fourth=self.ask('What should I focus on improving?')
  self.assertEqual(fourth['verification'],'passed',fourth);self.assertIn('First, check that all transactions for October 1',fourth['reply'])
  self.assertNotIn("can't safely complete",fourth['reply']);self.assertEqual(self.kinds(fourth).get('advice.check_imports'),'recommendation')

 def test_unsupported_causal_claim_fails_closed(self):
  script(self.p,[{'intent':'sales_analysis','updates':[('reporting_period','this month')],'tool_requests':[{'name':'get_financial_summary','arguments':OCTOBER}]}],
   [{'segments':[{'claim':'fact0.net_sales','kind':'backend_fact'},{'claim':'fact0.coverage_gap','kind':'data_limitation'},{'text':'Sales fell because customers stopped visiting.'}]}])
  r=self.ask('How is my business performing this month?')
  self.assertEqual(r['connection_status'],'fallback');self.assertEqual(r['reason_code'],'unsupported_causal_claim');self.assertEqual(r['failure_category'],'unsupported_financial_assessment')
  self.assertNotIn('customers',r['reply'])

 def test_unhedged_performance_verdict_fails_closed(self):
  script(self.p,[{'intent':'sales_analysis','updates':[('reporting_period','this month')],'tool_requests':[{'name':'get_financial_summary','arguments':OCTOBER}]}],
   [{'segments':[{'claim':'fact0.coverage_gap','kind':'data_limitation'},{'text':'Your sales declined sharply this period.'}]}])
  r=self.ask('How is my business performing this month?');self.assertEqual(r['reason_code'],'unsupported_business_fact')


class EvidenceContracts(unittest.TestCase):
 """Backend records, qualifications and recommendations without any provider."""
 def records(self,*periods):
  out={};results=[]
  for index,p in enumerate(periods):
   value={**SALES[(p['start'],p['end'])],'period':p,'currency':'CNY','source_timestamp':'t'};results.append(('fact'+str(index),'get_financial_summary',value))
   out.update(tool_claims('get_financial_summary',value,prefix='fact'+str(index)))
  out.update(analytical_claims(results));out.update(recommendation_claims(out));return out
 def test_percentage_is_exact_decimal(self):
  r=self.records(OCTOBER,SEPTEMBER);expected=((Decimal('11000.00')-Decimal('181755.62'))/Decimal('181755.62')*100).quantize(Decimal('.01'))
  self.assertEqual(r['analysis.comparison']['value'],str(Decimal('11000.00')-Decimal('181755.62')));self.assertIn(str(abs(expected))+'% lower',r['analysis.comparison']['brief'])
 def test_comparison_requires_its_qualification(self):
  r=self.records(OCTOBER,SEPTEMBER)
  with self.assertRaises(ClaimError) as ctx:verify_response(json.dumps(claims('analysis.comparison')),r,inline=True)
  self.assertEqual(ctx.exception.code,'missing_required_qualification');self.assertEqual(ctx.exception.detail,{'claim':'analysis.comparison','required':'analysis.comparison_caveat'})
 def test_complete_coverage_needs_no_unrelated_warning(self):
  r=self.records(SEPTEMBER);self.assertEqual(r['fact0.net_sales']['requires'],[]);self.assertNotIn('advice.check_imports',r)
  reply,_=verify_response(json.dumps(claims('fact0.net_sales',kinds={'fact0.net_sales':'backend_fact'})),r,inline=True);self.assertEqual(sentences(reply),1)
 def test_whole_calendar_months_are_not_flagged_as_unequal(self):
  aug={'start':'2026-08-01','end':'2026-08-31'};SALES[(aug['start'],aug['end'])]={'coverage':dict(aug),'recorded_net_sales':'100.00','transaction_count':1}
  try:r=self.records(SEPTEMBER,aug)
  finally:SALES.pop((aug['start'],aug['end']))
  self.assertNotIn('analysis.comparison_caveat',r);self.assertEqual(r['analysis.comparison']['requires'],[])
 def test_recommendation_only_from_evidence(self):
  self.assertIn('advice.check_imports',self.records(OCTOBER));self.assertNotIn('advice.check_imports',self.records(SEPTEMBER))
 def test_month_names_allowed_only_for_verified_context(self):
  from copilot.conversation_review import Conversation
  r=self.records(OCTOBER);state=cs.fresh()
  reply,_=Conversation.check(None,{'segments':[{'text':'Here is October so far.'},{'claim':'fact0.coverage_gap','kind':'data_limitation'}]},r,['get_financial_summary'],state,'How is October?',False)
  self.assertIn('October',reply)
  with self.assertRaises(ClaimError) as ctx:Conversation.check(None,{'segments':[{'text':'March looks similar.'}]},r,['get_financial_summary'],state,'How is this month?',False)
  self.assertEqual(ctx.exception.code,'untyped_period_claim')
 def test_verb_may_is_not_a_month_and_speculative_causes_fail(self):
  from copilot.conversation_review import Conversation
  check=lambda t:Conversation.check(None,{'segments':[{'text':t}]},{},[],cs.fresh(),'why?',True)
  self.assertTrue(check('The gap may be because records are missing.')[0]) # previously rejected as the month May
  for text,code in [('Sales may have dropped because customers left.','unsupported_causal_claim'),('Sales fell due to the season.','unsupported_causal_claim'),('Customers may return in October.','untyped_period_claim')]:
   with self.assertRaises(ClaimError) as ctx:check(text)
   self.assertEqual(ctx.exception.code,code,text)
 def test_length_limit_and_detailed_mode(self):
  from copilot.conversation_review import Conversation
  r=self.records(OCTOBER,SEPTEMBER);payload=claims('fact0.net_sales','fact0.coverage_gap','fact1.net_sales',kinds={'fact0.net_sales':'backend_fact','fact0.coverage_gap':'data_limitation','fact1.net_sales':'backend_fact'})
  with self.assertRaises(ClaimError) as ctx:Conversation.check(None,payload,r,[],cs.fresh(),'How are sales?',False)
  self.assertEqual(ctx.exception.code,'response_too_long')
  reply,_=Conversation.check(None,payload,r,[],cs.fresh(),'Explain the breakdown in detail',True);self.assertEqual(sentences(reply),3)


class AmountsAndDates(unittest.TestCase):
 def test_magnitude_suffixes(self):
  for text,value in [('20k','20000.00'),('30k','30000.00'),('30K','30000.00'),('20 thousand','20000.00'),('1.5m','1500000.00'),('¥20k','20000.00'),('CNY 18,000','18000.00'),('2.345k','2345.00')]:
   self.assertEqual(cs.scalar('one_time_cost',text,currency='CNY',today=TODAY)['value'],value,text)
  with self.assertRaises(ClaimError):cs.scalar('one_time_cost','1.234567k',currency='CNY',today=TODAY)
 def test_suffix_survives_source_spans_and_short_answers(self):
  from copilot.conversation_review import sources
  self.assertIn('30k',sources('What if the cost increases to 30k?').values())
  s=cs.fresh();s['pending']={'entity':'one_time_cost','text':'How much would the expansion cost?'}
  self.assertTrue(cs.answer_pending(s,'20k',currency='CNY',today=TODAY));self.assertEqual(s['entities']['one_time_cost']['value'],'20000.00')
 def test_relative_payment_dates(self):
  self.assertEqual(cs.scalar('purchase_date','next month',currency='CNY',today=TODAY),{'value':'2026-11-01','precision':'month'})
  self.assertEqual(cs.scalar('purchase_date','next month',currency='CNY',today=date(2026,12,20))['value'],'2027-01-01')
  self.assertEqual(cs.scalar('purchase_date','next week',currency='CNY',today=TODAY)['value'],'2026-10-23')
 def test_expansion_cost_maps_to_one_time_cost(self):
  previous=cs.fresh();updated=cs.fresh();updated['turn']=1
  cs.put(updated,'expansion_cost',cs.scalar('expansion_cost','20k',currency='CNY',today=TODAY),'20k')
  updated=ev.prepare_state(previous,updated,'20k');self.assertEqual(updated['entities']['one_time_cost']['value'],'20000.00');self.assertNotIn('expansion_cost',updated['entities'])
 def test_dated_cost_without_funding_is_modeled_as_labeled_cash(self):
  s=cs.fresh()
  for key,text in [('one_time_cost','20k')]:s['turn']+=1;cs.put(s,key,cs.scalar(key,text,currency='CNY',today=TODAY),text)
  self.assertIsNone(ev.scenario_args(s,TODAY)) # no date and no funding yet: ask, do not guess
  s['turn']+=1;cs.put(s,'purchase_date',cs.scalar('purchase_date','next month',currency='CNY',today=TODAY),'next month')
  self.assertEqual(ev.scenario_args(s,TODAY)['purchase_date'],'2026-11-01');self.assertTrue(ev.assumed_cash(s))
  s['turn']+=1;cs.put(s,'payment_method',{'value':'financing'},'financing');self.assertIsNone(ev.scenario_args(s,TODAY))


class ForecastAlignment(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=unittest.TestCase();setup_identity(cls.fixture,all_merchants=True);cls.c=cls.fixture.c
 @classmethod
 def tearDownClass(cls):cls.fixture.doCleanups()
 def test_scenario_starts_at_the_opening_balance_date(self):
  c=self.c;assessment=max(TODAY,c.as_of);args={'assessment_date':assessment.isoformat(),'horizon_days':90,'one_time_cost':20000,'purchase_date':assessment.isoformat()}
  result=cash_impact(c,'M002',args);anchor=c.as_of
  self.assertEqual(result['opening_balance_date'],anchor.isoformat())
  span=(assessment-anchor).days+90;m=c.financial_data.project('M002')
  baseline=forecast(m,anchor,span);adjusted=forecast(m,anchor,span,extra_outflows=[{'date':assessment.isoformat(),'amount':'20000.00'}])
  self.assertEqual(result['baseline']['min_balance'],format(Decimal(str(baseline['min_balance'])),'.2f'))
  self.assertEqual(result['adjusted']['closing_balance'],format(Decimal(str(adjusted['closing_balance'])),'.2f'))
  # The one-time payment lowers the closing balance by exactly its amount.
  self.assertEqual(Decimal(result['baseline']['closing_balance'])-Decimal(result['adjusted']['closing_balance']),Decimal('20000.00'))
  if adjusted['runway_days'] is not None:
   self.assertEqual(result['adjusted']['first_negative_date'],date.fromordinal(anchor.toordinal()+adjusted['runway_days']).isoformat())


class WarehouseExpansion(Base):
 """Observed Test Case 2: afford -> 20k -> next month -> effect -> 30k -> less risky."""
 def test_six_turn_scenario_conversation(self):
  plans=[
   {'intent':'decision_support','updates':[('business_subject','warehouse expansion')],'question':{'entity':'one_time_cost','text':'How much would the expansion cost?'},'tool_requests':[{'name':'get_cash_flow','arguments':{}}]},
   {'intent':'decision_support','question':{'entity':'purchase_date','text':'When do you plan to make the payment?'},'tool_requests':[]},
   {'intent':'decision_support','updates':[('purchase_date','next month')],'tool_requests':[]},
   {'intent':'decision_support','tool_requests':[]},
   {'intent':'decision_support','updates':[('one_time_cost','30k')],'tool_requests':[]},
   {'intent':'unknown','tool_requests':[]}]
  basis={'fact0.scenario_basis':'data_limitation'}
  narrations=[claims('fact0.min_balance','fact0.synthetic_basis',kinds={'fact0.synthetic_basis':'data_limitation'}),
   claims('user.one_time_cost',kinds={'user.one_time_cost':'user_assumption'}),
   claims('fact0.adjusted','fact0.scenario_basis',kinds={**basis,'fact0.adjusted':'simulation_result'}),
   claims('fact0.adjusted','fact0.scenario_basis',kinds={**basis,'fact0.adjusted':'simulation_result'}),
   claims('fact0.adjusted','fact0.scenario_basis',kinds={**basis,'fact0.adjusted':'simulation_result'}),
   claims('analysis.scenario_comparison','fact0.scenario_basis',kinds=basis)]
  script(self.p,plans,narrations)
  first=self.ask('Can I afford a warehouse expansion?')
  self.assertEqual(first['verification'],'passed',first);self.assertIn('synthetic demo balance, not your verified available cash',first['reply'])
  self.assertTrue(first['reply'].endswith('How much would the expansion cost?'));self.assertLessEqual(sentences(self.answer(first)),2)
  second=self.ask('20k')
  self.assertEqual(self.state()['entities']['one_time_cost']['value'],'20000.00');self.assertIn(format_money('20000.00'),second['reply'])
  self.assertTrue(second['reply'].endswith('When do you plan to make the payment?'));self.assertNotIn('How much',second['reply'])
  third=self.ask('I plan to pay for it next month.')
  self.assertEqual(third['verification'],'passed',third);self.assertEqual(third['tools_used'],['run_cash_impact_scenario'])
  self.assertEqual(self.state()['entities']['purchase_date']['value'],'2026-11-01');self.assertIn('This assumes you pay from business cash',third['reply'])
  self.assertIn('November 1, 2026',third['reply']);self.assertNotIn('?',third['reply']);self.assertIn('assumption.cash_payment',self.kinds(third))
  fourth=self.ask('How would that affect my cash flow?')
  self.assertEqual(fourth['tools_used'],['run_cash_impact_scenario']);self.assertNotIn('?',fourth['reply'])
  fifth=self.ask('What if the cost increases to 30k?')
  self.assertEqual(self.state()['entities']['one_time_cost']['value'],'30000.00');self.assertIn(format_money('30000.00'),fifth['reply'])
  self.assertEqual([s['one_time_cost']['value'] for s in self.state()['scenarios']],['20000.00'])
  sixth=self.ask('Which option is less risky?')
  self.assertEqual(sixth['verification'],'passed',sixth);self.assertEqual(sixth['tools_used'],['run_cash_impact_scenario']*2) # both recalculated
  # Expected ranking derived independently from the backend scenario calculation.
  runs={cost:cash_impact(self.c,'M002',{'assessment_date':TODAY.isoformat(),'horizon_days':90,'one_time_cost':cost,'purchase_date':'2026-11-01'})['adjusted'] for cost in (20000,30000)}
  for cost,row in runs.items():self.assertIn(format_money(row['min_balance']),sixth['reply'])
  rank=lambda row:(row['first_negative_date'] is None,row['first_negative_date'] or '',Decimal(row['min_balance']))
  if rank(runs[20000])!=rank(runs[30000]):
   best=max(runs,key=lambda k:rank(runs[k]));self.assertIn('The '+format_money(str(best))+' option carries less projected cash-flow risk',sixth['reply'])

 def test_merchant_switch_invalidates_context(self):
  script(self.p,[{'intent':'decision_support','updates':[('one_time_cost','CNY 20000')],'question':{'entity':'purchase_date','text':'When do you plan to make the payment?'},'tool_requests':[]}],[claims('user.one_time_cost',kinds={'user.one_time_cost':'user_assumption'})])
  self.ask('A warehouse expansion would cost CNY 20000')
  with self.assertRaises(AccessDenied):self.p.reply(self.token,'M003',self.ref,'20k')
  other=self.p.create(self.token,'M003')['conversation']
  self.assertEqual(self.p.context(self.token,'M003',other)[1]['conversation_state']['entities'],{})
  with self.assertRaises(AccessDenied):self.p.context(self.token,'M002',self.ref) # creating a new context drops the old page session


class LiveRunFindings(Base):
 """Failure modes observed in the single live Gemini run, reproduced with a scripted provider."""
 def test_mismatched_model_period_uses_backend_period(self):
  wrong={'start':'2026-10-01','end':'2026-10-31'} # the model's own month range, not the resolved "this month"
  script(self.p,[{'intent':'sales_analysis','updates':[('reporting_period','this month')],'tool_requests':[{'name':'get_financial_summary','arguments':wrong}]}],
   [claims('fact0.net_sales','fact0.coverage_gap',kinds={'fact0.net_sales':'backend_fact','fact0.coverage_gap':'data_limitation'})])
  r=self.ask('How is my business performing this month?')
  self.assertEqual(r['verification'],'passed',r);self.assertIn('October 1–16, 2026',r['reply'])
 def test_cash_flow_follow_up_stays_on_ready_scenario_without_cash_question(self):
  plans=[{'intent':'decision_support','updates':[('one_time_cost','CNY 20000'),('purchase_date','next month')],'tool_requests':[]},
   {'intent':'cash_flow','question':{'entity':'available_cash','text':'What is your current available cash?'},'tool_requests':[]}]
  scenario=claims('fact0.adjusted','fact0.scenario_basis',kinds={'fact0.adjusted':'simulation_result','fact0.scenario_basis':'data_limitation'})
  script(self.p,plans,[scenario,scenario])
  self.ask('A warehouse expansion costs CNY 20000 and I pay next month');r=self.ask('How would that affect my cash flow?')
  self.assertEqual(r['verification'],'passed',r);self.assertEqual(r['tools_used'],['run_cash_impact_scenario'])
  self.assertNotIn('available cash?',r['reply']);self.assertIsNone(self.state()['pending'])
 def test_amount_never_becomes_a_percentage(self):
  from copilot.conversation_review import sources,plan_schema
  with self.assertRaises(ClaimError):cs.scalar('sales_change_percent','30k',currency='CNY',today=TODAY)
  spans=sources('What if the cost increases to 30k?');schema=plan_schema(spans,cs.fresh(),text='What if the cost increases to 30k?',currency='CNY',today=TODAY)
  options={o['properties']['entity']['enum'][0]:[spans[x] for x in o['properties']['source']['enum']] for o in schema['properties']['updates']['items']['anyOf']}
  self.assertEqual(options['one_time_cost'],['30k']);self.assertFalse({'sales_change_percent','expense_change_percent','annual_interest_rate','business_subject'}&set(options))
 def test_provider_rejection_records_http_status(self):
  script(self.p,[HTTPError('https://provider.invalid',400,'Bad Request',{},None)],[]);r=self.ask('How are sales?')
  self.assertEqual((r['failure_category'],r['provider_status'],r['provider_http_status']),('provider_unavailable','request_rejected',400))


class ConciseAndFallback(Base):
 def plan(self):return [{'intent':'sales_analysis','updates':[('reporting_period','this month')],'tool_requests':[{'name':'get_financial_summary','arguments':OCTOBER}]}]
 def test_two_overlong_narrations_compose_verified_answer(self):
  long=claims('fact0.net_sales','fact0.coverage_gap','fact0.transaction_count',kinds={'fact0.net_sales':'backend_fact','fact0.coverage_gap':'data_limitation','fact0.transaction_count':'backend_fact'})
  script(self.p,self.plan(),[long,long]);r=self.ask('How is my business performing this month?')
  self.assertEqual(r['connection_status'],'composed');self.assertEqual(r['verification'],'passed');self.assertEqual(r['response_path'],'composed')
  self.assertIn('only cover October 16, 2026',r['reply']);self.assertLessEqual(sentences(r['reply']),2)
  self.assertTrue(any('Some transactions may not be imported' in e['text'] for e in r['evidence'])) # full detail stays in Sources & Tools

 def test_detailed_request_allows_longer_answer(self):
  long=claims('fact0.net_sales','fact0.coverage_gap','fact0.transaction_count',kinds={'fact0.net_sales':'backend_fact','fact0.coverage_gap':'data_limitation','fact0.transaction_count':'backend_fact'})
  script(self.p,self.plan(),[long]);r=self.ask('Explain this month in detail')
  self.assertEqual(r['verification'],'passed');self.assertEqual(sentences(r['reply']),3)

 def test_invented_numbers_are_not_retried(self):
  calls=script(self.p,self.plan(),[{'segments':[{'text':'You earned 999999 this month.'}]}]);r=self.ask('How is my business performing this month?')
  # The narration schema forbids digits in prose, so the contract layer rejects it before claim checks.
  self.assertEqual(r['reason_code'],'invalid_review_contract');self.assertEqual(r['failure_category'],'financial_verification');self.assertNotIn('999999',r['reply'])
  self.assertEqual(len(calls),2) # interpretation + one narration; no retry for fabricated content

 def test_provider_authentication_failure_is_classified(self):
  script(self.p,[HTTPError('https://provider.invalid',401,'Unauthorized',{},None)],[]);r=self.ask('How are sales?')
  self.assertEqual((r['failure_stage'],r['failure_category'],r['provider_status']),('interpretation','provider_unavailable','authentication_rejected'))
  self.assertIn("isn't responding",r['reply']);self.assertTrue(r['retry_available'])
  event=self.auth.audit_records(self.tokens['security_admin'],{'action':'ai_response_provider_error'})[0]
  self.assertEqual((event['failure_stage'],event['failure_category'],event['provider_status']),('interpretation','provider_unavailable','authentication_rejected'))
  self.assertNotIn('Unauthorized',json.dumps(event));self.assertEqual(event['request_id'],r['request_id'])

 def test_provider_timeout_at_narration(self):
  script(self.p,self.plan(),[TimeoutError('slow')]);r=self.ask('How is my business performing this month?')
  self.assertEqual((r['failure_stage'],r['failure_category']),('narration','provider_timeout'));self.assertEqual(r['classification'],'TIMEOUT')

 def test_backend_tool_failure_names_the_tool(self):
  script(self.p,self.plan(),[]);self.g._read.side_effect=ValueError('database unavailable')
  r=self.ask('How is my business performing this month?')
  self.assertEqual((r['failure_stage'],r['failure_category'],r['tool']),('tools','backend_tool_failure','get_financial_summary'))
  self.assertIn("couldn't load the business data",r['reply']);self.assertNotIn('database',r['reply'])

 def test_fallback_keeps_saved_answers_without_repeating_answered_questions(self):
  script(self.p,[{'intent':'decision_support','updates':[('one_time_cost','CNY 20000')],'question':{'entity':'purchase_date','text':'When do you plan to make the payment?'},'tool_requests':[]},TimeoutError('slow')],[claims('user.one_time_cost',kinds={'user.one_time_cost':'user_assumption'})])
  self.ask('The expansion costs CNY 20000');r=self.ask('Hmm, let me think')
  self.assertIn('Your earlier answers are saved. When do you plan to make the payment?',r['reply'])
  self.assertEqual(self.state()['entities']['one_time_cost']['value'],'20000.00');self.assertNotIn('How much',r['reply'])


if __name__=='__main__':unittest.main()
