import csv,io,json,os,sqlite3,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from tests.auth_support import setup_identity,PASSWORD
from copilot.auth import AuthStore,AuthError,InputError
from copilot.authorization import POLICY,AUTHORITATIVE_ROLES,STAFF_ACTIONS
from copilot.security import AccessDenied,Principal
from copilot.bank_workflow import BankWorkflow

class FourRoleWorkflow(unittest.TestCase):
 def setUp(self):
  setup_identity(self,all_merchants=True);self.w=BankWorkflow(self.auth,self.c)
 def consent(self,categories=None):
  return self.auth.grant_consent(self.tokens['owner'],{'merchant':'M002','recipient_id':self.ids['lender_analyst'],'purpose':'Synthetic Bank review','categories':categories or ['reports','assessment','forecasts','financing','applications'],'expires_at':self.auth.clock()+3600})
 def grantstaff(self,actions):
  self.w.staff(self.tokens['owner'],'M002',self.ids['staff'],{'permissions':actions})
  self.tokens['staff']=self.auth.login('staff',PASSWORD)[0]
 def submit(self):
  self.consent();amount=self.c.call(self.auth.principal(self.tokens['owner']),'rbf_quote','M002')['advance']
  r=self.w.draft(self.tokens['owner'],'M002',body={'amount':amount,'recipient_id':self.ids['lender_analyst']})
  proposal=self.w.propose(self.tokens['owner'],'M002',r['drafts'][0]['draft_id'])
  result=self.c.partner_state.confirm(self.auth.principal(self.tokens['owner']),'M002',self.auth.principal(self.tokens['owner']).session_id,proposal['action_id'],True)
  return result['result']
 def test_only_four_authoritative_roles_and_canonical_records(self):
  self.assertEqual(set(POLICY),{'SYSTEM_ADMIN','SME_OWNER','SME_STAFF','BANK'})
  with self.auth.db() as db:
   self.assertTrue({r[0] for r in db.execute('SELECT role FROM users')}<=set(POLICY))
  for role in ('coach','demo_guest'):
   from copilot.authorization import require
   with self.assertRaises(AccessDenied):require(Principal('legacy',role,{'M002'}),'view_reports','M002')
 def test_legacy_role_migration_preserves_records_and_revokes_sessions(self):
  from copilot.auth import password_hash,digest
  from copilot import auth as auth_module
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'legacy.sqlite3';db=sqlite3.connect(path)
   db.execute('CREATE TABLE schema_migrations(version TEXT PRIMARY KEY,applied_at REAL)')
   for migration in sorted((Path(auth_module.__file__).parent/'migrations').glob('*.sql')):
    if migration.name<'007':
     db.executescript(migration.read_text());db.execute('INSERT INTO schema_migrations VALUES (?,?)',(migration.name,1))
   for i,role in enumerate(('owner','staff','lender_analyst','security_admin','user_admin','coach')):
    db.execute('INSERT INTO users(user_id,username,email,display_name,role,password_hash,created_at,updated_at,created_by) VALUES(?,?,?,?,?,?,?,?,?)',(str(i),'legacy'+str(i),'legacy'+str(i)+'@example.test','Legacy',role,password_hash(PASSWORD),1,1,'fixture'))
    db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?)',(digest('old'+str(i)),str(i),'csrf',1,1,1,0))
   db.commit();db.close()
   migrated=AuthStore(path,self.c.merchants)
   with migrated.db() as db:
    roles={r['username']:r['role'] for r in db.execute('SELECT username,role FROM users')}
    self.assertEqual(roles['legacy0'],'SME_OWNER');self.assertEqual(roles['legacy2'],'BANK');self.assertEqual(roles['legacy4'],'user_admin');self.assertEqual(roles['legacy5'],'coach')
    self.assertEqual(db.execute('SELECT COUNT(*) FROM role_migration_history').fetchone()[0],6)
    self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions WHERE revoked=1').fetchone()[0],6)
   self.assertEqual(migrated.me(migrated.login('legacy0',PASSWORD)[0])['user']['effective_role'],'SME_OWNER')
   with self.assertRaises(AuthError):migrated.principal(migrated.login('legacy5',PASSWORD)[0])
 def test_admin_cannot_read_or_authorize_bank(self):
  for action in ('view_reports','simulate_payments','submit_application','manage_consents'):
   with self.assertRaises(AccessDenied):self.auth.authorize(self.tokens['security_admin'],action,'M002')
 def test_staff_explicit_delegation_and_no_submission(self):
  self.grantstaff(['use_copilot','view_applications','create_financing_draft','edit_financing_draft'])
  r=self.w.draft(self.tokens['staff'],'M002',body={'amount':100})
  self.w.draft(self.tokens['staff'],'M002',r['drafts'][0]['draft_id'],{'amount':200})
  for action in ('submit_application','prepare_application','manage_merchant_staff','manage_consents','view_reports'):
   with self.assertRaises(AccessDenied):self.auth.authorize(self.tokens['staff'],action,'M002')
  with self.assertRaises(AccessDenied):self.w.propose(self.tokens['staff'],'M002',r['drafts'][0]['draft_id'])
  self.assertEqual(self.c.handle(self.auth.principal(self.tokens['staff']),'M002','Submit financing application for 100')['intent'].endswith('denied'),True)
 def test_owner_cannot_delegate_privilege_or_foreign_staff(self):
  with self.assertRaises(InputError):self.w.staff(self.tokens['owner'],'M002',self.ids['staff'],{'permissions':['submit_application']})
  with self.assertRaises(AccessDenied):self.w.staff(self.tokens['owner'],'M002',self.ids['security_admin'],{'permissions':['use_copilot']})
 def test_bank_authorization_without_case_assignment(self):
  self.consent(['reports']);self.auth.authorize(self.tokens['lender_analyst'],'view_reports','M002')
  with self.assertRaises(AccessDenied):self.auth.authorize(self.tokens['lender_analyst'],'view_forecasts','M002')
  with self.assertRaises(AccessDenied):self.auth.authorize(self.tokens['lender_analyst'],'view_reports','M001')
 def test_bank_categories_and_csv(self):
  self.consent(['reports']);r=self.w.review(self.tokens['lender_analyst'],'M002')
  self.assertIn('historical',r['sections']);self.assertNotIn('assessment',r['sections']);self.assertNotIn('forecast',r['sections'])
  text=self.w.review(self.tokens['lender_analyst'],'M002',export=True).decode('utf-8-sig')
  self.assertIn('Simulated financial review',text);self.assertNotIn('M001',text)
  self.assertTrue(list(csv.reader(io.StringIO(text))))
 def test_expiry_revocation_block_new_exports_and_ai(self):
  cid=self.consent();self.w.review(self.tokens['lender_analyst'],'M002',export=True)
  self.auth.revoke_consent(self.tokens['owner'],cid['consent_id'])
  with self.assertRaises(AccessDenied):self.w.review(self.tokens['lender_analyst'],'M002',export=True)
  with self.assertRaises(AccessDenied):self.c.handle(self.auth.principal(self.tokens['lender_analyst']),'M002','Show my financial report')
  self.consent()
  with self.auth.db() as db:db.execute('UPDATE consents SET expires_at=?',(self.auth.clock()-1,))
  with self.assertRaises(AccessDenied):self.w.review(self.tokens['lender_analyst'],'M002')
 def test_owner_confirmed_submission_routed_and_persisted(self):
  packet=self.submit();self.assertEqual(packet['recipient_id'],self.ids['lender_analyst'])
  self.assertEqual(packet['status'],'SUBMITTED_FOR_LENDER_REVIEW')
  self.assertEqual(self.w.draft(self.tokens['owner'],'M002')['drafts'][0]['state'],'SUBMITTED')
  self.assertEqual(self.w.review(self.tokens['lender_analyst'],'M002',packet['application_id'])['application']['application_id'],packet['application_id'])
 def test_unrouted_application_denied(self):
  self.consent()
  with self.auth.db() as db:db.execute('INSERT INTO applications VALUES (?,?,?,?,?,?)',('APP-'+'b'*20,'M002',self.ids['owner'],self.ids['user_admin'],self.auth.clock(),json.dumps({'application_id':'APP-'+'b'*20})))
  with self.assertRaises(AccessDenied):self.w.review(self.tokens['lender_analyst'],'M002','APP-'+'b'*20)
 def test_selected_bank_status_rechecked_even_with_other_valid_authorization(self):
  self.consent()
  with self.auth.db() as db:
   user=self.auth._create(db,self.auth.principal(self.tokens['security_admin']),{'username':'bank2','email':'bank2@example.test','display_name':'Bank Two','role':'BANK','merchants':['M002'],'organization':'Synthetic bank'},PASSWORD,False)
  self.auth.grant_consent(self.tokens['owner'],{'merchant':'M002','recipient_id':user['user_id'],'purpose':'Synthetic alternate','categories':['applications'],'expires_at':self.auth.clock()+3600})
  draft=self.w.draft(self.tokens['owner'],'M002',body={'amount':100,'recipient_id':self.ids['lender_analyst']})['drafts'][0]
  self.auth.update_user(self.tokens['security_admin'],self.ids['lender_analyst'],{'account_status':'inactive'})
  with self.assertRaises(AccessDenied):self.w.propose(self.tokens['owner'],'M002',draft['draft_id'])
 def test_bank_cannot_mutate_decision_or_payment(self):
  self.consent()
  for action in ('review_application','simulate_payments','submit_application','create_transactions','manage_users'):
   with self.assertRaises(AccessDenied):self.auth.authorize(self.tokens['lender_analyst'],action,'M002')
 def test_selected_bank_required_and_stale_draft_rejected(self):
  self.consent();r=self.w.draft(self.tokens['owner'],'M002',body={'amount':100})
  with self.assertRaises(InputError):self.w.propose(self.tokens['owner'],'M002',r['drafts'][0]['draft_id'])
 def test_financial_tools_unchanged_and_audit_chain(self):
  p=self.auth.principal(self.tokens['owner']);before=self.c.financial_data.aggregate('M002')
  self.consent();r=self.w.review(self.tokens['lender_analyst'],'M002')
  self.assertEqual({k:v for k,v in before.items() if k not in ('retrieved_at','as_of')},{k:v for k,v in r['sections']['recorded_metrics'].items() if k not in ('retrieved_at','as_of')})
  self.assertEqual(r['sections']['forecast'],self.c.call(p,'cashflow_forecast','M002'))
  self.w.review(self.tokens['lender_analyst'],'M002',export=True)
  from copilot.security import AuditLog
  with self.auth.db() as db:records=[json.loads(r[0]) for r in db.execute('SELECT record FROM audit_events ORDER BY seq')]
  self.assertTrue(AuditLog.verify(records));self.assertTrue(any(r['action']=='bank_report_exported' for r in records))

if __name__=='__main__':unittest.main()
