# Synthetic CNY POS reports

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
