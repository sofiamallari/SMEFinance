# Login and Account Recovery — User Journey Scenarios

**Entry point:** /login. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 01-01: Existing business user

**Prerequisites:** Active assigned business account.

**Pathway:** Sign in → select an authorized merchant → open an enabled module.

**Expected result / boundary:** Menus and backend access follow the saved role and scope, not a visible role selector.

## 01-02: New user first login

**Prerequisites:** Administrator has created an account with a temporary password.

**Pathway:** Sign in → complete Change password → sign in again.

**Expected result / boundary:** Password change invalidates prior sessions; use the new private password.

## 01-03: Forgotten password

**Prerequisites:** Authorized administrator can manage the target account.

**Pathway:** Administrator issues reset token → shares it privately → user selects administrator-issued reset option → sets a compliant password → signs in.

**Expected result / boundary:** Token is single-use and time-limited. It is not a password, API key or action approval token.

## 01-04: Expired or reused reset token

**Prerequisites:** Previously issued recovery token.

**Pathway:** Try the reset → if rejected, request a new token from the administrator.

**Expected result / boundary:** Rejected token does not reset the password. Do not delete the database to recover access.

## 01-05: Wrong password or unavailable account

**Prerequisites:** Synthetic test account; avoid intentionally locking a teammate out.

**Pathway:** Attempt sign-in → read failure → use authorized recovery if needed.

**Expected result / boundary:** Invalid credentials, restricted account status or lockout prevent access under current policy.

## 01-06: Session expiry or sign-out

**Prerequisites:** Signed-in user.

**Pathway:** Sign out or allow configured timeout → attempt a protected page → sign in again.

**Expected result / boundary:** Protected operations require a current session; merchant authorization is checked again.

## 01-07: Administrator versus business login

**Prerequisites:** Separate appropriately authorized accounts.

**Pathway:** Sign in as administrator for administration → sign out → sign in as Owner for business work.

**Expected result / boundary:** Administrative authority does not grant merchant financial access.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Login and Account Recovery guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
