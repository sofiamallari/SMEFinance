> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Security Administration implementation report

> Historical snapshot: retained for chronology and original evidence. Role, consent, menu, API and test instructions below may be superseded. Use [current documentation](../../README.md) for the four-role baseline.

Implemented directly in the local SMEFinance checkout on `feature/security-admin-config`. The feature is proposed for security-owner review; main is not merged.

## Architecture and files

The existing SQLite AuthStore, Principal/PolicyGuard, sessions, CSRF, role boundaries, consent, T0–T4 restrictions, and financial modules remain in place. Global policies already existed, so validation/writing was extracted for reuse rather than adding a new authentication system. Preview does not change policy/account/financial records; required audit entries and normal authenticated session timestamps still occur.

- `web/security.html`, new `web/security-admin.js`, and scoped `common.css` additions provide Overview, Authentication, Roles & Permissions, AI & MCP Controls, Consent Policies, Audit & Monitoring and Configuration. `admin.js` startup waits for page scripts before loading.
- New `copilot/security_configuration.py` implements schema-v1 serialization, strict JSON parsing, complete differences, bounded/session-bound previews, stale checking and confirmed import.
- `auth.py` reuses existing authorization inside SQLite transactions, shares policy validation/writing, records approved configuration metadata and retains generated digests exactly without PII phone masking.
- `server.py` adds the export/validate/import endpoints and protected page script, preserving existing authentication/CSRF/error conventions and auditing early request denials.
- Migration `003_security_configuration.sql` adds only `security_config_state`, a singleton monotonic policy revision. Original migrations and identity/financial records are preserved.
- Added `tests/test_security_configuration.py` and `scripts/verify_security_ui.cjs`. Existing browser assertions adapt to the new sidebar. The test package's server DB/ledger initialization now uses an isolated temporary directory.
- Added `docs/SECURITY_CONFIGURATION.md`, `docs/security-config.schema.json`, a safe full `examples/security-config.json`, verification evidence, onboarding links and refreshed packaging support.

No changes were made to financial calculation modules, transaction ledger implementation, agent orchestration, immutable security boundaries or MCP transport/authorization logic.

## API and schema

`GET /api/security/config/export` downloads actual effective supported global policy as `security-config.json`. `POST /api/security/config/validate` accepts only `{filename,content}` and returns all current/imported field differences and a ten-minute preview token. `POST /api/security/config/import` accepts only `{preview_token,confirmed:true}` and requires recent Security Administrator reauthentication.

Schema version 1 requires exactly `schema_version`, `application`, `authentication`, `permissions` and `ai_tiers`. All eight supported authentication settings and all six compatible roles are required. Unknown/missing fields, duplicate JSON keys/actions, unsafe types/ranges, excessive tiers, role escalation and T4 are rejected. Exports contain no identity records, credentials, tokens, memberships, consent, financial data, audit records or machine paths.

`BEGIN IMMEDIATE` covers final authorization, stale checking, revalidation, all policy/revision writes and success auditing. Failed writes roll back before sanitized failure auditing. Confirmation is single-use even for concurrent no-change requests. Repeated fresh-preview imports of identical policy do not alter policy or revision. Individual account grants/memberships and existing consent remain independent.

## Actual verification

- `python -m unittest discover -s tests -q`: **157 tests passed in 166.704 seconds**, including all 131 prior regressions and 26 configuration unit/integration/API/security tests. Tests used temporary SQLite databases and synthetic data; the developer's live identity database and transaction ledger were not opened.
- `node scripts/verify_security_ui.cjs`: passed after final backend changes. Verified all seven sections, keyboard/mobile navigation, authentication/permission/tier saves, real JSON download, complete differences, cancel, confirmed import, malformed/T4 rejection and audit filtering; no JavaScript errors or mobile page overflow.
- `node scripts/verify_auth_ui.cjs`: passed for the existing authenticated administrator/user/transaction/dashboard/consent/application-review workflows.
- Visually inspected desktop Overview and mobile Configuration evidence. `git diff --check` passed. Verified immutable authorization/MCP and financial module files have no diff.
- Additional tests include forced transaction failure, no partial writes, stale/reverted policy previews, expired/session-bound/single-use previews, concurrent confirmations, preview-capacity failure auditing, preserved users/sessions/consent/applications/ledger, independent-installation portability, restart persistence, exact digest metadata and valid audit hash chains.

## Limits and review

Previews are process-local and expire on restart. Version 1 requires complete compatible policy snapshots; it is not a generic database/settings importer. Files are validated but not cryptographically signed as team-approved. Obtain approval from the designated security owner before sharing/applying a policy. Existing monitoring/audit display windows remain bounded. Consent and MCP authentication requirements shown in their sections are read-only because no independent global editor exists. HTTPS/environment secrets remain installation-specific and are not transferred. Shorter imported lifetimes can expire older sessions on the next request without deleting them.

Automated security findings are preliminary until team review. This work does not add OAuth/MFA, cloud infrastructure, centralized accounts, real lending or payment processing, or multi-process JSONL transaction writes. See the configuration guide for authenticated recovery using an approved export and existing account controls.
