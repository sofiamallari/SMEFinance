# Transaction Management delivery notes

This release modifies the existing SME Finance Copilot v1.2 application for the Shenzhen International FinTechathon.

## API

All JSON requests use the existing demo role and consent headers and merchant scope.

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

- Role selection via `X-Demo-Role` is demo authentication. Production must replace it with authenticated accounts, merchant assignments and staff upload grants. In this demo, all staff selected through the UI are authorized upload staff for the demo merchants.
- Single-process JSONL storage supports thread serialization and durable batch events. It is not a multi-process database; back up the ledger and use a transactional database before production deployment. A corrupted ledger currently stops startup so financial records are not silently discarded.
- Duplicate detection covers manual/imported rows and references, not aggregate synthetic baseline records or simulator payment settlements.
- XLSX supports a single worksheet, scalar values and ISO date text; native Excel serial dates, formulas, macros and multi-sheet workbooks require conversion. No external services receive uploaded files.
- The reproducible synthetic business data is fixed at 2026-09-30, and future transaction dates are rejected. Ledger amounts use validated two-decimal inputs but existing analytics use floating-point arithmetic.
- Financial projections repeat the recent 30-day sales total and do not model seasonality or uncertainty. Financing recommendations are indicative and use existing synthetic business profile data. They do not approve credit or move money.
- AI prose requires configured LLM credentials. Without them, the existing rule engine generates the report; automated AI tests use a mock model rather than a live provider. Aggregate tool outputs may be sent to the configured provider; transaction descriptions are not exposed by the report tool.
- Saved revenue and expenses affect dashboard and forecasts; they do not automatically reconcile wallet opening balance or synthetic receivables/payables.
- No transaction writes are exposed to AI tools. Confirmation and owner management happen through the authenticated application API/UI once production authentication is installed.
