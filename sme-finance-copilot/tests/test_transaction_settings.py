import copy,json,unittest
from types import SimpleNamespace
from copilot.auth import InputError,AuthError
from copilot.security import AccessDenied
from copilot.currency_catalog import search,catalog
from copilot.canonical_transactions import normalize,suggest,timestamp
from copilot.transaction_settings import restore_currency_configuration
from tests.test_pos_import import POSFixture,POSHTTP
from tests.pos_fixtures import csv_file,mapping

class Settings(POSFixture):
 def cfg(self):return self.pos.settings.get(self.owner,self.mid)
 def save(self,**values):return self.pos.settings.save(self.owner,self.mid,{'expected_version':self.cfg()['version'],'confirmed':True,**values})
 def test_owner_persistence_version_and_audit(self):
  before=self.cfg();self.assertEqual(before['timezone'],'Asia/Jakarta');self.assertTrue(before['currency_locked'])
  after=self.save(timezone='Asia/Shanghai',display_date_format='DD/MM/YYYY',payment_method_values={'Tap-to-Pay':'tap_pay'})
  self.assertEqual(after['version'],1);self.assertEqual(self.pos.settings.get(self.owner,self.mid)['payment_method_values'],{'Tap-to-Pay':'tap_pay'})
  with self.auth.db() as db:self.assertEqual(sum(json.loads(r[0]).get('action')=='transaction_settings_updated' and json.loads(r[0]).get('merchant_id')==self.mid for r in db.execute('SELECT record FROM audit_events')),1)
  with self.assertRaises(InputError):self.pos.settings.save(self.owner,self.mid,{'expected_version':0,'confirmed':True})
 def test_authorization_each_role_and_merchant_isolation(self):
  for role in ('staff','lender_analyst','security_admin','user_admin'):
   with self.subTest(role=role),self.assertRaises((AccessDenied,AuthError)):self.pos.settings.save(self.tokens[role],self.mid,{'expected_version':0,'confirmed':True})
  self.assertFalse(self.pos.settings.get(self.tokens['staff'],self.mid)['can_edit'])
  for role in ('lender_analyst','security_admin','user_admin'):
   with self.assertRaises((AccessDenied,AuthError)):self.pos.settings.get(self.tokens[role],self.mid,True)
  with self.assertRaises(AccessDenied):self.pos.settings.get(self.owner,'M003')
  with self.auth.db() as db:db.execute('INSERT INTO memberships VALUES (?,?)',(self.ids['owner'],'M003'))
  original=self.pos.settings.get(self.owner,'M003');self.save(timezone='Asia/Tokyo');self.assertEqual(self.pos.settings.get(self.owner,'M003'),original)
 def test_staff_requires_live_delegation_and_membership(self):
  with self.auth.db() as db:db.execute('DELETE FROM merchant_transaction_grants WHERE user_id=?',(self.ids['staff'],))
  with self.assertRaises(AccessDenied):self.pos.settings.get(self.tokens['staff'],self.mid)
 def test_currency_catalog_search_and_separate_eligibility(self):
  self.assertGreater(len(catalog()),100);self.assertIn('PHP',[c['code'] for c in search('philippine')]);self.assertIn('CNY',[c['code'] for c in search('cny')]);self.assertTrue(search('Euro'))
  before=copy.deepcopy(self.c.financial_data.base[self.mid]);
  with self.assertRaises(InputError):self.save(base_currency='CNY')
  with self.assertRaises(InputError):self.save(base_currency='USD')
  self.assertEqual(self.c.financial_data.base[self.mid],before);self.assertEqual(self.cfg()['base_currency'],'IDR')
 def test_empty_merchant_currency_initialization_is_safe_and_record_locks(self):
  for merchant in (self.c.merchants[self.mid],self.c.financial_data.base[self.mid]):
   for k in ('transactions','expenses','receivables','payables'):setattr(merchant,k,[])
   for k in ('wallet_balance','monthly_debt_service','confirmed_orders_value','prior_loans'):setattr(merchant,k,0)
  self.assertFalse(self.cfg()['currency_locked']);self.save(base_currency='CNY');self.assertEqual(self.c.financial_data.base[self.mid].currency,'CNY')
  self.pos.single(self.owner,self.mid,self.entry(currency='CNY'),'currency-init-key')
  with self.assertRaises(InputError):self.save(base_currency='IDR')
  restore_currency_configuration(self.c,self.auth);self.assertEqual(self.c.financial_data.aggregate(self.mid)['currency'],'CNY')
 def test_confirmation_and_invalid_configuration(self):
  for changes in ({'timezone':'Wrong/Zone'},{'display_date_format':'day_first'},{'default_status':'approved-loan'},{'payment_method_values':{'Unknown':'cash-like'}},{'base_currency':['IDR']},{'timezone':None}):
   with self.subTest(changes=changes),self.assertRaises(InputError):self.save(**changes)
  with self.assertRaises(InputError):self.pos.settings.save(self.owner,self.mid,{'expected_version':0})
 def test_single_iana_timezone_and_preserved_historical_business_date(self):
  self.save(timezone='America/New_York',display_date_format='MM/DD/YYYY')
  self.pos.single(self.owner,self.mid,self.entry(transaction_date='2026-10-01T23:30:00'),'zone-single-key')
  row=self.pos.history(self.owner,self.mid)['transactions'][0];self.assertEqual(row['transaction_date'],'2026-10-02T03:30:00Z');self.assertEqual(row['business_date'],'2026-10-01')
  self.save(timezone='Asia/Shanghai');self.assertEqual(self.pos.history(self.owner,self.mid)['transactions'][0]['business_date'],'2026-10-01')
 def test_dst_ambiguity_and_nonexistent_time_rejected(self):
  for value in ('2026-03-08T02:30:00','2025-11-02T01:30:00'):
   with self.assertRaises(InputError):timestamp(value,'America/New_York','iso',self.auth.clock())
  self.assertEqual(timestamp('2025-11-02T01:30:00-04:00','America/New_York','iso',self.auth.clock()),'2025-11-02T05:30:00Z')
 def test_import_uses_timezone_default_and_no_fabricated_payment(self):
  self.save(timezone='Asia/Shanghai',payment_method_values={'Tap-to-Pay':'tap_pay'})
  st=self.stage();maps=mapping(st)
  for m in maps.values():m.pop('timezone')
  r=self.pos.validate(self.owner,self.mid,st['batch_id'],maps);self.assertTrue(r['valid']);self.commit(st,r)
  self.assertTrue(all(x['source_timezone']=='Asia/Shanghai' for x in self.pos.history(self.owner,self.mid)['transactions']))
  with self.assertRaises(InputError):normalize(self.entry(payment_method='unknown'),self.c.merchants[self.mid],{},self.auth.clock())
 def test_mapping_aliases_and_financial_ambiguity(self):
  result=suggest(['Expense Date','Net Amount (¥)','Expense ID','Expense Category','Details','Payment Type']);self.assertEqual(result['transaction_date'],'Expense Date');self.assertEqual(result['net_amount'],'Net Amount (¥)');self.assertEqual(result['external_reference'],'Expense ID')
  self.assertNotIn('net_amount',suggest(['Gross Amount','Amount']))
  st=self.stage();maps=mapping(st);m=next(iter(maps.values()));m['columns'].pop('transaction_type');m['review']={}
  self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],maps)['valid']);m['review']['type_confirmed']=True;self.assertTrue(self.pos.validate(self.owner,self.mid,st['batch_id'],maps)['valid'])
 def test_fee_source_never_auto_combines_gross_with_net(self):
  hints=suggest(['Transaction Date','Net Amount (\u00a5)','Gross Amount (\u00a5)','Processing Fee (\u00a5)','Tax'])
  self.assertEqual(hints['net_amount'],'Net Amount (\u00a5)');self.assertNotIn('gross_amount',hints);self.assertNotIn('tax',hints)
  # The canonical gross/net accounting check remains strict when explicitly mapped.
  with self.assertRaises(InputError):normalize(self.entry(net_amount='98',gross_amount='100'),self.c.merchants[self.mid],{},self.auth.clock())
 def test_ambiguous_currency_symbol_confirmation_and_explicit_conflict(self):
  st=self.stage([csv_file(headers=['date','Net Amount (¥)','currency','type','channel','status','reference'])]);maps=mapping(st)
  # Currency-column values supply explicit evidence in source row samples.
  f=st['files'][0];self.assertIn('¥',f['ambiguous_currency_symbols'])
  # With explicit IDR column the declarations are still normalized per row.
  for m in maps.values():m['review']['currency_confirmed']=True
  self.assertTrue(self.pos.validate(self.owner,self.mid,st['batch_id'],maps)['valid'])
  st=self.stage([csv_file(headers=['date','Net Amount (CNY)','currency','type','channel','status','reference'])]);self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],mapping(st))['valid'])
 def test_validated_templates_scoped_versioned_no_control_reuse(self):
  st,r=self.validated();self.assertTrue(r['valid']);file=st['files'][0]
  body={'name':'Confirmed sales','batch_id':st['batch_id'],'file_id':file['file_id'],'confirmed':True}
  first=self.pos.settings.save_template(self.owner,self.mid,body);second=self.pos.settings.save_template(self.owner,self.mid,{**body,'template_id':first['template_id'],'expected_version':1});self.assertEqual(second['version'],2)
  t=self.pos.settings.templates(self.owner,self.mid)[0];self.assertNotIn('control_totals',t['mapping']);self.assertEqual(t['version'],2)
  for role in ('staff','lender_analyst','security_admin'):
   with self.assertRaises(AccessDenied):self.pos.settings.save_template(self.tokens[role],self.mid,body)
  self.assertEqual(len(self.pos.settings.templates(self.tokens['staff'],self.mid)),1)
  maps=mapping(st);m=maps[file['file_id']];m['template']={'id':first['template_id'],'version':2};self.assertTrue(self.pos.validate(self.owner,self.mid,st['batch_id'],maps)['valid'])
  m['columns'].pop('transaction_type');m['defaults']['transaction_type']='expense';self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],maps)['valid'])
 def test_template_cannot_be_created_from_invalid_or_other_batch(self):
  st=self.stage();body={'name':'Unverified','batch_id':st['batch_id'],'file_id':st['files'][0]['file_id'],'confirmed':True}
  with self.assertRaises(InputError):self.pos.settings.save_template(self.owner,self.mid,body)

class SettingsHTTP(POSHTTP):
 def test_settings_routes_csrf_catalog_and_role_denials(self):
  self.assertEqual(self.req('/merchant-transactions/settings?merchant=M002','owner')[0],200)
  for role in ('staff','lender_analyst','security_admin'):self.assertEqual(self.req('/merchant-transactions/settings?merchant=M002',role)[0],403)
  status,r,_=self.req('/api/merchant-transactions/settings?merchant=M002&catalog=1','owner');self.assertEqual(status,200);self.assertGreater(len(r['currencies']),100)
  self.assertEqual(self.req('/api/transaction-currencies?merchant=M002&search=philippine','owner')[1]['currencies'][0]['code'],'PHP')
  for role in ('lender_analyst','security_admin'):self.assertEqual(self.req('/api/transaction-currencies?merchant=M002',role)[0],403)
  self.assertEqual(self.req('/api/merchant-transactions/settings','owner',{'merchant':self.mid,'settings':{'expected_version':0,'confirmed':True}},method='PATCH',csrf=False)[0],403)
