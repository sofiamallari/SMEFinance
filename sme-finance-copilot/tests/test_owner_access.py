"""Isolated Owner/Staff/Bank association and consent acceptance tests."""
import json,unittest
from unittest.mock import patch
from tests.auth_support import setup_identity,PASSWORD
from copilot.owner_access import OwnerAccess
from copilot.bank_workflow import BankWorkflow
from copilot.auth import InputError
from copilot.security import AccessDenied

class OwnerAccessTests(unittest.TestCase):
 def setUp(self):
  setup_identity(self,all_merchants=True);self.s=OwnerAccess(self.auth);self.w=BankWorkflow(self.auth,self.c);self.t=self.tokens['owner'];self.bank=self.ids['lender_analyst']
 def new(self,role='SME_STAFF',**kw):
  body={'role':role,'username':'newstaff' if role=='SME_STAFF' else 'newbank','email':'newstaff@example.test' if role=='SME_STAFF' else 'newbank@example.test','display_name':'Synthetic User','organization':'Synthetic demo Bank' if role=='BANK' else '', 'merchants':['M002','M003'],'permissions':{}};body.update(kw);return self.s.save(self.t,body,'create')
 def grant(self,grants=None,**kw):
  body={'recipient_id':self.bank,'purpose':'Synthetic review','expires_at':self.auth.clock()+3600,'confirmed':True,'grants':grants or [{'merchant':'M002','categories':['reports'],'allow_download':False}]};body.update(kw);return self.s.authorize(self.t,body)
 def test_candidates_match_role_and_exclude_linked(self):
  staff=self.new()['user'];bank=self.new('BANK')['user']
  result=self.s.candidates(self.t,{'role':'SME_STAFF','merchants':['M004']})['users']
  self.assertIn(staff['user_id'],[u['user_id'] for u in result]);self.assertNotIn(bank['user_id'],[u['user_id'] for u in result])
  self.assertNotIn(staff['user_id'],[u['user_id'] for u in self.s.candidates(self.t,{'role':'SME_STAFF','merchants':['M002','M004']})['users']])
  for u in result:self.assertEqual(set(u),{'user_id','display_name','username','email','role'})
 def test_candidates_hide_unrelated_and_inactive(self):
  uid=self.new()['user']['user_id']
  with self.auth.db() as db:
   db.execute('DELETE FROM memberships WHERE user_id=?',(uid,));db.execute('UPDATE users SET created_by=? WHERE user_id=?',(self.ids['security_admin'],uid))
  self.assertNotIn(uid,[u['user_id'] for u in self.s.candidates(self.t,{'role':'SME_STAFF','merchants':['M004']})['users']])
  with self.auth.db() as db:db.execute("UPDATE users SET created_by=?,account_status='suspended' WHERE user_id=?",(self.ids['owner'],uid))
  self.assertNotIn(uid,[u['user_id'] for u in self.s.candidates(self.t,{'role':'SME_STAFF','merchants':['M004']})['users']])
 def test_candidates_require_owner_and_managed_scope(self):
  for name in ('staff','lender_analyst','security_admin'):
   with self.assertRaises(AccessDenied):self.s.candidates(self.tokens[name],{'role':'SME_STAFF','merchants':['M004']})
  with self.auth.db() as db:db.execute("DELETE FROM memberships WHERE user_id=? AND merchant_id='M001'",(self.ids['owner'],))
  with self.assertRaises(AccessDenied):self.s.candidates(self.t,{'role':'BANK','merchants':['M001']})
  with self.assertRaises(InputError):self.s.candidates(self.t,{'role':'SYSTEM_ADMIN','merchants':['M004']})
  with self.assertRaises(InputError):self.s.candidates(self.t,{'role':'BANK','merchants':[]})
 def test_create_staff_least_privilege_and_no_credentials(self):
  result=self.new();u=result['user'];self.assertEqual(u['role'],'SME_STAFF');self.assertEqual(u['permissions'],{'M002':[],'M003':[]});self.assertNotIn('password',result);self.assertNotIn('invitation_token',result)
  with self.auth.db() as db:self.assertTrue(db.execute('SELECT must_change_password FROM users WHERE user_id=?',(u['user_id'],)).fetchone()[0])
 def test_create_bank_without_financial_consent(self):
  u=self.new('BANK')['user'];self.assertEqual(u['role'],'BANK')
  with self.auth.db() as db:self.assertIsNone(self.auth._consent(db,'M002',u['user_id']))
 def test_duplicate_creation_does_not_link_or_reset(self):
  with self.auth.db() as db:before=db.execute('SELECT password_hash FROM users WHERE user_id=?',(self.bank,)).fetchone()[0]
  with self.assertRaises(InputError) as error:self.new('BANK',email='lender_analyst@example.test')
  self.assertEqual(error.exception.status,409)
  with self.auth.db() as db:self.assertEqual(before,db.execute('SELECT password_hash FROM users WHERE user_id=?',(self.bank,)).fetchone()[0])
 def test_link_staff_without_changing_identity_or_grants(self):
  uid=self.ids['staff']
  with self.auth.db() as db:
   db.execute("DELETE FROM memberships WHERE user_id=? AND merchant_id='M003'",(uid,));db.execute("DELETE FROM merchant_transaction_grants WHERE user_id=? AND merchant_id='M003'",(uid,));before=tuple(db.execute('SELECT email,password_hash,role FROM users WHERE user_id=?',(uid,)).fetchone())
  result=self.s.lookup(self.t,{'role':'SME_STAFF','email':'staff@example.test','merchants':['M003']});self.assertEqual(result['match']['user_id'],uid)
  self.s.save(self.t,{'role':'SME_STAFF','user_id':uid,'email':'staff@example.test','merchants':['M003'],'confirmed':True},'link')
  with self.auth.db() as db:self.assertEqual(before,tuple(db.execute('SELECT email,password_hash,role FROM users WHERE user_id=?',(uid,)).fetchone()));self.assertFalse(list(db.execute("SELECT * FROM merchant_transaction_grants WHERE user_id=? AND merchant_id='M003'",(uid,))))
 def test_link_bank_no_consent_duplicate_and_wrong_role(self):
  with self.auth.db() as db:db.execute("DELETE FROM memberships WHERE user_id=? AND merchant_id='M003'",(self.bank,))
  body={'role':'BANK','user_id':self.bank,'email':'lender_analyst@example.test','merchants':['M003'],'confirmed':True}
  self.s.save(self.t,body,'link')
  with self.auth.db() as db:self.assertIsNone(self.auth._consent(db,'M003',self.bank))
  with self.assertRaises(InputError):self.s.save(self.t,body,'link')
  with self.assertRaises(InputError):self.s.save(self.t,body|{'user_id':self.ids['staff']},'link')
 def test_linked_global_identity_is_protected(self):
  with self.assertRaises(AccessDenied):self.s.save(self.t,{'role':'SME_STAFF','merchants':['M002'],'display_name':'Takeover'},'edit',self.ids['staff'])
 def test_edit_owned_identity_and_independent_permissions(self):
  uid=self.new()['user']['user_id'];self.s.save(self.t,{'role':'SME_STAFF','merchants':['M002','M003'],'display_name':'Edited','permissions':{'M002':['view_dashboard'],'M003':['view_transactions']}},'edit',uid)
  with self.auth.db() as db:
   self.assertEqual(db.execute('SELECT display_name FROM users WHERE user_id=?',(uid,)).fetchone()[0],'Edited')
   self.assertEqual([r[0] for r in db.execute("SELECT permission FROM merchant_transaction_grants WHERE user_id=? AND merchant_id='M002'",(uid,))],['view_dashboard'])
   self.assertEqual([r[0] for r in db.execute("SELECT permission FROM merchant_transaction_grants WHERE user_id=? AND merchant_id='M003'",(uid,))],['view_transactions'])
 def test_remove_only_one_merchant_and_audit(self):
  uid=self.new()['user']['user_id'];self.s.remove(self.t,uid,{'merchants':['M002'],'confirmed':True})
  with self.auth.db() as db:
   self.assertEqual([r[0] for r in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(uid,))],['M003']);self.assertIsNotNone(db.execute('SELECT 1 FROM users WHERE user_id=?',(uid,)).fetchone());self.assertIn('merchant_association_removed',str([r[0] for r in db.execute('SELECT record FROM audit_events')]))
 def test_unowned_merchant_and_non_owner_denied(self):
  with self.auth.db() as db:db.execute("DELETE FROM memberships WHERE user_id=? AND merchant_id='M001'",(self.ids['owner'],))
  with self.assertRaises(AccessDenied):self.new(merchants=['M001'])
  for role in ('staff','lender_analyst','security_admin'):
   with self.subTest(role=role),self.assertRaises(AccessDenied):self.s.listing(self.tokens[role])
 def test_three_merchant_grants_are_independent(self):
  self.grant([{'merchant':'M002','categories':['reports'],'allow_download':True},{'merchant':'M003','categories':['forecasts'],'allow_download':False},{'merchant':'M004','categories':['assessment'],'allow_download':False}])
  bank=self.tokens['lender_analyst'];self.auth.authorize(bank,'view_reports','M002')
  with self.assertRaises(AccessDenied):self.auth.authorize(bank,'view_forecasts','M002')
  self.auth.authorize(bank,'view_forecasts','M003')
  with self.assertRaises(AccessDenied):self.auth.authorize(bank,'view_reports','M003')
  self.auth.authorize(bank,'view_assessment','M004')
  self.assertEqual({m['id'] for m in self.w.merchants(bank)},{'M002','M003','M004'})
 def test_view_only_download_denied(self):
  self.grant();self.w.review(self.tokens['lender_analyst'],'M002')
  with self.assertRaises(AccessDenied):self.w.review(self.tokens['lender_analyst'],'M002',export=True)
 def test_download_filters_each_category_not_union(self):
  self.grant([{'merchant':'M002','categories':['reports'],'allow_download':False}]);self.grant([{'merchant':'M002','categories':['forecasts'],'allow_download':True}])
  text=self.w.review(self.tokens['lender_analyst'],'M002',export=True).decode('utf-8-sig');self.assertIn('forecast',text);self.assertNotIn('recorded_metrics,',text);self.assertNotIn('historical,',text)
 def test_edit_revokes_old_preserves_history(self):
  old=self.grant()['consent_ids'][0];new=self.grant([{'merchant':'M002','categories':['forecasts'],'allow_download':False,'replace_id':old}])['consent_ids'][0]
  with self.auth.db() as db:self.assertIsNotNone(db.execute('SELECT revoked_at FROM consents WHERE consent_id=?',(old,)).fetchone()[0]);self.assertIsNone(db.execute('SELECT revoked_at FROM consents WHERE consent_id=?',(new,)).fetchone()[0])
  self.assertEqual(len(self.s.listing(self.t)['consents']),2)
 def test_expiration_revocation_and_removal_block_access(self):
  cid=self.grant([{'merchant':'M002','categories':['reports'],'allow_download':True}])['consent_ids'][0];bank=self.tokens['lender_analyst'];self.w.review(bank,'M002',export=True)
  self.auth.revoke_consent(self.t,cid)
  with self.assertRaises(AccessDenied):self.w.review(bank,'M002',export=True)
  self.grant();self.s.remove(self.t,self.bank,{'merchants':['M002'],'confirmed':True})
  with self.assertRaises(AccessDenied):self.auth.authorize(bank,'view_reports','M002')
  with self.auth.db() as db:self.assertTrue(db.execute("SELECT 1 FROM memberships WHERE user_id=? AND merchant_id='M003'",(self.bank,)).fetchone())
 def test_batch_failure_is_atomic_and_explicit_confirmation(self):
  with self.assertRaises(InputError):self.grant([{'merchant':'M002','categories':['reports']},{'merchant':'M003','categories':['invented']}])
  self.assertFalse(self.s.listing(self.t)['consents'])
  with self.assertRaises(InputError):self.grant(confirmed=False)
  with self.assertRaises(InputError):self.s.remove(self.t,self.bank,{'merchants':['M002']})
 def test_staff_read_only_actual_authorization(self):
  uid=self.ids['staff'];self.s.save(self.t,{'role':'SME_STAFF','merchants':['M002'],'permissions':{'M002':['view_dashboard','view_forecasts','view_transactions']}},'edit',uid)
  token=self.auth.login('staff',PASSWORD)[0]
  for permission in ('view_dashboard','view_forecasts','view_transactions'):self.auth.authorize(token,permission,'M002')
  for permission in ('create_transactions','bulk_import','simulate_payments','submit_application','manage_consents','manage_merchant_staff','view_reports'):
   with self.subTest(permission=permission),self.assertRaises(AccessDenied):self.auth.authorize(token,permission,'M002')
 def test_existing_financing_decision_needs_routing_and_permission(self):
  self.grant();bank=self.tokens['lender_analyst']
  with self.assertRaises(AccessDenied):self.w.record_review(bank,'APP-unassigned',{'outcome':'approved'})
