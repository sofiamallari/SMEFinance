# Synthetic POS demo reports

Use merchant **M002** (IDR). Reports contain synthetic October 2026 transactions, never customer data. Each receipt is one transaction. Use the suggested mappings and UTC+07:00; generic amount columns require an explicit monetary mapping.

Start with `sample-pos-sales-october.csv`: 2 completed sales, total 150.00 IDR. If source controls are desired, enter count 2 and completed net 150.00. Importing the same file again excludes exact duplicates.

Add the different-column report (75.00) and refund/reversal report (-30.00) to demonstrate per-schema mapping. Select `folder/` to upload the two nested CSVs (net 100.00). XLSX uses a native Excel date cell and a distinct receipt ID.

The invalid file blocks its entire batch. The duplicate file demonstrates explicit exclusions. For the reconciliation-mismatch file, enter the intentionally incorrect synthetic report controls in the `.controls.json` sidecar (count 2, net 999.00) on the mapping page; validation must block import. The sidecar itself is not an upload file. No source controls are invented automatically.

Regenerate these fixtures with `python scripts/generate_pos_demo.py`. File selection may include unsupported README/JSON entries; the UI visibly excludes those and the backend rejects unsupported uploaded types.
