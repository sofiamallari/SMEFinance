# Digital Payments / Payment Sandbox — User Journey Scenarios

**Entry point:** /payment-sandbox. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 04-01: Standalone QR, Tap or Link sale

**Prerequisites:** Authorized simulate_payments action and sufficient tier.

**Pathway:** Enter amount → select method → review exact proposal → confirm → simulate customer payment → check status/history/reporting.

**Expected result / boundary:** Pending is not revenue; PAID records one canonical simulated sale. No real money moves.

## 04-02: POS cart checkout

**Prerequisites:** Authorized simulator access.

**Pathway:** Select products/quantities → review subtotal and demo tax → QR or Tap → confirm → simulate customer completion.

**Expected result / boundary:** Computed cart amount is proposed before creation. Clear resets cart, not saved transactions.

## 04-03: External-wallet payment link

**Prerequisites:** Authorized Pay Link simulation.

**Pathway:** Create and confirm Link → choose offered external e-wallet channel → simulate payment → review settlement.

**Expected result / boundary:** Sale is recorded, but external settlement adds zero to the internal sandbox wallet.

## 04-04: Cash at counter

**Prerequisites:** POS screen available.

**Pathway:** Choose Cash → read notice → encode cash activity through Single Transaction or POS Import if required.

**Expected result / boundary:** Cash button alone does not persist a cash sale.

## 04-05: Proposal or pending payment expires

**Prerequisites:** Synthetic request.

**Pathway:** Review expiry → attempt late confirmation/payment → create a fresh proposal when appropriate.

**Expected result / boundary:** Proposal expiry is five minutes; method pending windows differ. Expired requests do not become completed sales.

## 04-06: Repeated confirmation or uncertain result

**Prerequisites:** Known proposal/reference.

**Pathway:** Inspect existing state before retry → reconfirm same executed action when supported.

**Expected result / boundary:** Same executed confirmation returns saved outcome; a new proposal is a separate action. Paying an already-PAID request again is rejected.

## 04-07: Invalid amount or review-held payment

**Prerequisites:** Synthetic nonsecret inputs.

**Pathway:** Submit invalid or review-triggering data → inspect rejection/flags.

**Expected result / boundary:** No arbitrary release workflow is provided. Do not enter card numbers.

## 04-08: Refund request

**Prerequisites:** Existing simulated payment.

**Pathway:** Inspect supported backend capability and use documented accounting workflow as appropriate.

**Expected result / boundary:** No end-user linked-refund button or HTTP endpoint currently exists; do not present this as an executable UI pathway.

## 04-09: Read-only role tries payment

**Prerequisites:** Agent, Coach or administrator test account.

**Pathway:** Attempt a simulator write using a direct request or AI.

**Expected result / boundary:** Read/admin authority does not permit payment modification.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Digital Payments / Payment Sandbox guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
