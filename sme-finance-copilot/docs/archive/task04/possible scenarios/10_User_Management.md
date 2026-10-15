> **Historical snapshot — superseded.** Use [current documentation](../../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# User Management — scenario pathways

Entry: /admin/users and /owner/users. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../3%20README_User_Management.md); rules: [permissions](../../../technical/security-permissions.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 10-01: Platform provisioning

**Path:** System Admin creates canonical-role accounts and appropriate memberships.

**Expected result / boundary:** Bank membership alone grants no financial access.

## 10-02: Owner delegation

**Path:** Owner selects assigned Staff and per-merchant actions → Save.

**Expected result / boundary:** Only owned merchant grants change; affected Staff signs in again.

## 10-03: Owner provisioning request

**Path:** Request account/membership creation from System Admin.

**Expected result / boundary:** Owner has no platform provisioning; membership approval rules remain pending.

## 10-04: Protected/legacy account

**Path:** Try self-authority edit or unmapped-role login.

**Expected result / boundary:** Safeguards remain; explicit supported-role review is required.

## 10-05: Recovery/status

**Path:** System Admin issues reset/revokes sessions/changes status.

**Expected result / boundary:** Private recovery secrets and session invalidation remain enforced.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../implementation-notes/TESTING.md) for recorded evidence.
