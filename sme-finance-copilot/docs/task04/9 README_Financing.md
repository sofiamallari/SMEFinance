# Financing — Overview, Progression Engine, RBF and Applications

Open Financing in the SME workspace. Its children are Overview (`/financing`), Progression Engine (`/financing/progression`), RBF Calculator (`/financing/rbf`) and Applications (`/financing/applications`). Owner uses assigned scope; Staff require explicit delegated actions. Bank receives authorized read-only counterparts through `/bank`, not these SME screens. System Admin has no financial access. See [permissions](../SECURITY_PERMISSIONS.md).

## 1. Overview

1. Confirm the selected merchant/currency.
2. Select **Financing → Overview**.
3. Review ranked products, provider type, rationale, match score and any indicative size.
4. Expand **Not yet eligible — what it would take** to inspect exclusion reasons.
5. Ask the partner “What financing fits my business?” if authorized.

The provider-neutral catalog contains financing and noncredit support options.
Stage/readiness filters apply before ranking. Some products also require eligible
RBF history, confirmed orders or open receivables. Matching uses existing constraint,
stage, readiness and affordability components:

`score = 0.45 × constraint fit + 0.25 × stage fit + 0.15 × readiness + 0.15 × affordability`

Example components100,100,80,60 produce91.0 points. The score is not an approval
probability or lender credit score. Synthetic operational/readiness attributes and
provisional catalog terms affect results; no live lender offer is retrieved.

## 2. RBF Calculator

1. Select **Financing → RBF Calculator**.
2. Read the eligibility message and monthly own-rail sales basis.
3. Move the advance slider within its displayed bounds.
4. Review advance, flat fee, total repayable, sales remittance and estimated payoff.
5. Review strong/typical/slow/no-sales examples and the fixed-installment comparison.
6. Read warnings and the indicative-only disclaimer before requesting an application.

### Actual implemented rules

- Own-rail/ecosystem channels: QR Pay, Tap Pay and Pay Link.
- Monthly basis: last90-day ecosystem net sales divided by90, multiplied by30.
- Displayed limits: 5% and150% of nonnegative monthly basis, rounded to nearest100.
- Eligibility checks: at least60 elapsed history days, positive recorded net sales,
  at least30% digital share and at least85% on-time repayment ratio.
- Digital-share eligibility includes external digital channels; repayment/sizing basis
  uses own-rail channels only.
- Flat fee tiers:14% at advance/basis≤0.5;12%≤1.0;10% above1.0.
- Current incentive Tier2/3 discounts:1/2 percentage points; values are provisional.
- Remittance: `min(6% + advance/max_advance ×12%, 18%)`.
- Daily repayment: nonnegative rounded own-rail daily sales × remittance, capped by remaining debt.
- Payoff cycles the last90 days of sales; it is not a prediction that those sales will repeat.

Eligibility and quote checks are separate. The UI permits exploration when
**Not yet eligible** is shown. Quote validates positivity/maximum but is not
underwriting or an automatic eligibility approval. Do not infer that a generated
application packet means every lending condition was approved.

### Worked synthetic example

Daily own-rail sales200,000 over90 days gives monthly basis6,000,000 and maximum9,000,000.
An advance3,000,000 with incentive Tier2 has fee rate13%, fee390,000 and total3,390,000.
Remittance is10%; a200,000 sales day pays20,000. At repeated daily activity,
payoff is170 days, with a final10,000 repayment; no-sales days pay0.

The replay stops at payoff or1,080 days. Warnings apply beyond540 days, with a365-day
target. Payoff can be unavailable. These are existing demonstration parameters;
fees are not a regulated APR disclosure and rounding is not an approved currency policy.


## Applications: drafts and Owner confirmation

1. Owner or draft-authorized Staff opens Applications and saves a valid RBF draft with amount and scoped Bank selection.
2. Staff can edit its own permitted drafts using Edit amount / Bank. It cannot submit; the UI and API enforce that restriction.
3. Owner reviews/edits merchant drafts and grants current Bank authorization at `/consents` when needed. The `applications` category is required for the selected Bank.
4. Owner selects Review submission proposal, checks exact merchant, amount, product, recipient and expiry, then explicitly confirms.
5. Inspect the saved `SUBMITTED_FOR_LENDER_REVIEW` packet and submitted draft state. This is a simulation, not approval.

Recipient selection is explicit; the first qualifying authorization does not choose it automatically. Missing/inactive/out-of-scope recipients, stale/expired/foreign confirmations or changed drafts are rejected. Already-submitted drafts cannot be edited. Existing idempotent exact-action confirmation remains in place; uncertain outcomes require review rather than blind retries.

Bank sees only currently authorized packets routed to its identity through [Bank Financial Review](../BANK_FINANCIAL_REVIEW.md). No recommendation/decline/approval mutation is supported; historical review records remain. Revocation blocks subsequent protected access without deleting history.

General financing analysis remains available to authorized AI tools. A submission request without an explicit selected Bank is directed to Applications; chat cannot grant permissions or bypass confirmation. No real funds move.

## Technical references

Existing calculation modules: `assessment.py`, `matching.py`, `rbf.py`. Scoped workflows: `bank_workflow.py`, `auth.py`, `partner_state.py`; UI: `web/index.html`.

Draft APIs: GET/POST `/api/financing-drafts`, PATCH `/api/financing-drafts/<id>`, POST `/api/financing-drafts/<id>/propose`. Supply `merchant` and the supported `draft` body for create/edit. Owner confirmation uses POST `/api/partner/actions/confirm` with merchant, action_id and confirmed:true. Submitted packets use GET `/api/applications`; Staff use drafts, not this submitted-packet API. Legacy POST `/api/applications/<id>/review` is denied.

[End-to-end demo](../SECURITY_SME_BANK_WORKFLOW.md) · [Progression guide](10%20README_Progression_Engine.md) · [Tests](../TESTING.md) · [Limits](../KNOWN_LIMITATIONS.md).
