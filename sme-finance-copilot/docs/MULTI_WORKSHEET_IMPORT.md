# Merchant Transactions: selected-worksheet import

Implemented on `feature/security-sme-bank-workflow`; existing work preserved. No commit, push, merge, reset or discard performed.

Current automatic boundaries and review-only advanced controls: [Automatic XLSX detection](AUTOMATIC_XLSX_DETECTION.md). Earlier test counts below describe their original recorded run.

## User workflow

Single Transaction retains its required fields, amount/date/sign/status semantics and endpoint. Its two-column form collapses on mobile. Currency is a disabled native selector showing the selected merchant's sole supported currency; it does not suggest conversion or permit a different currency.

Bulk POS Import retains its five internal screens (six user-facing phases: Upload Files → Select Worksheets → Map Columns → Validate → Preview → Import) and explicit confirmation:

1. Select CSV/XLSX files or a browser folder. Excel discovery lists worksheet names and the first 20 nonempty candidate rows. No worksheet is preselected. Select transaction worksheets. Unique transaction tables and clearly labeled trailing totals are detected automatically. Only ambiguous sheets expose Review Detected Data and optional advanced range controls. At least one worksheet per selected workbook is required.
2. Continue to Map Columns. Switch between independent source mappings using labeled buttons. Unsaved selections remain in their DOM controls. Map date and net/gross amount and map or explicitly default required fields. Source values remain unchanged unless an explicit payment-method translation is selected. This supports source labels such as Tap-to-Pay without weakening canonical method validation. Hashes remain internal/auditable rather than shown as the main interface.
3. Run Validation. Every selected record is validated. Summary cards show parsed, eligible, duplicate and invalid counts, status and row-count reconciliation. Per-source counts are expandable. Findings preserve source, row, field, error/exclusion and correction, with a source filter and independent pagination (10/25/50). Filtering resets the findings page.
4. Continue to Preview. The combined eligible dataset uses server pagination (10/25/50), with file/worksheet provenance. Financial reconciliation appears here, with overall signed totals and per-source nominal/completed/gross/control metrics. Reconciliation Notes retain source controls, settlement, failed/pending/voided and no-FX explanations. Source totals include valid source rows before duplicate exclusions, as before. Signed batch totals include negative expenses and must not be read as sales revenue.
5. Confirm the exact validated import in the existing confirmation dialog. Success appears only after the backend confirms commitment. A zero-row committed batch explicitly says no new transactions were imported and reports duplicate exclusions. Technical Details retains the complete result, Batch ID and original timestamp; the primary summary formats labels, monetary amounts and local completion time. Existing History, Data Quality and Import Another Batch actions remain.

Buttons use shared tokens, native controls, wrapping flex groups and compatible spacing classes. The application has custom CSS rather than an installed Bootstrap framework; no new CSS framework or dependency was added. Tables scroll within bounded containers on phones instead of shrinking columns into unreadable text.

## Architecture and authorization

`POST /api/pos-import/inspect` is a read-only discovery addition, protected by existing authenticated session, CSRF, merchant membership and `bulk_import` authorization. It never commits or stages financial records. The upload body cap matches staging. Candidate formulas are labeled and never executed; sensitive candidate values are redacted.

The existing stage endpoint accepts an optional `worksheets` array per XLSX descriptor: `{name, header_row, last_data_row?}`. Existing CSV and legacy single-sheet descriptors still work. Every selected worksheet becomes a signed staged source with its own ID, mapping, bounds, findings and reconciliation. Metadata retains the physical workbook hash, worksheet-specific source identity, row numbers and mapping version. Single-sheet hashes remain compatible with previous imports. Physical upload count and worksheet count are separate.

