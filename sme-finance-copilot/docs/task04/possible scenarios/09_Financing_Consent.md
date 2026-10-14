# Financing Consent — User Journey Scenarios

**Entry point:** /consents. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 09-01: Eligible recipient available

**Prerequisites:** Owner plus active assigned Financing Agent or legacy Coach.

**Pathway:** Select business → recipient → purpose → expiry → required categories → Grant consent → history.

**Expected result / boundary:** Grant is recipient/category/time scoped; save rechecks eligibility.

## 09-02: Empty recipient list

**Prerequisites:** No active Agent/Coach assigned to selected merchant.

**Pathway:** Read empty message → authorized administrator creates/assigns local demo Agent → Owner reloads matching business.

**Expected result / boundary:** Submission is disabled. Do not list unrelated users or weaken RBAC.

## 09-03: API unavailable or business switched

**Prerequisites:** Synthetic failure or rapid selection changes.

**Pathway:** Read loading/error state → retry by selecting business → confirm current recipient options.

**Expected result / boundary:** Loading/failure disables submission; stale merchant responses cannot replace current options.

## 09-04: Invalid expiry/categories/purpose

**Prerequisites:** Owner uses synthetic invalid input.

**Pathway:** Try invalid grant → correct reported field → resubmit.

**Expected result / boundary:** At least one supported category, purpose 1–250 characters and future expiry within 366 days are required.

## 09-05: Consent without application assignment

**Prerequisites:** Agent is member and recipient but has no required assigned packet.

**Pathway:** Grant categories → try Agent financial access.

**Expected result / boundary:** Consent alone does not replace Agent application assignment or role permission checks.

## 09-06: Revoke or expire

**Prerequisites:** Existing consent.

**Pathway:** Owner revokes with confirmation or grant expires → Agent attempts a fresh request.

**Expected result / boundary:** Consent-dependent access stops; historical records remain.

## 09-07: Recipient changed after loading

**Prerequisites:** Recipient suspended or membership removed by authorized admin.

**Pathway:** Owner submits previous selection.

**Expected result / boundary:** Backend rejects no-longer-eligible recipient; refresh rather than bypass checks.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Financing Consent guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
