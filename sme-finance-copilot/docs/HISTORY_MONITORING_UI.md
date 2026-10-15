# Transaction History and Data Quality UI

Branch: `feature/security-sme-bank-workflow`. This task changes presentation and isolated browser fixtures only. Existing backend changes from earlier tasks are preserved; no backend application file or financial/security rule was changed here. No commit, push, merge, reset or discard was performed.

## Transaction History

The existing history endpoint supplies server pagination and sorting. The UI defaults to 10 rows, offers 25/50, and shows current/total pages and the backend matching count. Size changes reset to page 1. Changing a filter resets the pending offset and disables navigation until **Filter** applies it; this avoids navigating an old snapshot with new filters. Existing date/status/source/method filters and descending backend order remain unchanged. Empty results and page clamping are handled. Request/merchant guards prevent an older response replacing current merchant data.

One display dictionary supplies readable transaction, source, payment and status labels in filters and cells. Every option explicitly retains its original raw identifier. Unknown values receive a readable title-case fallback. Simulated Payment uses the actual `simulated_payment` source. Amounts use thousands separators, two decimal places, the original sign and explicit currency. Dates use the selected merchant’s configured timezone and preferred display format where loaded; the original timestamp and business date remain available on the time element. Long identifiers truncate visually while full values remain in title/accessible labels. No stored value is transformed.

## Data Quality dashboard — current redesign

Open Merchant Transactions → Data Quality & Monitoring. Four internal tabs replace the former long page: **Overview**, **Import History**, **Alerts**, and **Quality Rules**. Only one panel is visible. Selection survives foreground refreshes, filtering and ordinary navigation in the same page session; a full browser reload starts at Overview. Native tab semantics support Left/Right, Home/End, Enter/Space and roving focus. Tabs scroll horizontally on phones. The shared header/sidebar and existing theme tokens remain; the project uses custom Bootstrap-compatible styling rather than a new Bootstrap dependency.

### Overview

Ten compact KPI cards retain their exact backend values, scopes and percentage formatting. Information disclosures and **How Metrics Are Calculated** explain each definition. Rates use the latest validation of retained POS runs; valid means eligible plus exact duplicates. A zero denominator remains N/A. Unresolved means Open or Acknowledged. The refresh icon requests the existing foreground endpoint; it does not create continuous monitoring, timers or scheduled checks. Loading, request/merchant guards, failure/retry and snapshot time are visible.

### Import History

The source-focused table shows creation time, filenames, worksheet names, import status, recorded imported rows, duplicates, invalid-row issues and View Summary. Long batch IDs are reserved for technical details. Missing lifecycle results say Unavailable; Staged does not imply an import or a successful validation. Commit Status retains raw backend enums behind readable labels. Pagination defaults to 10 and offers 25/50; a status change resets to page 1. Pagination operates on the returned snapshot and makes no additional monitoring requests.

**Existing API cap:** latest 100 matching runs and 100 matching alerts. The visible disclosure and Returned Matching Runs label do not imply access to older history. Overview metrics retain their original full backend scope. No new server pagination or API change was introduced.

### Import Summary

View Summary opens an accessible native dialog with a fixed title/Close area and one scrollable body. It displays source/worksheets, creation time, actual lifecycle, detected/recorded currency where supplied, and an authorized readable initiator label only if supplied. The existing API supplies an actor ID but no readable label, so the business label says Unavailable and the ID remains in Technical Details.

Staged and unvalidated runs do not show fabricated zero eligible/imported/invalid counts. Validated runs show recorded validation metrics; only Committed runs show actual committed imported/excluded counts. Failed, expired, cancelled, integrity-blocked and in-progress states have separate explanations. Findings retain source, affected source row, field, error and correction, with existing 10/25/50 pagination and source filtering. Empty findings distinguish not-yet-validated from no recorded findings.

Reconciliation separates independently source-reported controls from calculated totals, status, explanations and recorded mismatch issues. Missing controls remain Unavailable. The API does not supply numeric difference fields: the UI explicitly says Not supplied by backend rather than introducing new financial arithmetic or manufacturing a difference. The configured currency remains explicit. Technical Details is collapsed by default and preserves batch IDs, mapping version, audit reference, actor ID, source provenance, findings, metrics, commit result and alert history as JSON. Escape closes the native dialog; merchant switches close it and invalidate outstanding detail requests.

