# Security Administration and portable configuration

Security Administration remains at `/admin/security`, restricted to authenticated Security Administrators. Each team member keeps a local SQLite installation, its own accounts, and the existing JSONL transaction ledger. No central hosting or new identity system is introduced.

## Sections

| Section | Supported behavior |
|---|---|
| Overview | Existing recorded monitoring indicators, current policy summary and recent administration events |
| Authentication | Existing bounded session, lockout, password and reauthentication settings |
| Roles & Permissions | Role-level action matrix inside fixed role boundaries |
| AI & MCP Controls | Reduced T0–T3 ceilings, session/consent requirements and immutable T4 restrictions |
| Consent Policies | Read-only explanation of the existing owner-managed, category-specific consent model |
| Audit & Monitoring | Existing actor, event, result and date filters; configuration operation metadata |
| Configuration | Export, server validation, complete difference preview, cancel and confirmed atomic import |

The desktop sidebar stays visible while scrolling. At smaller widths, a labeled section selector replaces it. Buttons support normal keyboard navigation plus Up/Down/Home/End; the current section is announced. URL fragments restore a section without new application routes. Authentication, permissions and tier settings each have one editor; changes require password reauthentication. Existing User Management, `/consents`, AI/MCP and financial workflows remain independent.

## Team workflow

The designated security owner signs into their local installation, reviews policies through the first sections, and selects **Configuration → Export Configuration**. The download is named `security-config.json`. Share only that policy file after team review, never SQLite databases or credentials.

Other developers clone/update the repository, run the existing migration and first-administrator bootstrap commands, and sign into their own Security Administrator account. They select **Configuration**, choose the approved `.json`, then **Validate and preview**. The table shows every supported field's current/imported values and whether it changes. **Cancel** discards the pending selection without saving policy changes. **Apply Configuration** requests the administrator password and sends explicit confirmation of that validated preview.

The server binds each preview to its actor and session for ten minutes. A monotonic SQLite policy revision and a current-policy digest detect intervening changes, including a change that was subsequently reverted. Stale, expired, reused or substituted previews are rejected; validate again. A preview cannot be applied by another Security Administrator's session. A failed or cancelled reauthentication does not grant apply authority.

## Schema version 1

Required top-level properties are exactly:

- `schema_version`: integer `1`.
- `application`: `"sme-finance-copilot"`.
- `authentication`: all eight existing supported settings.
- `permissions`: action arrays for all six supported internal roles.
- `ai_tiers`: integer ceilings for all six supported internal roles.

See [the JSON schema](security-config.schema.json) and [safe default example](../examples/security-config.json). The example contains real default action assignments, including the retained coach role; it is not a team approval or an instruction to erase permissions. Coach assignment enablement is a local environment setting and is not exported. `demo_guest` is not a configurable authenticated role.

| Authentication property | Allowed value |
|---|---|
| `idle_timeout` | integer 300–3600 seconds |
| `max_session_lifetime` | integer 900–86400 seconds, at least the idle timeout |
| `failure_threshold` | integer 3–10 |
| `lockout_duration` | integer 60–3600 seconds |
| `password_min_length` | integer 12–128 |
| `password_require_mixed` | exactly `true`; immutable |
| `reset_expiration` | integer 300–3600 seconds |
| `admin_reauth_window` | integer 60–600 seconds |

Permission arrays must contain unique, supported actions within each role's fixed boundary. Essential Security Administrator actions (`manage_users`, `manage_security`, `view_security_audit`) cannot be removed. Individual staff upload grants, memberships and account roles are separate local records and remain mandatory. Administrator roles never gain merchant financial authority.

Tier maxima are owner T3, staff T2, lender analyst T1, coach T1 and both administrative roles T0. Reduced ceilings do not grant action permissions. T4, owner approval, merchant authorization, consent, authenticated MCP identity, password hashing and cookie protections remain immutable. Environment settings, API keys, secrets and filesystem paths are not portable policy fields.

Only nonempty `.json` files up to 64 KiB are accepted. The backend rejects malformed/deeply nested JSON, duplicate properties, non-finite numbers, unknown/missing properties, unsupported application/version, wrong types, unsafe ranges, unsupported roles/actions, role escalation and T4. Booleans are not integers. JSON Schema documents the supported format; backend validation also enforces the timeout relationship and immutable business rules. Error/audit messages do not echo unexpected imported fields or payload values.

