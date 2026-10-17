"""Focused claim attribution and purchase reasoning, never production data."""
import json
import unittest
from unittest.mock import patch
from copilot.governed_claims import (ClaimError,purchase_context,assumptions,tool_claims,verify_response,affordability_guidance,render_tool)
from copilot.currency_policy import format_money
from tests import test_ai_governance as governance

QUESTION='If I were to buy an oven worth RMB 10,000, can I afford it as of today, October 15, 2026?'


class ClaimAttribution(unittest.TestCase):
 def setUp(self):self.context=purchase_context(QUESTION);self.records=assumptions(self.context)
 def test_user_price_is_hypothetical_not_business_cash(self):
  text,keys=verify_response(json.dumps({'segments':[{'claim':'user.purchase_price','kind':'user_assumption','value':'10000.00'}]}),self.records)
  self.assertIn('¥10,000.00',text);self.assertIn('your assumption',text);self.assertEqual(keys,['user.purchase_price'])
 def test_user_date_is_natural_and_not_verified_snapshot(self):
  text,_=verify_response(json.dumps({'segments':[{'claim':'user.assessment_date','kind':'user_date','value':'2026-10-15'}]}),self.records)
  self.assertIn('October 15, 2026',text);self.assertIn('not a verified cash snapshot',text)
 def test_assumption_cannot_be_reclassified_or_revalued(self):
  for fields in ({'kind':'backend_fact'},{'value':'20000.00'},{'metric':'available_cash'},{'currency':'USD'}):
   with self.subTest(fields=fields),self.assertRaises(ClaimError):verify_response(json.dumps({'segments':[{'claim':'user.purchase_price',**fields}]}),self.records)
 def test_verified_sales_exact_metric_period_currency(self):
  row={'period':{'start':'2026-07-18','end':'2026-10-15'},'currency':'CNY','recorded_net_sales':'421080.42','transaction_count':6767}
  records=tool_claims('get_financial_summary',row)
  good={'claim':'fact.net_sales','kind':'backend_fact','value':'421080.42','metric':'recorded_net_sales','currency':'CNY','period':row['period']}
  text,_=verify_response(json.dumps({'segments':[good]}),records);self.assertIn('¥421,080.42',text)
  for field,value in [('value','999999.00'),('metric','available_cash'),('currency','PHP'),('period',{'start':'2026-01-01','end':'2026-01-31'})]:
   with self.subTest(field=field),self.assertRaises(ClaimError):verify_response(json.dumps({'segments':[{**good,field:value}]}),records)
 def test_fabricated_merchant_cash_and_revenue_as_cash_rejected(self):
  for reply in ('Your available cash is RMB 10,000.','You can afford this oven.','Sales are available cash.','Your business is profitable.'):
   with self.subTest(reply=reply),self.assertRaises(ClaimError):verify_response(reply,self.records)
  with self.assertRaises(ClaimError):verify_response(json.dumps({'segments':[{'claim':'fact.cash_balance'}]}),self.records)
 def test_simulation_value_requires_actual_engine_record(self):
  v={'baseline_period':{'start':'2026-07-01','end':'2026-09-30'},'assumptions':{'sales_change_percent':-20,'expense_change_percent':0,'months':3},'simulation_results':{'currency':'CNY','baseline_monthly_operating_result':'2000.00','simulated_monthly_operating_result':'1000.00','cumulative_operating_result':'3000.00'}}
  records=tool_claims('run_survival_simulation',v)
  good={'claim':'fact.simulated_monthly_operating_result','kind':'simulation_output','value':'1000.00'}
  self.assertIn('Hypothetical',verify_response(json.dumps({'segments':[good]}),records)[0])
  with self.assertRaises(ClaimError):verify_response(json.dumps({'segments':[{**good,'value':'9999.00'}]}),records)
 def test_external_fact_requires_approved_provenance(self):
  record={'kind':'external_fact','metric':'quoted_public_source','value':'Published quote','display':'Published quote — https://example.org/source'}
  payload=json.dumps({'segments':[{'claim':'public.quote','kind':'external_fact','value':'Published quote'}]})
  with self.assertRaises(ClaimError):verify_response(payload,{'public.quote':record})
  record.update(approved_search=True,source_url='https://example.org/source',retrieved_at='2026-10-16T00:00:00Z')
  self.assertIn('example.org',verify_response(payload,{'public.quote':record})[0])
 def test_cash_followup_does_not_repeat_funding_question(self):
  context=purchase_context('I will pay in cash. The price includes installation.',self.context)
  question=affordability_guidance(context);self.assertNotIn('Will you pay',question);self.assertIn('verified cash position',question)
 def test_cash_payment_is_not_a_cash_balance_statement(self):
  context=purchase_context('I will pay in cash. The ¥10,000 includes delivery and installation',self.context)
  self.assertEqual(context['funding'],'cash');self.assertEqual(context['price'],'10000.00');self.assertNotIn('reported_cash',context);self.assertIn('extra_costs',context)
  self.assertNotIn('user.reported_cash',assumptions(context));self.assertIn('verified cash position',affordability_guidance(context))
 def test_explicit_cash_on_hand_is_still_an_assumption(self):
  context=purchase_context('I have RMB 20,000 in cash.',self.context)
  self.assertEqual(context['reported_cash'],'20000.00');self.assertEqual(context['price'],'10000.00')
 def test_reported_cash_does_not_replace_price_or_become_verified(self):
  context=purchase_context('My available cash is RMB 20,000.',self.context);self.assertEqual(context['price'],'10000.00');self.assertEqual(context['reported_cash'],'20000.00');self.assertEqual(assumptions(context)['user.reported_cash']['kind'],'user_assumption')
 def test_installation_followup_keeps_original_price(self):
  context=purchase_context('Installation costs RMB 500.',self.context);self.assertEqual(context['price'],'10000.00');self.assertEqual(context['additional_cost'],'500.00')
 def test_caution_is_allowed_but_unsupported_positive_verdict_is_not(self):
  self.assertIn('cannot',verify_response('I cannot determine your available cash without verification.',{})[0])
  with self.assertRaises(ClaimError):verify_response('Affordability confirmed.',{})
 def test_down_payment_and_purchase_currency_are_not_confused(self):
  c=purchase_context(QUESTION+' I will use financing with a down payment of RMB 2,000.');self.assertEqual(c['price'],'10000.00');self.assertEqual(c['down_payment'],'2000.00')
  c=purchase_context('My cash balance is USD 20,000.',c);self.assertEqual(c['price'],'10000.00');self.assertEqual(assumptions(c)['user.reported_cash']['currency'],'USD')
 def test_numbered_nonnumeric_explanations_are_not_rejected(self):
  text,_=verify_response('1. Review operating commitments.\n2. Do not treat revenue as cash.',{});self.assertIn('Review',text)
 def test_raw_structures_not_rendered(self):
  row={'period':{'start':'2026-07-18','end':'2026-10-15'},'currency':'CNY','recorded_net_sales':'421080.42','transaction_count':6767};text=render_tool('get_financial_summary',row);self.assertNotIn('{',text);self.assertNotIn("'start'",text);self.assertIn('July 18, 2026 to October 15, 2026',text)


