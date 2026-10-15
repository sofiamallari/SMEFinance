import base64,copy,json,os,shutil,tempfile,threading,unittest,zipfile,io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from copilot.auth import AuthStore,InputError,AuthError
from copilot.security import AccessDenied
from copilot.agent import Copilot
from copilot.modules.transactions import TransactionStore
from copilot.pos_import import POSImportService,TTL
from copilot.pos_extract import extract_files
from copilot.canonical_transactions import normalize,money
from copilot.transaction_journal import LedgerError
from tests.auth_support import setup_identity,attach_server,PASSWORD
from tests import test_authentication as http_support
from tests.pos_fixtures import csv_file,xlsx_bytes,mapping

class POSFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=SimpleNamespace(addCleanup=cls.addClassCleanup);setup_identity(cls.base)
    def setUp(self):
        mode=patch.dict(os.environ,{'COPILOT_AUTH_MODE':'authenticated'});mode.start();self.addCleanup(mode.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        path=Path(self.tmp.name)/'identity.sqlite3';shutil.copyfile(self.base.auth.path,path)
        self.c=Copilot();self.auth=AuthStore(path,self.c.merchants);self.c.identity_store=self.auth
        self.c.audit.sink=self.auth.financial_audit;self.tokens=self.base.tokens.copy();self.ids=self.base.ids.copy()
        self.store=TransactionStore(self.c,str(Path(self.tmp.name)/'transactions.jsonl'))
        self.pos=POSImportService(self.auth,self.store);self.owner=self.tokens['owner'];self.mid='M002'
    def stage(self,files=None):return self.pos.stage(self.owner,self.mid,files or [csv_file()])
    def validated(self,files=None,controls=None):
        staged=self.stage(files);result=self.pos.validate(self.owner,self.mid,staged['batch_id'],mapping(staged,controls));return staged,result
    def commit(self,staged,result):return self.pos.commit(self.owner,self.mid,staged['batch_id'],result['preview_token'],True)
    def entry(self,**change):return {'transaction_date':'2026-10-01T10:00:00+07:00','net_amount':'100.00','currency':'IDR','transaction_type':'sale','payment_method':'cash','status':'completed','external_reference':'MANUAL-1',**change}

class CanonicalAndExtraction(POSFixture):
    def test_decimal_types_statuses_currency_dates_and_mass_assignment(self):
        row=normalize(self.entry(),self.c.merchants[self.mid],{},self.auth.clock())
        self.assertEqual(row['amount'],'100.00');self.assertEqual(row['transaction_date'],'2026-10-01T03:00:00Z')
        for changes in ({'net_amount':'1.001'},{'net_amount':'NaN'},{'net_amount':True},{'transaction_date':'2030-01-01'},{'currency':'USD'},{'status':'unknown'},{'transaction_type':'credit_approval'},{'created_by':'admin'},{'description':'=cmd()'}):
            with self.subTest(changes=changes),self.assertRaises(InputError):normalize(self.entry(**changes),self.c.merchants[self.mid],{},self.auth.clock())
        self.assertEqual(money('1,234.50').as_tuple().exponent,-2)
    def test_refunds_reversals_voids_pending_and_gross_net(self):
        for kind in ('refund','reversal','expense'):
            self.assertEqual(normalize(self.entry(transaction_type=kind),self.c.merchants[self.mid],{},self.auth.clock())['amount'],'-100.00')
        for state in ('failed','pending','voided'):
            self.assertEqual(normalize(self.entry(status=state),self.c.merchants[self.mid],{},self.auth.clock())['effective_amount'],'0.00')
        row=normalize(self.entry(net_amount='102.00',gross_amount='100.00',discount='10.00',tax='12.00'),self.c.merchants[self.mid],{},self.auth.clock())
        self.assertEqual(row['amount'],'102.00')
        with self.assertRaises(InputError):normalize(self.entry(net_amount='101',gross_amount='100',tax='12'),self.c.merchants[self.mid],{},self.auth.clock())
    def test_multiple_nested_folder_files_and_xlsx_native_dates(self):
        files=[csv_file(),csv_file(name='other.csv'),{'filename':'native.xlsx','relative_path':'demo/nested/native.xlsx','content':base64.b64encode(xlsx_bytes(native_date=True)).decode()}]
        source=extract_files(files,self.mid);self.assertEqual(len(source),3);self.assertIn('2026-10-01',source[2]['rows'][0]['values']['date'])
        self.assertEqual(source[2]['relative_path'],'demo/nested/native.xlsx')
    def test_unsafe_file_structures_formulas_limits_and_encoding(self):
        cases=[{'filename':'x.xlsm','content':'AAAA'}, {'filename':'x.xlsx','content':base64.b64encode(b'not a zip').decode()},
            {'filename':'x.csv','content':base64.b64encode(b'\xff\xfe').decode()}, {'filename':'../x.csv','content':csv_file()['content']},
            {'filename':'x.xlsx','content':base64.b64encode(xlsx_bytes(formula=True)).decode()}, {'filename':'x.xlsx','content':base64.b64encode(xlsx_bytes(external=True)).decode()},
            {'filename':'x.csv','content':'A'*4_000_004},csv_file(rows=[['2026-10-01','=cmd()','IDR','sale','cash','paid','X']])]
        for item in cases:
            with self.subTest(name=item['filename']),self.assertRaises(InputError):extract_files([item],self.mid)
        with self.assertRaises(InputError):extract_files([csv_file()]*11,self.mid)
        with self.assertRaises(InputError):extract_files([csv_file(rows=[['x']*31],headers=[str(i) for i in range(31)])],self.mid)
        with self.assertRaises(InputError):extract_files([csv_file(rows=[['2026-10-01','1','IDR','sale','cash','paid',str(i)] for i in range(10001)])],self.mid)
    def test_sensitive_columns_excluded_and_resource_attack_rejected(self):
        file=csv_file(rows=[['2026-10-01','100','IDR','sale','cash','paid','X','private@example.test']],headers=['date','net_amount','currency','type','channel','status','reference','customer email'])
        source=extract_files([file],self.mid);self.assertEqual(source[0]['excluded_sensitive_columns'],1);self.assertNotIn('private@example',json.dumps(source))
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('bomb.xml','x'*21_000_000)
        with self.assertRaises(InputError):extract_files([{'filename':'bomb.xlsx','content':base64.b64encode(out.getvalue()).decode()}],self.mid)

class POSPipeline(POSFixture):
    def test_single_entry_submission_idempotency_and_duplicate_rejection(self):
        before=self.c.call(self.auth.principal(self.owner),'get_dashboard',self.mid,start='2026-07-01',end='2026-10-01')
        first=self.pos.single(self.owner,self.mid,self.entry(),'single-key-1')
        self.assertEqual(first,self.pos.single(self.owner,self.mid,self.entry(),'single-key-1'))
        with self.assertRaises(InputError):self.pos.single(self.owner,self.mid,self.entry(net_amount='200'),'single-key-1')
        with self.assertRaises(InputError):self.pos.single(self.owner,self.mid,self.entry(),'single-key-2')
        self.assertEqual(self.pos.history(self.owner,self.mid)['total'],1)
        # Task 03 consumes canonical records once. Keep the period fixed so the
        # assertion measures the new entry rather than a moving default window.
        after=self.c.call(self.auth.principal(self.owner),'get_dashboard',self.mid,start='2026-07-01',end='2026-10-01')
        from decimal import Decimal
        self.assertEqual(Decimal(after['financial_metrics']['net_sales'])-Decimal(before['financial_metrics']['net_sales']),Decimal('100.00'))
        self.assertEqual(after['mix']['total_transactions'],before['mix']['total_transactions']+1)
        self.assertEqual(after['period'],before['period'])
    def test_staging_mapping_preview_commit_and_provenance(self):
        staged,validated=self.validated(controls={'count':2,'net_total':'150.00','basis':'completed_net'})
        self.assertEqual(validated['metrics']['eligible_total'],'150.00');self.assertTrue(validated['valid'])
        self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
        preview=self.pos.preview(self.owner,self.mid,staged['batch_id']);self.assertEqual(len(preview['rows']),2)
        result=self.commit(staged,validated);self.assertEqual(result['imported_rows'],2)
        row=self.pos.history(self.owner,self.mid)['transactions'][0]
        self.assertEqual(row['source'],'pos_csv');self.assertEqual(row['import_batch_id'],staged['batch_id']);self.assertTrue(row['source_file_hash'])
        with self.assertRaises(InputError):self.commit(staged,validated)
        with self.auth.db() as db:self.assertIsNone(db.execute('SELECT source_json FROM pos_import_runs WHERE batch_id=?',(staged['batch_id'],)).fetchone()[0])
    def test_different_schemas_and_explicit_ambiguous_monetary_mapping(self):
        files=[csv_file(),csv_file(name='different.csv',headers=['Sale Date','Amount','Currency','Transaction Type','Tender Type','Status','Receipt No.'],rows=[['2026-10-02','75','IDR','sale','wallet','paid','DIFFERENT']])]
        stage=self.stage(files);maps=mapping(stage);second=stage['files'][1];self.assertNotIn('net_amount',second['suggestions'])
        maps[second['file_id']]['columns']['net_amount']='Amount'
        blocked=self.pos.validate(self.owner,self.mid,stage['batch_id'],maps);self.assertFalse(blocked['valid'])
        maps[second['file_id']]['review']['amount_confirmed']=True
        result=self.pos.validate(self.owner,self.mid,stage['batch_id'],maps);self.assertTrue(result['valid']);self.assertEqual(result['metrics']['eligible_total'],'225.00')
    def test_exact_duplicates_within_across_and_against_committed(self):
        file=csv_file();stage,result=self.validated([file,{**file,'filename':'same-again.csv'}]);self.assertEqual(result['metrics']['duplicate_rows'],2)
        self.assertEqual(result['metrics']['parsed_rows'],result['metrics']['eligible_rows']+result['metrics']['duplicate_rows']+result['metrics']['invalid_rows'])
        self.commit(stage,result);again,v=self.validated([file]);self.assertEqual(v['metrics']['eligible_rows'],0);self.commit(again,v)
        self.assertEqual(self.pos.history(self.owner,self.mid)['total'],2)
    def test_ambiguous_duplicate_and_missing_identifiers_are_not_silently_discarded(self):
        rows=[['2026-10-01','100','IDR','sale','cash','paid','SAME'],['2026-10-01','200','IDR','sale','cash','paid','SAME']]
        s,r=self.validated([csv_file(rows=rows)]);self.assertFalse(r['valid']);self.assertEqual(r['metrics']['ambiguous_duplicates'],1)
        rows=[['2026-10-01','100','IDR','sale','cash','paid',''],['2026-10-01','100','IDR','sale','cash','paid','']]
        s,r=self.validated([csv_file(rows=rows)]);self.assertFalse(r['valid'])
    def test_invalid_row_blocks_entire_batch_and_financial_mismatch(self):
        rows=[['2026-10-01','100','IDR','sale','cash','paid','OK'],['bad-date','abc','IDR','sale','cash','paid','BAD']]
        stage,result=self.validated([csv_file(rows=rows)]);self.assertFalse(result['valid']);self.assertEqual(result['metrics']['invalid_rows'],1)
        self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
        stage,result=self.validated(controls={'count':3,'net_total':'999.00'})
        self.assertFalse(result['valid']);self.assertEqual(result['metrics']['reconciliation_failures'],1)
        with self.assertRaises(InputError):self.commit(stage,result)
    def test_refunds_voids_and_missing_control_totals(self):
        rows=[['2026-10-01','100','IDR','sale','cash','paid','SALE'],['2026-10-01','20','IDR','refund','cash','paid','REF'],['2026-10-01','30','IDR','sale','cash','void','VOID'],['2026-10-01','10','IDR','reversal','cash','pending','REV']]
        stage,result=self.validated([csv_file(rows=rows)],{'count':4,'net_total':'80.00','basis':'completed_net'})
        self.assertTrue(result['valid']);self.assertEqual(result['metrics']['eligible_total'],'80.00');self.assertEqual(result['metrics']['eligible_nominal_total'],'100.00')
        self.commit(stage,result)
        s,r=self.validated();self.assertEqual(r['metrics']['reconciliation'][0]['status'],'not_available')
    def test_mapping_protected_fields_conflicts_summary_and_settlement(self):
        s=self.stage();base=mapping(s);fid=s['files'][0]['file_id']
        for modifications in ({'created_by':'reference'},{'gross_amount':'net_amount'}):
            maps=copy.deepcopy(base);maps[fid]['columns'].update(modifications)
            self.assertFalse(self.pos.validate(self.owner,self.mid,s['batch_id'],maps)['valid'])
        s=self.stage([csv_file(headers=['date','total sales','sales count'],rows=[['2026-10-01','100','5']])]);self.assertFalse(self.pos.validate(self.owner,self.mid,s['batch_id'],mapping(s))['valid'])
    def test_cancel_expiration_and_cleanup(self):
        s=self.stage();self.pos.cancel(self.owner,self.mid,s['batch_id']);self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
        with self.auth.db() as db:self.assertIsNone(db.execute('SELECT source_json FROM pos_import_runs WHERE batch_id=?',(s['batch_id'],)).fetchone()[0])
        s=self.stage();now=self.auth.clock();self.auth.clock=lambda:now+TTL+1
        fresh=self.auth.login('owner',PASSWORD)[0];quality=self.pos.monitoring(fresh,self.mid)
        self.assertTrue(any(a['rule']=='session_expired' for a in quality['alerts']))
    def test_interrupted_commit_recovery_and_restart_durability(self):
        s,r=self.validated()
        with patch.object(self.pos,'_finalize',side_effect=RuntimeError('injected')),self.assertRaises(InputError):self.commit(s,r)
        self.assertEqual(self.pos.history(self.owner,self.mid)['total'],2)
        self.pos.recover();self.assertEqual(self.pos.get_session(self.owner,self.mid,s['batch_id'])['state'],'committed')
        new_c=Copilot();new_store=TransactionStore(new_c,self.store.path);new=POSImportService(self.auth,new_store)
        self.assertEqual(new.history(self.owner,self.mid)['total'],2)
    def test_failure_before_append_does_not_create_partial_financial_records(self):
        s,r=self.validated()
        with patch.object(self.pos.journal,'append_batch',side_effect=OSError('injected')),self.assertRaises(InputError):self.commit(s,r)
        self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
        self.pos.recover();self.assertEqual(self.pos.get_session(self.owner,self.mid,s['batch_id'])['state'],'failed')
    def test_concurrent_imports_do_not_double_count_and_revalidate(self):
        one,v1=self.validated();two,v2=self.validated()
        self.commit(one,v1);result=self.commit(two,v2);self.assertFalse(result['ok'])
        v2=self.pos.validate(self.owner,self.mid,two['batch_id'],mapping(two));self.assertEqual(v2['metrics']['duplicate_rows'],2)
        self.commit(two,v2);self.assertEqual(self.pos.history(self.owner,self.mid)['total'],2)
    def test_modified_source_dataset_and_mapping_fail_integrity(self):
        s,r=self.validated()
        with self.auth.db() as db:
            dataset=json.loads(db.execute('SELECT dataset_json FROM pos_import_runs WHERE batch_id=?',(s['batch_id'],)).fetchone()[0]);dataset[0]['amount']='900.00'
            db.execute('UPDATE pos_import_runs SET dataset_json=? WHERE batch_id=?',(json.dumps(dataset),s['batch_id']))
        result=self.commit(s,r);self.assertFalse(result['valid']);self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
        self.assertTrue(any(a['severity']=='critical' for a in self.pos.monitoring(self.owner,self.mid)['alerts']))
    def test_permissions_session_binding_and_scoped_grant_revocation(self):
        for role in ('user_admin','security_admin','lender_analyst'):
            with self.assertRaises(AccessDenied):self.pos.stage(self.tokens[role],self.mid,[csv_file()])
        with self.assertRaises(AccessDenied):self.pos.stage(self.tokens['staff'],self.mid,[csv_file()])
        self.auth.update_user(self.tokens['security_admin'],self.ids['staff'],{'transaction_grants':{self.mid:['create_transactions','bulk_import']}})
        staff=self.auth.login('staff',PASSWORD)[0];run=self.pos.stage(staff,self.mid,[csv_file()])
        with self.assertRaises(AccessDenied):self.pos.get_session(self.owner,self.mid,run['batch_id'])
        with self.assertRaises(AccessDenied):self.pos.stage(self.owner,'M001',[csv_file()])
        self.auth.update_user(self.tokens['security_admin'],self.ids['staff'],{'transaction_grants':{self.mid:[]},'optional_permissions':[]})
        with self.assertRaises(AccessDenied):self.pos.validate(staff,self.mid,run['batch_id'],mapping(run))
    def test_new_staff_read_only_and_authorized_history_monitoring(self):
        body={'username':'readonly','email':'readonly@example.test','display_name':'Read only','role':'staff','merchants':[self.mid],'transaction_grants':{self.mid:['view_quality_monitoring','view_transactions']}}
        with self.auth.db() as db:self.auth._create(db,self.auth.principal(self.tokens['security_admin']),body,PASSWORD,False)
        token=self.auth.login('readonly',PASSWORD)[0];self.pos.monitoring(token,self.mid);self.pos.history(token,self.mid)
        with self.assertRaises(AccessDenied):self.pos.single(token,self.mid,self.entry(),'readonly-key')
        with self.assertRaises(AccessDenied):self.pos.stage(token,self.mid,[csv_file()])
    def test_alert_rates_deduplication_lifecycle_and_audit_history(self):
        s,r=self.validated([csv_file(),csv_file(name='again.csv')]);quality=self.pos.monitoring(self.owner,self.mid)
        self.assertEqual(quality['summary']['duplicate_rate'],.5);self.assertEqual(quality['summary']['valid_row_rate'],1)
        count=len(quality['alerts']);self.pos.validate(self.owner,self.mid,s['batch_id'],mapping(s));self.assertEqual(len(self.pos.monitoring(self.owner,self.mid)['alerts']),count)
        aid=quality['alerts'][0]['alert_id']
        with self.assertRaises(AccessDenied):self.pos.alert_action(self.tokens['staff'],self.mid,aid,'acknowledged','Reviewed report')
        with self.assertRaises(InputError):self.pos.alert_action(self.owner,self.mid,aid,'resolved','Reviewed report')
        self.pos.alert_action(self.owner,self.mid,aid,'acknowledged','Reviewed original source report')
        self.pos.alert_action(self.owner,self.mid,aid,'resolved','Confirmed exact duplicate exclusions against source receipts')
        self.assertEqual(len(self.pos.run_details(self.owner,self.mid,s['batch_id'])['alert_events']),2)
        self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
    def test_monitoring_isolation_filters_history_pagination_and_storage_corruption(self):
        s,r=self.validated();self.commit(s,r)
        self.assertEqual(self.pos.history(self.owner,self.mid,{'payment_method':'cash','limit':1})['total'],1)
        self.assertEqual(self.pos.monitoring(self.owner,self.mid)['summary']['successful_imports'],1)
        with self.assertRaises(AccessDenied):self.pos.monitoring(self.owner,'M001')
        Path(self.store.path).write_text('corrupt\n',encoding='utf-8')
        with self.assertRaises(LedgerError):self.pos.history(self.owner,self.mid)
        self.assertTrue(any(a['severity']=='critical' for a in self.pos.monitoring(self.owner,self.mid)['alerts']))

    def test_actual_concurrent_commits_are_serialized(self):
        one,v1=self.validated();two,v2=self.validated();barrier=threading.Barrier(2)
        def run(pair):
            barrier.wait();return self.commit(*pair)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[(one,v1),(two,v2)]))
        self.assertEqual(sum(bool(r.get('ok')) for r in results),1);self.assertEqual(self.pos.history(self.owner,self.mid)['total'],2)

    def test_source_and_mapping_tampering_and_new_session_are_rejected(self):
        stage=self.stage();bid=stage['batch_id']
        with self.auth.db() as db:
            source=json.loads(db.execute('SELECT source_json FROM pos_import_runs WHERE batch_id=?',(bid,)).fetchone()[0]);source[0]['rows'][0]['values']['net_amount']='999'
            db.execute('UPDATE pos_import_runs SET source_json=? WHERE batch_id=?',(json.dumps(source),bid))
        self.assertFalse(self.pos.validate(self.owner,self.mid,bid,mapping(stage))['valid'])
        stage,v=self.validated()
        with self.auth.db() as db:db.execute('UPDATE pos_import_runs SET validation_version=99 WHERE batch_id=?',(stage['batch_id'],))
        self.assertFalse(self.commit(stage,v)['valid'])
        fresh=self.auth.login('owner',PASSWORD)[0]
        with self.assertRaises(AccessDenied):self.pos.get_session(fresh,self.mid,stage['batch_id'])

    def test_cross_merchant_source_and_permission_denials_generate_audit(self):
        file=csv_file(headers=['date','net_amount','currency','type','channel','status','reference','merchant_id'],rows=[['2026-10-01','100','IDR','sale','cash','paid','OTHER','M001']])
        with self.assertRaises(AccessDenied):self.stage([file])
        quality=self.pos.monitoring(self.owner,self.mid)
        self.assertTrue(any(a['severity']=='critical' for a in quality['alerts']))
        events=self.auth.audit_records(self.tokens['security_admin'],{'action':'pos_extract_failed'})
        self.assertTrue(any(e['result']=='denied' for e in events))

    def test_high_value_and_date_gap_alerts_use_actual_history(self):
        for i in range(5):self.pos.single(self.owner,self.mid,self.entry(external_reference='BASE-'+str(i),transaction_date='2026-09-01'),'baseline-key-'+str(i))
        file=csv_file(rows=[['2026-10-01','5000','IDR','sale','cash','paid','LARGE'],['2026-10-10','10','IDR','sale','cash','paid','GAP']])
        self.validated([file]);rules={a['rule'] for a in self.pos.monitoring(self.owner,self.mid)['alerts']}
        self.assertTrue({'unusual_amount','date_gap'}<=rules)

    def test_declared_gross_net_controls_are_not_compared_to_settlement(self):
        file=csv_file(headers=['date','gross_amount','net_amount','discount','tax','settlement_amount','currency','type','channel','status','reference'],rows=[['2026-10-01','100','102','10','12','95','IDR','sale','cash','paid','GROSS']])
        s,r=self.validated([file],{'count':1,'gross_total':'100','net_total':'102'});self.assertTrue(r['valid'])
        maps=mapping(s);maps[s['files'][0]['file_id']]['columns'].pop('settlement_amount');maps[s['files'][0]['file_id']]['columns']['net_amount']='settlement_amount'
        self.assertFalse(self.pos.validate(self.owner,self.mid,s['batch_id'],maps)['valid'])

    def test_manual_missing_reference_and_staged_session_expiry_fail_closed(self):
        with self.assertRaises(InputError):self.pos.single(self.owner,self.mid,self.entry(external_reference=''),'missing-reference')
        with self.assertRaises(InputError):self.pos.single(self.owner,self.mid,self.entry(external_reference='  '),'whitespace-reference')
        s,v=self.validated();self.auth.logout(self.owner)
        with self.assertRaises(AccessDenied):self.commit(s,v)

    def test_legacy_text_compatibility_does_not_reject_existing_financial_records(self):
        principal=self.auth.principal(self.owner)
        self.store.save(principal,self.mid,[{'date':'2026-09-29','type':'income','amount':5,'channel':'cash','reference':'LEGACY-COMPAT','category':'legacy@example.test','description':'+historical note'}])
        row=self.pos.history(self.owner,self.mid)['transactions'][0]
        self.assertEqual(row['amount'],'5.00');self.assertEqual(row['category'],'[EMAIL]')

