# Merchant Transactions: selected-worksheet import

Implemented on `feature/security-sme-bank-workflow`; existing work preserved. No commit, push, merge, reset or discard performed.

## User workflow

Single Transaction retains its required fields, amount/date/sign/status semantics and endpoint. Its two-column form collapses on mobile. Currency is a disabled native selector showing the selected merchant's sole supported currency; it does not suggest conversion or permit a different currency.

Bulk POS Import retains the five-step workflow and explicit confirmation:

1. Select CSV/XLSX files or a browser folder. Excel discovery lists worksheet names and the first 20 nonempty candidate rows. No worksheet is preselected. Select one or more transaction worksheets, choose each header row, and optionally specify its last data row to exclude report footers. At least one worksheet per selected workbook is required.
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

Also approved: the parsed batch cap is 10,000 instead of 5,000. Other protections remain: 10 files, 3 MB each, 10 MB total, 30 columns, bounded cell/XML/ZIP expansion, extraction time, staging quotas and all original financial validation. Selected transaction cells containing formulas remain rejected. Header and explicit last-row selection exclude introductions/footers without evaluating formulas or guessing which financial records to discard.

**Processing fees remain a canonical-schema limitation.** The existing gross/net equality formula has no processing-fee component and is unchanged. Bao imports map supplied net amounts as authoritative; original gross and processing-fee source values are preserved as provenance. Mapping gross and net together when they differ due to fees remains an error. Canonical gross-sales reporting may remain unavailable; no fee is subtracted twice. Expense payment method is absent in this workbook and requires an explicit user default; test fixtures choose cash, which is a test assumption, not verified business evidence. Sub-category is retained in source provenance; no new financial category model was invented.

## Bao Burgers verification

The supplied workbook was read without editing it. In disposable CNY merchant data:

| Source | Selection | Records |
|---|---|---:|
| Overview & Summary | Excluded | 0 |
| Revenue Report | Header 5; transaction rows 6–5413 | 5,408 |
| Expense Report | Header 5; transaction rows 6–217 | 212 |
| Combined | Explicit confirmed atomic batch | 5,620 |

Backend completed signed totals: sales 1,834,714.52 CNY; expenses −2,227,858.71 CNY; combined −393,144.19 CNY. These values come from existing validation metrics, not a new financial formula. Reimport excludes all 5,620 exact duplicates and commits zero new rows. Wrong-merchant currency is blocked even if an IDR default is supplied. Introductory/summary/formula rows are not imported; formulas inside the chosen data range remain prohibited. Synthetic fixtures separately test cross-sheet duplicates, blocking errors, authorization, legacy single-sheet identity and invalid selections.

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

[UI assessment](../evidence/multi-worksheet-import/assessment.json) · [Mapping](../evidence/multi-worksheet-import/mapping-desktop.png) · [Desktop preview](../evidence/multi-worksheet-import/preview-desktop.png) · [Mobile preview](../evidence/multi-worksheet-import/preview-mobile.png) · [Findings pagination](../evidence/multi-worksheet-import/validation-pagination.png) · [Import result](../evidence/multi-worksheet-import/result-desktop.png).

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

CNY simulator taxes are deliberately unconfigured. Processing-fee-aware canonical gross/net accounting needs an approved schema/formula change. Header and end-row selection are explicit; only the first 20 nonempty rows are candidate previews. No automatic ambiguous-column inference or summary-row deletion is performed. Payment translation choices list at most 30 distinct source values; unsupported values still fail backend validation. Source control totals must be supplied independently; unavailable controls are labeled honestly. Existing POC journal/staging quotas and foreground monitoring remain. Tests cover Edge, not a full browser certification, and do not make a fresh live Gemini request.
