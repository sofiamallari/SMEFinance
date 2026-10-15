# Owner Dashboard tabs — hackathon POC

Branch: `feature/security-sme-bank-workflow`. Existing uncommitted work retained.
No commit, push, merge, reset, database migration or persistent demo-data changes.

## Completed and verified

- Dashboard contains Overview (default), Sales & Payments, Business Growth, Alerts.
  Tabs use accessible tab/panel roles, roving focus, arrow/Home/End keys and a
  horizontally scrolling tab strip on narrow screens.
- Overview: shared reporting controls, canonical net sales/expenses/net income,
  capture, original volume/revenue donuts, concise incentive and receivables highlights,
  and collapsible provenance. No frontend net-income formula.
- Sales & Payments: identical shared donut HTML/legends/colors/percentages, original
  count-bucket bar renderer and existing recorded-sales SVG trend renderer. Both use
  the same dashboard response. Wider trend content scrolls inside its card on mobile.
- Business Growth: original six maturity stages, actual backend stage name/composite,
  seven dimension values, next-stage gap and gate targets, highest-priority diagnosed
  constraint/intervention, collapsed assessment details. No Activation Plan UI; its
  backend logic is intact. Stage names match `config.STAGES` exactly (full labels).
- Alerts: original `cashflow_alerts` output, including returned messages/actual values,
  thresholds where present in messages, severities and recommended actions. No Data
  Quality alerts merged. Empty state says “No business alerts for the available assessment.”
- Financing sidebar contains only Overview, RBF Calculator, Applications. Overview
  has a compact maturity/credit-readiness summary from the same cached assessment.
- `/financing/progression` and `/copilot` safely map authorized Owner navigation to
  Dashboard → Business Growth. Backend five-step journey services, evidence, APIs,
  tests and stored records remain intact. No completion rules were added.
- Shared AI drawer remains accessible. Existing assessment AI answers expose stage
  and composite; arbitrary explanations of all seven dimensions are not newly added
  to its typed fact renderer. Existing forecast/risk tools remain unchanged.

## Data and security

`/api/dashboard` still supplies channel counts/shares, values/shares, trend buckets,
capture and authoritative canonical financial metrics. No new financial formula.
Assessment uses the existing authenticated MCP `assess_business` read tool; alerts
use existing MCP `cashflow_alerts`. They keep live PolicyGuard/RBAC, merchant checks
and audit. This avoids calling the composite `/api/cycle`, which also requires
unrelated financing/incentive capabilities and creates assessment-history snapshots.

Assessment results are cached per mounted merchant context and shared with Financing.
Alerts load on demand and remain cached until Refresh alerts or merchant change.
Refresh assessment explicitly reloads maturity data. Neither claims continuous monitoring.
Reporting filters apply only to the dashboard financial charts, not maturity or alerts.
Merchant change clears visible cached financial/assessment/alert content immediately;
request guards reject responses from a different merchant. Staff see an unavailable/
not-delegated message where their separate assessment or forecast grant is missing.

Current maturity and financing matching call the same canonical assessment service
with the same data date; a targeted test verifies matching stage agreement for two
merchants. Historical screenshot discrepancies cannot be independently reproduced
from screenshots alone. Different record snapshots or as-of dates can change scores;
no alternate scoring system was merged or thresholds changed.

## Definition conflict / known limitation

The existing API labels `mix.gross_revenue` with a legacy name, but canonical
projection replaces its total with recorded **net sales**, and existing channel
shares/trends include recorded refunds. Therefore Revenue Split and Revenue Trend
retain their actual original backend values and explicitly say net of recorded refunds.
An authoritative gross-processed channel split is **not implemented** by this task:
the existing API does not supply it. Relabeling net figures as gross would be incorrect.
True gross analysis needs a separately approved data-definition/API change.

The backend returns no numeric next-stage gap at stages 5/6; the UI shows its existing
graduation guidance rather than inventing an advancement target. Synthetic profile
inputs and maturity thresholds remain provisional POC rules, never credit approval.

## Targeted verification

- Python compilation: modified server/help files passed.
- JavaScript syntax: dashboard asset and extracted Owner inline script passed.
- `python scripts/run_isolated_regression.py --pattern test_dashboard_binding.py`:
  **7 tests passed**, no failures/errors/skips. Covers canonical metric/assessment/
  alert agreement, stage labels, matching agreement and Staff/Admin boundaries.
- `node scripts/verify_dashboard_tabs.cjs`: **42 focused browser checks passed**,
  isolated synthetic Owner fixture, no major browser JavaScript errors. Covers all
  tabs/charts, exact legends/score values, original alert messages, three Financing
  routes, legacy route compatibility, reporting filters, keyboard use, merchant
  changes including an active Growth pane, and desktop/tablet/mobile layouts.
- Financial formula/config files have no diff: assessment, dashboard, cashflow,
  matching, RBF, canonical financial aggregation and config were not changed.
- Financial calculations changed: **No**. Security rules changed: **No**.

Full backend regression, full browser regression, cross-browser testing, extensive
visual snapshots, performance benchmarks, unrelated imports and Admin tests:
**Not run — deferred due to time constraints.** Prior-task full-suite results are
historical and are not presented as a rerun for this restructuring.

Re-run browser checks with `COPILOT_TEST_PYTHON` pointing to the installed project
Python and `COPILOT_PLAYWRIGHT_MODULE` if Playwright is outside Node's normal search
path. Evidence: `evidence/dashboard-tabs/assessment.json` and screenshots in that folder.

## Files modified for this task

- `web/index.html`: tabs, panels, sidebar/legacy routes, responsive styles, merchant
  clearing and existing financing-response scope guards.
- New `web/dashboard-tabs.js`: composition, caching and existing tool/data bindings.
- `copilot/server.py`: serves the new JavaScript asset only.
- `copilot/partner_help.py`: current Business Growth navigation guidance.
- New `tests/test_dashboard_binding.py`, `scripts/verify_dashboard_tabs.cjs`.
- This reference and documentation index; generated focused-test/browser evidence.

Remaining work: resolve the gross-versus-net product definition with business approval;
run deferred wider tests when time permits. No new alert engine, AI write tool,
database schema, financing formula or journey completion rule is needed for the demo UI.
