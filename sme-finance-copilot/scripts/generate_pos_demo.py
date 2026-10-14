"""Synthetic demo files only; no identity or financial database is opened."""
import sys,json,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.pos_fixtures import csv_file,xlsx_bytes

root=Path(__file__).resolve().parents[1]/'examples'/'pos-reports';root.mkdir(parents=True,exist_ok=True)
files={
 'sample-pos-sales-october.csv':csv_file(),
 'sample-pos-refunds.csv':csv_file(rows=[['2026-10-02T10:00:00+07:00','20','IDR','refund','cash','paid','REFUND-001'],['2026-10-02T11:00:00+07:00','10','IDR','reversal','card','paid','REVERSAL-001']]),
 'sample-pos-different-columns.csv':csv_file(headers=['Sale Date','Total Paid','Currency','Transaction Type','Tender Type','Transaction Status','Receipt No.'],rows=[['2026-10-03','75','IDR','sale','wallet','paid','ALT-001']]),
 'sample-pos-duplicates.csv':csv_file(rows=[['2026-10-01T10:00:00+07:00','100.00','IDR','sale','cash','completed','POS-1'],['2026-10-01T10:00:00+07:00','100.00','IDR','sale','cash','completed','POS-1']]),
 'sample-pos-invalid.csv':csv_file(rows=[['not-a-date','abc','IDR','sale','cash','completed','INVALID-1'],['2026-10-02','50.001','IDR','sale','cash','completed','INVALID-2']]),
 'sample-pos-reconciliation-mismatch.csv':csv_file(rows=[['2026-10-04','100','IDR','sale','cash','paid','RECON-1'],['2026-10-04','50','IDR','sale','cash','paid','RECON-2']]),
 'folder/sales.csv':csv_file(rows=[['2026-10-05','125','IDR','sale','cash','paid','FOLDER-1']]),
 'folder/nested/refunds.csv':csv_file(rows=[['2026-10-05','25','IDR','refund','cash','paid','FOLDER-REFUND']])}
for name,data in files.items():
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(data['content']))
(root/'sample-pos-sales.xlsx').write_bytes(xlsx_bytes(native_date=True))
(root/'sample-pos-reconciliation-mismatch.controls.json').write_text(json.dumps({'count':2,'net_total':'999.00','basis':'completed_net'},indent=2)+'\n')
(root/'README.md').write_text('''# Synthetic POS demo reports

Use merchant **M002** (IDR). Reports contain synthetic October 2026 transactions, never customer data. Each receipt is one transaction. Use the suggested mappings and UTC+07:00; generic amount columns require an explicit monetary mapping.

Start with `sample-pos-sales-october.csv`: 2 completed sales, total 150.00 IDR. If source controls are desired, enter count 2 and completed net 150.00. Importing the same file again excludes exact duplicates.

Add the different-column report (75.00) and refund/reversal report (-30.00) to demonstrate per-schema mapping. Select `folder/` to upload the two nested CSVs (net 100.00). XLSX uses a native Excel date cell and a distinct receipt ID.

The invalid file blocks its entire batch. The duplicate file demonstrates explicit exclusions. For the reconciliation-mismatch file, enter the intentionally incorrect synthetic report controls in the `.controls.json` sidecar (count 2, net 999.00) on the mapping page; validation must block import. The sidecar itself is not an upload file. No source controls are invented automatically.

Regenerate these fixtures with `python scripts/generate_pos_demo.py`. File selection may include unsupported README/JSON entries; the UI visibly excludes those and the backend rejects unsupported uploaded types.
''',encoding='utf-8')
print('Generated synthetic multi-schema, folder, refund, duplicate, invalid, XLSX and reconciliation fixtures.')
