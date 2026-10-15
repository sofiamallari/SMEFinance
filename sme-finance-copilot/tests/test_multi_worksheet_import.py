import base64,io,os,zipfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from tests.test_pos_import import POSFixture
from tests.pos_fixtures import xlsx_bytes,mapping,csv_file
from copilot.auth import InputError,AuthError
from copilot.security import AccessDenied
from copilot.pos_extract import extract_files,MAX_ROWS

BAO=Path(os.environ.get('COPILOT_BAO_WORKBOOK',str(Path(__file__).resolve().parents[1]/'examples/Initial Test Data - Bao Burgers Business.xlsx')))
def workbook():
 base=xlsx_bytes();z=zipfile.ZipFile(io.BytesIO(base));out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dest:
  for name in z.namelist():
   data=z.read(name)
   if name=='xl/workbook.xml':data=data.replace(b'</sheets>',b'<sheet name="Expenses" sheetId="2" r:id="rId2"/></sheets>')
   if name=='xl/_rels/workbook.xml.rels':data=data.replace(b'</Relationships>',b'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
   dest.writestr(name,data)
  data=z.read('xl/worksheets/sheet1.xml').replace(b'XLSX-1',b'EXP-1')
  dest.writestr('xl/worksheets/sheet2.xml',data)
 return {'filename':'multi.xlsx','content':base64.b64encode(out.getvalue()).decode(),'worksheets':[{'name':'POS Sales','header_row':1},{'name':'Expenses','header_row':1}]}

class MultiWorksheet(POSFixture):
 def test_discovery_requires_selection_and_independent_source_identity(self):
  f=workbook();d=self.pos.inspect_files(self.owner,self.mid,[{k:v for k,v in f.items() if k!='worksheets'}]);self.assertEqual([s['name'] for s in d['files'][0]['worksheets']],['POS Sales','Expenses'])
  with self.assertRaises(InputError):self.stage([{k:v for k,v in f.items() if k!='worksheets'}])
  f['worksheets']=[]
  with self.assertRaises(InputError):self.stage([f])
  f=workbook();sources=extract_files([f],self.mid);self.assertNotEqual(sources[0]['sha256'],sources[1]['sha256']);self.assertEqual(sources[0]['workbook_hash'],sources[1]['workbook_hash'])
 def test_combined_atomic_commit_and_duplicate_only_reimport(self):
  f=workbook();st=self.stage([f]);m=mapping(st);m[st['files'][1]['file_id']]['defaults']['transaction_type']='expense';m[st['files'][1]['file_id']]['columns'].pop('transaction_type',None);r=self.pos.validate(self.owner,self.mid,st['batch_id'],m);self.assertTrue(r['valid']);self.assertEqual(r['metrics']['eligible_total'],'0.00');result=self.commit(st,r);self.assertEqual(result['worksheets_processed'],2);self.assertEqual(result['files_processed'],1)
  rows=self.pos.history(self.owner,self.mid)['transactions'];self.assertEqual({x['transaction_type'] for x in rows},{'sale','expense'});self.assertTrue(all(x['source_worksheet'] and x['source_values'] for x in rows))
  st=self.stage([f]);r=self.pos.validate(self.owner,self.mid,st['batch_id'],{st['files'][0]['file_id']:m[ list(m)[0]],st['files'][1]['file_id']:m[list(m)[1]]});self.assertEqual(r['metrics']['duplicate_rows'],2);self.assertEqual(self.commit(st,r)['imported_rows'],0)
 def test_one_invalid_sheet_blocks_entire_batch(self):
  st=self.stage([workbook()]);m=mapping(st);m[st['files'][1]['file_id']]['defaults']['currency']='PHP';m[st['files'][1]['file_id']]['columns'].pop('currency',None);r=self.pos.validate(self.owner,self.mid,st['batch_id'],m);self.assertFalse(r['valid']);self.assertEqual(len(r['metrics']['source_counts']),2)
  with self.assertRaises(InputError):self.commit(st,r)
  self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
 def test_cross_sheet_duplicate_and_authorization(self):
  f=workbook();b=io.BytesIO(base64.b64decode(f['content']));out=io.BytesIO()
  with zipfile.ZipFile(b) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dest:
   for n in src.namelist():dest.writestr(n,src.read(n).replace(b'EXP-1',b'XLSX-1'))
  f['content']=base64.b64encode(out.getvalue()).decode();st,r=self.validated([f]);self.assertEqual(r['metrics']['duplicate_rows'],1)
  for who in ['lender_analyst','security_admin']:
   with self.assertRaises((AccessDenied,AuthError)) as e:self.pos.inspect_files(self.tokens[who],self.mid,[f])
   self.assertIn(getattr(e.exception,'status',403),(403,))
 def test_single_sheet_legacy_source_hash_compatibility(self):
  f={'filename':'single.xlsx','content':base64.b64encode(xlsx_bytes()).decode()};legacy=extract_files([f],self.mid)[0];f['worksheets']=[{'name':'POS Sales','header_row':1}];selected=extract_files([f],self.mid)[0];self.assertEqual(legacy['sha256'],selected['sha256'])
 def test_invalid_selection_ranges_and_formula_transaction_cells(self):
  f=workbook()
  for selections in ('not-a-list',[4],[{'name':{}}],[{'name':'Missing'}],[{'name':'POS Sales','header_row':0}],[{'name':'POS Sales','header_row':1,'last_data_row':1}],[{'name':'POS Sales'},{'name':'POS Sales'}]):
   with self.subTest(selections=selections),self.assertRaises(InputError):extract_files([{**f,'worksheets':selections}],self.mid)
  f={'filename':'formula.xlsx','content':base64.b64encode(xlsx_bytes(formula=True)).decode(),'worksheets':[{'name':'POS Sales','header_row':1}]}
  with self.assertRaises(InputError):extract_files([f],self.mid)
  self.assertEqual(len(self.pos.inspect_files(self.owner,self.mid,[{k:v for k,v in f.items() if k!='worksheets'}])['files'][0]['worksheets']),1)
 def test_cny_is_import_only_and_merchant_bound(self):
  from copilot.canonical_transactions import normalize
  from copilot.config import CURRENCIES
  self.assertNotIn('CNY',CURRENCIES)
  with self.assertRaises(InputError):normalize(self.entry(currency='CNY'),self.c.merchants[self.mid],{},self.auth.clock())
  merchant=self.c.merchants[self.mid];merchant.currency='CNY';merchant.country='CN'
  row=normalize(self.entry(currency='CNY',transaction_date='2026-10-01T00:30:00+08:00'),merchant,{},self.auth.clock())
  self.assertEqual(row['currency'],'CNY');self.assertEqual(row['amount'],'100.00');self.assertEqual(row['business_date'],'2026-10-01')
 def test_bao_full_workbook_currency_headers_and_preserved_components(self):
  if not BAO.exists():self.skipTest('Set COPILOT_BAO_WORKBOOK to run the supplied-workbook acceptance test')
  try:import openpyxl
  except ImportError:self.skipTest('The optional supplied-workbook test requires openpyxl')
  w=openpyxl.load_workbook(BAO,read_only=True,data_only=False);expense=list(w['Expense Report'].values);last=max(i for i,row in enumerate(expense,1) if row and isinstance(row[0],str) and row[0].startswith('EXP-'))
  f={'filename':BAO.name,'content':base64.b64encode(BAO.read_bytes()).decode(),'worksheets':[{'name':'Revenue Report','header_row':5,'last_data_row':5413},{'name':'Expense Report','header_row':5,'last_data_row':last}]}
  st=self.stage([f]);m={}
  for src in st['files']:
   revenue=src['worksheet']=='Revenue Report';headers=src['headers'];m[src['file_id']]={'columns':{'transaction_date':headers[1],'external_reference':headers[0],'net_amount':headers[5]},'defaults':{'currency':'CNY','status':'completed','transaction_type':'sale' if revenue else 'expense','payment_method':'cash'},'timezone':'+08:00','payment_method_values':{'Tap-to-Pay':'tap_pay'}}
   if revenue:m[src['file_id']]['columns']['payment_method']=headers[2]
   else:m[src['file_id']]['columns'].update(category=headers[2],description=headers[4])
  wrong_defaults={key:{**value,'defaults':{**value['defaults'],'currency':'IDR'}} for key,value in m.items()};wrong=self.pos.validate(self.owner,self.mid,st['batch_id'],wrong_defaults);self.assertFalse(wrong['valid']);self.assertEqual(self.pos.history(self.owner,self.mid)['total'],0)
  self.c.merchants[self.mid].currency='CNY';self.c.merchants[self.mid].country='CN'
  r=self.pos.validate(self.owner,self.mid,st['batch_id'],m)
  if not r['valid']:self.fail(json.dumps(r['findings'][:5]))
  self.assertEqual(r['metrics']['parsed_rows'],5408+last-5);self.assertEqual(r['metrics']['invalid_rows'],0);self.assertLess(r['metrics']['parsed_rows'],MAX_ROWS)
  result=self.commit(st,r);self.assertEqual(result['imported_rows'],r['metrics']['parsed_rows']);rows=self.pos.history(self.owner,self.mid)['transactions'];self.assertEqual({x['currency'] for x in rows},{'CNY'});self.assertTrue(all(x['source_values'] for x in rows))
  st2=self.stage([f]);m2={s['file_id']:m[st['files'][i]['file_id']] for i,s in enumerate(st2['files'])};r2=self.pos.validate(self.owner,self.mid,st2['batch_id'],m2);self.assertTrue(r2['valid']);self.assertEqual(r2['metrics']['eligible_rows'],0);self.assertEqual(self.commit(st2,r2)['imported_rows'],0)

if __name__=='__main__':unittest.main()