Canonical rows retain filtered original source values in `source_values`, worksheet/workbook provenance and source row. Unmapped gross, fees, sub-category and other source columns are therefore retained, not silently lost or used in calculations. Existing duplicate fingerprints and rules remain authoritative across worksheets/files/history. The existing signed preview token and journal writer/commit-intent/recovery mechanism commit the combined batch; any selected-source blocking error prevents the whole batch. Concurrent duplicates, revoked authority and stale/tampered previews remain blocking.

## Currency, resource limits and financial boundaries

At the user's explicit approval, canonical transaction import now accepts CNY in addition to the existing six currencies, always requiring equality with the authorized merchant currency. CN uses UTC+08:00 for business dates. Explicit CNY/RMB declarations in selected-sheet introductory/sample rows are checked against merchant currency. No FX conversion, merchant-currency mutation, simulator tax rate or financing formula was added. A correctly configured CNY merchant is required; the application does not automatically create one.

Also approved: the parsed batch cap is 10,000 instead of 5,000. Other protections remain: 10 files, 3 MB each, 10 MB total, 30 columns, bounded cell/XML/ZIP expansion, extraction time, staging quotas and all original financial validation. Selected transaction cells containing formulas remain rejected. Automatic structural detection excludes only clearly identified introductions/trailing totals; uncertain boundaries require explicit review. Advanced ranges remain available within that review.

**Processing fees remain a canonical-schema limitation.** The existing gross/net equality formula has no processing-fee component and is unchanged. Bao imports map supplied net amounts as authoritative; original gross and processing-fee source values are preserved as provenance. Mapping gross and net together when they differ due to fees remains an error. Canonical gross-sales reporting may remain unavailable; no fee is subtracted twice. Expense payment method is absent in this workbook and requires an explicit user default; test fixtures choose cash, which is a test assumption, not verified business evidence. Sub-category is retained in source provenance; no new financial category model was invented.

## Bao Burgers verification

The supplied workbook was read without editing it. In disposable CNY merchant data:

| Source | Selection | Records |
|---|---|---:|
| Overview & Summary | Excluded | 0 |
| Revenue Report | Header 5; transaction rows 6â€“5413 | 5,408 |
| Expense Report | Header 5; transaction rows 6â€“217 | 212 |
| Combined | Explicit confirmed atomic batch | 5,620 |

Backend completed signed totals: sales 1,834,714.52 CNY; expenses âˆ’2,227,858.71 CNY; combined âˆ’393,144.19 CNY. These values come from existing validation metrics, not a new financial formula. Reimport excludes all 5,620 exact duplicates and commits zero new rows. Wrong-merchant currency is blocked even if an IDR default is supplied. Introductory/summary/formula rows are not imported; formulas inside the chosen data range remain prohibited. Synthetic fixtures separately test cross-sheet duplicates, blocking errors, authorization, legacy single-sheet identity and invalid selections.

## Verification and screenshots

| Verification | Actual result |
|---|---|
| Full backend regression | 297 tests PASS (592.669 seconds) |
| Final worksheet/CNY/portability checks, including real Bao import/reimport | 8 tests PASS (15.830 seconds) |
| Original importer plus then-current worksheet tests | 36 tests PASS |
| Worksheet, role, transaction and agent security checks | 63 tests PASS |
| Final worksheet UI verification | 31 checks PASS |
| Existing Owner header/workflow regression | 48 checks PASS |
| Existing Bank portal regression | 84 checks PASS |
| Documentation link check | 300 local links; zero broken |

The full suite ran before the final test-portability/descriptor-validation and presentation refinements. The eight focused tests and final 31 browser checks passed after those refinements. Backend discovery audit attribution was then checked separately. Existing canonical gross/net formulas and duplicate fingerprints were inspected unchanged. Browser tests use headless Edge with isolated identity SQLite and transaction journals; production/demo financial records are not changed.

