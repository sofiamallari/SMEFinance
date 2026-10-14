# Financing User Guide

## Purpose access and submenus

Expand **Financing** for three implemented views:

| View | Route | Purpose |
|---|---|---|
| Overview | `/financing` | Indicative ranked financing/support options. |
| RBF Calculator | `/financing/rbf` | Explore advance, fee, repayment and estimated payoff. |
| Applications | `/financing/applications` | Saved confirmed sandbox packets and assigned reviews. |

Owners need enabled financing permissions for assigned merchants. Financing
Agents/legacy Coaches need current category consent and required scope; Agent
application assignment also applies. Staff financing is restricted. Administrator
authority does not grant financing access.

**Quotes, matches and reviews are simulations/advice, not real credit approval.**

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

## 3. Applications — Owner workflow

1. Use **Financing consent** at `/consents` to grant an active assigned Agent the
   necessary categories, purpose and expiry. Membership alone is insufficient.
2. Request an explicit supported RBF application in the partner, for example:
   “Submit my financing application for 10000000” — use an amount within this merchant's limit.
3. Review the exact proposal, selected merchant, currency, amount/product and expiry.
4. Click **Confirm exact simulated action** only when correct.
5. Open **Financing → Applications** to inspect the saved reference and assigned packet.

The current new confirmed workflow supports RBF applications. Proposal is not
submission. Confirmation needs Owner submit/preparation authority, current consent,
T3 approval, matching user/session/merchant and fresh financial version. Proposals
expire after five minutes. Changed data requires a fresh reviewed proposal.

The saved status **SUBMITTED_FOR_LENDER_REVIEW** means sandbox submission, not a
lender approval. Reconfirming the same executed action returns its saved outcome;
a new proposal can be a separate request. Uncertain execution needs review, not blind retry.
Multiple consented recipients do not imply every Agent can see every packet;
access follows the actual saved application assignment.

## 4. Applications — Financing Agent review

1. Sign out and sign in with the separate assigned Financing Agent account.
2. Select the permitted merchant and open **Applications**.
3. Click **Record simulated review** for the assigned packet.
4. Enter one supported outcome: `request_information`, `sandbox_recommended`
   or `sandbox_declined`.
5. Enter a meaningful review note and inspect the saved review.

Only assigned, currently consent-authorized Agents can review. Review notes are
required and limited to1,000 characters. Reviews append separately; they do not
convert the original packet status into real credit approval. AI application-status
answers report the saved submitted packet status, not an invented approval decision.

## 5. Consent revocation and boundaries

Owner consent covers specified categories and expires within the implemented limit.
Owners can revoke grants at `/consents`; new Agent access/reviews then stop.
Historical packets/reviews remain local records. Previously displayed information
cannot be recalled from someone's memory or an already captured screenshot.

No real lender submission, disbursement, credit-limit change, bank integration or
T4 approval is performed. Staff and administrators cannot bypass this through chat.

## 6. Common issues

| Situation | Check |
|---|---|
| Financing menu missing | Account role, enabled permission, tier, merchant scope and Agent consent/assignment. |
| Not yet eligible | Read actual reasons; do not interpret calculator exploration as eligibility approval. |
| Quote rejected | Positive amount, displayed maximum and reconciled channel/net-sales data. |
| No assigned applications | Owner must submit a confirmed packet; Agent must be its saved recipient. |
| Application request denied | Owner role, prepare/submit permissions, active consent and T3 ceiling. |
| Proposal expired or data changed | Request a new proposal and review exact parameters again. |
| Agent cannot review | Assignment, category consent, membership and review permission. |
| Payoff unavailable or excessive | Existing sales cannot repay within modeled limits; smaller size may help but is not guaranteed. |

## Implementation reference

UI: `web/index.html`, `web/financial-partner.js`, `web/consents.html`.
Backend: `copilot/modules/assessment.py`, `copilot/modules/matching.py`,
`copilot/modules/rbf.py`, `copilot/partner_state.py`, `copilot/auth.py`.
API families: `/api/match`, `/api/rbf/limits`, `/api/rbf/quote`, `/api/consents`,
`/api/applications`, `/api/partner/actions` and `/api/partner/actions/confirm`.
No financing/consent/application records or formulas were changed to create this guide.
