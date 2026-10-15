import unittest
from copilot.report_profiles import report_profile
from copilot.canonical_transactions import suggest
from tests.test_pos_import import POSFixture
from tests.pos_fixtures import mapping,csv_file

class Suggestions(unittest.TestCase):
 def test_revenue_columns_without_name(self):
  headers=['Transaction ID','Transaction Date','Payment Method','Gross Amount (CNY)','Processing Fee (CNY)','Net Amount (CNY)']
  self.assertEqual(report_profile(headers,{})['kind'],'revenue')
  hints=suggest(headers);self.assertEqual(hints['net_amount'],'Net Amount (CNY)');self.assertNotIn('gross_amount',hints)
 def test_expense_columns_without_name(self):
  headers=['Expense ID','Expense Date','Category','Subcategory','Description / Vendor','Amount (CNY)']
  self.assertEqual(report_profile(headers,{})['kind'],'expense')
  hints=suggest(headers);self.assertNotIn('transaction_type',hints);self.assertNotIn('payment_method',hints);self.assertEqual(hints['description'],'Description / Vendor');self.assertNotIn('subcategory',hints)
 def test_generic_headers_require_review(self):
  self.assertIsNone(report_profile(['date','amount','reference'],{})['kind'])
 def test_explicit_source_types(self):
  self.assertEqual(report_profile(['date','type','net_amount'],{'type':['expense']})['kind'],'expense')
  self.assertEqual(report_profile(['date','type','net_amount'],{'type':['sale','refund','reversal']})['kind'],'revenue')
 def test_mixed_source_types_are_not_auto_classified(self):
  self.assertTrue(report_profile(['date','type','net_amount'],{'type':['expense','sale']})['ambiguous'])
 def test_nonstandard_but_supported_headers(self):
  self.assertEqual(report_profile(['Timestamp','Transaction Type','Total Paid','Receipt Number'],{'Transaction Type':['income']})['kind'],'revenue')

class ProfileValidation(POSFixture):
 def maps(self):
  st=self.stage();m=mapping(st);item=next(iter(m.values()));item['profile']={'kind':'revenue','confirmed':True};return st,m,item
 def test_confirmed_profile_preserves_source_types_and_totals(self):
  st,m,item=self.maps();r=self.pos.validate(self.owner,self.mid,st['batch_id'],m);self.assertTrue(r['valid']);self.assertEqual(r['metrics']['eligible_total'],'150.00')
 def test_unconfirmed_invalid_profile_blocks(self):
  st,m,item=self.maps()
  for profile in ({'kind':'revenue','confirmed':False},{'kind':'anything','confirmed':True},{'kind':'expense','confirmed':'true'},[]):
   item['profile']=profile
   self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
 def test_expense_profile_cannot_silently_use_sale_default(self):
  st,m,item=self.maps();item['profile']['kind']='expense';item['columns'].pop('transaction_type');item['defaults']['transaction_type']='sale'
  self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
  item['defaults']['transaction_type']='expense';r=self.pos.validate(self.owner,self.mid,st['batch_id'],m);self.assertTrue(r['valid']);self.assertEqual(r['metrics']['eligible_total'],'-150.00')
 def test_missing_payment_method_remains_blocked(self):
  st,m,item=self.maps();item['columns'].pop('payment_method');self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
  item['defaults']['payment_method']='cash';self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
  item['review']['payment_method_confirmed']=True;self.assertTrue(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
 def test_generic_amount_still_requires_financial_confirmation(self):
  st=self.stage([csv_file(headers=['date','Amount','currency','type','channel','status','reference'])]);m=mapping(st);item=next(iter(m.values()));item['profile']={'kind':'revenue','confirmed':True};item['columns']['net_amount']='Amount'
  self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid']);item['review']['amount_confirmed']=True;self.assertTrue(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
 def test_legacy_mapping_without_profile_is_preserved(self):
  st,r=self.validated();self.assertTrue(r['valid']);self.assertEqual(self.commit(st,r)['imported_rows'],2)

 def test_malformed_profile_mapping_values_fail_without_crashing(self):
  st,m,item=self.maps()
  for key in ('columns','defaults'):
   original=item[key]
   for value in (None,[],False):
    item[key]=value
    self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
   item[key]=original

 def test_profile_cannot_be_applied_to_conflicting_source_types(self):
  st,m,item=self.maps();item['profile']['kind']='expense'
  self.assertFalse(self.pos.validate(self.owner,self.mid,st['batch_id'],m)['valid'])
  st=self.stage([csv_file(rows=[['2026-10-01','40','IDR','expense','cash','completed','EXP-PROFILE']])]);m=mapping(st);item=next(iter(m.values()));item['profile']={'kind':'revenue','confirmed':True}
  result=self.pos.validate(self.owner,self.mid,st['batch_id'],m);self.assertFalse(result['valid']);self.assertEqual(result['metrics']['eligible_rows'],0)
