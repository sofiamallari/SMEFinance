import io
import tempfile
import unittest
import zipfile
import json
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
from copilot.agent import Copilot
from copilot.modules.transactions import TransactionStore, validate_entry, parse_upload
from copilot.security import Principal, AccessDenied
from copilot.tools_spec import execute

class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = Copilot()
        self.path = str(Path(self.tmp.name)/'ledger.jsonl')
        self.store = TransactionStore(self.c,self.path)
        self.owner = Principal('o','owner',{'M002'})
        self.staff = Principal('s','staff',{'M002'})
        self.row = dict(date='2026-09-29',type='income',amount='123.45',channel='qr_pay',reference='SALE-1',description='Sale',category='sales')

    def test_validation(self):
        self.assertEqual(validate_entry(self.row,self.c.as_of)['amount'],123.45)
        for change in [dict(amount='NaN'),dict(amount=-1),dict(amount='1.001'),dict(date='2027-01-01'),dict(type='other'),dict(channel='invalid'),dict(description='x'*251)]:
            with self.subTest(change=change), self.assertRaises(ValueError): validate_entry({**self.row,**change},self.c.as_of)

    def test_preview_confirmation_and_replay(self):
        p = self.store.preview(self.staff,'M002',{'rows':[self.row]})
        self.assertFalse(Path(self.path).exists())
        with self.assertRaises(ValueError): self.store.confirm(self.staff,'M002',p['preview_token'],False)
        with self.assertRaises(ValueError): self.store.confirm(self.owner,'M002',p['preview_token'],True)
        self.assertTrue(self.store.confirm(self.staff,'M002',p['preview_token'],True)['valid'])
        with self.assertRaises(ValueError): self.store.confirm(self.staff,'M002',p['preview_token'],True)
        new = Copilot(); TransactionStore(new,self.path)
        self.assertEqual(new.merchants['M002'].transactions[-1]['description'],'Sale')

    def test_duplicates_atomic_errors(self):
        self.assertFalse(self.store.save(self.owner,'M002',[self.row,self.row])['valid'])
        self.assertFalse(Path(self.path).exists())
        self.store.save(self.owner,'M002',[self.row])
        self.assertFalse(self.store.preview(self.owner,'M002',{'rows':[self.row]})['valid'])

    def test_permissions(self):
        for role in ['lender_analyst','coach','demo_guest']:
            with self.assertRaises(AccessDenied): self.store.preview(Principal('x',role,{'M002'}),'M002',{'rows':[self.row]})
        with self.assertRaises(AccessDenied): self.store.save(self.owner,'M001',[self.row])
        with self.assertRaises(AccessDenied): self.store.manage(self.staff,'M002',{})
        lender = Principal('l','lender_analyst',{'M002'},{'share_with_lender'})
        with self.assertRaises(AccessDenied): execute(self.c,lender,'get_dashboard',{'merchant_id':'M002'})
        self.assertIn('net_income',execute(self.c,lender,'financial_report',{'merchant_id':'M002'}))
        with self.assertRaises(AccessDenied): execute(self.c,Principal('l','lender_analyst',{'M002'}),'financial_report',{'merchant_id':'M002'})

    def test_dashboard_edit_delete(self):
        before=self.c.call(self.owner,'get_dashboard','M002')
        self.store.save(self.owner,'M002',[self.row,{**self.row,'type':'expense','amount':23.45,'reference':'EXP-1'}])
        after=self.c.call(self.owner,'get_dashboard','M002')
        self.assertAlmostEqual(after['mix']['gross_revenue']-before['mix']['gross_revenue'],123.45)
        self.assertAlmostEqual(after['expenses']-before['expenses'],23.45)
        self.assertEqual(after['mix']['total_transactions'],before['mix']['total_transactions']+1)
        tid=next(iter(self.store.entries))
        self.store.manage(self.owner,'M002',{'action':'update','id':tid,'entry':{**self.row,'amount':200}})
        self.store.manage(self.owner,'M002',{'action':'delete','id':tid})
        new=Copilot(); reloaded=TransactionStore(new,self.path)
        self.assertEqual(len(reloaded.entries),1)

    def test_csv_structure(self):
        self.assertEqual(len(parse_upload('x.csv',b'date,type,amount\n2026-09-29,income,1\n')),1)
        for content in [b'date,type\nx,y',b'date,type,amount,amount\nx,y,1,2',b'date,type,amount\nx,y,1,2']:
            with self.assertRaises(ValueError): parse_upload('x.csv',content)

    def test_xlsx(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1" t="inlineStr"><is><t>date</t></is></c><c r="B1" t="inlineStr"><is><t>type</t></is></c><c r="C1" t="inlineStr"><is><t>amount</t></is></c></row><row><c r="A2" t="inlineStr"><is><t>2026-09-29</t></is></c><c r="B2" t="inlineStr"><is><t>income</t></is></c><c r="C2"><v>100</v></c></row></sheetData></worksheet>')
        rows=parse_upload('x.xlsx',out.getvalue())
        self.assertEqual(validate_entry(rows[0],self.c.as_of)['amount'],100)

    def test_report_saved_upload(self):
        before=execute(self.c,self.owner,'financial_report',{'merchant_id':'M002'})
        p=self.store.preview(self.owner,'M002',{'rows':[self.row]});self.store.confirm(self.owner,'M002',p['preview_token'],True)
        after=execute(self.c,self.owner,'financial_report',{'merchant_id':'M002'})
        self.assertAlmostEqual(after['revenue_projection_30_days']-before['revenue_projection_30_days'],123.45)
        self.assertEqual(self.c.handle(self.owner,'M002','Analyze uploaded transactions')['intent'],'report')

class TransactionHTTP(unittest.TestCase):
    def test_upload_and_dashboard_over_http(self):
        from copilot import server
        with tempfile.TemporaryDirectory() as tmp:
            old_c, old_store = server.COPILOT, server.STORE
            server.COPILOT = Copilot()
            server.STORE = TransactionStore(server.COPILOT,str(Path(tmp)/'ledger.jsonl'))
            srv = ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
            threading.Thread(target=srv.serve_forever,daemon=True).start()
            def request(path,body=None,role='owner'):
                req=urllib.request.Request(f'http://127.0.0.1:{srv.server_port}'+path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type':'application/json','X-Demo-Role':role,'X-Demo-Consent':'yes'})
                try:
                    with urllib.request.urlopen(req) as r:return r.status,json.load(r)
                except urllib.error.HTTPError as e:
                    with e:return e.code,json.load(e)
            try:
                before=request('/api/dashboard?merchant=M002')[1]
                rows=[dict(date='2026-09-29',type='income',amount=100,channel='cash',reference='HTTP-1')]
                status,p=request('/api/transactions/preview',{'merchant':'M002','rows':rows},'staff')
                self.assertEqual(status,200)
                self.assertEqual(request('/api/transactions?merchant=M002')[1]['transactions'],[])
                self.assertEqual(request('/api/transactions/import',{'merchant':'M002','rows':rows})[0],400)
                self.assertEqual(request('/api/transactions/entry',{'merchant':'M002','entry':rows[0]},'lender_analyst')[0],403)
                self.assertEqual(request('/api/transactions/import',{'merchant':'M002','preview_token':p['preview_token'],'confirmed':True},'staff')[1]['imported'],1)
                after=request('/api/dashboard?merchant=M002')[1]
                self.assertAlmostEqual(after['mix']['gross_revenue']-before['mix']['gross_revenue'],100)
                self.assertFalse(request('/api/transactions/preview',{'merchant':'M002','rows':rows})[1]['valid'])
            finally:
                srv.shutdown();srv.server_close()
                server.COPILOT,server.STORE=old_c,old_store