[UI assessment](../evidence/multi-worksheet-import/assessment.json) Â· [Mapping](../evidence/multi-worksheet-import/mapping-desktop.png) Â· [Desktop preview](../evidence/multi-worksheet-import/preview-desktop.png) Â· [Mobile preview](../evidence/multi-worksheet-import/preview-mobile.png) Â· [Findings pagination](../evidence/multi-worksheet-import/validation-pagination.png) Â· [Import result](../evidence/multi-worksheet-import/result-desktop.png).

Run from `sme-finance-copilot/`:

```powershell
$env:COPILOT_BAO_WORKBOOK = 'C:\path\to\Initial Test Data - Bao Burgers Business.xlsx'
python -m unittest tests.test_pos_import tests.test_multi_worksheet_import -v
node scripts/verify_multi_worksheet_ui.cjs
node scripts/verify_owner_header.cjs
node scripts/verify_bank_portal.cjs
```

Tests require Python/Node/Playwright/Edge; the workbook test additionally uses the bundled openpyxl reader. Set `COPILOT_BAO_WORKBOOK` to your local workbook path. The supplied-workbook acceptance test is explicitly skipped when that file or its optional openpyxl reader is absent; portable synthetic tests still run. Install openpyxl in your development environment to run that acceptance test. `COPILOT_TEST_PYTHON` and `COPILOT_PLAYWRIGHT_MODULE` override browser-test runtimes. The CNY fixture is opt-in via `COPILOT_CNY_IMPORT_FIXTURE=yes` in the disposable fixture server only. Run browser scripts sequentially on port 8126. No production credentials or default accounts are created.

## Changed files

- `copilot/pos_extract.py`: bounded worksheet discovery, explicit selection/ranges, currency hints, source metadata and approved row cap.
- `copilot/pos_import.py`: authorized discovery, independent-source metrics/provenance, explicit payment-label translations and worksheet result count; original financial/duplicate/commit rules reused.
- `copilot/canonical_transactions.py`: import-only CNY and CN date offset; financial formulas unchanged.
- `copilot/server.py`: authorized discovery route and its request-size cap, preserving earlier static-asset changes.
- `web/index.html`, `web/merchant-transactions.js`: refined existing forms/wizard, pagination, reconciliation and result presentation; previous Dashboard/header changes preserved.
- `tests/test_multi_worksheet_import.py`, `tests/test_pos_import.py`: new worksheet/currency/atomicity coverage and updated approved limit boundary.
- `scripts/serve_four_role_ui_test.py`, `scripts/verify_multi_worksheet_ui.cjs`: opt-in isolated CNY fixture and repeatable browser evidence.
- This guide, docs index and existing importer/module documentation: current instructions and limitations.

No migration is required: source metadata and mappings use the existing signed JSON storage and journal. No new production user, merchant or financial record was created.

## Remaining limitations

CNY simulator taxes are deliberately unconfigured. Processing-fee-aware canonical gross/net accounting needs an approved schema/formula change. Header and end rows are detected automatically where unambiguous. Review samples include boundaries and questionable rows; explicit advanced ranges are available only when review is needed. No automatic ambiguous-column inference or summary-row deletion is performed. Payment translation choices list at most 30 distinct source values; unsupported values still fail backend validation. Source control totals must be supplied independently; unavailable controls are labeled honestly. Existing POC journal/staging quotas and foreground monitoring remain. Tests cover Edge, not a full browser certification, and do not make a fresh live Gemini request.

## Merchant Transaction Settings and currency metadata

Open **Merchant Transactions → Transaction Settings** (`/merchant-transactions/settings?merchant=M002`, substituting an authorized merchant ID). The current merchant selector supplies the scope. Owners with enabled `manage_transactions` can edit; Staff can read/use settings through a live delegated `create_transactions`, `bulk_import` or `view_transactions` operation, but cannot edit. Banks and System Admin cannot access these merchant settings or templates. Existing upload grants are unchanged. Every backend request checks session, membership and permissions; writes retain CSRF protection.

