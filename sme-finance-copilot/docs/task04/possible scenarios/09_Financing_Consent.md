# Bank Authorization — scenario pathways

Entry: /consents. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../11%20README_Financing_Consent_and_Recipients.md); rules: [permissions](../../SECURITY_PERMISSIONS.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 09-01: Grant

**Path:** Owner selects active scoped Bank, purpose, categories and expiry → authorize.

**Expected result / boundary:** Authorization is account/category/time scoped.

## 09-02: Empty list

**Path:** No eligible Bank exists → inspect message → ask System Admin to provision scoped account.

**Expected result / boundary:** Submission disabled; do not expose unrelated/unmapped users.

## 09-03: Partial category

**Path:** Authorize reports only → Bank opens review.

**Expected result / boundary:** Only permitted sections appear; missing forecast/assessment stays unavailable.

## 09-04: No submitted case

**Path:** Authorized Bank reviews general permitted merchant information.

**Expected result / boundary:** Case assignment is not required for general reads.

## 09-05: Revoked/expired/changed Bank

**Path:** Revoke/expire grant or change Bank status/scope → request new protected access.

**Expected result / boundary:** Denied despite another valid Bank grant; prior downloads cannot be recalled.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../TESTING.md) for recorded evidence.
