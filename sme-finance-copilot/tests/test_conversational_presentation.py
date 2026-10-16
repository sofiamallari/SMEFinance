"""Final deterministic prose is sourced independently of provider wording."""
import copy,unittest
from unittest.mock import patch
from copilot import governed_claims as claims
class Presentation(unittest.TestCase):
 def setUp(self):
  self.context=claims.purchase_context('Can I afford an oven worth RMB 10,000?')
  self.records=claims.assumptions(self.context)
  self.records.update(claims.tool_claims('get_financial_summary',{'period':{'start':'2026-07-19','end':'2026-10-16'},'currency':'CNY','recorded_net_sales':'12345.67','transaction_count':42},prefix='fact0'))
 def test_plain_language_exact_values_period_and_one_question(self):
  r=claims.render_purchase(self.context,self.records)
  self.assertIn(claims.money('10000.00'),r);self.assertIn(claims.money('12345.67'),r)
  self.assertIn('July 19, 2026 to October 16, 2026',r);self.assertEqual(r.count('?'),1)
  for phrase in ['your assumption','backend_fact','Recorded net sales','transaction count','approved one-time','verified available cash','42']:
   self.assertNotIn(phrase,r)
  self.assertIn("Sales alone don't tell us",r)
 def test_cash_followup_no_sales_or_repeated_funding_question(self):
  c=claims.purchase_context("I'll pay in cash. The RMB 10,000 includes delivery and installation.",self.context)
  records={**self.records,**claims.assumptions(c)};r=claims.render_purchase(c,records,True)
  self.assertNotIn('net sales',r);self.assertNotIn('through financing',r);self.assertIn('in cash',r);self.assertEqual(r.count('?'),1)
  self.assertNotIn('reported_cash',c)
 def test_user_cash_stays_unconfirmed(self):
  c=claims.purchase_context('My available cash is RMB 20,000.',self.context)
  r=claims.render_purchase(c,{**self.records,**claims.assumptions(c)},True)
  self.assertIn('You told me',r);self.assertIn("haven't independently confirmed",r);self.assertNotIn('you can afford',r)
 def test_display_claims_are_rechecked(self):
  with patch.object(claims,'verify_response',wraps=claims.verify_response) as verify:
   claims.render_purchase(self.context,self.records)
  self.assertEqual(verify.call_count,1)
  self.assertIn('fact0.net_sales',verify.call_args.args[0])
 def test_changed_or_missing_assumption_cannot_be_rendered(self):
  records=copy.deepcopy(self.records);records['user.purchase_price']['value']='999999'
  with self.assertRaises(claims.ClaimError):claims.render_purchase(self.context,records)
  records.pop('user.purchase_price')
  with self.assertRaises(claims.ClaimError):claims.render_purchase(self.context,records)
 def test_financing_asks_only_next_missing_detail(self):
  c=claims.purchase_context('I will use financing.',self.context)
  r=claims.render_purchase(c,{**self.records,**claims.assumptions(c)},True)
  self.assertIn('What repayment period',r);self.assertEqual(r.count('?'),1)

 def test_short_cash_answer_advances_without_inventing_balance(self):
  for text in ('cash','Cash.','in cash'):
   c=claims.purchase_context(text,self.context)
   self.assertEqual(c['funding'],'cash');self.assertEqual(c['price'],'10000.00');self.assertNotIn('reported_cash',c)
   reply=claims.render_purchase(c,{**self.records,**claims.assumptions(c)},True)
   self.assertNotIn('through financing?',reply);self.assertIn('Does that price include',reply)
 def test_short_financing_answer_and_no_unrelated_inference(self):
  c=claims.purchase_context('financing',self.context);self.assertEqual(c['funding'],'financing')
  self.assertNotIn('funding',claims.purchase_context('cash'))
  self.assertNotIn('funding',claims.purchase_context('What is cash flow?',self.context))