1. Select the merchant and open Transaction Settings.
2. Review base currency. Existing financial data, balances, payment state, applications or import runs lock it. No historical currency migration is offered.
3. Search and choose an IANA timezone. Choose a preferred date **display** format and an existing canonical default status. Display formatting does not select source date parsing.
4. Optionally add verified external POS labels and their canonical payment-method translations. This is merchant-specific; do not guess translations.
5. Confirm and Save Settings. A stale settings version is rejected; reload before retrying. Saving is audited as `transaction_settings_updated`. Merchant switching reloads isolated settings and clears stale import context.

Single Transaction loads the base currency (not independently editable), timezone and default status. Bulk Import initially loads currency, timezone, status and confirmed payment translations. An explicit source timezone override remains possible. New canonical business dates use the configured merchant timezone; previously stored business dates and timestamps are not rewritten. Ambiguous/nonexistent daylight-saving local times require an explicit offset. Payment-simulator calculations and its existing country/offset behavior are unchanged.

**Currency metadata is not eligibility.** Babel supplies CLDR currency codes, English names, symbols and fraction-digit metadata, including historical entries. Search matches codes or names. Runtime dependencies are `Babel>=2.17,<3` and `tzdata>=2025.2` (verified with Babel 2.18.0 and tzdata 2026.5). Existing transaction eligibility remains IDR, PHP, MYR, THB, VND, SGD and import/manual CNY; this does not enable simulator tax assumptions for CNY. Other catalog currencies remain metadata-only. Canonical monetary validation still requires at most two decimal places; catalog precision does not change accounting. Install with `python -m pip install -r requirements.txt` before starting the server.

Explicit currency declarations or row values conflicting with the merchant are blocked. Symbols such as ¥ and $ are not definitive currency evidence; symbol-only evidence requires explicit confirmation. No FX, multi-currency aggregation, automatic conversion or historical relabeling is performed. Source detection uses bounded worksheet metadata/sample text and headers; mapped currency values are validated for every transaction. It is assistance, not a guarantee that arbitrary prose or every currency symbol is recognized.

## Assisted mapping and confirmed templates

Five primary mappings remain visible: Transaction Date/Time, Net Transaction Amount (or map Gross under Additional Fields), Transaction Type, Payment Method, and Transaction Reference. Safe aliases include Expense Date, Expense ID, Payment Type, Details and Expense Category, and currency suffixes on clear Net/Gross headers. When an explicit net column and a processing/transaction/service fee column coexist, suggestions leave gross and its adjustments unmapped to avoid assuming an unsupported fee accounting treatment. Those source values remain in provenance and can still be mapped explicitly for strict validation. Generic Amount is deliberately not silently mapped as net; selecting it requires an explicit net/gross meaning confirmation. Defaults for transaction type must be chosen and confirmed when no type column exists; a worksheet name does not approve a default.

**Additional Fields** is initially collapsed and retains Gross, Discounts, Tax, Refund Component, Settlement, Category, Description and Status. **Import Settings & Reconciliation** is initially collapsed and retains source currency, timezone, source parsing format, translations, optional independent control totals and mapping/template controls. Source currency remains visible in the mapping summary. Filled controls alone do not mark a worksheet backend-validated: Needs Review remains until validation succeeds. Changing mappings invalidates the visible validation/commit state.

After successful validation, an Owner may name and save a confirmed worksheet mapping template before committing. Templates are merchant-scoped, append-versioned and tied to the exact ordered source headers. Apply a compatible template explicitly on a future source and confirm its financial meaning again. Revenue and Expense meanings are not inferred from column similarity. Independently reported control totals are excluded from templates and remain specific to each source. API updates to an existing template require its expected version; the UI currently creates/lists/applies templates, without a rename/delete/version-history editor. Latest templates are listed, at most 50 identities per merchant. Template writes are audited as `transaction_mapping_template_saved`.

## Persistence and API reference

