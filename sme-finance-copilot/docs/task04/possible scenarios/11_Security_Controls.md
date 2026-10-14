# Security Controls and Configuration — User Journey Scenarios

**Entry point:** /admin/security. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 11-01: Review security overview/audit

**Prerequisites:** Authorized Security Administrator.

**Pathway:** Open Overview → Audit & Monitoring → filter actor/event/result/date → inspect recorded events.

**Expected result / boundary:** Indicators summarize recorded events, not a certified compliance/risk score; UI returns latest 500 matching records.

## 11-02: Change supported authentication policy

**Prerequisites:** Security Administrator with reauthentication.

**Pathway:** Authentication → adjust supported bounded values → Save → reauthenticate.

**Expected result / boundary:** Server validates ranges/relationships. Use isolated demo settings for scenario exercises, not shared production policy.

## 11-03: Reduce role permission or AI ceiling

**Prerequisites:** Security Administrator.

**Pathway:** Roles & Permissions or AI & MCP Controls → make permitted reduction → save → check affected role.

**Expected result / boundary:** Ceilings cannot exceed immutable role maxima; enabling action does not bypass merchant/grants/consent.

## 11-04: Export configuration

**Prerequisites:** Security Administrator.

**Pathway:** Configuration → export current JSON → inspect approved nonsecret settings → retain locally.

**Expected result / boundary:** Export is policy configuration, not users, sessions, individual consents, merchant ledger or provider credentials.

## 11-05: Validate, preview and import JSON

**Prerequisites:** Supported policy JSON and authorized administrator.

**Pathway:** Select JSON → Validate/Preview → review differences → explicitly apply/import → reauthenticate.

**Expected result / boundary:** Validation/preview alone does not save. Invalid or unsupported settings must be rejected.

## 11-06: Reject unsafe configuration

**Prerequisites:** Isolated synthetic JSON.

**Pathway:** Try out-of-bound role permissions, tier escalation or unsupported fields → read validation.

**Expected result / boundary:** No T4, admin financial access or merchant-authorization bypass can be enabled through portable configuration.

## 11-07: Consent policy information

**Prerequisites:** Security Administrator.

**Pathway:** Consent Policies → review explanation → Owner separately manages individual grants at /consents.

**Expected result / boundary:** This section is read-only; it does not grant consent on behalf of a merchant.

## 11-08: Unauthorized administration or MCP

**Prerequisites:** Controlled User Administrator/business account or unauthenticated MCP caller.

**Pathway:** Attempt security page/API or protected tool.

**Expected result / boundary:** Authentication and relevant permission remain required; API keys do not grant merchant authority.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Security Controls and Configuration guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
