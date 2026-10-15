> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Digital Payments User Guide

Current access rules: [four-role permissions](../../technical/security-permissions.md). These user instructions use the current baseline; earlier dated results remain historical.

## Purpose and access

Open **Digital Payments**, route `/payment-sandbox`, for an authorized merchant.
Owners and permitted Staff need `simulate_payments` and sufficient AI/action tier.
Banks, System Admin and unmapped legacy accounts cannot use read/admin
authority to perform sandbox payments.

**This is a simulator. No real money moves.** The QR is a non-scannable visual
placeholder and the Payment Link is not a live payment-provider checkout.

## 1. Standalone payment

1. Confirm merchant and currency.
2. Enter a positive amount, such as 45000 for a suitable synthetic merchant.
3. Choose **QR Pay**, **Tap Pay** or **Pay Link**.
4. Review the exact proposed amount/currency/method. No payment exists yet.
5. Click **Confirm exact simulated payment**.
6. Inspect the created reference and **PENDING** status.
7. Use the displayed customer simulation control to complete payment.
8. Inspect **PAID**, fee/settlement information, then check history and financial reporting.

## 2. POS-integrated payment

1. Select catalog products; clicking again increases quantity.
2. Review the cart subtotal. Configured demo tax is added at checkout.
3. Choose **Pay by QR** or **Pay by Tap**.
4. Review and confirm the computed proposal, then simulate customer payment.
5. **Clear** resets the cart, not committed transactions/payment state.

The POS **Cash** button only displays a collect-at-counter notice. It does not
persist a cash transaction. Record actual demonstration cash activity through
Single Transaction or POS Import with payment method Cash.

## 3. Method behavior

| Method | What the user sees | Pending validity |
|---|---|---|
| QR Pay | Sandbox QR placeholder/payload and Simulate customer scan & pay. | 5 minutes |
| Tap Pay | Contactless instruction and Simulate customer tap & settle; no card-data collection. | 2 minutes |
| Pay Link | Sandbox URL and customer-channel choices: own-rail QR/card or external e-wallet. | 72 hours |

Proposal confirmation expires separately after five minutes. QR/Tap payment
channels must match their method. Pay Link supports its offered digital channels.
Use **Check status** for a pending request; expiry is checked by the backend.

## 4. Status and financial effect

| Status | Meaning/effect |
|---|---|
| PENDING | Created request, not revenue or received funds. |
| PAID | Completed simulation; one canonical sale is recorded. |
| EXPIRED / CANCELLED / FAILED | No completed sale. Some transitions are backend-only rather than UI buttons. |

Own-rail channels are QR Pay, Tap Pay and Pay Link. Ecosystem settlement is:

`merchant fee = round(payment amount × stage MDR rate, 2)`

`sandbox settlement = round(payment amount - merchant fee, 2)`

Example: amount1000 at0.6% MDR gives fee6 and internal settlement994.
An external payment channel records a sale but credits **zero** to this internal
sandbox wallet. External digital sales can still affect the general digital-share
signal; they do not contribute to own-rail incentive sales/RBF sizing basis.

POS tax/MDR parameters are demonstration assumptions, not approved real tax or
provider charges. Imported sales are not automatically wallet settlement.

## 5. Confirmation duplicate handling and recovery

Proposals bind exact parameters to user/session/merchant and current financial
version. Expired/stale/foreign proposals are rejected. Reconfirming the **same
executed action** returns the saved outcome; a new proposal is a separate action.
Trying to pay an already-PAID request again is rejected.

Canonical payment markers and SQLite payment/refund/wallet state persist locally
and support tested restart recovery. This is not a distributed banking guarantee.
For an uncertain action outcome, review its state rather than generating repeated requests.

## 6. Refunds and integrity flags

The backend supports capped, idempotent linked full/partial simulated refunds, but
there is **no current end-user refund button or HTTP endpoint**. Manual/POS Refund
entries reduce accounting sales without automatically refunding a payment or wallet.

Amounts must be finite positive exact cents, capped at one trillion. Card numbers
must not be entered. Large-ticket review flags can block simulated payment;
velocity/repeated-amount warnings are indicators, not proof of fraud. The current
UI does not provide a human-release workflow for a review-held payment.

## 7. Check with the AI partner

After completing a simulation, ask:

- “What happened to my latest simulated payment?”
- “Show recorded sales this month.”

Read reference, status, dates and simulated provenance. A historical answer is not
proof of a new payment; refresh after changes.

## Implementation reference

UI: `web/index.html` and `web/financial-partner.js`. Backend:
`copilot/modules/payments.py`, `copilot/partner_state.py`, `copilot/financial_data.py`.
APIs: `/api/partner/actions`, `/api/partner/actions/confirm`, `/api/payments/pay`,
`/api/payments/status`, `/api/pos/catalog`.
No payment/refund or policy change was performed to create this guide.
