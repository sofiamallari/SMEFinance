# Dashboard User Guide

Current access rules: [four-role permissions](../SECURITY_PERMISSIONS.md). These user instructions use the current baseline; earlier dated results remain historical.

Current layout, operational workflow locations, chart limitations and actual verification: [Business Overview](../DASHBOARD_OVERVIEW.md).

## Purpose and access

Dashboard summarizes recorded financial activity for the selected merchant.
Open **Dashboard** or `http://127.0.0.1:8000/dashboard` after signing in.
SME Owners need assigned scope; Staff require explicit `view_dashboard` delegation. Bank has no SME Dashboard access and uses authorized Bank review summaries. System Admin and unmapped legacy roles have no financial access.

## How to use it

1. Confirm the merchant and currency in the header.
2. Select the reporting start/end dates and a granularity: daily, weekly, monthly,
   or quarterly.
3. Click **Apply**.
4. Review Recorded Net Sales, Expenses, Net Income and Digital Capture, the historical sales chart and Insights & risk awareness.
5. Expand Data Sources & Freshness for retrieval time, source counts and sandbox limitations. Payment activity and incentive details are in separate expandable sections.
6. To compare with chat, request recorded sales for the **same merchant and dates**.

## What the cards and charts mean

| Item | Meaning |
|---|---|
| Expenses | Completed recorded expense amounts in the selected period. |
| Net income | Recorded net sales minus recorded expenses; not a bank balance. |
| Recorded net sales | Completed sales less recorded refunds/reversals. |
| Digital capture | Net-sales channel mix across digital, ecosystem and cash activity. |
| Incentive milestone | Current calendar-based ecosystem-sales growth tier; not a paid reward. |
| Volume mix/trend | Sales/refund transaction activity grouped by channel/period. |
| Revenue mix/trend | Signed recorded sales grouped by channel/period. |
| Receivables insight | Existing demonstration signals distinguishing payment timing from repayment risk. |

## Calculations and a simple example

Completed sale 100, refund 25 and expense 20 produce:

- Recorded net sales: `100 - 25 = 75`.
- Expenses: `20`.
- Net income: `75 - 20 = 55`.

A pending or failed sale does not increase revenue. Expenses do not subtract from
the sales figure itself; they subtract when calculating net income.

Default display dates cover 90 days ending at the latest available business-data
date. The latest data date can differ from today. Incentives use their own calendar
windows, not the selected chart period.

## Things users must remember

- Sources can include synthetic seed history, imported POS, manual and simulated
  activity. These are not independently verified bank settlement records.
- Transaction History shows committed journal records. It does not list every
  synthetic seed entry included in the Dashboard.
- Dashboard volume uses sales/refund activity and legacy count weights. AI's
  completed count can also include expenses; compare definitions before calling
  a count difference an error.
- The legacy API field `mix.gross_revenue` represents recorded net sales. True
  source gross can be unavailable when only net amounts were supplied.
- Zero recorded sales means no recorded sales for that period, not proof that
  the real business earned nothing.
- Zero/negative net-channel totals may not support a meaningful pie. A note is
  shown instead; reconcile refunds before interpreting ratios or financing.
- An incentive display is an illustrative rule result, not cash credited to an account.

## Troubleshooting and related actions

| Situation | Check |
|---|---|
| Incorrect totals | Merchant, currency, dates, completed status, duplicate exclusions and refund representation. |
| Dates rejected | Start date must be on or before end date. |
| Import saved but not visible | Refresh; ensure the selected reporting dates include the imported records. |
| Dashboard and chat differ | Use the same dates and distinguish sales, expenses, counts and cash. |
| Access denied | Membership and enabled financial permission; admin role alone is insufficient. |

Use the available quick actions to import POS data, encode a transaction or try
simulated payments. Prior chat replies do not update retroactively; ask again after changes.

## Implementation reference

UI: `web/index.html` (`loadDashboard`). Backend:
`copilot/financial_data.py`, `copilot/modules/dashboard.py`.
APIs: `GET /api/dashboard`, `GET /api/financial-metrics`.
No application data or settings were changed to create this guide.
