> **Historical snapshot — superseded.** Use [current documentation](../../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Login and recovery — scenario pathways

Entry: /login. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../1%20README_Login_Admin_User_and_Password_Reset.md); rules: [permissions](../../../technical/security-permissions.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 01-01: Existing account

**Path:** Sign in with saved credentials → follow role landing page → select permitted merchant.

**Expected result / boundary:** Current session, active account and effective permissions govern access.

## 01-02: Temporary password

**Path:** Sign in → change temporary password → sign in again.

**Expected result / boundary:** Password change invalidates sessions.

## 01-03: Recovery

**Path:** System Admin issues private token → intended user resets on login page.

**Expected result / boundary:** Used/expired/replaced tokens are rejected; no shared default password.

## 01-04: Unmapped legacy role

**Path:** Attempt Coach/demo_guest/restricted user_admin access.

**Expected result / boundary:** Denied pending explicit supported mapping, not an environment-enabled demo path.

## 01-05: Session invalidated

**Path:** Sign out, change delegation/role/status, or reach expiry → try a protected request.

**Expected result / boundary:** Sign in again; prior session cannot preserve revoked authority.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../implementation-notes/TESTING.md) for recorded evidence.
