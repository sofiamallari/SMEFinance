"""Staged integration: public reply stays on its existing implementation."""
import unittest
from tests.test_ai_governance import GovernanceTests
from copilot.security import AccessDenied
class StagedIntegration(GovernanceTests):
 def test_state_is_scoped_to_authenticated_conversation(self):
  _,row=self.partner.context(self.token,'M002',self.ref)
  self.assertEqual(row['conversation_state']['entities'],{})
  row['conversation_state']['entities']['private_marker']={'value':'synthetic'}
  with self.assertRaises(AccessDenied):self.partner.context(self.tokens['staff'],'M002',self.ref)
  self.partner.close(self.token,'M002',self.ref)
  ref=self.partner.create(self.token,'M002')['conversation']
  self.assertFalse(self.partner.context(self.token,'M002',ref)[1]['conversation_state']['entities'])
 def test_merchant_change_discards_typed_state(self):
  self.partner.context(self.token,'M002',self.ref)[1]['conversation_state']['intent']='decision_support'
  self.partner.forget_merchant(self.token,self.ref)
  with self.assertRaises(AccessDenied):self.partner.context(self.token,'M002',self.ref)
 def test_no_automatic_generalized_dispatch(self):
  self.assertNotIn('generalized',self.partner.create(self.token,'M002'))

 def review(self,replies):
  from copilot.conversation_review import ReviewConversation
  import json
  queue=iter(replies)
  def request(messages,schema):
   value=next(queue)
   if isinstance(value,Exception):raise value
   return {'content':json.dumps(value)}
  return ReviewConversation(self.partner,request)
 def plan(self,intent='decision_support',updates=None,question=None,topic=False):
  return {'intent':intent,'topic_change':topic,'updates':updates or [],'question':question}
 def test_review_commits_validated_answer_before_narration_failure(self):
  import copy
  from copilot import conversation_state as cs
  state=self.partner.context(self.token,'M002',self.ref)[1]['conversation_state']
  state['pending']={'entity':'available_cash','text':'How much cash is available?'}
  review=self.review([self.plan('cash_flow'),TimeoutError('SECRET_TRANSPORT_DETAIL')])
  r=review.reply(self.token,'M002',self.ref,'CNY 35000')
  self.assertEqual(r['connection_status'],'fallback');self.assertEqual(r['failure_stage'],'narration')
  self.assertEqual(state['entities']['available_cash']['value'],'35000.00')
  self.assertNotIn('How much cash',r['reply']);self.assertNotIn('SECRET',str(r))
 def test_review_financial_fabrication_still_rejected(self):
  review=self.review([self.plan('sales_analysis'),{'segments':[{'text':'Your verified cash balance is CNY 999999.'}]}])
  r=review.reply(self.token,'M002',self.ref,'Show sales')
  self.assertEqual(r['connection_status'],'fallback');self.assertNotIn('999999',r['reply'])
 def test_review_uses_only_authorized_backend_fact(self):
  review=self.review([self.plan('sales_analysis'),{'segments':[{'claim':'fact0.net_sales','kind':'backend_fact'}]}])
  r=review.reply(self.token,'M002',self.ref,'Show sales')
  self.assertEqual(r['verification'],'passed');self.assertEqual(r['engine'],'generalized');self.assertEqual(r['connection_status'],'test_double')
  self.assertEqual(r['tools_used'],['get_financial_summary'])
 def test_review_staff_denied_before_provider_and_reads(self):
  from unittest.mock import patch
  from copilot.conversation_review import ReviewConversation
  token=self.tokens['staff'];ref=self.partner.create(token,'M002')['conversation']
  with patch.object(self.g,'execute',side_effect=AssertionError('No reads')):
   r=ReviewConversation(self.partner,lambda *a:(_ for _ in ()).throw(AssertionError('No provider'))).reply(token,'M002',ref,'Show my financing application status')
  self.assertEqual(r['classification'],'DENIED')
 def test_review_bank_cannot_bypass_existing_consent_permissions(self):
  token=self.tokens['lender_analyst'];ref=self.partner.create(token,'M002')['conversation']
  review=self.review([self.plan('financing')])
  r=review.reply(token,'M002',ref,'Show application APP-unassigned')
  self.assertEqual(r['fallback_reason'],'authorization');self.assertFalse(r['tools_used'])
 def test_review_admin_and_cross_merchant_denied(self):
  from copilot.conversation_review import ReviewConversation
  with self.assertRaises(AccessDenied):self.partner.create(self.tokens['security_admin'],'M002')
  with self.assertRaises(AccessDenied):ReviewConversation(self.partner).reply(self.token,'M001',self.ref,'Show sales')
 def test_review_source_schema_eliminates_invalid_type_combinations(self):
  from copilot.conversation_review import sources,plan_schema
  from copilot import conversation_state as cs
  from datetime import date
  from jsonschema import Draft202012Validator
  text='I intend to pay cash.';spans=sources(text);schema=plan_schema(spans,cs.fresh(),text=text,currency='CNY',today=date(2026,10,16))
  valid=next(k for k,v in spans.items() if v=='cash')
  Draft202012Validator(schema).validate(self.plan(updates=[{'entity':'payment_method','source':valid}]))
  with self.assertRaises(Exception):Draft202012Validator(schema).validate(self.plan(updates=[{'entity':'available_cash','source':valid}]))
 def test_review_narration_schema_requires_supplied_claim_ids(self):
  from copilot.conversation_review import narration_schema
  from jsonschema import Draft202012Validator
  schema=narration_schema({'user.one_time_cost':{'kind':'user_assumption'}})
  with self.assertRaises(Exception):Draft202012Validator(schema).validate({'segments':[{'claim':'user.cash_balance','kind':'backend_fact'}]})
  with self.assertRaises(Exception):Draft202012Validator(schema).validate({'segments':[{'text':'Cost is 35000.'}]})


 def test_review_cannot_claim_business_records_were_written(self):
  review=self.review([self.plan('sales_analysis'),{'segments':[{'text':'I have updated your financial records.'}]}])
  r=review.reply(self.token,'M002',self.ref,'Show sales')
  self.assertEqual(r['connection_status'],'fallback');self.assertEqual(r['reason_code'],'unsupported_action_claim')


 def test_review_topic_switch_does_not_reuse_previous_financial_assumptions(self):
  from copilot import conversation_state as cs
  from datetime import date
  state=self.partner.context(self.token,'M002',self.ref)[1]['conversation_state']
  cs.put(state,'one_time_cost',{'value':'18000.00','currency':'CNY'},'CNY 18000')
  review=self.review([self.plan('payment_channels',topic=True),{'segments':[{'text':'Here is the requested channel comparison.'}]}])
  r=review.reply(self.token,'M002',self.ref,'Compare payment channels instead')
  current=self.partner.context(self.token,'M002',self.ref)[1]['conversation_state']
  self.assertEqual(r['verification'],'passed');self.assertFalse(current['entities']);self.assertNotIn('18000',r['reply'])
 def test_review_month_names_cannot_bypass_date_provenance(self):
  review=self.review([self.plan('sales_analysis'),{'segments':[{'text':'The forecast covers October.'}]}])
  r=review.reply(self.token,'M002',self.ref,'Show sales')
  self.assertEqual(r['reason_code'],'untyped_period_claim');self.assertNotIn('October',r['reply'])


 def test_review_out_of_scope_stops_before_financial_reads(self):
  from unittest.mock import patch
  review=self.review([self.plan('out_of_scope')])
  with patch.object(self.g,'execute',side_effect=AssertionError('No reads')):
   r=review.reply(self.token,'M002',self.ref,'Tell me a sports score')
  self.assertEqual(r['classification'],'OUT_OF_SCOPE');self.assertFalse(r['tools_used'])


 def test_existing_help_service_has_no_financial_read_or_role_bypass(self):
  from copilot.partner_help import answer
  from unittest.mock import patch
  with patch.object(self.g,'execute',side_effect=AssertionError('No financial reads')):
   self.assertEqual(answer(self.auth.principal(self.token),'M002','How do I authorize a bank?')['classification'],'APPLICATION_GUIDANCE')
   with self.assertRaises(AccessDenied):answer(self.auth.principal(self.tokens['staff']),'M002','How do I authorize a bank?')
 def test_existing_research_proposal_is_not_execution(self):
  calls=[];self.partner.research.provider=lambda *a,**k:calls.append(True) or []
  row=self.partner.context(self.token,'M002',self.ref)[1]
  proposal=self.partner.research.propose(self.token,'M002',row,'sme_lending_rates')
  self.assertTrue(proposal['available']);self.assertFalse(calls);self.assertNotIn('M002',proposal['exact_query'])


def load_tests(loader,tests,pattern):
 return unittest.TestSuite(StagedIntegration(name) for name in StagedIntegration.__dict__ if name.startswith('test_'))
