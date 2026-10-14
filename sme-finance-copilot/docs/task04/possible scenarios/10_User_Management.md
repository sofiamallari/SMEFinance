# User Management — User Journey Scenarios

**Entry point:** /admin/users. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 10-01: Create business account

**Prerequisites:** Authorized User/Security Administrator.

**Pathway:** Create user → fields, role, active status, merchant memberships → private temporary password → Save → reauthenticate.

**Expected result / boundary:** New user must change password. Accounts are local; Git pull does not copy another installation database.

## 10-02: Authorize Staff selectively

**Prerequisites:** Staff assigned to intended merchants.

**Pathway:** Edit account → choose per-merchant entry/import/quality grants → Save → user signs in again as needed.

**Expected result / boundary:** Upload optional permission is derived by current form; backend still checks optional plus merchant grant.

## 10-03: Provision local demo Agent

**Prerequisites:** Authorized administrator in local demo environment.

**Pathway:** Create Financing Agent → organization/demo scope → only intended merchant → save → Owner consent workflow.

**Expected result / boundary:** No automatic production account creation; membership alone is not financing consent.

## 10-04: Owner requests Staff access change

**Prerequisites:** Owner manage-request capability.

**Pathway:** Consent page → Request a staff access change → administrator reviews request and edits account if appropriate.

**Expected result / boundary:** Request is not an automatic permission grant.

## 10-05: Reset password or revoke sessions

**Prerequisites:** Administrator authorized for target account.

**Pathway:** Find user → action → reauthenticate → privately deliver reset token or have user sign in again.

**Expected result / boundary:** Reset secrets must not appear in shared docs/Git. Recovery does not grant new merchant access.

## 10-06: Suspend, edit or reassign account

**Prerequisites:** Authorized administrator and legitimate reason.

**Pathway:** Find user → review details/history → edit status/role/membership → save.

**Expected result / boundary:** Affected sessions are revoked; changed authority applies on subsequent access.

## 10-07: Duplicate/invalid account

**Prerequisites:** Synthetic attempt.

**Pathway:** Try duplicate username/email, missing Agent organization or invalid memberships → correct validation.

**Expected result / boundary:** Invalid create/update is rejected; admin accounts cannot hold merchant memberships.

## 10-08: Privileged account boundaries

**Prerequisites:** User Administrator test account.

**Pathway:** Attempt privileged administrator changes or business financial route.

**Expected result / boundary:** User Administrator cannot manage privileged admin accounts; neither admin role automatically gains financial access.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing User Management guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
