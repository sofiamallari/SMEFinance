import base64,io,os,unittest,zipfile
from copilot.pos_extract import extract_files
from copilot.worksheet_detection import detect_table
from copilot.auth import InputError
from tests.pos_fixtures import xlsx_bytes,csv_file

HEADER=['reference','date','net_amount','currency','channel']
RECORD=['R-1','2026-10-01T10:00:00+07:00','100.00','IDR','cash']
def row(number,values,formulas=()):return {'row':number,'values':values,'formula_columns':list(formulas)}
def descriptor(rows,**kw):return {'filename':'any-business.xlsx','content':base64.b64encode(xlsx_bytes(rows=rows,**kw)).decode()}
def auto(file):return extract_files([{**file,'worksheets':[{'name':'POS Sales','detection_mode':'auto'}]}],'M002')[0]

class WorksheetDetection(unittest.TestCase):
 def test_unique_header_introduction_blank_rows_and_no_money_changes(self):
  source=auto(descriptor([['Sales report'],[],HEADER,RECORD,[],['R-2','2026-10-02','-20','IDR','card']]))
  self.assertEqual(source['header_row'],3);self.assertEqual(source['last_data_row'],6);self.assertEqual(len(source['rows']),2);self.assertEqual(source['rows'][1]['values']['net_amount'],'-20')
 def test_trailing_total_is_excluded_only_with_empty_identity_and_date(self):
  detected=detect_table([row(1,HEADER),row(2,RECORD),row(3,['','','100','','Total Revenue'])]);self.assertEqual(detected['status'],'ready');self.assertEqual(detected['transaction_count'],1);self.assertEqual(detected['excluded_summary_rows'],[3])
 def test_formula_summary_ignored_without_using_cached_number(self):
  file=descriptor([HEADER,RECORD,['','','100','','Total Revenue']]);out=io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(file['content']))) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dest:
   for name in src.namelist():
    data=src.read(name)
    if name=='xl/worksheets/sheet1.xml':data=data.replace(b'<c r="C3" t="inlineStr"><is><t>100</t></is></c>',b'<c r="C3" t="e"><f>SUM(C2:C2)</f><v>#VALUE!</v></c>')
    dest.writestr(name,data)
  file['content']=base64.b64encode(out.getvalue()).decode();source=auto(file);self.assertEqual(len(source['rows']),1);self.assertEqual(source['detection']['excluded_summary_rows'],[3])
 def test_unlabelled_formula_is_not_assumed_to_be_a_total(self):
  d=detect_table([row(1,HEADER),row(2,RECORD),row(3,['','','[Formula — not evaluated]'],[2])]);self.assertEqual(d['status'],'review_required');self.assertEqual(d['transaction_count'],2);self.assertEqual(d['excluded_summary_rows'],[])
 def test_formula_record_with_reference_and_date_is_never_removed(self):
  d=detect_table([row(1,HEADER),row(2,RECORD),row(3,['R-2','2026-10-02','[Formula — not evaluated]','IDR','Total'],[2])]);self.assertEqual(d['status'],'review_required');self.assertEqual(d['transaction_count'],2);self.assertFalse(d['excluded_summary_rows'])
 def test_nonfinancial_formula_is_still_blocked(self):
  file=descriptor([['date','net_amount','currency','type','channel','status','reference'],['2026-10-01','100','IDR','sale','cash','completed','X']],formula=True)
  with self.assertRaises(InputError):auto(file)
 def test_summary_in_middle_and_later_transaction_force_review(self):
  d=detect_table([row(1,HEADER),row(2,RECORD),row(3,['','','100','','Total']),row(4,['R-2','2026-10-02','200','IDR','cash'])]);self.assertEqual(d['status'],'review_required');self.assertEqual(d['transaction_count'],3);self.assertFalse(d['excluded_summary_rows'])
 def test_unknown_footer_is_not_silently_dropped(self):
  d=detect_table([row(1,HEADER),row(2,RECORD),row(3,['This row needs review'])]);self.assertEqual(d['status'],'review_required');self.assertEqual(d['transaction_count'],2)
 def test_incomplete_record_is_retained_for_review(self):
  d=detect_table([row(1,HEADER),row(2,RECORD),row(3,['R-2','','200','IDR','cash'])]);self.assertEqual(d['transaction_count'],2);self.assertEqual(d['status'],'review_required')
 def test_repeated_and_multiple_headers_do_not_choose_one_silently(self):
  d=detect_table([row(1,HEADER),row(2,RECORD),row(3,HEADER),row(4,RECORD)]);self.assertEqual(d['status'],'review_required');self.assertEqual(d['header_candidates'],[1,3]);self.assertIsNone(d['transaction_count'])
 def test_possible_records_before_header_are_not_silently_dropped(self):
  
  for record in (['R-0','','200','IDR','cash'],['R-0','200','2026-10-01','IDR','cash'],['R-0','200']):
   d=detect_table([row(1,record),row(2,HEADER),row(3,RECORD)]);self.assertEqual(d['status'],'review_required');self.assertTrue(any('before' in r for r in d['reasons']))
 def test_unknown_headers_require_review_and_explicit_confirmation(self):
  f=descriptor([['Business Day','Value'],['2026-10-01','10']]);selection={'name':'POS Sales','detection_mode':'reviewed','header_row':1,'last_data_row':2}
  with self.assertRaises(InputError):auto(f)
  with self.assertRaises(InputError):extract_files([{**f,'worksheets':[selection]}],'M002')
  result=extract_files([{**f,'worksheets':[{**selection,'review_confirmed':True}]}],'M002');self.assertEqual(len(result[0]['rows']),1);self.assertTrue(result[0]['detection']['review_confirmed'])
 def test_client_cannot_override_automatic_bounds_or_bypass_formula_safety(self):
  f=descriptor([HEADER,RECORD])
  with self.assertRaises(InputError):extract_files([{**f,'worksheets':[{'name':'POS Sales','detection_mode':'auto','header_row':1}]}],'M002')
  f=descriptor([['date','net_amount','currency','type','channel','status','reference'],['2026-10-01','100','IDR','sale','cash','completed','X']],formula=True)
  with self.assertRaises(InputError):extract_files([{**f,'worksheets':[{'name':'POS Sales','detection_mode':'reviewed','header_row':1,'last_data_row':2,'review_confirmed':True}]}],'M002')
 def test_unsorted_or_duplicate_rows_cannot_shrink_automatic_boundary(self):
  for numbers in ((1,5,2),(1,2,2)):
   d=detect_table([row(numbers[0],HEADER),row(numbers[1],RECORD),row(numbers[2],RECORD)]);self.assertEqual(d['status'],'review_required');self.assertIsNone(d['last_data_row'])
 def test_csv_path_and_values_are_unchanged(self):
  s=extract_files([csv_file()],'M002')[0];self.assertEqual(len(s['rows']),2);self.assertEqual(s['rows'][0]['values']['net_amount'],'100.00')

if __name__=='__main__':unittest.main()