### Alerts

Existing Severity, Status, From and Through filters remain. Compact cards show readable rule/severity/state, time, recorded affected rows, business explanation, recommendation and View Related Import. Readable option labels retain exact backend enum values. Acknowledge and Resolve with evidence remain explicit, permission-controlled actions using the existing endpoint, reason validation and audit chain. No automatic acknowledgment/resolution or changes to alert-generation rules were added.

### Data Validation Rules

The Quality Rules tab explains the eleven existing built-in rules: Required Fields, Uniqueness, Monetary Precision, Date Validity, Currency Validity, Status Validity, Payment Method Validity, Count Reconciliation, Financial Reconciliation, Merchant Authorization and Import Integrity. Each describes what is checked and why it matters. No rule is labeled Passed without recorded `metrics.rules` evidence from an explicitly selected validated run; that evidence is labeled selected-import scope, not a global/latest assertion. Staged runs have no validation results. Rules remain informational and cannot be disabled or made executable here.

### Security and integrity

No backend application, API, migration, dependency, permission, financial formula, status transition, expiration rule or alert generator changes in this redesign. Owners retain authorized merchant access; Staff needs existing explicit monitoring delegation. Bank/System Admin gain no operational monitoring access. Existing backend controls enforce every read/action and merchant scope. Settings, Babel catalog, mapping templates and intelligent import are preserved. Tests use disposable fixtures and do not write persistent demo financial records.

## Earlier presentation change inventory (historical)

- `web/index.html`: responsive filters/tables, metric guides, refresh/header and scroll regions; existing header/Dashboard/import changes preserved.
- `web/merchant-transactions.js`: shared presentation helpers, history pagination, local run pagination, metric explanations, refresh states and merchant/request guards.
- `web/icons.svg`: vendored Lucide refresh symbol.
- `scripts/serve_four_role_ui_test.py`: opt-in synthetic history/run seeding in its temporary environment only.
- `scripts/verify_history_quality.cjs`: repeatable browser verification and screenshots.
- This guide, docs index and existing Merchant Transactions guide: current instructions.
- `evidence/history-quality/`: actual assessment and screenshots; Owner/Bank/import evidence was also refreshed by regression runs.

## Earlier verification (historical)

| Check | Result |
|---|---|
| Final history/quality browser checks | 42 PASS |
| Existing multi-worksheet import UI checks | 31 PASS |
| Existing Owner header/workflow checks | 48 PASS |
| Existing Bank portal checks | 84 PASS on unchanged rerun |
| Existing backend history/monitoring/authorization/lifecycle tests | 3 PASS |

The focused browser fixture contains 71 committed transactions and 35 POS runs, including duplicate-only commits, a validation failure and cancellation. Checks compare filtered results, signed amounts, original timestamps, merchant-local formatting, rates and unresolved counts against real backend responses. They cover separate page sizes/states, filter resets, batch drilldown, keyboard metric guides, empty/N/A states, authorized merchant switching, foreign-merchant denial, refresh loading/failure/recovery and no JavaScript errors. Desktop 1600px, tablet 900px, mobile 390px and 320px were checked for page overflow. Production records are not seeded or edited.

An initial Bank regression attempt timed out waiting for its Activity sort control. An unchanged rerun passed all 84 checks; no Bank application code was modified. This intermittent test failure was not reproduced. Full backend regression/live Gemini were not rerun for this UI-only task; previous results remain historical.

[Assessment](../evidence/history-quality/assessment.json) · [History desktop](../evidence/history-quality/history-desktop.png) · [History mobile](../evidence/history-quality/history-mobile.png) · [Metrics desktop](../evidence/history-quality/quality-desktop.png) · [Metrics mobile](../evidence/history-quality/quality-mobile.png) · [Run history mobile](../evidence/history-quality/runs-mobile.png).

## Run and manual validation

From the application directory, run `node scripts/verify_history_quality.cjs` with Node, Playwright, Edge and Python available. Optional overrides: `COPILOT_TEST_PYTHON`, `COPILOT_PLAYWRIGHT_MODULE`. It starts/stops the temporary fixture on port 8126; run browser fixture scripts sequentially. The opt-in `COPILOT_HISTORY_QUALITY_FIXTURE=yes` flag belongs only to that disposable fixture server.

