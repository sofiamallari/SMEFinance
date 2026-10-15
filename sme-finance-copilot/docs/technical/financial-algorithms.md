# Financial algorithms and provisional parameters

Source code, not historical screenshots, owns the math. Monetary inputs are CNY; presentation uses shared formatters. No FX conversion or legacy relabeling is implemented. All parameters below describe the POC, not institutional approval.

## Canonical reports

financial_data.aggregate applies existing completed/status and sign rules to synthetic history and canonical records. Sales contribute positive amounts; refunds/reversals reduce sales; expenses are normalized negative records and reported as positive expense magnitude. Pending/failed/voided records do not contribute completed value. Recorded Net Income = Recorded Net Sales − Recorded Expenses. This is a named recorded metric, not audited taxable profit, EBITDA or cash.

Financial reports carry merchant_id and currency; backend projection/report code remains authoritative. History lists canonical records; aggregate historical seed coverage is broader. Digital capture and own-rail capture are separate: own rails are QR/Tap/Pay Link, while other supported digital channels can contribute broader digital share. Settlement is not extra sales. See [financial_data.py](../../copilot/financial_data.py) and [dashboard.py](../../copilot/modules/dashboard.py).

## Cash-flow forecast

The last 56 days are grouped by weekday. Each weekday mean includes zero-record days in its denominator. Future inflow uses the matching weekday sales mean plus scheduled unpaid receivables; outflow uses supplies/operating/household-draw weekday means plus scheduled payables and debt service on day 15. Balance starts from the configured synthetic wallet and updates by inflow − outflow over the default 30 days. Overdue receivables are not assumed collected by default. Existing alerts use CASHFLOW parameters, including 7/14-day critical/warning buffer thresholds. This is a forecast, not a connected bank balance. See [cashflow.py](../../copilot/modules/cashflow.py) and [config.py](../../copilot/config.py).

## Maturity and incentives

Seven weighted scores use Financial Health .18, Formalization .12, Digital Maturity .15, Market Access .13, Operational Capacity .14, Credit Readiness .18 and Sustainability .10. Composite is their weighted sum rounded to one decimal. Lower composite bounds for stages 1–5 are 0, 35, 50, 65 and 78. Required dimension gates can downgrade the candidate stage.

Stage gates: stage 3 financial_health ≥45 and credit_readiness ≥40; stage 4 ≥60/55 plus operational_capacity ≥50; stage 5 financial_health ≥70, credit_readiness ≥65, market_access ≥60 and operational_capacity ≥65. Actual place_stage then chooses stage 6 when owner_transition_expected is true and the gated stage is at least 4. A config comment refers to a stage-5-level score: **this comment/code difference requires business confirmation; this documentation does not change the algorithm**.

Dimension factors and signal formulas remain in [assessment.py](../../copilot/modules/assessment.py); do not replace them with frontend arithmetic. Incentive thresholds in config are 15/30/50% own-rail month-on-month growth, with minimum-base-share safeguards. Rewards are provisional descriptions, not actual entitlements or loan approval.

## RBF

verified_monthly_sales uses 90-day history normalized to 30 days. Limits use own-rail monthly sales: minimum multiple .05 and maximum 1.5, with existing nearest-hundred rounding. Indicative flat fees are 14%, 12% or 10% by advance/monthly-sales tier, less applicable configured incentive discount. Remittance is min(.06 + advance/max_advance × .12, .18). Fee is rounded advance × fee rate; total repayable = advance + fee.

Payoff replays the actual last-90-day own-rail series cyclically, caps each day’s remittance at remaining obligation and uses the existing stopping/maximum-horizon rules. Eligibility includes minimum history 60 days, digital verified share .30 and on-time repayment ratio .85; a quote is not approval. Matching separately uses existing product/rule scores in matching.py.

Illustrative math only, not a merchant quote: own-rail monthly basis ¥10,000 gives max ¥15,000. Advance ¥5,000, no incentive discount, uses 14% fee = ¥700 and total repayable ¥5,700. Remittance rate is .06 + (5,000/15,000)×.12 = .10. A ¥100 day remits ¥10, subject to the remaining obligation cap. See [rbf.py](../../copilot/modules/rbf.py) and [matching.py](../../copilot/modules/matching.py).

## Sandbox payments

MDR_BY_STAGE is 0%, .3%, .6%, .8%, 1%, 1%. Successful own-rail fee and net settlement use existing cent rounding. CNY POS-cart tax is the central zero-tax sandbox assumption, **not Chinese VAT**. No real collection/disbursement occurs. [payments.py](../../copilot/modules/payments.py) is authoritative.

## Business Stress Test

Use eligible activity in up to the latest three complete calendar months; omit months with no eligible records rather than asserting zero sales. Average observed monthly net sales and expenses independently, using backend Decimal cent rounding. Simulated sales = rounded average sales × (1 + sales_change/100); simulated expenses analogous. Monthly operating result = simulated sales − simulated expenses; monthly impact subtracts baseline operating result. Month i cumulative value = rounded monthly result × i, including month 0 = 0. No compounding, seasonality, FX or cash runway is inferred.

Illustrative values: baseline sales ¥1,000 and expenses ¥700; -20% sales/+10% expenses gives ¥800/¥770, operating result ¥30 versus baseline ¥300, impact -¥270 and 3-month cumulative ¥90. These are examples, not injected records. See [survival_simulation.py](../../copilot/survival_simulation.py).
