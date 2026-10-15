> **Historical snapshot — superseded.** Use [current documentation](../../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# AI Financial Partner — scenario pathways

Entry: SME partner panel; Bank read-only form. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../4%20README_AI_Copilot.md); rules: [permissions](../../../technical/security-permissions.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 08-01: Financial evidence

**Path:** Ask permitted same-period sales/report/forecast question.

**Expected result / boundary:** Backend calculations and typed evidence, not model confidence, establish numbers.

## 08-02: Delegated Staff

**Path:** Give use_copilot plus needed financial read action → ask analysis.

**Expected result / boundary:** AI alone grants no data access; no Staff submission.

## 08-03: Bank analysis

**Path:** Owner grants category → Bank asks permitted read-only question.

**Expected result / boundary:** No general case required; packet status remains routed.

## 08-04: Missing/unsafe request

**Path:** Ask unavailable metric, real approval or out-of-domain request.

**Expected result / boundary:** Safe insufficient-evidence/refusal; no invented approval/cause.

## 08-05: Provider failure

**Path:** Run controlled synthetic failure/mocked tests.

**Expected result / boundary:** Deterministic fallback is not live Gemini verification.

## 08-06: Refresh/scope

**Path:** Change merchant/data or revoke access → ask again.

**Expected result / boundary:** Old replies do not update retroactively or authorize new data.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../implementation-notes/TESTING.md) for recorded evidence.