For manual checks, sign in as an authorized Owner, open History, change page sizes, apply filters and inspect a negative transaction and its full reference/timestamp. Open Data Quality, activate metric information with keyboard, refresh, change Commit Status, page through runs and open batch details. Repeat at mobile width. Staff still needs the existing explicit merchant grants; System Admin and Bank do not gain transaction/monitoring access.

## Limits

Runs/alerts retain the backend 100-record cap. Rate display retains one decimal and can round a very small nonzero invalid rate to 0.0%; invalid counts/findings remain authoritative. Native title accessibility varies by browser, with full values additionally exposed through accessible labels and existing details. Testing used Edge; no broad browser certification or new continuous monitoring is claimed.

## Redesign implementation and verification

Current implementation files: `web/index.html` (tab panels, compact responsive styling and Import Summary dialog), `web/merchant-transactions.js` (presentation, lifecycle-aware summary, readable alerts/rules and context guards), `scripts/verify_quality_dashboard.cjs` (new disposable browser checks), and `scripts/verify_history_quality.cjs` (existing checks adapted to tabs and current date settings). This guide and the existing documentation index/testing guide provide navigation. Backend and previous Transaction Settings/import files are unchanged.

Run `node scripts/verify_quality_dashboard.cjs` and `node scripts/verify_history_quality.cjs` sequentially with Playwright/installed Edge and optional `COPILOT_PLAYWRIGHT_MODULE` / `COPILOT_TEST_PYTHON`. Their temporary fixture server uses port 8126. For regression, run `python scripts/run_isolated_regression.py`; set `COPILOT_BAO_WORKBOOK` to the supplied workbook to avoid skipping the actual-file test. Current browser results/screenshots are under `evidence/quality-dashboard/`; backend results remain under `evidence/transaction-settings/`. Earlier result counts above are historical.

Remaining limitations: the existing 100-item API caps, no server-side monitoring pagination, no readable actor labels in the response, no numeric reconciliation difference fields, no persistence of internal tab choice across full reload, and no continuous monitoring. These are disclosed rather than invented functionality.

### Final redesign verification — 15 October 2026

Baseline HEAD: `7e36f57fd89bd1b5aa7528d8ed9a2b3258a09846`; branch `feature/security-sme-bank-workflow`. Existing unrelated root README/ZIP changes were preserved. No commit, push, merge, reset or discard performed.

| Executed check | Result |
|---|---|
| Full isolated backend regression, actual Bao workbook enabled | PASS — 332 tests, 0 failures, 0 errors, 0 skips |
| New monitoring dashboard browser suite | PASS — 75 checks |
| Existing history/monitoring browser suite adapted to current tabs/date settings | PASS — 42 checks |
| Existing Transaction Settings browser suite | PASS — 45 checks |
| Existing real Bao multi-worksheet import browser suite | PASS — 33 checks |
| Python compilation, changed JavaScript syntax, Git whitespace checks | PASS |
| Updated documentation links | PASS — 51 checked, 0 broken |

The new browser suite compares metrics and severity/status filtering with live fixture API responses; checks date-filter empty states, page resets/sizes, Staged/Validation Failed/Committed summaries, collapsed JSON, findings, unavailable controls, evidence-only rule results, keyboard tabs, explicit acknowledgment, denied undelegated actions, Bank/Admin detail denial, merchant isolation, refresh errors/recovery and runtime errors. Screenshots/no-overflow checks cover all four tabs at 1600, 900, 390 and 320px, plus the mobile summary. Visual inspection found and fixed inherited white dialog-title styling; a contrast assertion now covers it. Refresh recovery also has an assertion ensuring stale error styling is cleared.

Changed code: `web/index.html`, `web/merchant-transactions.js`, `scripts/verify_history_quality.cjs`; added `scripts/verify_quality_dashboard.cjs`. Documentation: this guide, `docs/README.md`, `docs/TESTING.md`. Generated verification evidence updates include `evidence/quality-dashboard/`, `evidence/history-quality/` and refreshed settings/import/backend evidence. No backend/API/security rules changed. No outstanding failed required checks; remaining limitations are listed above. No deployment or external provider verification was executed in this UI task.
