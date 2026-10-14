# Financing — Overview, RBF and Applications — User Journey Scenarios

**Entry point:** /financing; /financing/rbf; /financing/applications. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 06-01: Explore indicative options

**Prerequisites:** Authorized view_financing and required merchant/consent scope.

**Pathway:** Overview → review ranked products/rationale → expand exclusions → ask AI what financing fits.

**Expected result / boundary:** Catalog matches and scores are not lender offers or approval probabilities.

## 06-02: Explore RBF quote

**Prerequisites:** Authorized financing access and positive supported sales basis.

**Pathway:** RBF Calculator → read eligibility → choose advance within displayed bounds → review fee, remittance and payoff scenarios.

**Expected result / boundary:** Eligibility checks and quote validation are separate. Quote does not prove eligibility or approval.

## 06-03: Not yet eligible

**Prerequisites:** Actual merchant fails existing eligibility checks.

**Pathway:** Read specific reasons → review source data/history through authorized modules.

**Expected result / boundary:** Do not invent milestones or manipulate data merely to show eligible. Calculator exploration may still be available.

## 06-04: Zero sales or unavailable payoff

**Prerequisites:** Synthetic merchant/input with limited own-rail activity.

**Pathway:** Review sizing and unavailable estimate/warnings.

**Expected result / boundary:** No-sales days have zero sales-linked repayment; repeated-history payoff is not guaranteed.

## 06-05: Owner submits RBF sandbox application

**Prerequisites:** Owner prepare/submit authority, T3 ceiling, current recipient consent and valid amount.

**Pathway:** Grant consent → request explicit supported application in AI → review exact proposal → Confirm exact simulated action → Applications.

**Expected result / boundary:** Only confirmed authorized action saves the sandbox packet. SUBMITTED_FOR_LENDER_REVIEW is not credit approval.

## 06-06: Missing consent or stale proposal

**Prerequisites:** Owner lacks applicable current consent, or data/session/expiry changed.

**Pathway:** Attempt request/confirmation → read denial → grant valid consent or request a fresh reviewed proposal as appropriate.

**Expected result / boundary:** No bypass; old or mismatched confirmation must not create an application.

## 06-07: Agent reviews assigned packet

**Prerequisites:** Active assigned Agent, current relevant consent and review permission.

**Pathway:** Sign in as Agent → Applications → Record simulated review → supported outcome and meaningful note → save.

**Expected result / boundary:** Supported outcomes: request_information, sandbox_recommended, sandbox_declined. Reviews are simulated and append separately.

## 06-08: Multiple Agents

**Prerequisites:** Multiple properly assigned and consented recipients.

**Pathway:** Inspect actual saved packet assignment → each Agent opens its authorized applications.

**Expected result / boundary:** Consent to multiple Agents does not make every packet visible to all Agents.

## 06-09: Revoked consent after submission

**Prerequisites:** Existing packet and Owner consent control.

**Pathway:** Owner revokes → Agent attempts fresh access/review.

**Expected result / boundary:** Consent-dependent access stops; historical packets/reviews remain. Previously seen information cannot be recalled.

## 06-10: Missing menu or prohibited action

**Prerequisites:** Staff/admin or user requesting real approval.

**Pathway:** Check actual role/scope; attempt controlled unauthorized request if testing.

**Expected result / boundary:** No real credit approval, disbursement or credit-limit change; T4 remains prohibited.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Financing — Overview, RBF and Applications guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
