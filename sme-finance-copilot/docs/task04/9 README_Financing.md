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


## Financing Applications: drafts and Owner confirmation

The page heading is **Financing Applications**: “Manage your financing requests and track their review status.” The compact sandbox notice remains visible. Nothing on this page is a real credit approval, disbursement or payment.

1. Open **Financing → Applications** for the selected merchant. The responsive New Financing Application form supports only **Revenue-Based Financing**. Requested Amount uses the merchant currency from the existing merchant API, with readable ISO-currency formatting and a preview. Enter a positive decimal with at most two places, up to the existing draft limit of one trillion. The unchanged RBF quote/limit checks still run when proposing submission; the draft input limit is not an underwriting offer.
2. Choose **Bank for Review** from the existing active, merchant-assigned routing list. This is **routing**, not data-access consent. A Bank is optional when saving a draft under current backend rules. If no Bank is available, the UI explains that an unassigned draft can be saved but a Bank must be selected before submission. Unavailable historical recipients are not introduced as eligible selectable options.
3. Select **Save Draft**. Saving does not submit. Invalid/missing amounts show an accessible error without making a write request. Backend errors preserve the form/list and provide Refresh. Edit Draft opens a responsive native dialog; Cancel/Escape do not persist changes. Staff may create/edit only their own drafts with explicit delegated permissions. Staff cannot submit or fetch submitted packets.
4. The Owner must separately grant current authorization to the selected Bank at `/consents`, including the `applications` category. The page refreshes existing capabilities when loading; unavailable submission permissions/authorization are explained rather than implying that selecting a Bank grants access. Role policy, merchant membership, current authorization and selected recipient remain backend-enforced.
5. When available, the Owner selects **Review Submission**. The existing proposal API checks the selected Bank and RBF amount. A readable dialog shows the exact merchant, product, amount, Bank and proposal expiry. **Cancel** does not submit. **Confirm and Submit** is the explicit Owner action calling the existing session-bound confirmation endpoint. Data changes, expiry, stale drafts and authorization changes remain protected by the backend. No automatic retry or approval was introduced.
6. Submitted packets display **Submitted for Bank Review**, mapping the actual `SUBMITTED_FOR_LENDER_REVIEW` value. `DRAFT` displays Draft; linked `SUBMITTED` draft records retain Submitted where that is the only available data. A submitted packet and its linked draft are not duplicated for the Owner. Already-submitted drafts cannot be edited or resubmitted. Staff still see only the draft data supplied for their own records.

### Cards and View Application

Structured cards show Financing Type, requested amount, selected Bank label from the authorized routing response, actual status, available dates and a concise reference. Raw IDs are not primary headings. **View Application** shows the full reference, business fields, actual permitted actions, recorded submission/review events when returned, and collapsed Technical Details. The native dialog supports keyboard Escape, focus handling, a fixed heading/Close area and one scrollable body. Mobile form fields stack; identifiers and amounts wrap safely.

The current draft API does **not** return creation timestamps, update timestamps or a draft event history. These display Unavailable or “No lifecycle event history is supplied”; local browser time is not fabricated as a creation date. Submitted packets expose `submitted_at`, so the UI can show that actual event. Historical review rows are read-only evidence and do not add new decision functionality or alter the current packet status. Dates use the viewer’s locale/timezone. Historical Bank labels may be unavailable if that account is no longer in the current routing list; its existing recipient ID remains in Technical Details.

“No financing applications yet.” appears when the authorized response is empty, with a Create a Draft focus action only when permitted. A Refresh control reloads the existing APIs. Loading, write-in-progress and error states are accessible. Merchant changes clear the prior request context and close financial dialogs; stale responses cannot replace the newly selected merchant’s records. A refresh after a capability denial clears the protected application display. Draft creation/editing/confirmation retain existing audit mechanisms.

Bank sees only currently authorized packets routed to its identity through [Bank Financial Review](../BANK_FINANCIAL_REVIEW.md). Bank cannot create/edit SME drafts or make approval/rejection decisions. System Admin gains no financial access. Revocation blocks subsequent protected access without deleting history. General authorized AI financing analysis remains separate; chat cannot grant permission or bypass confirmation.

## Technical references

Existing calculation modules: `assessment.py`, `matching.py`, `rbf.py`. Scoped workflows: `bank_workflow.py`, `auth.py`, `partner_state.py`; UI: `web/index.html` and `web/financing-applications.js`. The HTTP server adds only an authenticated static asset route for that script; business APIs and calculations are unchanged.

