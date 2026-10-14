"""Portable policy tests use isolated SQLite copies; never a developer's live DB."""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from copilot.auth import AuthStore, InputError, POLICIES, RANGES
from copilot.authorization import BOUNDARIES
from copilot.security import AccessDenied, AuditLog
from copilot.security_configuration import parse_file, normalize, configuration_digest
from copilot.agent import Copilot
from copilot.modules.transactions import TransactionStore
from copilot import mcp_server
from tests.auth_support import setup_identity, attach_server, PASSWORD
from tests import test_authentication as existing_http

class ConfigFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template=SimpleNamespace(addCleanup=cls.addClassCleanup)
        setup_identity(cls.template)

    def setUp(self):
        mode=patch.dict(os.environ,{'COPILOT_AUTH_MODE':'authenticated'})
        mode.start();self.addCleanup(mode.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'identity.sqlite3'
        shutil.copyfile(self.template.auth.path,self.path)
        self.auth=AuthStore(self.path,self.template.c.merchants)
        self.tokens=self.template.tokens.copy();self.ids=self.template.ids.copy()
        self.c=Copilot();self.c.identity_store=self.auth;self.c.audit.sink=self.auth.financial_audit
        self.store=TransactionStore(self.c,str(Path(self.tmp.name)/'transactions.jsonl'))
        self.service=self.auth.security_config;self.admin=self.tokens['security_admin']

    def current(self):
        with self.auth.db() as db:return self.service.current(db)

    def preview(self,config=None,token=None):
        return self.service.preview(token or self.admin,{'filename':'security-config.json','content':json.dumps(config or self.current())})

    def apply(self,preview,token=None):
        return self.service.apply(token or self.admin,{'preview_token':preview['preview_token'],'confirmed':True})

    def local_records(self):
        tables=('users','sessions','memberships','optional_permissions','consents','applications','application_reviews','reset_tokens','staff_access_requests')
        with self.auth.db() as db:return {table:[tuple(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid')] for table in tables}

class ConfigurationUnit(ConfigFixture):
    def test_export_is_complete_supported_and_contains_no_local_data(self):
        exported=self.service.export(self.admin)
        self.assertEqual(normalize(exported),exported)
        self.assertEqual(set(exported),{'schema_version','application','authentication','permissions','ai_tiers'})
        self.assertEqual(set(exported['authentication']),set(POLICIES))
        self.assertEqual(set(exported['permissions']),set(BOUNDARIES))
        raw=json.dumps(exported)
        for secret in [PASSWORD,str(self.auth.path),*self.tokens.values(),*self.ids.values(),'security@example.test','csrf_token','password_hash','"consents":','"transactions":']:
            self.assertNotIn(secret,raw)
        self.assertEqual(exported,self.current())

    def test_preview_complete_difference_and_cancel_changes_nothing(self):
        before=self.current();local=self.local_records()
        config=copy.deepcopy(before);config['authentication']['password_min_length']=14
        result=self.preview(config)
        self.assertEqual(result['change_count'],1)
        self.assertEqual(len(result['differences']),len(POLICIES)+2*len(BOUNDARIES))
        changed=[r for r in result['differences'] if r['changed']][0]
        self.assertEqual(changed,{'setting':'authentication.password_min_length','current':12,'imported':14,'changed':True})
        # Cancel simply discards the preview. Policy, identity and financial records are untouched.
        self.assertEqual(self.current(),before);self.assertEqual(self.local_records(),local)

    def test_strict_json_file_validation(self):
        invalid=[('x.csv','{}'),('x.json','{bad'),('x.json',''),('x.json',' ' * 65537),
                 ('x.json','{"schema_version":1,"schema_version":1}'),('x.json','{"test":NaN}'),
                 ('x.json','['*1500+']'*1500),('x.json','{"n":'+('9'*5000)+'}')]
        for filename,content in invalid:
            with self.subTest(filename=filename,length=len(content)),self.assertRaises(InputError):
                self.service.preview(self.admin,{'filename':filename,'content':content})

    def test_schema_version_application_unknown_and_missing_fields(self):
        baseline=self.current()
        cases=[]
        for key,value in [('schema_version',2),('schema_version',True),('application','other'),('password','DO_NOT_LOG_SECRET')]:
            cases.append({**baseline,key:value})
        cases.append({k:v for k,v in baseline.items() if k!='authentication'})
        for config in cases:
            with self.subTest(keys=list(config)),self.assertRaises(InputError):self.preview(config)
        logs=self.auth.audit_records(self.admin)
        self.assertNotIn('DO_NOT_LOG_SECRET',json.dumps(logs))

    def test_nested_unknown_missing_and_invalid_types(self):
        baseline=self.current()
        for group in ('authentication','permissions','ai_tiers'):
            for mode in ('unknown','missing','wrong_type'):
                candidate=copy.deepcopy(baseline)
                if mode=='unknown':candidate[group]['unknown_secret']='DO_NOT_LOG_SECRET'
                elif mode=='missing':candidate[group].pop(next(iter(candidate[group])))
                else:candidate[group]=[]
                with self.subTest(group=group,mode=mode),self.assertRaises(InputError):self.preview(candidate)

    def test_authentication_bounds_complexity_and_session_relationship(self):
        for key,(low,high) in RANGES.items():
            for value in (low-1,high+1,True,'1200',1.0):
                config=self.current();config['authentication'][key]=value
                with self.subTest(key=key,value=value),self.assertRaises(InputError):self.preview(config)
        config=self.current();config['authentication']['password_require_mixed']=False
        with self.assertRaises(InputError):self.preview(config)
        config=self.current();config['authentication'].update(idle_timeout=3600,max_session_lifetime=900)
        with self.assertRaises(InputError):self.preview(config)

    def test_permission_boundaries_essential_admin_and_duplicate_actions(self):
        cases=[('staff',['submit_application']),('security_admin',['get_dashboard']),('security_admin',[]),('owner',['view_dashboard','view_dashboard']),('owner','view_dashboard')]
        for role,actions in cases:
            config=self.current();config['permissions'][role]=actions
            with self.subTest(role=role,actions=actions),self.assertRaises(InputError):self.preview(config)

    def test_tiers_cannot_enable_t4_or_admin_financial_access(self):
        for role,value in [('owner',4),('staff',3),('security_admin',1),('owner',True),('owner',-1),('owner','3')]:
            config=self.current();config['ai_tiers'][role]=value
            with self.subTest(role=role,value=value),self.assertRaises(InputError):self.preview(config)
        for role in self.tokens:
            with self.assertRaises(AccessDenied):self.c.call(self.auth.principal(self.tokens[role]),'approve_credit','M002')

    def test_export_preview_and_import_require_security_administrator(self):
        allowed=self.preview()
        for role in ('owner','staff','lender_analyst'):
            token=self.tokens[role]
            with self.subTest(role=role):
                with self.assertRaises(AccessDenied):self.service.export(token)
                with self.assertRaises(AccessDenied):self.preview(token=token)
                with self.assertRaises(AccessDenied):self.apply(allowed,token)

    def test_recent_reauthentication_required_to_apply(self):
        config=self.current();config['authentication']['idle_timeout']=1200
        preview=self.preview(config)
        with self.auth.db() as db:db.execute('UPDATE sessions SET reauthenticated_at=0')
        with self.assertRaises(AccessDenied):self.apply(preview)
        self.auth.reauthenticate(self.admin,PASSWORD)
        self.assertTrue(self.apply(preview)['changed'])

    def test_confirmed_single_use_session_bound_and_expiring_preview(self):
        preview=self.preview()
        with self.assertRaises(InputError):self.service.apply(self.admin,{'preview_token':preview['preview_token'],'confirmed':False})
        other_session=self.auth.login('security',PASSWORD)[0]
        with self.assertRaises(InputError):self.apply(preview,other_session)
        self.apply(preview)
        with self.assertRaises(InputError):self.apply(preview)
        fresh=self.preview();now=self.auth.clock();self.auth.clock=lambda:now+601
        self.auth.reauthenticate(self.admin,PASSWORD)
        with self.assertRaises(InputError):self.apply(fresh)

    def test_no_payload_substitution_at_apply(self):
        preview=self.preview()
        with self.assertRaises(InputError):self.service.apply(self.admin,{'preview_token':preview['preview_token'],'confirmed':True,'configuration':self.current()})

    def test_stale_and_reverted_policy_previews_rejected(self):
        preview=self.preview()
        self.auth.update_policies(self.admin,{'settings':{'password_min_length':14}})
        with self.assertRaises(InputError) as ctx:self.apply(preview)
        self.assertEqual(ctx.exception.status,409)
        self.auth.update_policies(self.admin,{'settings':{'password_min_length':12}})
        with self.assertRaises(InputError):self.apply(preview)

    def test_atomic_rollback_on_injected_write_failure(self):
        before=self.current();local=self.local_records()
        config=copy.deepcopy(before);config['authentication']['password_min_length']=14;config['ai_tiers']['owner']=1
        preview=self.preview(config);original=self.auth._write_policy_changes
        def fail_after_writes(db,settings,permissions,tiers):
            original(db,settings,permissions,tiers)
            raise RuntimeError('DO_NOT_LOG_SECRET')
        with patch.object(self.auth,'_write_policy_changes',side_effect=fail_after_writes),self.assertRaises(InputError) as ctx:self.apply(preview)
        self.assertEqual(ctx.exception.status,500);self.assertNotIn('DO_NOT_LOG_SECRET',str(ctx.exception))
        self.assertEqual(self.current(),before);self.assertEqual(self.local_records(),local)
        with self.auth.db() as db:self.assertEqual(self.service.revision(db),0)
        self.assertTrue(self.apply(preview)['changed'])

    def test_idempotence_and_restart_persistence(self):
        config=self.current();config['authentication']['password_min_length']=14
        self.apply(self.preview(config))
        with self.auth.db() as db:revision=self.service.revision(db)
        result=self.apply(self.preview(config));self.assertFalse(result['changed'])
        with self.auth.db() as db:self.assertEqual(self.service.revision(db),revision)
        restarted=AuthStore(self.path,self.c.merchants)
        with restarted.db() as db:self.assertEqual(restarted.security_config.current(db),normalize(config))

    def test_independent_installation_receives_equivalent_policies(self):
        config=self.current();config['authentication']['failure_threshold']=3;config['ai_tiers']['staff']=1
        self.apply(self.preview(config));exported=self.service.export(self.admin)
        other=AuthStore(Path(self.tmp.name)/'team-member.sqlite3',self.c.merchants)
        other.bootstrap('teammate','teammate@example.test',PASSWORD)
        token=other.login('teammate',PASSWORD)[0]
        with other.db() as db:before=[tuple(r) for r in db.execute('SELECT * FROM users')]
        p=other.security_config.preview(token,{'filename':'shared.json','content':json.dumps(exported)})
        other.security_config.apply(token,{'preview_token':p['preview_token'],'confirmed':True})
        with other.db() as db:
            self.assertEqual(other.security_config.current(db),exported)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM users')],before)

    def test_identity_consent_application_and_financial_records_preserved(self):
        owner=self.auth.principal(self.tokens['owner'])
        self.store.save(owner,'M002',[{'date':'2026-09-29','type':'income','amount':100,'reference':'KEEP'}])
        self.auth.grant_consent(self.tokens['owner'],{'merchant':'M002','recipient_id':self.ids['lender_analyst'],'purpose':'Keep consent','categories':['applications','financing'],'expires_at':self.auth.clock()+3600})
        from copilot.security import ApprovalRequired
        try:self.c.call(owner,'prepare_financing_application','M002')
        except ApprovalRequired as e:approval=e.token
        self.c.call(owner,'prepare_financing_application','M002',approval_token=approval,recipient_id=self.ids['lender_analyst'])
        before=self.local_records();ledger=Path(self.store.path).read_bytes()
        config=self.current();config['authentication']['password_min_length']=14
        self.apply(self.preview(config))
        self.assertEqual(self.local_records(),before);self.assertEqual(Path(self.store.path).read_bytes(),ledger)

    def test_audit_success_denial_failure_metadata_and_hash_chain(self):
        self.service.export(self.admin);self.apply(self.preview())
        with self.assertRaises(AccessDenied):self.service.export(self.tokens['owner'])
        with self.assertRaises(InputError):self.service.preview(self.admin,{'filename':'secret.json','content':'{"secret":"DO_NOT_LOG_SECRET"}'})
        events=self.auth.audit_records(self.admin)
        self.assertTrue(any(e['action']=='security_config_export' and e['result']=='denied' for e in events))
        self.assertTrue(any(e['action']=='security_config_validate' and e['result']=='failed' for e in events))
        successful=next(e for e in events if e['action']=='security_config_import')
        self.assertEqual(successful['schema_version'],1);self.assertIn('configuration_digest',successful)
        self.assertNotIn('DO_NOT_LOG_SECRET',json.dumps(events))
        self.assertNotIn(self.admin,json.dumps(events))
        self.assertTrue(AuditLog.verify(list(reversed(events))))

    def test_generated_digest_is_retained_verbatim_without_pii_masking(self):
        generated='1'*64
        record=self.auth.audit('security_config_export',self.auth.principal(self.admin),metadata={'schema_version':1,'configuration_digest':generated})
        self.assertEqual(record['configuration_digest'],generated)
        with self.auth.db() as db:
            events=[json.loads(r[0]) for r in db.execute('SELECT record FROM audit_events ORDER BY seq')]
        self.assertTrue(AuditLog.verify(events))

    def test_no_change_preview_cannot_be_confirmed_concurrently_twice(self):
        preview=self.preview();barrier=threading.Barrier(2)
        def confirm():
            barrier.wait()
            try:return self.apply(preview)['ok']
            except InputError:return False
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _:confirm(),range(2)))
        self.assertEqual(sorted(results),[False,True])

    def test_preview_capacity_rejection_is_audited_as_failure_only(self):
        now=self.auth.clock()
        self.service.previews={str(i):{'expires_at':now+600} for i in range(256)}
        with self.assertRaises(InputError) as ctx:self.preview()
        self.assertEqual(ctx.exception.status,429)
        events=self.auth.audit_records(self.admin,{'action':'security_config_validate'})
        self.assertEqual(len(events),1);self.assertEqual(events[0]['result'],'failed')

    def test_live_ai_and_mcp_authorization_use_imported_tiers(self):
        owner=self.auth.principal(self.tokens['owner'])
        config=self.current();config['ai_tiers']['owner']=0
        self.apply(self.preview(config))
        with self.assertRaises(AccessDenied):self.c.call(owner,'rbf_quote','M002')
        rpc=mcp_server.MCPHandler(self.c,owner).handle({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'rbf_quote','arguments':{'merchant_id':'M002'}}})
        self.assertTrue(rpc['result']['isError'])
        self.assertIn('mix',self.c.call(owner,'get_dashboard','M002'))

class ConfigurationHTTP(ConfigFixture):
    req=existing_http.AuthenticatedHTTP.req

    def setUp(self):
        super().setUp();attach_server(self)
        from copilot.server import Handler
        self.srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=self.srv.serve_forever,daemon=True).start()
        self.addCleanup(self.srv.server_close);self.addCleanup(self.srv.shutdown)

    def test_security_page_access_and_all_operations_authorized(self):
        self.assertEqual(self.req('/admin/security','security_admin')[0],200)
        for role in ('owner','staff','lender_analyst'):
            self.assertEqual(self.req('/admin/security',role)[0],403)
            self.assertEqual(self.req('/api/security/config/export',role)[0],403)
            self.assertEqual(self.req('/api/security/config/validate',role,{'filename':'x.json','content':'{}'})[0],403)
            self.assertEqual(self.req('/api/security/config/import',role,{'preview_token':'fake','confirmed':True})[0],403)
        self.assertEqual(self.req('/api/security/config/export')[0],401)

    def test_export_filename_and_preview_apply_current_behavior(self):
        status,config,headers=self.req('/api/security/config/export','security_admin')
        self.assertEqual(status,200);self.assertIn('security-config.json',headers['Content-Disposition'])
        config['authentication']['password_min_length']=14
        status,preview,_=self.req('/api/security/config/validate','security_admin',{'filename':'security-config.json','content':json.dumps(config)})
        self.assertEqual(status,200);self.assertEqual(preview['change_count'],1)
        status,result,_=self.req('/api/security/config/import','security_admin',{'preview_token':preview['preview_token'],'confirmed':True})
        self.assertEqual(status,200);self.assertTrue(result['changed'])
        self.assertEqual(self.req('/api/security/policies','security_admin')[1]['settings']['password_min_length'],14)

    def test_csrf_outer_malformed_json_and_audit_filters(self):
        self.assertEqual(self.req('/api/security/config/validate','security_admin',{'filename':'x.json','content':'{}'},csrf=False)[0],403)
        self.assertEqual(self.req('/api/security/config/validate','security_admin',{'filename':'x.json','content':'{bad'})[0],400)
        records=self.req('/api/security/audit?action=security_config_validate&result=failed','security_admin')[1]['records']
        self.assertTrue(records);self.assertTrue(all(r['result']=='failed' for r in records))

    def test_import_stale_reauthentication_and_t4_through_http(self):
        config=self.current();config['ai_tiers']['owner']=4
        self.assertEqual(self.req('/api/security/config/validate','security_admin',{'filename':'x.json','content':json.dumps(config)})[0],400)
        config=self.current();config['authentication']['idle_timeout']=1200
        preview=self.req('/api/security/config/validate','security_admin',{'filename':'x.json','content':json.dumps(config)})[1]
        with self.auth.db() as db:db.execute('UPDATE sessions SET reauthenticated_at=0')
        body={'preview_token':preview['preview_token'],'confirmed':True}
        self.assertEqual(self.req('/api/security/config/import','security_admin',body)[0],403)
        self.auth.reauthenticate(self.admin,PASSWORD)
        self.auth.update_policies(self.admin,{'settings':{'password_min_length':14}})
        self.assertEqual(self.req('/api/security/config/import','security_admin',body)[0],409)
