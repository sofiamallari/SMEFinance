# Cash Flow User Guide

Current access rules: [four-role permissions](../SECURITY_PERMISSIONS.md). These user instructions use the current baseline; earlier dated results remain historical.

## Purpose and access

Open **Cash Flow**, route `/cash-flow`, to review estimated future balances and
rule-based alerts for the selected merchant. Authorized users need `view_forecasts`.
Staff need explicit forecast delegation. Bank sees forecasts through its review view under current forecast authorization; general forecasts do not require an application case. System Admin has no financial access.

## 1. Read the screen

1. Confirm the selected merchant and currency.
2. Review **Balance today**, **Lowest projected (30d)** and **Cash buffer**.
3. Read the stated forecast method and 30-day chart, including the zero-balance line.
4. Review alerts and their suggested actions; validate their assumptions.
5. Ask the AI partner for a forecast/buffer explanation and inspect ESTIMATED evidence.

| Display | Meaning |
|---|---|
| Balance today | Opening sandbox wallet balance, not verified bank cash. |
| Lowest projected (30d) | Minimum balance on the future modeled path. |
| Cash buffer | Opening balance divided by estimated average daily outflow. |
| Negative on day N | First modeled day whose balance becomes negative. |
| No alerts | No implemented rules triggered for these inputs; not a guarantee of financial health. |

## 2. Actual forecast calculation

The method uses **56 days (8 weeks) of weekday-seasonal averages**, including
zero-activity dates, plus scheduled financial items:

`future inflow = average sales for that weekday + scheduled receivable collections`

`future outflow = average eligible expenses for that weekday + due payables + debt service`

`balance today = previous balance + inflow - outflow`

Eligible variable expense categories are **supplies**, **operating** and
**household_draw**. Other categories can appear in recorded expense totals without
entering this particular forecast profile. Debt service is scheduled on day15.
Paid receivables are excluded; overdue collections are excluded by default.

The opening wallet combines synthetic base wallet with internal simulated
settlement. Manual/POS sales do not establish that those funds reached a bank/wallet.
The business-data date can differ from today's calendar date.

### Worked example

Opening1000, weekday sales200, receivable50, variable expense120 and supplier bill100:

`next balance = 1000 + 200 + 50 - 120 - 100 = 1030`

Cash buffer uses average variable outflow plus monthly debt service/30.
If wallet1000 and average outflow110/day, buffer rounds to9.1 days.
Zero estimated outflow gives an unavailable buffer, not infinite certainty.
The current screen may show `null days` for that unavailable case.

## 3. Existing alert rules

| Condition | Signal |
|---|---|
| First negative forecast day≤7 | Critical runway |
| Negative day≤14, not already critical | Low runway warning |
| Later negative day within horizon | Runway watch |
| Buffer<14 days and no negative day | Thin buffer |
| Last7-day sales drop≥20% from nonzero prior7 days | Sales-drop warning |
| Unpaid receivables overdue | Receivables alert; severity also considers age>30 days |
| Supplier bills next7 days>50% current balance | Obligations-due warning |
| Household draws>25% nonzero sales inflows | Funds-mixing warning |
| Cash sales share>60% | Cash-dependence information |

These thresholds are current provisional/demo rules, not certified lending-risk
or default criteria. An alert does not establish the underlying cause of a decline.
Recommendations are advisory; no bill, collection or financing action executes automatically.

## 4. Forecast versus revenue projection

Cash Flow forecasts a **balance path** using weekday activity and obligations.
The AI financial report's **30-day revenue projection** instead repeats recent
30-day net sales. These are distinct calculations, not matching numbers by design.
Revenue is not available cash, and net income is not settlement.

## 5. What users need to remember

- Forecasts are estimates; they do not guarantee sales or receivable collections.
- Synthetic balances, payables, receivables and debt assumptions can remain in the
  demonstration merchant profile even after importing real-looking synthetic POS rows.
- There is no general UI for maintaining all these underlying business assumptions.
- No-negative-day result means no negative day within this horizon, not permanent solvency.
- Use the source period/currency and ask again after imports/payments change data.
- Task03.1 Financial Survival Simulation is deferred. Borrow-versus-expense-cutting
  scenarios, automatic survival plans and real transfers are not implemented here.

## Prompts and troubleshooting

Try “Show my cash flow forecast”, “What is my cash buffer?” or “Show my financial
report” where permitted. If a report is denied to Staff, view_forecasts does not
automatically grant view_reports.

Unexpected chart: check dates, expense categories, synthetic obligations and
sandbox wallet assumptions. Access denied: check permission and any Agent consent.
Missing/unsafe evidence: treat the fallback as a request to review inputs, not invent balances.

## Implementation reference

UI: `web/index.html` (`loadCashflow`). Backend: `copilot/modules/cashflow.py`,
`copilot/financial_data.py`, `copilot/modules/reporting.py`. API: `GET /api/cashflow`.
No forecasts, obligations or production rules were changed to create this guide.
