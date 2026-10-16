# Digital Payments Simulator

Current implemented guide · 16 October 2026.

## Purpose

Demonstrate sandbox collection methods and checkout behavior.

## Access and prerequisites

Owner or Staff with delegated simulation permission and authorized merchant access.

## Navigation

Digital Payments Simulator (`/payment-sandbox`).

## Step-by-step instructions

1. Select the correct merchant.
2. Choose QR Pay, Tap Pay or Pay Link; enter the requested amount or select supported POS cart items.
3. Review the exact proposal and explicitly confirm creation.
4. Use the displayed sandbox customer-payment/status controls for the chosen method.
5. Inspect the payment state, amount, MDR fee and net settlement when paid.
6. Review the sandbox status and wallet only. Simulator activity is separate from recorded business transactions; record actual business activity through Merchant Transactions.

## Understanding results and statuses

Pending is not paid. Paid, cancelled, expired and failed states remain distinct. Fee and settlement use the existing maturity-stage MDR configuration. CNY cart tax is a documented zero-tax sandbox assumption.

## Common errors and troubleshooting

An expired or cancelled payment cannot be treated as paid. Integrity-review holds and amount/method errors must be reviewed, not bypassed.

## Important limitations

No real money moves. Successful, pending, failed and refunded simulator activity does not affect dashboards, cash-flow metrics, Financial Reviews, application amounts or canonical transaction totals. Dedicated simulator SQLite tables persist state and idempotency separately; old simulator ledger evidence is retained but excluded from financial projection. Zero sandbox tax is not Chinese VAT. POS Cash is a notice rather than a completed wallet collection. Existing backend-linked refund support is not a general end-user refund UI.

## Related guides

[Merchant Transactions](merchant-transactions.md) · [Dashboard and Business Overview](dashboard.md) · [Cash Flow](cash-flow.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
