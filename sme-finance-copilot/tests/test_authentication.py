import json
import os
import time
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import threading
import urllib.request
import urllib.error
from copilot.auth import AuthError, InputError, AuthStore, verify_password
from copilot.security import AccessDenied, ApprovalRequired, Tier, AuditLog
from copilot.tools_spec import execute
from tests.auth_support import setup_identity, attach_server, PASSWORD, CHANGED

class Authentication(unittest.TestCase):
    def setUp(self):
        self.mode=patch.dict(os.environ,{'COPILOT_AUTH_MODE':'authenticated'})
        self.mode.start();self.addCleanup(self.mode.stop)
        setup_identity(self)

    def p(self,role):return self.auth.principal(self.tokens[role])
    def grant(self,categories=None):
        return self.auth.grant_consent(self.tokens['owner'],{'merchant':'M002','recipient_id':self.ids['lender_analyst'],'purpose':'Financing review','categories':categories or ['applications','reports','assessment','financing','forecasts'],'expires_at':self.auth.clock()+3600})
    def submit(self):
        p=self.p('owner')
        with self.assertRaises(ApprovalRequired) as ctx:self.c.call(p,'prepare_financing_application','M002')
        return self.c.call(p,'prepare_financing_application','M002',approval_token=ctx.exception.token)

    def test_login_and_no_plaintext_password(self):
        token,csrf,change=self.auth.login('owner',PASSWORD)
        self.assertEqual(self.auth.principal(token).role,'owner');self.assertTrue(csrf);self.assertFalse(change)
        with self.auth.db() as db:
            stored=db.execute('SELECT password_hash FROM users WHERE user_id=?',(self.ids['owner'],)).fetchone()[0]
            self.assertNotIn(PASSWORD,stored);self.assertTrue(verify_password(PASSWORD,stored))
            self.assertIsNone(db.execute('SELECT 1 FROM sessions WHERE token_hash=?',(token,)).fetchone())

    def test_invalid_and_unknown_credentials_are_generic(self):
        for name in ('owner','unknown'):
            with self.assertRaises(AuthError) as ctx:self.auth.login(name,'wrong')
            self.assertEqual(str(ctx.exception),'Invalid credentials')

    def test_disabled_accounts_and_revoked_existing_session(self):
        for status in ('inactive','suspended','locked'):
            self.auth.update_user(self.tokens['security_admin'],self.ids['owner'],{'account_status':status})
            with self.assertRaises(AuthError):self.auth.login('owner',PASSWORD)
            with self.assertRaises(AuthError):self.auth.principal(self.tokens['owner'])

    def test_idle_and_absolute_expiry(self):
        now=time.time();self.auth.clock=lambda:now
        token=self.auth.login('owner',PASSWORD)[0]
        self.auth.clock=lambda:now+1801
        with self.assertRaises(AuthError):self.auth.principal(token)
        self.auth.clock=lambda:now
        token=self.auth.login('owner',PASSWORD)[0]
        with self.auth.db() as db:db.execute('UPDATE sessions SET last_seen=?',(now+28801,))
        self.auth.clock=lambda:now+28801
        with self.assertRaises(AuthError):self.auth.principal(token)

    def test_logout_and_csrf(self):
        token=self.tokens['owner'];csrf=self.auth.me(token)['csrf_token']
        self.auth.csrf(token,csrf)
        with self.assertRaises(AccessDenied):self.auth.csrf(token,'fake')
        self.auth.logout(token)
        with self.assertRaises(AuthError):self.auth.principal(token)

    def test_login_lockout_and_audit_survive_failure(self):
        for _ in range(5):
            with self.assertRaises(AuthError):self.auth.login('owner','wrong')
        with self.assertRaises(AuthError) as ctx:self.auth.login('owner',PASSWORD)
        self.assertEqual(ctx.exception.status,429)
        events=self.auth.audit_records(self.tokens['security_admin'],{'action':'login_failed'})
        self.assertGreaterEqual(len(events),6)

    def test_forced_password_change_and_all_session_invalidation(self):
        user=self.auth.create_user(self.tokens['security_admin'],{'username':'new','email':'new@example.test','display_name':'New Staff','role':'staff','merchants':['M002'],'transaction_grants':{'M002':['create_transactions']},'password':PASSWORD})
        token,_,force=self.auth.login('new',PASSWORD);self.assertTrue(force)
        with self.assertRaises(AccessDenied):self.auth.authorize(token,'create_transactions','M002')
        self.auth.change_password(token,PASSWORD,CHANGED)
        with self.assertRaises(AuthError):self.auth.principal(token)
        new=self.auth.login('new',CHANGED);self.assertFalse(new[2]);self.auth.authorize(new[0],'create_transactions','M002')

    def test_reset_token_expiring_single_use_and_no_secrets_in_audit(self):
        reset=self.auth.account_action(self.tokens['security_admin'],self.ids['owner'],'reset-password')['reset_token']
        self.auth.reset_password(reset,CHANGED)
        with self.assertRaises(InputError):self.auth.reset_password(reset,PASSWORD)
        self.assertEqual(self.auth.principal(self.auth.login('owner',CHANGED)[0]).role,'owner')
        records=self.auth.audit_records(self.tokens['security_admin'])
        self.assertNotIn(reset,json.dumps(records));self.assertNotIn(PASSWORD,json.dumps(records))
        reset=self.auth.account_action(self.tokens['security_admin'],self.ids['owner'],'reset-password')['reset_token']
        with self.auth.db() as db:db.execute('UPDATE reset_tokens SET expires_at=0')
        with self.assertRaises(InputError):self.auth.reset_password(reset,PASSWORD)

    def test_admin_roles_do_not_inherit_financial_permissions(self):
        for role in ('security_admin','user_admin'):
            self.assertFalse(self.p(role).merchant_ids)
            with self.assertRaises(AccessDenied):self.c.call(self.p(role),'get_dashboard','M002')
            with self.assertRaises(AccessDenied):execute(self.c,self.p(role),'list_merchants',{})

    def test_user_administrator_cannot_escalate_roles(self):
        body={'username':'escalate','email':'escalate@example.test','display_name':'No','role':'security_admin','merchants':[],'password':PASSWORD}
        with self.assertRaises(AccessDenied):self.auth.create_user(self.tokens['user_admin'],body)
        with self.assertRaises(AccessDenied):self.auth.update_user(self.tokens['user_admin'],self.ids['owner'],{'role':'security_admin','merchants':[]})
        with self.assertRaises(AccessDenied):self.auth.update_user(self.tokens['security_admin'],self.ids['security_admin'],{'role':'owner','merchants':['M002']})

    def test_last_security_administrator_protected(self):
        with self.assertRaises(AccessDenied):self.auth.update_user(self.tokens['security_admin'],self.ids['security_admin'],{'account_status':'suspended'})
        # A second administrator may maintain the first but cannot remove the final active administrator.
        user=self.auth.create_user(self.tokens['security_admin'],{'username':'admin2','email':'admin2@example.test','display_name':'Two','role':'security_admin','merchants':[],'password':PASSWORD})
        token=self.auth.login('admin2',PASSWORD)[0];self.auth.change_password(token,PASSWORD,CHANGED);token=self.auth.login('admin2',CHANGED)[0]
        self.auth.update_user(token,self.ids['security_admin'],{'account_status':'suspended'})
        with self.assertRaises(AccessDenied):self.auth.update_user(token,user['user_id'],{'account_status':'locked'})

    def test_staff_permissions_scope_and_ai_denial(self):
        staff=self.p('staff')
        row={'date':'2026-09-29','type':'income','amount':100}
        self.assertTrue(self.store.save(staff,'M002',[row])['valid'])
        with self.assertRaises(AccessDenied):self.store.save(staff,'M001',[row])
        with self.assertRaises(AccessDenied):self.store.preview(staff,'M002',{'rows':[row]})
        with self.assertRaises(AccessDenied):self.auth.security_policies(self.tokens['staff'])
        with self.assertRaises(AccessDenied):self.c.call(staff,'assess_business','M002')
        self.assertIn('Access denied',self.c.handle(staff,'M002','Show the financing assessment')['reply'])
        self.auth.update_user(self.tokens['security_admin'],self.ids['staff'],{'optional_permissions':['bulk_import']})
        with self.assertRaises(AuthError):self.auth.principal(self.tokens['staff'])
        self.tokens['staff']=self.auth.login('staff',PASSWORD)[0]
        self.assertTrue(self.store.preview(self.p('staff'),'M002',{'rows':[row|{'reference':'new'}]})['valid'])

    def test_financing_consent_assignment_categories_revocation(self):
        lender=self.p('lender_analyst')
        with self.assertRaises(AccessDenied):self.c.call(lender,'financial_report','M002')
        consent=self.grant(['applications','financing']);packet=self.submit()
        self.assertTrue(packet['sandbox'])
        self.c.call(lender,'rbf_quote','M002')
        with self.assertRaises(AccessDenied):self.c.call(lender,'financial_report','M002')
        with self.assertRaises(AccessDenied):self.store.preview(lender,'M002',{'rows':[]})
        self.auth.revoke_consent(self.tokens['owner'],consent['consent_id'])
        with self.assertRaises(AccessDenied):self.c.call(lender,'rbf_quote','M002')

    def test_consent_expiry_and_application_persistence(self):
        consent=self.grant();packet=self.submit()
        self.assertEqual(len(self.auth.application_list(self.tokens['lender_analyst'],'M002')),1)
        self.auth.review_application(self.tokens['lender_analyst'],packet['application_id'],{'outcome':'request_information','note':'Please provide inventory details'})
        self.assertEqual(len(self.auth.application_list(self.tokens['owner'],'M002')[0]['reviews']),1)
        with self.auth.db() as db:db.execute('UPDATE consents SET expires_at=0')
        with self.assertRaises(AccessDenied):self.auth.application_list(self.tokens['lender_analyst'],'M002')
        replay=AuthStore(self.auth.path,self.c.merchants)
        with replay.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM applications').fetchone()[0],1)

    def test_policies_boundaries_reauthentication_and_audit(self):
        for body in ({'settings':{'idle_timeout':1}},{'settings':{'password_require_mixed':False}}, {'permissions':{'staff':['submit_application']}},{'ai_tiers':{'owner':4}}):
            with self.assertRaises(InputError):self.auth.update_policies(self.tokens['security_admin'],body)
        with self.assertRaises(AccessDenied):self.auth.update_policies(self.tokens['user_admin'],{})
        self.auth.update_policies(self.tokens['security_admin'],{'settings':{'idle_timeout':600},'ai_tiers':{'owner':0}})
        with self.assertRaises(AccessDenied):self.c.call(self.p('owner'),'rbf_quote','M002')
        for role in self.tokens:
            with self.assertRaises(AccessDenied):self.c.call(self.p(role),'approve_credit','M002')
        self.assertTrue(self.auth.audit_records(self.tokens['security_admin'],{'action':'security_policy_changed'}))
        with self.auth.db() as db:db.execute('UPDATE sessions SET reauthenticated_at=0')
        with self.assertRaises(AccessDenied):self.auth.update_policies(self.tokens['security_admin'],{})
        self.auth.reauthenticate(self.tokens['security_admin'],PASSWORD)
        self.auth.update_policies(self.tokens['security_admin'],{})

    def test_account_search_details_history_and_audit_chain(self):
        self.assertEqual(len(self.auth.users(self.tokens['user_admin'],'owner')),1)
        self.auth.update_user(self.tokens['security_admin'],self.ids['owner'],{'display_name':'Updated Owner'})
        with self.auth.db() as db:records=[json.loads(r[0]) for r in db.execute('SELECT record FROM audit_events ORDER BY seq')]
        self.assertTrue(AuditLog.verify(records))
        records[0]['action']='tampered';self.assertFalse(AuditLog.verify(records))
        account_events=self.auth.audit_records(self.tokens['user_admin'])
        self.assertTrue(all(r['action']!='ai_tool_execution' for r in account_events))

    def test_global_upload_policy_cannot_be_bypassed_by_optional_grant(self):
        self.auth.update_user(self.tokens['security_admin'],self.ids['staff'],{'optional_permissions':['bulk_import']})
        token=self.auth.login('staff',PASSWORD)[0]
        self.auth.authorize(token,'bulk_import','M002')
        self.auth.update_policies(self.tokens['security_admin'],{'permissions':{'staff':['create_transactions','view_transactions','use_copilot']}})
        with self.assertRaises(AccessDenied):self.auth.authorize(token,'bulk_import','M002')

    def test_reauthentication_failures_lock_session_and_admin_can_unlock(self):
        token=self.tokens['user_admin']
        for _ in range(5):
            with self.assertRaises(AuthError):self.auth.reauthenticate(token,'wrong')
        with self.assertRaises(AuthError):self.auth.principal(token)
        self.auth.update_user(self.tokens['security_admin'],self.ids['user_admin'],{'account_status':'active'})
        self.assertEqual(self.auth.principal(self.auth.login('user_admin',PASSWORD)[0]).role,'user_admin')

    def test_live_principal_policy_refresh_and_consent_loss(self):
        p=self.p('owner')
        self.auth.update_policies(self.tokens['security_admin'],{'ai_tiers':{'owner':0}})
        with self.assertRaises(AccessDenied):self.c.call(p,'rbf_quote','M002')

    def test_migrations_idempotent_and_legacy_ledger_unchanged(self):
        row={'date':'2026-09-29','type':'income','amount':15.50,'reference':'MIGRATION'}
        self.store.save(self.p('owner'),'M002',[row])
        from pathlib import Path
        before=Path(self.store.path).read_bytes()
        self.auth.migrate();self.auth.migrate()
        self.assertEqual(Path(self.store.path).read_bytes(),before)
        with self.auth.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],4)

    def test_financing_data_master_permission_is_enforced(self):
        self.grant();self.submit()
        self.auth.update_policies(self.tokens['security_admin'],{'permissions':{'lender_analyst':['view_financing','view_applications','use_copilot']}})
        with self.assertRaises(AccessDenied):self.c.call(self.p('lender_analyst'),'rbf_quote','M002')

