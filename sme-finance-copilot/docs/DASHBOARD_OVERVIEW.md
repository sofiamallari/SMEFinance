# Business Overview Dashboard

Branch: `feature/security-sme-bank-workflow`. Existing working changes are preserved. No commit, push, merge, reset or discard was performed.

## Layout and user workflow

Open Dashboard for an authorized merchant. The main heading is **Business Overview**. Set Start, End and Granularity (daily, weekly, monthly or quarterly), then Apply. The four primary cards are Recorded Net Sales, Expenses, Net Income and Digital Capture. Values continue to use the existing formatter and backend metrics. Cards use four columns on wide desktop screens, two through tablet/narrow desktop widths, and one at 600px or below, with equal padding and heights within each row.

Operational workflows remain in the existing sidebar: Merchant Transactions → Single Transaction or Bulk POS Import, and Digital Payments → existing simulator. No duplicate forms or workflows were added. The Dashboard action shortcuts were removed.

The historical trend uses only the existing `/api/dashboard` response's `trend` rows. It supports negative values and provides an expandable table and point titles containing exact formatted values. Its heading labels the reporting dates, granularity and currency. **The existing response has no expense time series**, so expenses remain a period-total KPI; no historical expense values are inferred.

Insights display the existing receivables classification/explanation and, when `view_forecasts` is allowed, alerts from the existing `/api/cashflow` endpoint with their severity and recommended action. The link opens existing Cash Flow. Cash Flow alerts are explicitly identified as the current assessment, independent of the historical reporting filter. A failed alert request shows a retry instruction rather than a healthy-state claim.

**Data Sources & Freshness** retains reporting dates, retrieval time, source counts and financial-data limitations, including synthetic seed/simulated-payment disclosures. The existing global synthetic-data footer remains. Payment mix, transaction volume trend and incentive milestone information are retained in expandable sections. Incentives remain calendar-based sandbox rules, not credit approvals or guaranteed rewards.

## Files changed for this task

- `web/index.html`: Dashboard markup, scoped styling, existing response rendering and historical SVG chart; read-only existing Cash Flow alert request.
- `scripts/verify_dashboard_overview.cjs`: focused isolated browser verification.
- This report, `docs/README.md` and the existing Task 04 Dashboard guide: current instructions and navigation.
- `evidence/dashboard-overview/`: actual screenshots and focused assessment. Existing Owner/Bank verifier evidence was refreshed by their regression runs.

No backend application file, financial formula, classification/reconciliation/import rule, permission policy, dependency or Bank UI was changed for this task.

## Actual verification

| Suite | Result |
|---|---|
| Focused Dashboard verification | 37 checks PASS |
| Existing Owner header/workflow regression | 48 checks PASS |
| Existing Bank portal regression | 84 checks PASS |

Focused checks exercised four granularities and an explicit reporting range, invalid date ordering, exact formatted KPI parity with backend responses, chart-point parity, accessible trend values, source/freshness/sandbox disclosures, Cash Flow navigation, real manual-entry save, POS validation/preview/explicit-confirmation commit, saved records feeding Dashboard sources, simulator access and absence of JavaScript errors. Responsive checks covered 1600px, 900px, 390px and 320px, expected card columns/heights and no page overflow. Screenshots were visually inspected and currency wrapping corrected.

[Assessment](../evidence/dashboard-overview/assessment.json) · [Desktop](../evidence/dashboard-overview/desktop.png) · [Tablet](../evidence/dashboard-overview/tablet.png) · [Mobile](../evidence/dashboard-overview/mobile.png) · [320px](../evidence/dashboard-overview/small-mobile.png).

Run `node scripts/verify_dashboard_overview.cjs` from the application directory. The script uses disposable synthetic users/data on port 8126 and requires Python, Node, Playwright and Edge. Optional runtime overrides: `COPILOT_TEST_PYTHON`, `COPILOT_PLAYWRIGHT_MODULE`. Run fixture scripts sequentially.

## Remaining limitations

Expense history is not supplied by the existing Dashboard API. Current Cash Flow alerts do not follow the Dashboard's historical date filter and are labeled accordingly. Chart text is compact on phones; the expandable values table provides exact readable amounts. Existing backend assumptions about incentives, receivables and synthetic data remain unchanged. Edge was tested; full backend regression and live Gemini requests were not rerun for this UI-only change.