## API

All operations use existing session authentication and Security Administrator authorization. Cookie-authenticated POST requests also require the existing CSRF token and same-origin protections. Legacy identity headers/API keys grant no configuration access.

| Method and path | Response / request |
|---|---|
| GET `/api/security/config/export` | Actual effective portable configuration; `Content-Disposition: attachment; filename="security-config.json"` |
| POST `/api/security/config/validate` | Body `{filename,content}` with JSON file text; returns validation status, single-use preview token, expiry, revision, complete differences and change count |
| POST `/api/security/config/import` | Body `{preview_token,confirmed:true}` only; returns success, changed flag/count and revision |

Import revalidates the stored preview inside the same transaction as authorization, stale checking, policy writes, revision update and success audit. The original `PATCH /api/security/policies` reuses the same validator/writer and increments the same revision, so section edits also invalidate stale previews. Recent administrator reauthentication is checked again in that transaction.

Statuses: 400 invalid file/schema/confirmation, 401 invalid session, 403 denied role/permission/CSRF/reauthentication, 409 stale/expired/reused/session-mismatched preview, 429 too many pending previews, 500 failed atomic application. A no-change import succeeds without changing the policy revision. Repeated imports through newly validated previews are idempotent; a consumed token cannot be replayed.

## SQLite and local data preservation

Migration `003_security_configuration.sql` adds only `security_config_state`, a singleton policy-revision counter. Existing migrations and account, session, membership, consent, financial and audit tables remain intact. AuthStore applies the migration at normal startup; restart the app after updating the code.

Successful import changes only supported global values in `security_policies`, role-level `role_permissions`, and the revision counter. `BEGIN IMMEDIATE` serializes changes and prevents races across connections. A failed write rolls back all policy/revision/success-audit changes before recording a sanitized failure event. No database reset or administrator recreation occurs. Policy values remain effective after restart, and existing AI/MCP calls recheck live policy.

Export and preview never change policy values or revision. The requested operation audit entries are still appended, and normal authenticated HTTP requests maintain existing session timestamps. These bookkeeping writes are not copies/resets of local records. Import does not change password hashes, assigned user roles, optional grants, memberships, consent, applications, JSONL ledger or JSONL audit/execution files. A shorter imported session lifetime can expire an older session on its next request; sign in again rather than bypassing that policy.

## Audit, verification and recovery

Recorded actions include `security_config_export`, `security_config_validate`, `security_config_import`, and an actual `security_policy_changed` when a configuration changes policy. Success, authorization denial, validation failure, stale import and transaction failure are recorded with actor/role, timestamp, request ID, reason code and schema version. Valid operations include a digest and non-sensitive change count. No full imported payload, credential, preview/session token or individual record is logged or exported. Existing hash chaining and audit filters remain in place. Rejected validation is a `failed` result; authorization/reauthentication denial is `denied`.

Before changing policy, retain an approved export. To recover, sign in as an active authorized Security Administrator, reauthenticate, preview that known-good file against current state, and apply it. Alternatively use the relevant existing section editor within enforced bounds. If a preview is stale, validate again. If the active account is locked, an appropriately authorized second administrator can use existing account controls; do not bypass authentication or edit credentials/security tables directly. Essential administrator permissions and safe ranges reduce lockout risk but do not replace operational recovery planning.

Run `python -m unittest discover -s tests -v`. New configuration tests cover schema/bounds, authorization, CSRF, preview binding/expiry/staleness, atomic rollback, idempotence, restart, independent installation portability, preserved local records, audit hashing and live AI/MCP enforcement. Tests use isolated temporary databases, including the server import fixture; the developer's identity DB/ledger are never opened. Optional Playwright with installed Edge: `node scripts/verify_security_ui.cjs`; it starts a disposable synthetic server on port 8124, exercises desktop/mobile behavior and writes synthetic screenshots. The existing authenticated UI regression is `node scripts/verify_auth_ui.cjs`.

Previews are held in memory, so restart invalidates pending confirmations; validate again after restart. Schema version 1 requires all supported roles/fields, rather than partial configuration files. Policy files are validated for safety and compatibility, not cryptographically signed or authenticated as team-approved. Review the file and its source with the designated security owner. There is no new global consent editor, environment-secret transfer, cloud service, real lending, centralized account sharing or production compliance certification. Automated findings remain preliminary until the team's security owner reviews the PR.