class AuthenticatedHTTP(unittest.TestCase):
    def setUp(self):
        self.mode=patch.dict(os.environ,{'COPILOT_AUTH_MODE':'authenticated'});self.mode.start();self.addCleanup(self.mode.stop)
        setup_identity(self);attach_server(self)
        from copilot.server import Handler
        self.srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=self.srv.serve_forever,daemon=True).start()
        self.addCleanup(self.srv.server_close);self.addCleanup(self.srv.shutdown)

    def req(self,path,role=None,body=None,method=None,extra=None,csrf=True):
        headers={'Content-Type':'application/json'}
        if role:
            headers['Cookie']='sme_session='+self.tokens[role]
            if csrf:headers['X-CSRF-Token']=self.auth.me(self.tokens[role])['csrf_token']
        headers.update(extra or {})
        request=urllib.request.Request(f'http://127.0.0.1:{self.srv.server_port}'+path,
            data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
        try:
            with urllib.request.urlopen(request) as r:
                raw=r.read();return r.status,json.loads(raw) if r.headers.get_content_type()=='application/json' and raw else raw,dict(r.headers)
        except urllib.error.HTTPError as e:
            with e:return e.code,json.load(e),dict(e.headers)

    def test_login_cookie_and_role_header_cannot_impersonate(self):
        status,data,headers=self.req('/api/auth/login',body={'username':'owner','password':PASSWORD})
        self.assertEqual(status,200);cookie=headers['Set-Cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
        with patch.dict(os.environ,{'COPILOT_HTTPS':'yes'}):
            self.assertIn('Secure',self.req('/api/auth/login',body={'username':'owner','password':PASSWORD})[2]['Set-Cookie'])
        self.assertEqual(self.req('/api/dashboard?merchant=M002',extra={'X-Demo-Role':'owner','X-Demo-Consent':'yes'})[0],401)
        self.assertEqual(self.req('/api/security/policies','staff',extra={'X-Demo-Role':'security_admin'})[0],403)

    def test_direct_http_scope_csrf_and_admin_separation(self):
        row={'date':'2026-09-29','type':'income','amount':100}
        self.assertEqual(self.req('/api/transactions/entry','staff',{'merchant':'M002','entry':row},csrf=False)[0],403)
        self.assertEqual(self.req('/api/transactions/entry','staff',{'merchant':'M002','entry':row})[0],200)
        self.assertEqual(self.req('/api/transactions/entry','staff',{'merchant':'M001','entry':row})[0],404)
        self.assertEqual(self.req('/api/admin/users','owner')[0],403)
        self.assertEqual(self.req('/api/dashboard?merchant=M002','user_admin')[0],403)
        self.assertEqual(self.req('/api/transactions/preview','staff',{'merchant':'M002','rows':[row]})[0],403)
        self.assertEqual(self.req('/api/transactions/import','lender_analyst',{'merchant':'M002','rows':[row]})[0],403)

    def test_mcp_api_key_and_env_identity_cannot_bypass(self):
        body={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_dashboard','arguments':{'merchant_id':'M002'}}}
        with patch.dict(os.environ,{'COPILOT_MCP_API_KEY':'unrestricted','COPILOT_MCP_ROLE':'owner'}):
            self.assertEqual(self.req('/mcp',body=body,extra={'Authorization':'Bearer unrestricted','X-Demo-Role':'owner'})[0],401)
            status,r,_=self.req('/mcp','owner',body);self.assertEqual(status,200);self.assertFalse(r['result']['isError'])
            body['params']['arguments']['merchant_id']='M001';self.assertTrue(self.req('/mcp','owner',body)[1]['result']['isError'])
            body['params']={'name':'assess_business','arguments':{'merchant_id':'M002'}}
            self.assertTrue(self.req('/mcp','staff',body)[1]['result']['isError'])

    def test_admin_endpoints_security_pages_and_audit(self):
        self.assertEqual(self.req('/admin/users','user_admin')[0],200)
        self.assertEqual(self.req('/admin/security','staff')[0],403)
        self.assertEqual(self.req('/api/security/policies','security_admin',{'settings':{'idle_timeout':900}},'PATCH')[0],200)
        r=self.req('/api/security/audit?action=security_policy_changed','security_admin')[1]
        self.assertEqual(len(r['records']),1)
        detail=self.req('/api/admin/users/'+self.ids['owner'],'user_admin')[1];self.assertEqual(detail['user']['role'],'owner')

    def test_logout_and_external_origin(self):
        self.assertEqual(self.req('/api/auth/logout','owner',{})[0],200)
        self.assertEqual(self.req('/api/auth/me',extra={'Cookie':'sme_session='+self.tokens['owner']})[0],401)
        self.assertEqual(self.req('/api/auth/login',body={'username':'staff','password':PASSWORD},extra={'Origin':'https://evil.example'})[0],403)