Additive migration `008_transaction_settings.sql` adds `merchant_transaction_settings` (one versioned configuration per merchant) and `merchant_mapping_templates` (merchant/template/version composite key). The existing migration runner applies it in filename order and tracks it in `schema_migrations`. Existing users and transaction journals are retained. Back up both identity SQLite and financial journals before deployment. Rollback requires restoring compatible application/database backups together; do not delete migration markers or tables against a running older application. Persisted currency conflicting with preconfigured historical financial data blocks startup for operator review rather than relabeling the history.

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/api/merchant-transactions/settings?merchant=ID&catalog=1` | Authorized settings; optional currency/timezone catalog |
| PATCH | `/api/merchant-transactions/settings` | `{merchant, settings: {expected_version, confirmed:true, ...fields}}`; Owner only |
| GET | `/api/transaction-currencies?merchant=ID&search=term` | Authorized currency metadata search |
| GET | `/api/merchant-transactions/templates?merchant=ID` | Latest merchant templates |
| POST | `/api/merchant-transactions/templates` | `{merchant, template:{name,batch_id,file_id,confirmed:true}}`; validated session and Owner required; optional `template_id`/`expected_version` updates |

The existing POS validate endpoint now accepts `review.type_confirmed`, `review.amount_confirmed`, and `review.currency_confirmed` booleans when their conditions apply. It does not accept absent confirmation for a default type or generic Amount meaning. Existing integrations must send genuine confirmations rather than blanket defaults. Template selection uses `{id,version}` and validates exact headers and unchanged type meaning on the backend. Existing preview-token, duplicate, reconciliation and atomic commit checks remain active.

## Financial boundaries and pending decisions

Gross and Net remain distinct. The unchanged calculation is gross minus discounts plus tax minus refund component; mismatched supplied net values fail validation. Settlement is not sales revenue. Processing fees remain original source provenance, without a canonical accounting field: no extra fee expense or second subtraction is introduced. Optional source controls must be independently supplied; missing controls remain unavailable rather than fabricated.

Missing payment methods remain invalid and are never automatically Cash. Introducing **Unknown / Not Provided** remains **pending business approval**: it needs agreed digital-capture denominators, channel analytics, exports and AI interpretation. The Bao expense fixture explicitly uses synthetic Cash only as a test assumption; it does not establish the actual workbook's expense payment methods. Real imports must supply trustworthy method information. Cash-flow, digital-capture, financing and RBF formulas are unchanged.

Settings display-format preference currently applies to transaction-history presentation; native datetime inputs retain browser-native formatting. Source timezone suggestions accept IANA IDs or explicit offsets; the settings page provides the full searchable IANA catalog. The currency catalog includes unsupported/historical codes for reference, not a promise of processing support.

## Reproduce verification safely

From the application directory, install requirements and run `python scripts/run_isolated_regression.py` for the full backend suite, or add `--pattern test_transaction_settings.py` / `--pattern test_worksheet_detection.py`. This runner isolates startup identity databases, financial journals and logs in temporary directories. To include the actual supplied workbook, set `COPILOT_BAO_WORKBOOK` locally to its full path. The workbook is not committed.

Browser checks: `node scripts/verify_transaction_settings_ui.cjs`, `node scripts/verify_detection_review.cjs`, and `node scripts/verify_multi_worksheet_ui.cjs`. They need Playwright and installed Edge; configure `COPILOT_PLAYWRIGHT_MODULE` and `COPILOT_TEST_PYTHON` for nondefault runtimes. Run sequentially: their disposable fixture server uses port 8126. They never substitute persistent demo data. Latest executed results are in `evidence/transaction-settings/` and the existing worksheet/import evidence folders; earlier counts elsewhere remain historical.

## Continuation acceptance record — 15 October 2026

Working branch: `feature/security-sme-bank-workflow`; HEAD `db78556f88487b66f6f5786e3b087bd97c6f41e3`. The working tree remains modified/untracked; existing work and the unrelated ZIP/root README changes were preserved. No commit, push, merge, reset or discard was performed.

| Verification | Actual result |
|---|---|
| Two original failures, executed individually | PASS — 2 tests |
| Final isolated full backend regression, actual Bao workbook enabled | PASS — 332 tests, 0 failures, 0 errors, 0 skipped |
| Settings-focused suite, including fee-suggestion regression | PASS — 19 tests (also included in the full suite) |
| Automatic worksheet-detection unit suite | PASS — 15 tests |
| Settings browser suite, Edge | PASS — 45 checks |
| Actual Bao multi-worksheet browser suite, Edge | PASS — 33 checks; 5,620 rows validated/imported in disposable data |
| Automatic detection/review browser suite, Edge | PASS — 18 checks |
| Python compilation; changed application JavaScript syntax; Git whitespace check | PASS |
| Documentation links in the five updated entry/module/testing guides | PASS — 62 local links, 0 broken after URL decoding |

Security checks cover Owner membership/manage permission, Staff read grants and denied writes, Bank/Admin denied settings/financial access, direct route denial, CSRF, audit events, version conflicts and merchant switching. Financial checks cover currency locks/mismatches, no FX/relabeling, canonical signs, gross/net validation, fee provenance, missing-method rejection, duplicates, reconciliation, explicit confirmation, existing forecasts/financing/RBF and prior authorization regressions. Tests use disposable synthetic databases and journals, with the actual Bao source workbook read-only; no persistent demo financial records were changed.

The migration failure was corrected by asserting ordered migration filenames, the new table columns, foreign-key integrity, unique schema markers, idempotency and unchanged legacy ledger bytes rather than merely increasing a count. The Bao fixture now explicitly confirms its generic expense Amount as net; this is a source/test interpretation, not weakened production validation. Browser verification found and fixed an additional suggestion defect: a fee-bearing source no longer automatically combines net with gross/adjustments that cannot represent the fee. A regression test preserves the strict canonical gross/net check.

Feature implementation inventory (all paths relative to the application directory):

- Backend additions: `copilot/currency_catalog.py`, `copilot/transaction_settings.py`, `copilot/migrations/008_transaction_settings.sql`. Integration: `copilot/canonical_transactions.py`, `copilot/modules/transactions.py`, `copilot/pos_extract.py`, `copilot/pos_import.py`, `copilot/server.py`. The preserved detection implementation is `copilot/worksheet_detection.py`.
- UI: `web/transaction-settings.js`, `web/merchant-transactions.js`, `web/index.html`.
- Dependencies/configuration: `requirements.txt`, `.gitignore` (local verification virtual environments ignored).
- Tests: `tests/test_authentication.py`, `tests/test_transaction_settings.py`, `tests/test_pos_import.py`, `tests/test_multi_worksheet_import.py`, `tests/pos_fixtures.py`; preserved `tests/test_worksheet_detection.py`.
- Verification: `scripts/run_isolated_regression.py`, `scripts/verify_transaction_settings_ui.cjs`, `scripts/serve_four_role_ui_test.py`, `scripts/verify_multi_worksheet_ui.cjs`; preserved `scripts/verify_detection_review.cjs`.
- Documentation: application `README.md`, `docs/README.md`, this guide, `docs/TESTING.md`, and `docs/task04/6 README_Merchant_Transactions.md`. Existing automatic-detection documentation is preserved and cross-linked.
- Recorded backend/browser JSON and responsive PNGs: `evidence/transaction-settings/`, `evidence/worksheet-detection/`, and `evidence/multi-worksheet-import/`.

Remaining business decision: Unknown/Not Provided payment-method accounting and digital-capture interpretation are **not implemented, pending approval**. Historical currency migration, additional currency processing/simulator rules, and new processing-fee accounting are likewise not introduced. There are no remaining failed required tests in the final recorded run. Live deployment and provider/Gemini connectivity were NOT EXECUTED; they are outside this continuation's verification scope.