Draft APIs: GET/POST `/api/financing-drafts`, PATCH `/api/financing-drafts/<id>`, POST `/api/financing-drafts/<id>/propose`. Supply `merchant` and the supported `draft` body for create/edit. Owner confirmation uses POST `/api/partner/actions/confirm` with merchant, action_id and confirmed:true. Submitted packets use GET `/api/applications`; Staff use drafts, not this submitted-packet API. Legacy POST `/api/applications/<id>/review` is denied.

[End-to-end demo](../SECURITY_SME_BANK_WORKFLOW.md) · [Progression guide](10%20README_Progression_Engine.md) · [Tests](../TESTING.md) · [Limits](../KNOWN_LIMITATIONS.md).

## UI verification and change inventory

Application files: `web/index.html` (heading, form/card/dialog styles, merchant-context hooks), `web/financing-applications.js` (dedicated presentation/controller), and `copilot/server.py` (serve the new static asset only). Tests: `scripts/verify_financing_applications.cjs` and existing `scripts/verify_four_role_browser.cjs` adapted to the readable HTML confirmation. No dependency, migration, financial formula, permission or new financing endpoint.

Run `node scripts/verify_financing_applications.cjs` with Playwright and installed Edge; configure `COPILOT_PLAYWRIGHT_MODULE` / `COPILOT_TEST_PYTHON` for custom runtimes. It uses the existing disposable four-role fixture on port 8126, so run browser scripts sequentially. Full backend verification uses `python scripts/run_isolated_regression.py`; set `COPILOT_BAO_WORKBOOK` for the actual workbook test. Evidence/screenshots are stored under `evidence/financing-applications/`. Persistent demo financial records are not modified.

Remaining limitations: no real lending decisions/funds, no new products, no draft timestamp/history fields beyond the current API, no invented missing Bank labels, and no inferred approval timeline. Draft amounts use the merchant currency supplied by the existing API; no FX or currency migration is performed.

### Financing Applications redesign — final executed results

Branch `feature/security-sme-bank-workflow`; baseline HEAD `7e36f57fd89bd1b5aa7528d8ed9a2b3258a09846`. Existing Transaction Settings, currency, report-profile and monitoring work is preserved. No commit, push, merge, reset or discard.

| Verification | Result |
|---|---|
| Full isolated backend regression with actual Bao workbook enabled | PASS — 346 tests, 0 failures, 0 errors, 0 skips |
| New Financing Applications browser suite | PASS — 62 checks |
| Existing four-role end-to-end browser workflow | PASS — provisioning, delegation, Owner authorization, Staff drafts, explicit submission, Bank review/charts/CSV/AI, revocation and isolation |
| Python compilation, new JavaScript syntax, Git whitespace checks | PASS |

The new browser checks cover five invalid amount cases without writes, ISO-currency formatting, exact routing choices, no submission on save/cancel, editing/cancelling, missing authorization, readable details, no invented dates/events, explicit Owner confirmation, unchanged packet amount/status, linked-draft deduplication, Staff/Bank backend denials, foreign-merchant denial, empty Bank routing, backend failures and no JavaScript errors. Screenshots and fit/no-overflow checks cover desktop 1600px, tablet 900px, mobile 390px and 320px. All accounts, consent grants, drafts, packets and financial records are disposable fixture data; production/demo records are untouched.

API reuse: GET `/api/capabilities` supplies live merchant permissions; GET/POST `/api/financing-drafts` and PATCH `/api/financing-drafts/<id>` handle scoped records and allowed Bank options; GET `/api/applications` supplies Owner-visible submitted packets; POST `/api/financing-drafts/<id>/propose` and POST `/api/partner/actions/confirm` preserve proposal/explicit-confirmation safeguards. Bank authorization continues through the existing `/consents` workflow. The only server change is serving `/assets/financing-applications.js`; restart the local Python server after updating that handler. No financing/RBF calculation or backend authorization logic changed.

Current evidence is in `evidence/financing-applications/assessment.json` and the responsive PNGs, with the full backend result copied into `evidence/financing-applications/backend-assessment.json`. No required check remains failed. Real deployment, external Gemini connectivity and real Bank credit decisions were NOT EXECUTED in this UI task.
