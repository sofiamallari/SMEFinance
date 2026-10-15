"""Fresh synthetic CNY examples; no database/ledger opened or monetary conversion performed."""
import sys,json,base64,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.pos_fixtures import csv_file,xlsx_bytes
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'examples/pos-reports')
root=parser.parse_args().output;root.mkdir(parents=True,exist_ok=True)
sales=[['2026-10-01T10:00:00+08:00','38.50','CNY','sale','cash','completed','CNY-SAMPLE-001'],['2026-10-01T11:00:00+08:00','64.25','CNY','sale','card','paid','CNY-SAMPLE-002']]
files={
 'sample-pos-sales-october.csv':csv_file(rows=sales),
 'sample-pos-refunds.csv':csv_file(rows=[['2026-10-02T10:00:00+08:00','6.25','CNY','refund','cash','paid','CNY-REFUND-001'],['2026-10-02T11:00:00+08:00','3.10','CNY','reversal','card','paid','CNY-REVERSAL-001']]),
 'sample-pos-different-columns.csv':csv_file(headers=['Sale Date','Total Paid','Currency','Transaction Type','Tender Type','Transaction Status','Receipt No.'],rows=[['2026-10-03','63.80','CNY','sale','wallet','paid','CNY-ALT-001']]),
 'sample-pos-duplicates.csv':csv_file(rows=[sales[0],sales[0]]),
 'sample-pos-invalid.csv':csv_file(rows=[['not-a-date','abc','CNY','sale','cash','completed','CNY-INVALID-1'],['2026-10-02','35.005','CNY','sale','cash','completed','CNY-INVALID-2']]),
 'sample-pos-reconciliation-mismatch.csv':csv_file(rows=[['2026-10-04','48.50','CNY','sale','cash','paid','CNY-RECON-1'],['2026-10-04','27.80','CNY','sale','cash','paid','CNY-RECON-2']]),
 'folder/sales.csv':csv_file(rows=[['2026-10-05','86.40','CNY','sale','cash','paid','CNY-FOLDER-1']]),
 'folder/nested/refunds.csv':csv_file(rows=[['2026-10-05','9.60','CNY','refund','cash','paid','CNY-FOLDER-REFUND']])}
for name,data in files.items():
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(data['content']))
headers=['date','net_amount','currency','type','channel','status','reference']
(root/'sample-pos-sales.xlsx').write_bytes(xlsx_bytes(rows=[headers,['2026-10-01','78.90','CNY','sale','cash','completed','CNY-XLSX-001']],native_date=True))
(root/'sample-pos-reconciliation-mismatch.controls.json').write_text(json.dumps({'count':2,'net_total':'999.00','basis':'completed_net'},indent=2)+'\n',encoding='utf-8')
(root/'README.md').write_text('''# Synthetic CNY POS reports

Current access rules: [four-role permissions](../../docs/SECURITY_PERMISSIONS.md).

Use any authorized CNY merchant, such as M002. All amounts are new RMB scenario values, not converted or relabeled legacy examples. CSV timestamps include UTC+08:00; native Excel dates require source timezone confirmation. Supported currency code is CNY; display is ¥.

- Sales CSV: 2 completed sales, CNY 102.75.
- Different-column CSV: CNY 63.80.
- Refund/reversal CSV: CNY -9.35 after existing sign normalization.
- Nested folder: CNY 76.80 net.
- Native-date XLSX: CNY 78.90, distinct source receipt.
- Duplicate example repeats a receipt: validation must detect it.
- Invalid example contains an invalid date/amount and excessive precision: do not import it.
- Reconciliation example totals CNY 76.30, deliberately mismatching sidecar control 999.00; validation must reject that control.

Files are not automatically imported. Use Merchant Transactions → Bulk POS Import, inspect/match columns, validate, review preview, and explicitly confirm. Never upload README or the JSON control sidecar as transaction files. CSV/XLSX use the existing validation and duplicate rules. Regenerate with `python scripts/generate_pos_demo.py`; `--output PATH` selects a separate fixture directory. No database or persistent ledger is opened by this command.
''',encoding='utf-8')
print('Generated fresh CNY CSV/XLSX examples; no database modified.')
