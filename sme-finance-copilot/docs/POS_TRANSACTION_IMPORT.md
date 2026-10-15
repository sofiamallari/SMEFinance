# Task 02 — Merchant Transactions and secure POS import

Current access rules: [four-role permissions](SECURITY_PERMISSIONS.md).

Implemented in `sme-finance-copilot/` on `feature/pos-transaction-import`, based on `origin/main` commit `f1792ca416ed139505d96861871becf60992af9f`. Security Administration was already merged in that baseline.

Current selected-worksheet import, approved 10,000-row cap and import-only CNY support: [current implementation guide](MULTI_WORKSHEET_IMPORT.md). Original Task 02 baseline notes below retain their historical scope.

## Architecture compatibility

The baseline business UI used horizontal tabs, despite the requested left-sidebar description. Task 02 moves that same navigation and content implementation into one left sidebar in the existing `web/index.html`; no duplicate application or authentication system is introduced. Dashboard, AI Copilot, Financing, Cash Flow and Payment Sandbox remain functional. Existing Financing Applications remains a secondary Financing link. Administration pages/navigation are unchanged.

Task 02 deliberately does not connect new canonical POS/manual records to the five existing demo modules. Their current synthetic data/calculations and legacy transaction API behavior are preserved. New committed data is available through authorized transaction/quality services for Task 03; no unrestricted storage/MCP tool is added.

## Run and demo

```powershell
cd C:\Users\User\source\repos\SMEFinance\sme-finance-copilot
python -m copilot.auth migrate
# Only on a new installation:
python -m copilot.auth bootstrap --username admin --email your-email@example.com
python -m copilot.server --port 8000
```

