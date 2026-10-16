"""Bank access/decisions and standalone simulator acceptance checks; isolated fixtures."""
import json,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from tests import test_four_role_workflow as existing
from tests.auth_support import setup_identity,PASSWORD
from copilot.bank_workflow import BankWorkflow
from copilot.security import AccessDenied
from copilot.auth import InputError,AuthError

class BankDelivery(unittest.TestCase):
 def setUp(self):
  setup_identity(self,all_merchants=True);self.w=BankWorkflow(self.auth,self.c)
 consent=existing.FourRoleWorkflow.consent
 submit=existing.FourRoleWorkflow.submit
 def invite(self,**kw):
  body=dict(merchant='M002',username='newbank',email='newbank@example.test',display_name='New Bank',organization='Synthetic Bank');body.update(kw)
  return self.w.invite_bank(self.tokens['owner'],body)
 def test_invite_existing_and_no_takeover(self):
  result=self.invite();uid=result['recipient']['user_id'];self.assertTrue(result['created']);self.assertNotIn('password',result)
  with self.auth.db() as db:
   self.assertEqual(db.execute('SELECT role FROM users WHERE user_id=?',(uid,)).fetchone()[0],'BANK')
   self.assertNotIn(result['invitation_token'],str([tuple(r) for r in db.execute('SELECT * FROM reset_tokens')]))
  self.auth.reset_password(result['invitation_token'],PASSWORD)
  with self.assertRaises((InputError,AuthError)):self.auth.reset_password(result['invitation_token'],PASSWORD)
  token=self.auth.login('newbank',PASSWORD)[0];self.assertEqual(self.w.merchants(token),[])
  first=self.auth.grant_consent(self.tokens['owner'],dict(merchant='M002',recipient_id=uid,purpose='Review',categories=['reports'],expires_at=self.auth.clock()+3600))
  self.assertEqual([m['id'] for m in self.w.merchants(token)],['M002'])
  repeat=self.invite(merchant='M003',username='ignored',display_name='Changed')
  self.assertFalse(repeat['created']);self.assertIsNone(repeat['invitation_token']);self.assertEqual(repeat['recipient']['display_name'],'New Bank')
  self.auth.grant_consent(self.tokens['owner'],dict(merchant='M003',recipient_id=uid,purpose='Second review',categories=['reports'],expires_at=self.auth.clock()+3600))
  self.assertEqual({m['id'] for m in self.w.merchants(token)},{'M002','M003'})
  self.assertEqual(self.w.review(token,'M002')['merchant_id'],'M002');self.assertEqual(self.w.review(token,'M003')['merchant_id'],'M003')
  self.auth.revoke_consent(self.tokens['owner'],first['consent_id'])
  for export in (False,True):
   with self.assertRaises(AccessDenied):self.w.review(token,'M002',export=export)
  self.assertTrue(self.w.review(token,'M003',export=True).startswith(b'\xef\xbb\xbf'))
  with self.auth.db() as db:db.execute("DELETE FROM memberships WHERE user_id=? AND merchant_id='M001'",(self.ids['owner'],))
  with self.assertRaises(AccessDenied):self.invite(merchant='M001')
  for role in ('staff','lender_analyst','security_admin'):
   with self.assertRaises(AccessDenied):self.w.invite_bank(self.tokens[role],dict(merchant='M002',email='a@example.test'))
  with self.assertRaises(InputError):self.invite(email='owner@example.test')
 def test_decisions_owner_visibility_and_no_financial_effect(self):
  packet=self.submit();aid=packet['application_id'];before=self.metrics();ledger=self.store.journal.read()
  for role in ('owner','staff','security_admin'):
   with self.assertRaises(AccessDenied):self.w.record_review(self.tokens[role],aid,{'outcome':'approved'})
  with self.assertRaises(InputError):self.w.record_review(self.tokens['lender_analyst'],aid,{'outcome':'approved','actor_id':'forged'})
  self.w.record_review(self.tokens['lender_analyst'],aid,{'outcome':'approved','note':'Synthetic approval'})
  result=self.auth.application_list(self.tokens['owner'],'M002')[0];self.assertEqual(result['status'],'APPROVED');self.assertTrue(result['simulated_decision']);self.assertEqual(result['decision_by'],self.ids['lender_analyst'])
  for outcome in ('approved','rejected','reviewed'):
   with self.assertRaises(InputError):self.w.record_review(self.tokens['lender_analyst'],aid,{'outcome':outcome,'note':'Repeat'})
  other=self.submit();aid2=other['application_id']
  with self.assertRaises(InputError):self.w.record_review(self.tokens['lender_analyst'],aid2,{'outcome':'rejected'})
  self.w.record_review(self.tokens['lender_analyst'],aid2,{'outcome':'rejected','note':'Insufficient supplied evidence'})
  rejected=next(a for a in self.auth.application_list(self.tokens['owner'],'M002') if a['application_id']==aid2)
  self.assertEqual(rejected['status'],'REJECTED');self.assertEqual(rejected['reviews'][-1]['note'],'Insufficient supplied evidence')
  self.assertEqual(self.metrics(),before);self.assertEqual(self.store.journal.read(),ledger);self.assertFalse(self.c.payments.payments)
  with self.auth.db() as db:
   events=[json.loads(r[0]) for r in db.execute('SELECT record FROM audit_events')]
  event=next(e for e in events if e['action']=='financing_simulated_approved');self.assertEqual(event['actor'],self.ids['lender_analyst']);self.assertEqual(event['merchant_id'],'M002');self.assertEqual(event['target'],aid);self.assertIn('ts',event)
 def test_routing_requires_live_applications_consent(self):
  aid=self.submit()['application_id'];bank=self.tokens['lender_analyst']
  self.assertEqual(len(self.w.applications(bank)),1)
  with self.auth.db() as db:db.execute('UPDATE consents SET revoked_at=?',(self.auth.clock(),))
  self.assertEqual(self.w.applications(bank),[])
  for fn in (lambda:self.w.applications(bank,aid),lambda:self.w.record_review(bank,aid,{'outcome':'approved'}),lambda:self.w.review(bank,'M002',export=True)):
   with self.assertRaises(AccessDenied):fn()
  self.consent(['reports']);self.assertEqual(self.w.applications(bank),[]);self.assertIn('recorded_metrics',self.w.review(bank,'M002')['sections'])
  self.consent(['applications'])
  with self.auth.db() as db:db.execute('UPDATE consents SET expires_at=?',(self.auth.clock()-1,))
  self.assertEqual(self.w.applications(bank),[])
 def test_concurrent_decisions_one_final_state(self):
  aid=self.submit()['application_id'];gate=threading.Barrier(2)
  def decide(outcome):
   gate.wait()
   try:self.w.record_review(self.tokens['lender_analyst'],aid,{'outcome':outcome,'note':'Concurrent synthetic decision'});return 'ok'
   except InputError as e:return e.status
  with ThreadPoolExecutor(2) as pool:result=list(pool.map(decide,['approved','rejected']))
  self.assertEqual(result.count('ok'),1);self.assertEqual(result.count(409),1)
  self.assertIn(self.auth.application_list(self.tokens['owner'],'M002')[0]['status'],('APPROVED','REJECTED'))
  with self.auth.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM application_reviews WHERE application_id=?',(aid,)).fetchone()[0],1)
 def metrics(self):
  result=self.c.financial_data.aggregate('M002');result.pop('as_of',None);return result
 def test_simulator_isolated_success_failure_refund_and_restart(self):
  from copilot.agent import Copilot
  from copilot.modules.transactions import TransactionStore
  self.consent();bank=self.tokens['lender_analyst'];before=self.metrics();version=self.c.financial_data.version('M002');ledger=self.store.journal.read();forecast=self.w.review(bank,'M002')['sections']['forecast'];apps=self.auth.application_list(self.tokens['owner'],'M002')
  p=self.c.payments.create(self.c.merchants['M002'],'qr_pay',10);self.c.payments.simulate_customer_payment(p.ref);self.c.payments.refund(p.ref,2,'unique-refund')
  failed=self.c.payments.create(self.c.merchants['M002'],'tap_pay',11);self.c.payments.fail(failed.ref)
  self.assertEqual(self.metrics(),before);self.assertEqual(self.store.journal.read(),ledger);self.assertEqual(self.c.financial_data.version('M002'),version)
  self.assertEqual(self.w.review(bank,'M002')['sections']['forecast'],forecast);self.assertEqual(self.auth.application_list(self.tokens['owner'],'M002'),apps)
  restored=Copilot();restored.identity_store=self.auth;TransactionStore(restored,str(self.store.path))
  self.assertEqual(restored.payments.payments[p.ref].refunded_amount,2);self.assertEqual(restored.payments.payments[failed.ref].status,'FAILED')
  self.assertEqual(restored.financial_data.aggregate('M002')['net_sales'],before['net_sales'])