class PurchaseIntegration(governance.GovernanceTests):
 # The former fixed purchase workflow is retired. These exercise the active
 # source-ID contract, retaining financial meaning and denial assertions.
 Q='Can I afford equipment worth RMB 10,000?'
 def scripted(self,plans,narrations):
  from tests.conversation_support import script
  return script(self.partner,plans,narrations)
 def state(self):return self.partner.context(self.token,'M002',self.ref)[1]['conversation_state']
 def test_live_double_accepts_user_price_and_authorized_sales(self):
  self.scripted([{'intent':'decision_support','updates':[('one_time_cost','RMB 10,000')],'question':{'entity':'payment_method','text':'How would you fund this expense?'}}],[{'segments':[{'claim':'user.one_time_cost','kind':'user_assumption'},{'claim':'fact0.net_sales','kind':'backend_fact'}]}])
  r=self.ask(self.Q);self.assertEqual(r['connection_status'],'test_double');self.assertEqual(r['verification'],'passed');self.assertEqual(r['tools_used'],['get_financial_summary']);self.assertIn(format_money(10000),r['reply'])
 def test_numeric_prose_is_not_automatically_retried(self):
  calls=self.scripted([{'intent':'decision_support'}],[{'segments':[{'text':'Your cash is 999999.'}]}])
  r=self.ask(self.Q);self.assertEqual(r['fallback_reason'],'response_validation');self.assertEqual(len(calls),2);self.assertNotIn('999999',r['reply'])
 def test_fabricated_balance_never_reaches_display(self):
  self.scripted([{'intent':'decision_support'}],[{'segments':[{'claim':'fact0.cash_balance','kind':'backend_fact'}]}])
  r=self.ask(self.Q);self.assertEqual(r['fallback_reason'],'response_validation');self.assertNotIn('cash_balance',r['reply'])
 def test_reporting_period_is_sourced_from_the_user(self):
  text='Show my sales for 2026-07-01 to 2026-09-30'
  self.scripted([{'intent':'sales_analysis','updates':[('reporting_period',text)]}],[{'segments':[{'claim':'fact0.net_sales','kind':'backend_fact'}]}])
  r=self.ask(text);self.assertEqual(r['verification'],'passed');self.assertEqual(self.state()['facts']['fact0.net_sales']['period'],{'start':'2026-07-01','end':'2026-09-30'})
 def test_cash_funding_asks_only_an_unresolved_question(self):
  self.scripted([{'intent':'decision_support','updates':[('payment_method','cash')],'question':{'entity':'costs_included','text':'Does that include the other costs?'}}],[{'segments':[{'text':'Other costs are still unknown.'}]}])
  # The stated RMB 10,000 cost and cash payment are filled from the user's own words, so the scenario can be modeled
  # at once; at most the one unresolved question remains and funding is never asked again.
  r=self.ask(self.Q+' I will pay cash.');self.assertEqual(self.state()['entities']['payment_method']['value'],'cash');self.assertLessEqual(r['reply'].count('?'),1);self.assertNotIn('How would you fund',r['reply'])
 def test_exact_cash_followup_does_not_invent_balance(self):
  self.scripted([{'intent':'decision_support','updates':[('one_time_cost','RMB 10,000')],'question':{'entity':'payment_method','text':'How would you fund this expense?'}},{'intent':'decision_support'}],[{'segments':[{'text':'The funding method is unknown.'}]},{'segments':[{'claim':'user.payment_method','kind':'user_assumption'}]}])
  self.ask(self.Q);r=self.ask('cash');self.assertNotIn('available_cash',self.state()['entities']);self.assertEqual(self.state()['entities']['one_time_cost']['value'],'10000.00');self.assertNotIn('How would you fund',r['reply'])
 def test_multiturn_preserves_cost_and_user_reported_cash(self):
  self.scripted([{'intent':'decision_support','updates':[('one_time_cost','RMB 10,000')],'question':{'entity':'available_cash','text':'How much cash is available?'}},{'intent':'decision_support'}],[{'segments':[{'text':'Cash is unknown.'}]},{'segments':[{'claim':'user.available_cash','kind':'user_assumption'}]}])
  self.ask(self.Q);r=self.ask('CNY 35000');self.assertEqual(self.state()['entities']['one_time_cost']['value'],'10000.00');self.assertEqual(self.state()['entities']['available_cash']['value'],'35000.00');self.assertIn('not independently confirmed',r['reply'])
 def test_positive_affordability_without_evidence_is_rejected(self):
  self.scripted([{'intent':'decision_support'}],[{'segments':[{'text':'Your business can afford the investment.'}]}])
  r=self.ask(self.Q);self.assertEqual(r['fallback_reason'],'response_validation');self.assertNotIn('can afford',r['reply'])
 def test_staff_denied_before_retrieval(self):
  token=self.tokens['staff'];ref=self.partner.create(token,'M002')['conversation']
  self.scripted([{'intent':'decision_support'}],[])
  with patch.object(self.g,'_read',side_effect=AssertionError('No protected reads')):
   r=self.ask(self.Q,token,ref)
  self.assertEqual(r['classification'],'DENIED')
 def test_owner_cross_merchant_denied(self):self.assertEqual(self.ask(self.Q+' Use M001 records.')['classification'],'DENIED')
 def test_verification_and_timeout_events_are_sanitized(self):
  self.scripted([{'intent':'decision_support'}],[{'segments':[{'claim':'fact0.cash_balance','kind':'backend_fact'}]}]);r=self.ask(self.Q);self.assertEqual(r['fallback_reason'],'response_validation')
  self.scripted([TimeoutError('SECRET_TIMEOUT')],[]);r=self.ask('Continue');self.assertEqual(r['fallback_reason'],'timeout');self.assertNotIn('SECRET_TIMEOUT',str(r))
  with self.auth.db() as db:events=[json.loads(row[0]) for row in db.execute('SELECT record FROM audit_events')]
  self.assertTrue(any(e.get('action')=='ai_response_response_validation' for e in events))
 def test_provider_error_does_not_expose_credentials(self):
  self.scripted([OSError('SECRET_PROVIDER')],[]);r=self.ask(self.Q);self.assertEqual(r['fallback_reason'],'provider_error');self.assertNotIn('SECRET_PROVIDER',str(r))
 def test_invalid_date_can_clarify_without_financial_read(self):
  self.scripted([{'intent':'unknown','question':{'entity':'assessment_date','text':'Which assessment date should I use?'}}],[{'segments':[{'text':'The date could not be interpreted.'}]}])
  with patch.object(self.g,'_read',side_effect=AssertionError('No reads')):r=self.ask('Use February 31, 2026')
  self.assertEqual(r['verification'],'passed');self.assertEqual(r['tools_used'],[]);self.assertIn('Which assessment date',r['reply'])


def load_tests(loader,tests,pattern):
 suite=loader.loadTestsFromTestCase(ClaimAttribution)
 suite.addTests(PurchaseIntegration(name) for name in PurchaseIntegration.__dict__ if name.startswith('test_'))
 return suite

if __name__=='__main__':unittest.main()