If Windows' `python` alias is unavailable, use your installed Python or this workspace's bundled executable: `C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. Set environment variables in the process; `.env` is not automatically loaded. Restart an already-running server after updating source. Migrations are additive; do not replace the developer's database with fixture data.

Log in as administrator, create a SME Owner with M002 membership, and use that separate owner login for transactions. Administrators do not automatically receive merchant access. New Staff have no implicit module access; Owner delegation or System Admin per-merchant controls must explicitly grant reads, encoding, bulk upload and alert actions as appropriate. Role policy must also allow the action. Existing staff encoding/bulk authority is converted to explicit migration grants to preserve compatibility. Legacy optional `bulk_import` updates remain supported, but new explicit per-merchant grants are authoritative and revocable.

For Docker, retain the existing Dockerfile/entry point and mount persistent `logs` storage for identity SQLite, the JSONL journal and its lock sidecar. Bootstrap your own account with the existing CLI, never ship a prepopulated identity DB or default password. Browser folder selection needs no host POS-directory mount. Use HTTPS and the existing Secure-cookie setting for non-local deployment.

### Recorded-demo walkthrough

1. Log in as SME Owner for M002 (IDR). Expand Merchant Transactions in the existing left sidebar.
2. Open Single Transaction. Enter business-local date/time, net amount, currency (fixed to merchant), type, method, status, a unique external reference and optional description/category. Save and inspect its internal ID in Transaction History.
3. Open Bulk POS Import. Select `examples/pos-reports/sample-pos-sales-october.csv` and optionally the different-column/refund files. Alternatively select `examples/pos-reports/folder/`; supported nested CSV/XLSX files are uploaded by the browser.
4. Verify the suggested column mappings; explicit defaults apply only to unmapped fields. Generic “Amount” requires an explicit net/gross choice. Choose the correct UTC offset and ISO/day-first/month-first format. Reuse a mapping for identical headers if desired.
5. Supply only real/source-provided control totals. For the two-sale fixture, controls may be count 2 and completed net 150.00 IDR. The intentional mismatch fixture has a sidecar with reported count 2/net 999.00, which must fail arithmetic reconciliation. The sidecar itself is not an upload format.
6. Run Validate, review all findings and monetary/count reconciliation, then Preview. Eligible records are paginated and exact duplicate exclusions are visible. Confirm Import explicitly. No success appears before the durable journal is confirmed.
7. Open History and Data Quality. Drill into run metadata/hash/mapping version, inspect real rates/alerts, acknowledge and resolve with recorded reason/evidence. Reuploading identical receipts excludes them rather than doubling revenue.
8. Use the invalid fixture to demonstrate batch blocking, and a read-only Staff or administrator session to demonstrate denied writes/financial access.

All supplied demo files are synthetic October 2026 reports for M002, earlier than the recorded-demo date. Unlike legacy APIs bounded by the synthetic September 30 as-of date, the new canonical APIs accept historical real dates up to current time plus five minutes of clock skew. No real customer, card or banking data is used. Regenerate fixtures with `python scripts/generate_pos_demo.py`.

## Navigation and routes

The sixth primary sidebar item is Merchant Transactions with receipt and chevron, expanding to exactly four indented subviews. The selected child and parent stay highlighted; the selected merchant is in the URL. Back/forward and refresh restore route/context. The existing application header retains merchant selection, identity, consent link and logout. Mobile uses the same collapsible navigation; focusable controls and `aria-expanded`/`aria-current` communicate state. Outline SVG assets are vendored from [Lucide](https://github.com/lucide-icons/lucide), with the full license in `web/LUCIDE-LICENSE.txt`; no CDN is required. The baseline has no dark-theme system to extend.

| View | URL |
|---|---|
| Dashboard | `/dashboard?merchant=M002` |
| AI Copilot | `/copilot?merchant=M002` |
| Financing | `/financing?merchant=M002` |
| Cash Flow | `/cash-flow?merchant=M002` |
| Payment Sandbox | `/payment-sandbox?merchant=M002` |
| Single Transaction | `/merchant-transactions/single?merchant=M002` |
| Bulk POS Import | `/merchant-transactions/import?merchant=M002` |
| Transaction History | `/merchant-transactions/history?merchant=M002` |
| Data Quality & Monitoring | `/merchant-transactions/data-quality?merchant=M002` |

Direct child routes are authorized on the server. Staff require explicit grants for read, write, upload and monitoring actions. System Admin and Bank have no SME transaction access; unmapped legacy roles remain denied. The alert badge is the backend count of open plus acknowledged alerts for the current authorized merchant, hidden when zero, and refreshed after validation/import/lifecycle changes. Hiding UI elements never replaces backend checks.

## Five-step wizard and reusable ETL

User flow is **Select Files → Map Columns → Validate → Preview → Import**. Backend stages are **Extract → Stage → Transform → Validate → Reconcile → Preview → Commit → Monitor**.

- `pos_extract.extract_files` accepts bounded file descriptors from acquisition (currently browser file/folder selection). It returns safe metadata/headers/rows and original-byte SHA-256. A future Google Drive connector can supply the same filename/byte descriptors through an authenticated acquisition adapter. No Drive OAuth, external credentials, ETL platform or cloud worker is implemented.
- `canonical_transactions.normalize` performs shared type/date/currency/status/payment/monetary normalization for manual and mapped POS records.
- `POSImportService` binds staged rows to authenticated user, merchant and login session, validates mappings, detects duplicates, reconciles, serves the exact signed dataset, commits through the existing journal, and persists monitoring/alerts.
- Existing transaction APIs remain available for compatibility. They share the same journal append locking and reject references already stored through canonical operations.

## Formats, bounds and data minimization

CSV must be UTF-8 (BOM accepted) and structurally valid. XLSX must be real OOXML with explicitly selected transaction worksheets and per-source header/data ranges. Inline/shared strings and native Excel date styles/1900 or 1904 date systems are supported. Macros, encrypted/OLE workbooks, formulas/error cells, XML entities/DOCTYPEs, external relationships, unsafe ZIP paths and unsupported types are rejected, never executed or fetched externally.

Limits: 10 files, 3 MB each, 10 MB total, 10,000 parsed rows across a batch, 30 columns, 4,096-character source cells, 20 MB expanded workbook content, 200 ZIP members and 200:1 maximum expansion ratio. A cooperative ten-second processing deadline is checked during extraction. This is bounded parsing, not an OS-level execution watchdog. Staging is limited to 64 active runs globally, 5 per user and 32 MB of source/normalized temporary JSON; the larger upload body limit applies to staging and authenticated worksheet inspection endpoints. Authentication/CSRF is checked before reading those request bodies.

Known sensitive columns (customer contact/identity, PAN/CVV, credentials/secrets) are excluded from staging; remaining possible card/contact/credential values and formula-like text are rejected. Broad numeric-card detection may reject long numeric receipt identifiers; use a safe non-card POS identifier or a reviewed preprocessing adapter rather than uploading payment credentials. Unknown unnecessary source columns are temporary only and discarded after validation/commit cleanup; do not intentionally upload private customer data. Filenames/relative paths are sanitized, cannot be absolute or traverse parents, and are never used to access host directories.

UI strings are escaped. No user-data spreadsheet export is added in this task; synthetic templates contain no formulas. Formula-like references/descriptions/source cells are rejected, and future CSV export must still apply spreadsheet-safe escaping. XLSX values-only conversion may be needed for reports containing formulas or multiple worksheets.

## Canonical model and normalization

### API contract

All endpoints use existing authenticated sessions, merchant scope and CSRF for cookie writes. Administration/financing roles receive no new transaction access. Error responses use the existing 400/401/403/404/409/429/500 conventions; unsafe source findings do not echo credentials or raw uploaded payloads.

| Endpoint | Behavior |
|---|---|
| POST `/api/merchant-transactions/entry` | `{merchant,entry,idempotency_key}`; canonical manual validation and durable save |
| GET `/api/merchant-transactions/history` | Merchant-scoped committed records and bounded filters/pagination |
| POST `/api/pos-import/stage` | `{merchant,files:[{filename,relative_path?,content}]}`; content is base64; returns a private staged batch |
| GET `/api/pos-import/{batch_id}` | Original actor/session's staged metadata, samples or confirmed outcome |
| POST `/api/pos-import/{batch_id}/validate` | `{merchant,mappings}`; transform, duplicate checks, controls, quality and preview token |
| GET `/api/pos-import/{batch_id}/preview` | Exact signed eligible dataset, offset/limit and findings |
| POST `/api/pos-import/{batch_id}/commit` | `{merchant,preview_token,confirmed:true}`; recheck and durable commit |
| POST `/api/pos-import/{batch_id}/cancel` | Clear uncommitted temporary data; no financial write |
| GET `/api/data-quality` | Scoped persisted summary, run/alert filters and actual foreground rechecks |
| GET `/api/data-quality/runs/{batch_id}` | Scoped lineage/quality/commit/audit/alert details |
| POST `/api/data-quality/alerts/{alert_id}` | `{merchant,state,reason}`; permission-controlled lifecycle |

Query parameters use `merchant`; history uses `start,end,status,source,payment_method,offset,limit`. Monitoring supports `run_state,severity,state,start,end`. Required file mapping keys are canonical-to-source `columns`, with explicit `defaults`, `timezone`, `date_format`, `report_kind:'transactions'` and optional `control_totals:{count,net_total,gross_total,basis}`. Mapping/source/internal provenance fields cannot be supplied through manual entry. There is no raw-storage read endpoint.

Committed canonical rows contain server-generated `transaction_id`, `merchant_id`, UTC `transaction_date`, `business_date`, signed decimal-string `amount`, completed-only `effective_amount`, currency, transaction type, method, status, source, external reference, optional description/category, gross/discount/tax/refund/settlement components, import batch/file/hash/row lineage, mapping/normalization version, source timezone, authenticated creator and creation time. Protected identity/source fields cannot be assigned in the manual body or mapping. Legacy journal entries are adapted for history without creating another transaction store. Sensitive legacy text is masked in history.

- Monetary calculations use Decimal, with exactly two decimal places and absolute values no greater than 1 trillion. Excess precision/non-finite/boolean values are rejected, not silently rounded. Decimal point and comma thousands grouping are supported; locale comma decimals/scientific notation are not auto-guessed.
- Currency is uppercase and must match the selected merchant's supported currency. There is no FX conversion.
- Explicit timestamp offsets win. Naive timestamps use the selected source UTC offset; business dates use the documented country demo offset (PH/MY/SG +08, ID/TH/VN +07). ISO dates and explicitly selected slash formats are supported. IANA/DST zones and all regional country timezones are not inferred.
- Sale amounts are positive. Expense, refund and sale-reversal amounts are negative. Pending, failed and voided records have effective amount zero and never count as completed revenue. Manual external reference is required; POS references may be absent under the conservative fingerprint rules below.
- When gross is mapped, `net = gross - discount + tax - refund_component`. Mapped net must agree. Adjustment components require gross and must be nonnegative. Known settlement columns cannot be mapped as revenue; settlement is retained separately, never substituted for sales net. Refund/reversal components are positive magnitudes before applying the transaction's negative direction.
- Status aliases include paid/success/approved → completed, on hold → pending, declined → failed, cancelled/void → voided. Supported type/method aliases are implemented in the canonical module. Unsupported meanings are corrected explicitly rather than fabricated.
- Aggregate reports and summary indicators are rejected; one receipt/transaction per row is required. Line-item aggregation, original-expense reversal semantics and unrestricted status-transition correction are not implemented. Correct historical canonical entries with an authorized, distinct reversal/refund record or verified reimport; direct canonical edits/deletes are not provided.

## Duplicate policy

Stable external references are merchant-scoped and case-insensitive. Exact financial/content fingerprints cover timestamp, signed amount, currency, type, method, status, reference, description/category and monetary components. Same reference with a different fingerprint is ambiguous and blocks the affected whole batch. Duplicates are checked within files, across selected files, against committed legacy/canonical history, at repeated upload, and again under the journal writer lock at commit.

Without references, matching content is not assumed to identify a unique real-world transaction: duplicate fingerprints are blocked as ambiguous unless they match the same source-byte hash and source row of a previously committed record. This avoids silently collapsing two legitimate identical cash sales. Filenames, hashes, timestamps or amounts alone are insufficient. Exact committed/batch duplicates are visibly excluded; an all-exact-duplicate batch can commit zero financial rows with a confirmed run result. Concurrent changes invalidate commit eligibility and require revalidation.

Manual submission keys are user/merchant scoped: identical retry returns the existing confirmed result; reuse for changed data is rejected. POS confirmation tokens are hashed, dataset/version-bound and single-use. A repeated committed POST is rejected with 409; GET the recorded batch outcome instead of reimporting.

## Count and financial reconciliation

`parsed = eligible + exact duplicate exclusions + invalid`, with mutually exclusive classes. Ambiguous duplicate conflicts are invalid/blocking rather than also counted as exclusions. `valid = eligible + exact duplicates` is a quality numerator, not a completed-payment count. All invalid records block the selected batch; no silent partial valid-subset import occurs.

Optional reliable control count/net/gross totals are supplied explicitly from a source report; they are not invented. A control basis distinguishes completed signed net (failed/pending/voided zero) from nominal signed net (all statuses). File controls compare against all valid source rows before visible duplicate exclusions. Eligible completed net is then reported separately, explaining exclusion effects. Gross is compared only when gross is mapped for every applicable row; absent gross is unknown, not fabricated zero. Material mismatch tolerance is exactly 0.00 for supported two-decimal amounts; mismatches block commit. Invalid monetary rows make provided controls unreconciled. With no reliable control totals, reconciliation is `not_available`/warning, and row validation still occurs.

## Staging, persistence, recovery and integrity guarantees

Migration `004_pos_import.sql` adds narrowly scoped merchant staff grants, POS run/staging/intent metadata, an installation integrity key, alerts and lifecycle events to the existing SQLite identity DB. The authoritative committed transaction source remains `logs/manual_transactions.jsonl`; SQLite does not become a second committed-row ledger. Its per-run aggregate metrics/result are monitoring metadata.

Raw file bytes are never retained. Bounded filtered extracted rows and canonical candidates are temporary SQLite JSON. HMAC signatures bind source and exact preview datasets to actor, merchant, batch and login-session context, including mappings/version. Source metadata carries original byte hashes. Unpredictable session/batch IDs, expiry, current account/session/membership/action checks, CSRF, protected-field whitelists and rechecked signatures prevent unauthorized staging/preview/commit and ordinary tampering. These guarantees do not protect against a fully privileged filesystem/SQLite attacker who can read/replace the integrity key.

The journal uses a thread lock plus platform file locking; canonical commit records are a single checksummed JSONL batch event. Duplicate checks are repeated under that writer lock. A durable SQLite `committing` intent is saved before append; financial success appears only after flush/fsync and metadata finalization. Recovery finalizes metadata only when a matching durable batch marker is present. If no marker exists, the run becomes failed and requires fresh authorized validation/reimport; recovery never fabricates financial entries or silently replays writes. Repeated completion never adds a second batch. Caught append errors truncate back to the pre-append offset; a power-loss torn tail/corruption is detected and blocks affected reads/writes rather than being automatically repaired. Restore a verified backup.

SQLite and JSONL are separate stores, not one distributed transaction. A finalized-marker recovery window is explicitly supported. The existing five modules' legacy in-memory projections are process snapshots; Task 03 must unify their authorized consumption. Use one app service in the demo, even though append locking protects concurrent journal writers. OS filesystem permissions and persistent-storage backups remain deployment responsibilities.

## Monitoring metrics, rules and alerts

Data Quality reads persisted POS run metadata, not fabricated examples. Its row metrics use the latest validation per retained POS run, not every revalidation attempt. Manual encodings are excluded from import-run denominators. Total runs includes all retained POS states; successful = committed, failed = failed/validation_failed/integrity_failed. Parsed/valid/invalid/exact-duplicate counts sum the latest validated runs. Rates divide by total parsed rows and are null when no rows were validated. Reconciliation failures sum latest per-file failed controls. Last successful import and unresolved count come from actual records; unresolved includes open and acknowledged.

Predefined checks cover required fields, uniqueness, precision, dates, currency, status/method, count/financial reconciliation, authorization and import integrity. Mapping prerequisites that prevent a check from running are warned, not claimed as passing. Import history is bounded to 100 runs/alerts, with status/severity/date filters and drilldown showing safe file/hash/version, validation, controls, commit result, audit reference and alert lifecycle. Transaction History supports date/status/source/method filters and 1–100 rows per page, using committed records only.

Deterministic rules deduplicate by merchant/batch/rule:

- Critical: staged signature failure, source merchant mismatch and confirmed journal corruption; affected operations remain blocked and security audit metadata is recorded.
- High: invalid required/financial records, ambiguous duplicates, control mismatch, concurrent commit conflict, failed/interrupted commit.
- Medium: exact duplicate rate ≥20% with at least 2 parsed rows; invalid rate ≥10% with at least 2; actual validated date gap >7 days; amounts >10× median absolute completed amount from at least 5 saved historical records and >1,000. Anomalies are not claimed as fraud.
- Informational: known exact duplicate exclusions and actually checked abandoned-session expiry. No continuous scheduler or invented no-activity finding is claimed.

Lifecycle is Open → Acknowledged → Resolved, with per-action authorization, actor/time and 8–500 character non-sensitive reason/evidence stored in lifecycle/audit records. Status changes never edit financial records or bypass invalid/integrity/reconciliation checks. Corrections must be revalidated. A failed commit's durable status must be checked before submitting another batch.

## Retention and extension boundaries

Import sessions expire after 30 minutes. Cleanup is evaluated on actual authorized staging/session/monitoring operations, not a claimed background timer. Committed/cancelled/expired/integrity-failed runs clear temporary rows; failed/validated candidates remain bounded until expiry for correction or recovery. Failed/cancelled/expired run metadata is retained 90 days, then removed; committed provenance, alerts/lifecycle history, journal and audit records remain retained for traceability. SQLite space reuse after cleanup is not secure-erasure certification. Directory uploads require a supporting browser; multi-file selection is the fallback.

Future adapters should reuse extraction/normalization/staging under authenticated scope. Task 03 should consume the existing authorized journal/history and quality services, completed-only signed effective amounts, provenance and quality warnings; distinguish simulated payments from historical imports and prevent double counting. POS sales alone are not full cash flow. Future AI/MCP integration must use permission-checked aggregates and retain T0–T4, consent and owner-approval limits. No downstream adapter, Drive OAuth or real payment/credit operation is implemented now.

## Verification

Run `python -m unittest discover -s tests -v`, `node scripts/verify_pos_ui.cjs`, `node scripts/verify_auth_ui.cjs` and the existing `node scripts/verify_security_ui.cjs` (optional Playwright plus installed Edge). Set `COPILOT_TEST_PYTHON` if needed. Browser scripts use disposable synthetic fixtures on port 8124; never substitute a production identity DB. Actual final results, modified files, baseline and commit details are recorded in `TASK02_REPORT.md` and verification evidence. Security findings remain preliminary until team review.
