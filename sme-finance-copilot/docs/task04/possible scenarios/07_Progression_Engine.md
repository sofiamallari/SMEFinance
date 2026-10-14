# Progression Engine — Merchant Financing Journey — User Journey Scenarios

**Entry point:** /financing/progression. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 07-01: Review five-step journey

**Prerequisites:** Authorized financing access.

**Pathway:** Financing → Progression Engine → review Identify, Profile, Place, Activate, Measure.

**Expected result / boundary:** Accessible steps are Not Yet Assessed because completion rules are not implemented.

## 07-02: Follow linked modules

**Prerequisites:** Permission to each linked view.

**Pathway:** Identify → Cash Flow; Profile → Dashboard/History; Place → Overview; Activate → Applications; Measure → Cash Flow/Dashboard.

**Expected result / boundary:** Only permitted links are exposed. Page visits do not complete stages.

## 07-03: Ask AI about journey

**Prerequisites:** Journey and use_copilot access.

**Pathway:** Ask AI About My Journey → ask current stage/next action → follow up Why?.

**Expected result / boundary:** AI uses shared authorized provider and cannot determine a current stage without completion rules.

## 07-04: Step blocked

**Prerequisites:** Account can open journey but lacks a linked-view permission.

**Pathway:** Read Blocked explanation → ask appropriate administrator/Owner to review access.

**Expected result / boundary:** Blocked denotes access restrictions, not lending ineligibility.

## 07-05: Saved application appears

**Prerequisites:** Authorized saved simulated packet.

**Pathway:** Return to journey after confirmed submission → inspect Activate explanation.

**Expected result / boundary:** Saved packet may change explanation; submission does not mark Activate complete.

## 07-06: Refresh or merchant change

**Prerequisites:** Authorized merchant scope.

**Pathway:** Refresh route or change merchant → read current backend result.

**Expected result / boundary:** Journey derives from current scope/data; no persisted completion history is created.

## 07-07: Request automatic advancement or incentives

**Prerequisites:** User asks for unsupported milestones.

**Pathway:** Explain current limitations and separate existing business maturity/incentive displays.

**Expected result / boundary:** Five journey steps are distinct from six maturity stages. No new progression scores, incentive eligibility or approval rules exist.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Progression Engine — Merchant Financing Journey guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
