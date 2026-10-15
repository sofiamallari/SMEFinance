> **Historical snapshot — superseded.** Use [current documentation](../../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Security Controls — scenario pathways

Entry: /admin/security. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../2%20README_Security_Controls_and_JSON_Configuration.md); rules: [permissions](../../../technical/security-permissions.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 11-01: Review/change bounded policy

**Path:** System Admin reviews sections → saves supported changes → reauthenticates.

**Expected result / boundary:** No financial access or T4 enablement.

## 11-02: Export/validate/preview/import

**Path:** Export current four-key policy → review → validate/preview → explicit apply.

**Expected result / boundary:** Preview does not save; local identities, delegation and Bank authorizations are not portable.

## 11-03: Old/unsafe JSON

**Path:** Try six-role or out-of-bound policy.

**Expected result / boundary:** Rejected; templates require current keys and supported actions.

## 11-04: Audit/access boundary

**Path:** Review administrative events; Staff/Owner/Bank attempt security API.

**Expected result / boundary:** Only authorized System Admin accesses platform security; merchant audit scope is separate.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../implementation-notes/TESTING.md) for recorded evidence.
