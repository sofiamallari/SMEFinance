"""Isolated proposed context layer; does not activate the new chatbot pipeline."""
import copy,json,unittest
from datetime import date
from copilot import conversation_state as cs
from copilot.governed_claims import ClaimError,verify_response
TODAY=date(2026,10,16)
class ContextTests(unittest.TestCase):
 def state(self,key=None):
  s=cs.fresh()
  if key:s['pending']={'entity':key,'text':'What value should I use?'}
  return s
 def apply(self,s,text,key,quote=None,intent='decision_support',question=None,topic=False):
  return cs.apply_proposal(s,{'intent':intent,'topic_change':topic,'updates':[{'entity':key,'quote':quote or text}] if key else [],'question':question},text,currency='CNY',today=TODAY)
 def test_short_typed_answers(self):
  cases=[('payment_method','cash','cash'),('available_cash','CNY 35000','35000.00'),('sales_change_percent','20%','20'),('financing_duration','6 months','6'),('costs_included','yes',True),('costs_included','no',False)]
  for key,text,value in cases:
   with self.subTest(entity=key):
    s=self.state(key);self.assertTrue(cs.answer_pending(s,text,currency='CNY',today=TODAY));self.assertEqual(s['entities'][key]['value'],value);self.assertIsNone(s['pending']);self.assertIn(key,s['resolved'])
 def test_last_month_uses_business_date(self):
  s=self.state('reporting_period');self.assertTrue(cs.answer_pending(s,'last month',currency='CNY',today=TODAY));self.assertEqual(s['entities']['reporting_period']['value'],{'start':'2026-09-01','end':'2026-09-30'})
 def test_bare_amount_without_pending_is_ambiguous(self):
  s=self.state();self.assertFalse(cs.answer_pending(s,'CNY 35000',currency='CNY',today=TODAY));self.assertFalse(s['entities'])
 def test_cost_does_not_become_cash(self):
  s=self.state('available_cash');self.assertFalse(cs.answer_pending(s,'Actually it costs CNY 12000',currency='CNY',today=TODAY))
  with self.assertRaises(ClaimError):self.apply(s,'The equipment costs CNY 12000','available_cash')
 def test_correction_is_targeted_and_source_attributed(self):
  s=self.apply(self.state(),'New equipment costs CNY 12000','one_time_cost',quote='CNY 12000')
  s=self.apply(s,'Available cash is CNY 35000','available_cash')
  s=self.apply(s,'Actually it costs CNY 14000','one_time_cost',quote='CNY 14000')
  self.assertEqual(s['entities']['one_time_cost']['value'],'14000.00');self.assertEqual(s['entities']['available_cash']['value'],'35000.00');self.assertEqual(s['corrections'][-1]['entity'],'one_time_cost')
 def test_negated_correction_is_rejected(self):
  with self.assertRaises(ClaimError):self.apply(self.state(),'Make that 15%, not 20%','sales_change_percent','20%')
  s=self.apply(self.state(),'Make that 15%, not 20%','sales_change_percent','15%');self.assertEqual(s['entities']['sales_change_percent']['value'],'15')
 def test_no_unstated_values(self):
  with self.assertRaises(ClaimError):self.apply(self.state(),'The cost is unknown','one_time_cost','CNY 99999')
 def test_no_repeated_resolved_question(self):
  s=self.state('payment_method');cs.answer_pending(s,'cash',currency='CNY',today=TODAY)
  with self.assertRaises(ClaimError):self.apply(s,'cash',None,question={'entity':'payment_method','text':'Will you pay cash?'})
 def test_fallback_keeps_answer_and_does_not_repeat(self):
  s=self.state('payment_method');cs.answer_pending(s,'cash',currency='CNY',today=TODAY)
  self.assertNotIn('Will you pay',cs.safe_fallback(s));self.assertEqual(s['entities']['payment_method']['value'],'cash')
 def test_topic_switch_separates_assumptions(self):
  s=self.apply(self.state(),'The extra employee costs CNY 5000','recurring_expense','CNY 5000')
  n=self.apply(s,'Compare payment channels',None,intent='payment_channels',topic=True)
  self.assertFalse(n['entities']);self.assertEqual(n['topics'][-1]['entities']['recurring_expense']['value'],'5000.00');self.assertEqual(s['intent'],'decision_support')
 def test_recurring_supplier_expansion_and_financing_remain_separate(self):
  s=self.state()
  for key,value in [('recurring_expense','4000'),('supplier_obligations','7000'),('expansion_cost','80000'),('financing_amount','25000')]:
   s=self.apply(s,'CNY '+value,key)
  self.assertEqual(len(s['entities']),4)
 def test_unsupported_provenance_cannot_be_introduced(self):
  s=self.apply(self.state(),'Cash balance is CNY 35000','available_cash')
  records=cs.claim_records(s)
  self.assertEqual(records['user.available_cash']['kind'],'user_assumption')
  with self.assertRaises(ClaimError):verify_response(json.dumps({'segments':[{'claim':'user.available_cash','kind':'backend_fact'}]}),records)
 def test_percentage_sign_respects_pending_question(self):
  s=self.state('sales_change_percent');s['pending']['text']='How large is the sales decline?'
  cs.answer_pending(s,'20%',currency='CNY',today=TODAY);self.assertEqual(s['entities']['sales_change_percent']['value'],'-20')
 def test_financial_records_not_model_editable(self):
  with self.assertRaises(Exception):self.apply(self.state(),'CNY 9000','verified_cash')
 def test_invalid_ranges_and_ambiguous_numbers(self):
  for key,text in [('available_cash','CNY -10'),('one_time_cost','CNY 100 and CNY 200'),('financing_duration','900 years'),('reporting_period','2026-10-20 to 2026-01-01')]:
   with self.subTest(key=key),self.assertRaises(Exception):cs.scalar(key,text,currency='CNY',today=TODAY)
 def test_yes_does_not_authorize_any_action(self):
  s=self.state('costs_included');cs.answer_pending(s,'yes',currency='CNY',today=TODAY)
  self.assertEqual(set(s['entities']),{'costs_included'});self.assertNotIn('execute',s)
 def test_reset_fresh_state_has_no_private_information(self):
  s=self.apply(self.state(),'Cash balance is CNY 35000','available_cash');n=cs.fresh()
  self.assertFalse(n['entities']);self.assertFalse(n['facts']);self.assertFalse(n['topics'])

 def test_auto_answer_cannot_be_reassigned_after_pending_is_cleared(self):
  s=self.state('available_cash');cs.answer_pending(s,'CNY 35000',currency='CNY',today=TODAY)
  with self.assertRaises(ClaimError):self.apply(s,'CNY 35000','one_time_cost')
  self.assertEqual(s['entities']['available_cash']['value'],'35000.00')
 def test_explicit_growth_correction_can_change_decline_direction(self):
  s=self.apply(self.state(),'Sales drop 20%','sales_change_percent')
  s=self.apply(s,'Sales increase 15%','sales_change_percent')
  self.assertEqual(s['entities']['sales_change_percent']['value'],'15')

 def test_full_available_cash_answer_is_not_a_purchase_cost(self):
  s=self.state('available_cash')
  s=self.apply(s,'I have CNY 40000 available.','available_cash')
  self.assertEqual(s['entities']['available_cash']['value'],'40000.00')
  self.assertEqual(cs.claim_records(s)['user.available_cash']['kind'],'user_assumption')
  with self.assertRaises(ClaimError):self.apply(self.state('available_cash'),'The equipment costs CNY 40000','available_cash')
 def test_general_subject_and_start_month(self):
  s=self.apply(self.state(),'A delivery vehicle','business_subject','delivery vehicle')
  s=self.apply(s,'Starting next month.','start_date','next month')
  self.assertEqual(s['entities']['business_subject']['value'],'delivery vehicle')
  self.assertEqual(s['entities']['start_date']['value'],'2026-11-01')
  self.assertEqual(s['entities']['start_date']['precision'],'month')
 def test_comparison_and_rolling_periods_use_backend_dates(self):
  s=self.apply(self.state(),'Last month','reporting_period','Last month',intent='sales_analysis')
  s=self.apply(s,'Compare with the previous month','comparison_period','previous month',intent='sales_analysis')
  self.assertEqual(s['entities']['comparison_period']['value'],{'start':'2026-08-01','end':'2026-08-31'})
  s=self.apply(s,'Use the last 30 days','reporting_period','last 30 days',intent='sales_analysis')
  self.assertEqual(s['entities']['reporting_period']['value'],{'start':'2026-09-17','end':'2026-10-16'})
  self.assertNotIn('comparison_period',s['entities']);self.assertNotIn('comparison_period',s['resolved'])
 def test_all_is_a_boolean_answer_not_action_authority(self):
  s=self.state('costs_included');self.assertTrue(cs.answer_pending(s,'all',currency='CNY',today=TODAY));self.assertTrue(s['entities']['costs_included']['value']);self.assertNotIn('execute',s)

 def test_subject_cannot_be_a_pronoun_or_generic_action(self):
  for subject in ('my business','buying a purchase','financing','Can my business','purchase plan','summary'):
   with self.subTest(subject=subject),self.assertRaises(ClaimError):cs.scalar('business_subject',subject,currency='CNY',today=TODAY)
  self.assertEqual(cs.scalar('business_subject','refrigerator',currency='CNY',today=TODAY)['value'],'refrigerator')
 def test_choice_answer_does_not_replace_pending_money_question(self):
  s=self.state('available_cash')
  n=self.apply(s,'cash','payment_method')
  self.assertEqual(n['entities']['payment_method']['value'],'cash');self.assertNotIn('available_cash',n['entities']);self.assertEqual(n['pending']['entity'],'available_cash')
  with self.assertRaises(ClaimError):self.apply(s,'CNY 15000','one_time_cost')

 def test_percentage_source_keeps_nearest_explicit_direction(self):
  s=self.state();s=self.apply(s,'Sales increase by 20%, expenses decrease by 10%','sales_change_percent','20%')
  s=self.apply(s,'Sales increase by 20%, expenses decrease by 10%','expense_change_percent','10%')
  self.assertEqual(s['entities']['sales_change_percent']['value'],'20');self.assertEqual(s['entities']['expense_change_percent']['value'],'-10')

 def test_explicit_date_can_arrive_while_cash_question_is_pending(self):
  s=self.apply(self.state('available_cash'),'Starting next month.','start_date','next month')
  self.assertEqual(s['entities']['start_date']['value'],'2026-11-01')
  self.assertNotIn('available_cash',s['entities'])
  self.assertEqual(s['pending']['entity'],'available_cash')