class POSHTTP(POSFixture):
    req=http_support.AuthenticatedHTTP.req
    def setUp(self):
        super().setUp();attach_server(self)
        from copilot.server import Handler
        self.srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=self.srv.serve_forever,daemon=True).start()
        self.addCleanup(self.srv.server_close);self.addCleanup(self.srv.shutdown)
    def test_direct_routes_permissions_csrf_and_staging_endpoints(self):
        self.assertEqual(self.req('/merchant-transactions/single?merchant=M002','owner')[0],200)
        self.assertEqual(self.req('/merchant-transactions/import?merchant=M002','staff')[0],403)
        self.assertEqual(self.req('/merchant-transactions/data-quality?merchant=M002','staff')[0],200)
        self.assertEqual(self.req('/merchant-transactions/history?merchant=M002','security_admin')[0],403)
        self.assertEqual(self.req('/api/pos-import/stage','owner',{'merchant':self.mid,'files':[csv_file()]},csrf=False)[0],403)
        status,run,_=self.req('/api/pos-import/stage','owner',{'merchant':self.mid,'files':[csv_file()]});self.assertEqual(status,201)
        status,v,_=self.req('/api/pos-import/'+run['batch_id']+'/validate','owner',{'merchant':self.mid,'mappings':mapping(run)});self.assertEqual(status,200)
        status,result,_=self.req('/api/pos-import/'+run['batch_id']+'/commit','owner',{'merchant':self.mid,'preview_token':v['preview_token'],'confirmed':True});self.assertEqual(status,200);self.assertEqual(result['imported_rows'],2)
    def test_no_demo_role_or_mass_assignment_bypass(self):
        self.assertEqual(self.req('/api/data-quality?merchant=M002',extra={'X-Demo-Role':'owner'})[0],401)
        self.assertEqual(self.req('/api/merchant-transactions/entry','owner',{'merchant':self.mid,'entry':self.entry(created_by='admin'),'idempotency_key':'protected-key'})[0],400)
