# Transaction History and Data Quality UI

Branch: `feature/security-sme-bank-workflow`. This task changes presentation and isolated browser fixtures only. Existing backend changes from earlier tasks are preserved; no backend application file or financial/security rule was changed here. No commit, push, merge, reset or discard was performed.

## Transaction History

The existing history endpoint supplies server pagination and sorting. The UI defaults to 10 rows, offers 25/50, and shows current/total pages and the backend matching count. Size changes reset to page 1. Changing a filter resets the pending offset and disables navigation until **Filter** applies it; this avoids navigating an old snapshot with new filters. Existing date/status/source/method filters and descending backend order remain unchanged. Empty results and page clamping are handled. Request/merchant guards prevent an older response replacing current merchant data.

One display dictionary supplies readable transaction, source, payment and status labels in filters and cells. Every option explicitly retains its original raw identifier. Unknown values receive a readable title-case fallback. Simulated Payment uses the actual `simulated_payment` source. Amounts use thousands separators, two decimal places, the original sign and explicit currency. Dates display in the selected merchant's business-local UTC offset; the original timestamp and business date remain available on the time element. Long identifiers truncate visually while full values remain in title/accessible labels. No stored value is transformed.

## Data Quality and Import Run History

The primary technical introduction is removed. A compact upper-right Lucide refresh icon retains the original refresh action, with accessible name, tooltip, disabled/loading state and reduced-motion support. Errors are shown, retries remain available, and successful refreshes clear previous error styling. No timer or background monitoring was added.

All ten existing metrics remain. Native keyboard-accessible information disclosures explain their actual backend scope. Examples: Successful Imports counts committed batches including zero-row duplicate-only imports; Failed Imports counts Failed, Validation Failed and Integrity Failed, excluding cancelled/expired runs. Rates use each retained POS run's latest validation; valid rows include eligible rows and exact duplicates. Reconciliation failures count source reconciliation failures. Unresolved Alerts includes Open and Acknowledged. The original formula is retained in **How Metrics Are Calculated**. Zero-denominator rates show N/A with an explanation. Current percentage display precision is preserved.

Import Run History paginates the returned snapshot locally at 10/25/50 rows, with independent state and a reset on Commit Status changes. Paging itself makes no new monitoring requests. Time and actor are separate columns; timestamps use the viewer's locale/timezone with the raw value retained in a title. Batch buttons show shortened IDs and retain full IDs and the existing drilldown. Commit status and quality status remain separate; warning/error styling follows actual status. Zero-row committed batches explicitly say no new transactions were imported.

**Existing backend limit:** monitoring returns at most the latest 100 matching runs and 100 alerts. The pager therefore labels its count **Returned Matching Runs**, with a visible cap disclosure; it does not claim to enumerate older runs. Summary metrics keep their full backend scope and are not recomputed from a visible page. Changing this cap or adding server run pagination would require a separate backend change.

## Shared design and accessibility

History and runs share `tablePager`, label/status/count helpers and wrapping `.import-actions` controls. Validation/preview retain their existing pagination and reuse the same action/table styling patterns; their behavior was regression-tested. Existing custom CSS/tokens provide Bootstrap-compatible forms and spacing; no Bootstrap package or new dependency was introduced. The refresh symbol extends the existing vendored Lucide sprite under its existing license ([official icon source](https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/refresh-cw.svg)). Tables scroll inside bounded regions on small screens rather than compressing dates/amounts. Long alert lists remain complete within a keyboard-focusable scroll region. Existing alert acknowledgement/resolution permissions and handlers remain unchanged.

## Files changed in this task

- `web/index.html`: responsive filters/tables, metric guides, refresh/header and scroll regions; existing header/Dashboard/import changes preserved.
- `web/merchant-transactions.js`: shared presentation helpers, history pagination, local run pagination, metric explanations, refresh states and merchant/request guards.
- `web/icons.svg`: vendored Lucide refresh symbol.
- `scripts/serve_four_role_ui_test.py`: opt-in synthetic history/run seeding in its temporary environment only.
- `scripts/verify_history_quality.cjs`: repeatable browser verification and screenshots.
- This guide, docs index and existing Merchant Transactions guide: current instructions.
- `evidence/history-quality/`: actual assessment and screenshots; Owner/Bank/import evidence was also refreshed by regression runs.

## Actual verification

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
