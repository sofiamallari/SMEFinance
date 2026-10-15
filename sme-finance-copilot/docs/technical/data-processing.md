# Data model and transaction processing

SQLite identity/workflow database and JSONL canonical journal are complementary stores, not interchangeable backups. [Migrations](../../copilot/migrations) preserve existing schema history; auth initializes them. Active paths are documented once in [operations](../operations/cny-dataset.md).

| Data | Source/table family |
|---|---|
| Identity and authority | users, memberships, sessions, optional_permissions, merchant_transaction_grants, role_permissions, security_policies, consents |
| Merchant metadata/settings | merchant_profiles, merchant_transaction_settings, merchant mapping templates |
| Import lifecycle | pos_import_runs, quality_alerts and signed temporary source/dataset information |
| Financing | financing_drafts, applications with explicit recipient_id, application_reviews append-only simulated feedback |
| Sandbox payments | simulated_payment_state, simulated_wallet_state, simulated_refund_state |
| Canonical records | transaction_journal.py append-only canonical_batch events, checksums and writer lock |
| Financial views | financial_data.py combines configured synthetic history with eligible canonical records and restored sandbox state |

Processing: inspect source structure/worksheets → detect table boundaries or require ambiguity review → independent mappings → normalize finite exact-cent values, timestamps/status/type/method/currency → duplicate and source-control checks → signed staging/validation → paginated normalized preview → session-bound token and explicit confirmation → durable journal append → finalize import metadata and audit. Failures/uncertain commits require state inspection before retry; never regenerate a receipt reference merely to defeat duplicate detection.

CSV and XLSX are supported; formula values are not evaluated as trustworthy transaction money. Clear trailing summaries can be excluded; ambiguous rows require review. Mapping and worksheet state remain independent. Signed normalized expenses/refunds/reversals and completed effective totals differ from nominal amounts. Existing financial control checks remain even though the simplified Validate/Preview UI omits count formulas and reconciliation details. See [current user workflow](../user-guide/merchant-transactions.md).

Canonical source lineage records merchant, source file/worksheet/row, hashes, mapping/normalization versions and batch. Imported settlement fields are not additional revenue. Unlinked POS and simulator collection events cannot independently be proven distinct; user double-entry remains a limitation. [Canonical normalization](../../copilot/canonical_transactions.py) · [import service](../../copilot/pos_import.py) · [projection](../../copilot/financial_data.py).
