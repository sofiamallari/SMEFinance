# Authentication and security extension

## Preserved architecture and compatibility changes

The standard-library HTTP server, unified `web/index.html`, Principal/PolicyGuard, T0–T4 boundaries, owner approval tokens, consent concepts, audit mechanism and financial modules are retained. Existing transaction routes and JSONL ledger remain in place. Calculations in dashboard, cash flow, matching, assessment, RBF and payment simulation were not replaced.

Three conflicts were resolved explicitly: client-selected demo identity cannot provide real authorization; environment-selected MCP roles cannot authorize authenticated callers; in-memory application records cannot provide persistent lender assignments. Default HTTP/MCP identity now comes from SQLite sessions. Explicit localhost demo mode preserves legacy tests and workflows. SQLite application packets supplement the existing approval workflow and calculations.

Internal role identifiers remain `owner`, `staff`, `lender_analyst` and `coach`. UI labels are Business Owner, Staff and Financing Agent. Added `user_admin` and `security_admin` have no merchant memberships or financial privileges. Coach is retained, with new assignments disabled unless `COPILOT_ALLOW_COACH_ASSIGNMENT=yes`. `demo_guest` cannot be assigned or authenticated.

## Install, migrate and bootstrap

Requires Python 3.10+ with SQLite and OpenSSL scrypt support. No new third-party runtime dependency. Password hashes use scrypt (N=32768, r=8, p=1) with random 128-bit salts and constant-time verification. Passwords are never stored plaintext. Set environment variables through your shell/service; `.env` is not automatically loaded.

```powershell
cd "C:\Users\User\source\repos\sme-finance-copilot-v1.2-transactions\sme-finance-copilot"
python -m copilot.auth migrate
python -m copilot.auth bootstrap --username admin --email admin@example.com
python -m copilot.server --port 8000
```

