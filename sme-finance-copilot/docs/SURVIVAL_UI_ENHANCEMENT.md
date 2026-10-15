# Business Stress Test — frontend enhancement

Implemented 2026-10-15 on `feature/security-sme-bank-workflow`, in `C:\Users\User\source\repos\SMEFinance\sme-finance-copilot`.

Only `web/index.html` and `web/survival-simulation.js` application files changed. The existing AI Financial Partner / Survival Simulation tabs, routes, feature flag and backend endpoints remain. No dependencies were added. Prior UI sources are in the private ignored `logs/backups/survival-ui-before-20261015` directory; hash checks confirm the simulator backend, security policy and shared currency files were unchanged. Existing uncommitted work was preserved and checked for concurrent changes before writing.

## Experience

- The shared drawer header, close control and tab bar stay outside the active content scroller. The simulation uses one vertically scrollable region, without nested chart/table scrollers.
- “Business Stress Test” introduces the compact “Your Monthly Baseline” card. Sales and expense figures are side by side when space permits, with the operating result below and an actual months-used badge. About Your Data contains periods, retrieval, source, provenance and coverage. Unverified bookkeeping/proxy warnings and limited-month warnings remain visible. Unavailable data disables Run.
- Adjust Your Scenario preserves -80..50 sales and -30..80 expense ranges, 5% steps, and -20/+10 defaults. Native radio buttons provide accessible 1/3/6-month segments, default 3. A hidden backing value preserves existing internal period/NLP prefill compatibility. Reset restores defaults and preserves existing results. Neither changing assumptions nor Reset submits a request.
- Results retain all three backend figures. Monthly result and change cards are side by side; cumulative result spans the row. Shortfall/surplus and improvement/deterioration have separate text labels. A positive but reduced surplus stays neutral; green is reserved for improvement relative to baseline.
- “Previous result · update to recalculate” identifies changed inputs while preserving the last graph. Completed-run assumptions remain visible. Failures retain the last result and show the existing status message; no financial action or write is introduced.
- “Baseline vs. Your Scenario” uses only backend projection points, with dashed gray baseline, teal scenario, markers, shared dynamic money ticks and focusable point labels/native titles. View Exact Monthly Values provides a text/table alternative for keyboard and touch users. Zero-domain padding affects chart layout only, not financial values.
- Compact business insight distinguishes operating sign from change versus baseline and displays up to two of the existing verified actions. Existing AI-assisted verified statements are preserved; fallback is identified as Rule-based guidance. Full Scenario Summary, Financial Impact, Potential Risks and Suggested Actions remain in Detailed Analysis.
- Assumptions & Limitations consolidates substantive baseline/explanation disclosures, with duplicate concatenation removed and existing rounding/no-compounding semantics retained. A concise synthetic-data disclaimer remains below. No synthetic-data or cash/credit limitations were removed.

## Focused verification

47 checks passed against a disposable database/journal copy, plus frontend JavaScript syntax checks. Coverage: all three periods, backend card/point matching, positive/negative results, positive-but-worse styling, explicit-only submission, stale graph retention, Reset, expanding details, all baseline limitations, fixed header/tabs, close accessibility, zero-series handling, dynamic currency rendering, 1440/768/390/320 widths, Chat preservation, unavailable baseline disablement and zero JavaScript page errors. Python Decimal checks matched every backend cumulative point. Active and disposable canonical ledger hashes remained unchanged.

Evidence: `logs/shenzhen_cny_demo/survival-ui/checks.json`, `desktop.png`, `results-desktop.png`, `768.png`, `390.png`, `320.png`. Screenshots were visually inspected. No new test suite was added; temporary verification helpers remain outside the application in the session workspace.

Limits: live Gemini was not exercised; the existing deterministic explanation path was verified with provider disabled. Native SVG hover/focus title behavior varies by browser; exact values are also available in the accessible table. Full regression and cross-browser suites were not run, as requested. No backend calculations, eligibility, authorization, merchant isolation, API contracts, feature flag, dataset, migrations, shared currency code or financial records were modified. No commit, push, merge or deployment was performed.

Refresh the browser to load the frontend changes. The existing `FINANCIAL_SURVIVAL_SIMULATION_ENABLED` flag still controls availability; the UI does not enable it or grant permissions.
