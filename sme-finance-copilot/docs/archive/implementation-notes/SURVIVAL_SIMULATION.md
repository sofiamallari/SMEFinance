> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Task 03.1 — Financial Survival Simulation

Experimental, Owner-only decision support inside **AI Financial Partner → Survival Simulation**. It is not a forecast of bank-account cash, credit approval, or financial execution. The existing AI Chat remains a separate tab; no main navigation item is added.

## Enable or disable

Default: **disabled**. Set the existing allowlisted local `.env` configuration or a process environment variable:

```ini
FINANCIAL_SURVIVAL_SIMULATION_ENABLED=true
```

Restart the server and refresh the page. PowerShell alternative:

```powershell
$env:FINANCIAL_SURVIVAL_SIMULATION_ENABLED="true"
python -m copilot.server --host 127.0.0.1 --port 8000
```

To disable quickly, set the flag to `false`, restart and refresh. The simulation tab disappears, simulation endpoints return 404, and the browser makes no simulation requests. Ordinary Chat and other workflows remain available. No saved scenarios or database migration exists for this feature. The actual local `.env` and API key were not modified.

## Owner workflow

Open the existing AI drawer, select Survival Simulation, and review the Recorded Baseline and data limitations. Choose Monthly Sales Change (-80% to +50%, step 5%), Operating Expense Change (-30% to +80%, step 5%), and 1/3/6 months. Defaults are -20%, +10%, 3 months. **Run Simulation** is the explicit confirmation; opening the tab never runs a scenario.

The results show monthly operating surplus/deficit, change from baseline, cumulative operating result, baseline/scenario chart and grounded explanation. Changing an assumption marks the previous result stale. Reset Assumptions restores defaults. Values survive switching between Chat and Simulation during the current panel session; merchant switching clears all baseline/results and discards in-flight responses. State is temporary and is not placed in browser storage.

Supported percentage-based “what if” requests in Chat offer a Review Survival Scenario button. Common sales-drop and expense-increase phrases can prefill validated slider values; other assumptions stay visible for review. Ambiguous requests ask for clarification. This lightweight recognizer is not a general natural-language scenario parser and never runs a simulation automatically.

## Baseline and calculation contract

The isolated service calls the existing `financial_data.aggregate` for the latest three complete calendar months, relative to the server clock in the merchant's configured IANA timezone. Months with no eligible records are omitted rather than presumed zero. At least one observed month in that window is required. The actual months used, period, record coverage, currency, provenance and retrieval time are shown.

**Complete calendar period does not mean verified complete bookkeeping.** A single observed month or sparse records may be unrepresentative. No coverage-percentage threshold or assurance of source completeness was invented. No eligible observed month returns the insufficient-data state. Existing synthetic/completed sandbox activity is clearly labeled.

The existing ledger does not independently separate every capital, tax or financing expense. Its authoritative recorded expense total is a disclosed **operating-expense proxy**, not a claim of complete accounting operating profit. Existing completed-status, refund/reversal signs, source classification and duplicate controls are reused. Pending/failed/voided payments are not added. No new posting, synchronization or cross-source deduplication is introduced; unrelated POS/payment records cannot be proven to refer to different real sales by this simulation.

With `n` observed calendar months:

- Baseline monthly sales/expenses = sum of each authoritative monthly total / `n`.
- Baseline monthly operating result = baseline monthly sales − baseline monthly expenses.
- Scenario monthly sales = baseline monthly sales × (1 + sales change / 100).
- Scenario monthly expenses = baseline monthly expenses × (1 + expense change / 100).
- Scenario monthly operating result = scenario sales − scenario expenses.
- Monthly impact = scenario result − baseline result.
- Cumulative result at month `i` = rounded monthly result × `i`.

Decimal arithmetic rounds monthly monetary values to cents using the existing default decimal rounding convention. Currency and negative signs are preserved. Percentage assumptions remain constant without compounding. Month 0 is zero cumulative operating result, **not starting cash**. No cash-runway metric is produced.

## AI and fallback

The existing OpenAI-compatible/Gemini client receives only the authorized structured baseline, deterministic result and allowed statement registry. No tools are exposed. The model selects IDs of server-authored supported statements under Scenario Summary, Financial Impact, Potential Risks, Suggested Actions and Limitations. The server rejects unsupported/extra sections or IDs and requires the numerical impact and limitations. Arbitrary model prose and numerical claims are never displayed.

This is labeled **AI-assisted explanation — verified selection**, rather than unrestricted generated financial advice. If configuration is disabled, a provider call fails/times out (six-second limit), or verification fails, identical deterministic results remain available with an explicitly **rule-based** explanation. Actual business actions remain user-controlled; no records, financing applications, consent, payments or maturity scores are changed.

Live Gemini explanation generation was **not verified** during focused checks. Only the deterministic/fallback path was exercised; the existing configured client is reused without a new provider or credential.

## Authorization, APIs and audit

- `GET /api/survival-simulation/baseline?merchant=…`
- `POST /api/survival-simulation/run`, with `merchant`, `sales_change_percent`, `expense_change_percent`, `months`, `confirmed: true`.

Both require a live authenticated SME Owner, current merchant membership and existing `use_copilot`/`view_reports` permissions. Staff, Bank and System Admin are denied. Input ranges, finite values, five-percent steps, periods and confirmation are checked server-side. Financial-data versions and permissions are checked again before returning results. No new financial/administrative permission or AI write tool is introduced.

Existing audit records log requested/completed/failed operational events and merchant context, without storing scenario financial payloads, prompts, credentials or scenario history. Standard session/CSRF/origin handling remains in place.

## Focused verification

Passed using disposable data and normal server startup: eligible baseline excluding current partial month; exact deterministic decimal formulas/cumulative values; rule-based fallback label; invalid ranges, NaN, wrong steps/period and missing confirmation rejection; unrelated merchant denial; Staff/Bank/Admin denial; unchanged transaction/application/review/consent records; guided results/chart; Chat availability and slider preservation; stale warning; natural-language offer without execution; mobile panel width; disabled flag hiding the UI with no simulation requests; no browser JavaScript errors.

No new test suites were added. Full regression, extensive browser testing, independent bookkeeping-coverage validation and live Gemini verification were not run. Existing financial formulas and operational workflows were not modified.


## Current frontend presentation

The tab now uses the Business Stress Test presentation: compact baseline, segmented period controls, stale-result indicators, comparison chart, concise insight and expandable analysis/disclosures. Backend formulas and access rules below are unchanged. See [UI enhancement and focused verification](SURVIVAL_UI_ENHANCEMENT.md).