Bootstrap prompts twice for a password, displays no password, and succeeds only when no user exists. Choose your own administrator username/email. No hardcoded production credentials exist. The test/browser fixtures create disposable accounts only, never default application users. If your Windows `python` alias is unavailable, use your installed Python executable; the bundled runtime in this workspace is `C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

Migrations in `copilot/migrations/` are applied in order, in a transaction, and tracked by filename in `schema_migrations`. They add users, memberships, optional permissions, sessions, reset tokens, login attempts, consent, role policy and audit tables, followed by application/review/staff-request tables. They do not read, move or rewrite the existing transaction ledger. Back up both the identity database and transaction ledger before deployment updates.

Defaults: `COPILOT_IDENTITY_DB=logs/identity.sqlite3`, `COPILOT_TRANSACTION_FILE=logs/manual_transactions.jsonl`. These paths are relative to your working directory. Keep them persistent and restrict filesystem access to the service account. Session and reset secrets are stored as SHA-256 digests. CSRF values are stored server-side and returned to the authenticated browser; browser session secrets stay in HttpOnly cookies and never in localStorage.

## Account and consent workflow

1. Sign in as the first Security Administrator. Use User Management to create a User Administrator and separate business accounts. Business-facing accounts require merchant memberships; a Financing Agent also requires an organization or explicit sandbox organization name.
2. Administrator-created users must change their temporary password before financial, administrative or AI access. Password changes revoke all their sessions. Suspensions, status/role/scope/optional-permission edits and reset/session-revocation actions also revoke affected sessions.
3. Staff can encode transactions and view operational information only for assigned merchants. Bulk upload needs both enabled role policy and an individual `bulk_import` grant. Staff cannot access confidential assessments, financing recommendations, reports, applications, consent or administration.
4. Owners grant named-recipient consent at `/consents`, including purpose, permitted categories and expiration. Current owner role/status/membership is checked when the consent is used. Revocation/expiry blocks access immediately.
5. Owners submit a sandbox application through the existing Copilot approval-token workflow. The packet is assigned to the recipient selected by an active owner consent that includes `applications` (the first qualifying consent if several exist). Financing Agents need matching membership, an assigned application, enabled financing-data permission, action permission and consent for the requested category.
6. Assigned agents can record `request_information`, `sandbox_recommended` or `sandbox_declined` review outcomes. They are explicitly simulated and never constitute bank credit approval. Applications and reviews persist in SQLite. Staff access requests are recorded for administrators; they do not change permissions automatically.

User Administrators may maintain business accounts, but cannot create or modify administrative accounts, grant Security Administrator authority, or inspect merchant finances. Security Administrators can assign administrative roles and change bounded policy. Administrators cannot change their own role/scope/authority/status through User Management, and the last active Security Administrator cannot be removed through administration. Keep a second authorized Security Administrator for operational recovery.

## Security controls and audit

Security Controls exposes the allowed action matrix, authentication settings, reduced AI-tier ceilings, an audit viewer and monitoring. A permission can only be enabled inside its hard-coded role boundary. Global policy overrides individual staff grants. T4 is permanently denied before all other checks; neither UI configuration, AI prompts, API keys nor administrator roles can enable it.

Session idle timeout defaults to 30 minutes and absolute lifetime to 8 hours. Login failure threshold is 5, temporary lockout 15 minutes, minimum password length 12 with lowercase/uppercase/number, reset-token lifetime 30 minutes, administrator reauthentication window 5 minutes. Unsafe values and disabling password complexity are rejected. Sessions check account status, expiry and live permission/consent on every protected request/tool call. Reauthentication failures also lock out the account. Unlocking through account status `active` clears account/login-attempt locks and revokes old sessions.

Cookies are HttpOnly and SameSite=Strict. Set `COPILOT_HTTPS=yes` under HTTPS to add Secure. Do not trust proxy/client role, consent or forwarding headers as identity. Cookie-authenticated writes require `X-CSRF-Token`; cross-origin browser writes are rejected. Session Bearer clients use the same identity and checks without cookie CSRF. Request bodies are capped at 4.1 MB. Login/password-reset are the public JSON POST routes; static login styling and minimal health status are public.

The existing AuditLog format and SHA-256 hash chaining are reused for persistent SQLite audit events. Identity/security events contain only structured metadata (actor, role, merchant, action, target, result, reason and correlation ID). No passwords, sessions, reset tokens, transaction descriptions or raw uploaded rows are included. Financial tool calls retain the original audit/execution logs and add a safe event to the central audit. User Administrators see only account-related audit records. Audit filtering supports actor/action/result/target/time; latest 500 matching events are returned. Monitoring reports the latest 500 events in the last day. Hash chains are tamper-evident, not protection against a fully compromised database/service.

## API additions

All protected routes require a session and permission; successful account creation returns 201. Errors use 400 invalid input, 401 absent/invalid session, 403 denied permission/CSRF, 404 concealed merchant or missing resource, 409 conflict, 429 login rate limit.

| Route | Operation |
|---|---|
| POST `/api/auth/login` | `{username,password}`; session cookie, CSRF and must-change flag |
| GET `/api/auth/me` | Current user, permitted actions, CSRF |
| POST `/api/auth/logout` | Revoke session |
| POST `/api/auth/change-password` | `{current_password,new_password}`; revoke sessions |
| POST `/api/auth/password-reset` | `{token,new_password}`; consume issued token |
| POST `/api/auth/reauthenticate` | `{password}`; sensitive admin actions |
| GET/POST `/api/admin/users` | Search/filter or create account |
| GET/PATCH `/api/admin/users/{id}` | Details/history or account edit |
| POST `/api/admin/users/{id}/suspend` | Suspend and revoke |
| POST `/api/admin/users/{id}/revoke-sessions` | Revoke all account sessions |
| POST `/api/admin/users/{id}/reset-password` | Issue expiring single-use reset token; shown once to admin |
| GET `/api/admin/roles` | Assignable role labels and membership catalog |
| GET `/api/admin/staff-requests` | Staff access requests |
| GET/PATCH `/api/security/policies` | Bounded role/action/tier and authentication configuration |
| GET `/api/security/audit`, `/api/security/events` | Filtered audit and monitoring |
| GET/POST `/api/consents` | Owner consent listing/grant |
| POST `/api/consents/{id}/revoke` | Immediate consent revocation |
| POST `/api/staff-access-requests` | Owner request for administrative review |
| GET `/api/applications?merchant=...` | Owner or consent-authorized assigned-agent packets |
| POST `/api/applications/{id}/review` | Simulated assigned-agent review |

See [MCP_SETUP.md](MCP_SETUP.md) for authenticated HTTP and stdio clients. API keys alone grant nothing in authenticated mode.

## Verification and limitations

Run `python -m unittest discover -s tests -v`. The suite includes authenticated HTTP/MCP authorization and original financial regressions. Optional Playwright/Edge walkthrough: `node scripts/verify_auth_ui.cjs`; set `COPILOT_TEST_PYTHON` for your Python path. It starts a disposable fixture on port 8124. The older `verify_ui.cjs` uses explicit synthetic demo mode for legacy transaction browser checks.

This is an MVP, not a production certification. External IdP/OAuth integration, MFA, email delivery, refresh tokens and multi-process transaction writes are not implemented. Reset tokens are handed to an authorized administrator for secure out-of-band delivery. SQLite provides persistent local identity/security records, while transaction writes still use a single-process JSONL ledger and payment simulation state resets at restart. Database/ledger backups and restricted OS access are deployment responsibilities. The identity audit and transaction ledger are separate stores; they are not one distributed transaction. Staff have operational dashboard/forecast access, not configurable redaction within each existing operational response. Grant only memberships appropriate for those summaries.

Consent is implemented per individual recipient (organization name records affiliation); organization-wide blanket grants are not implemented. Owner application preparation and submission remain one approval-gated existing tool rather than a new draft workflow. Standalone MCP ledger data is a startup snapshot. Uploaded XLSX retains the documented single-sheet/values/ISO-date restrictions; no transaction export feature is added, so CSV export formula injection has no new export path. Externally generated AI prose is provider-dependent and is tested with a mock model; financial/tool permissions are enforced independently of model output. Synthetic financial data remains fixed at 2026-09-30, and no real money or bank approval is involved.


## Scripted first-administrator password

Bootstrap also supports `--password-env NAME`, which reads and removes the named variable from the Python process instead of prompting. It still validates the password, stores only its scrypt hash, and refuses bootstrap after the first account exists. No literal-password command-line option is provided.

```powershell
$env:COPILOT_BOOTSTRAP_PASSWORD = "REPLACE_WITH_YOUR_STRONG_PASSWORD"
try {
    python -m copilot.auth bootstrap --username admin --email your-email@example.com --password-env COPILOT_BOOTSTRAP_PASSWORD
} finally {
    Remove-Item Env:COPILOT_BOOTSTRAP_PASSWORD -ErrorAction SilentlyContinue
}
```

For automation, inject that variable from your secret store rather than writing the password into a committed script or `.env.example`. The original hidden prompt remains available by omitting `--password-env`.
