> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Transaction Management delivery notes

Current access rules: [four-role permissions](../../technical/security-permissions.md).

This release modifies the existing SME Finance Copilot v1.2 application for the Shenzhen International FinTechathon.

## API

All requests require server-authenticated identity, assigned merchant scope and action permission. Cookie writes require X-CSRF-Token; role/consent headers never establish authority.

| Method | Endpoint | Body / behavior |
|---|---|---|
| GET | /api/transactions?merchant=M002 | Saved manual/imported entries, owner or staff |
| POST | /api/transactions/entry | `{merchant, entry}`; validates and saves one entry |
| POST | /api/transactions/preview | `{merchant, filename, content}`; content is base64 CSV/XLSX; alternatively `{merchant, rows}` |
| POST | /api/transactions/import | `{merchant, preview_token, confirmed:true}`; revalidates and saves the confirmed batch |
| POST | /api/transactions/manage | Owner only: `{merchant,id,action:"update",entry}` or `{merchant,id,action:"delete"}` |

Preview errors use one-based data-row indices (header excluded). The returned `rows` contains normalized valid rows; the original file remains the source for invalid rows. Any error blocks the entire batch. Owner management applies to manually encoded/imported entries; synthetic baseline and sandbox payment records are managed by their existing modules.

## Validation and test coverage

`python -m unittest discover -s tests -v` runs original module, security, HTTP, mocked AI and MCP tests plus transaction validation, CSV structure, XLSX ingestion, duplicate rejection, preview confirmation/scoping, role authorization, durable replay, edits/deletions, dashboard totals and report projections. Optional browser smoke test `scripts/verify_ui.cjs` requires Playwright and installed Edge; adjust its local runtime paths for your environment.

## Limitations

- Authenticated mode is the default. Staff need a merchant membership, enabled role policy and an explicit bulk_import grant. Client-selected demo headers and environment identities are disabled.
- Single-process JSONL storage supports thread serialization and durable batch events. It is not a multi-process database; back up the ledger and use a transactional database before production deployment. A corrupted ledger currently stops startup so financial records are not silently discarded.
- Duplicate detection covers manual/imported rows and references, not aggregate synthetic baseline records or simulator payment settlements.
- XLSX supports a single worksheet, scalar values and ISO date text; native Excel serial dates, formulas, macros and multi-sheet workbooks require conversion. No external services receive uploaded files.
- Synthetic seed history has its fixed base date. Legacy transaction dates and canonical POS entry dates have different validation rules; current canonical dates permit the implemented clock-skew allowance. Ledger amounts use validated two-decimal inputs but existing analytics use floating-point arithmetic.
- Financial projections repeat the recent 30-day sales total and do not model seasonality or uncertainty. Financing recommendations are indicative and use existing synthetic business profile data. They do not approve credit or move money.
- AI prose requires configured LLM credentials. Without them, the existing rule engine generates the report; automated AI tests use a mock model rather than a live provider. Aggregate tool outputs may be sent to the configured provider; transaction descriptions are not exposed by the report tool.
- Saved revenue and expenses affect dashboard and forecasts; they do not automatically reconcile wallet opening balance or synthetic receivables/payables.
- No transaction writes are exposed to AI tools. Confirmation and owner management happen through the authenticated application API/UI under the existing authenticated API/UI.
