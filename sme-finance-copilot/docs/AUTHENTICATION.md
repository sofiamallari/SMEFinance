# Authentication and security extension

## Preserved architecture and compatibility changes

The standard-library HTTP server, unified `web/index.html`, Principal/PolicyGuard, T0–T4 boundaries, owner approval tokens, consent concepts, audit mechanism and financial modules are retained. Existing transaction routes and JSONL ledger remain in place. Calculations in dashboard, cash flow, matching, assessment, RBF and payment simulation were not replaced.

HTTP/MCP identity comes from live SQLite sessions. Client demo headers, environment-selected identities and API keys never grant access. Four stored roles resolve to one policy; unmapped legacy roles are denied. Migration 007 is additive and preserves historical data while revoking sessions.

## Install, migrate and bootstrap

Requires Python 3.10+ with SQLite and OpenSSL scrypt support. No new third-party runtime dependency. Password hashes use scrypt (N=32768, r=8, p=1) with random 128-bit salts and constant-time verification. Passwords are never stored plaintext. Set environment variables through your shell/service; Only the four LLM keys auto-load from `.env`; other server/security/database settings require process environment configuration.

```powershell
cd "C:\Users\User\source\repos\SMEFinance\sme-finance-copilot"
python -m copilot.auth migrate
python -m copilot.auth bootstrap --username admin --email admin@example.com
python -m copilot.server --port 8000
```

Bootstrap prompts twice for a password, displays no password, and succeeds only when no user exists. Choose your own administrator username/email. No hardcoded production credentials exist. The test/browser fixtures create disposable accounts only, never default application users. If your Windows `python` alias is unavailable, use your installed Python executable; the bundled runtime in this workspace is `C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

Migrations in `copilot/migrations/` are applied in order, in a transaction, and tracked by filename in `schema_migrations`. They add users, memberships, optional permissions, sessions, reset tokens, login attempts, consent, role policy and audit tables, followed by application/review/staff-request tables. They do not read, move or rewrite the existing transaction ledger. Back up both the identity database and transaction ledger before deployment updates.

Defaults: `COPILOT_IDENTITY_DB=logs/identity.sqlite3`, `COPILOT_TRANSACTION_FILE=logs/manual_transactions.jsonl`. These paths are relative to your working directory. Keep them persistent and restrict filesystem access to the service account. Session and reset secrets are stored as SHA-256 digests. CSRF values are stored server-side and returned to the authenticated browser; browser session secrets stay in HttpOnly cookies and never in localStorage.

## Roles, delegation and Bank authorization

Use [Security and permissions](SECURITY_PERMISSIONS.md) for the authoritative model and [workflow](SECURITY_SME_BANK_WORKFLOW.md) to validate each role. System Admin provisions accounts; Owner delegates existing Staff and authorizes scoped Banks. Staff need explicit grants for reads, AI and drafts as well as writes. Bank general reads need current category authorization, not case assignment. Packets require explicit Bank selection and recipient routing. New Bank review mutations are denied.

## Security controls and audit

Security Controls exposes the allowed action matrix, authentication settings, reduced AI-tier ceilings, an audit viewer and monitoring. A permission can only be enabled inside its hard-coded role boundary. Global policy overrides individual staff grants. T4 is permanently denied before all other checks; neither UI configuration, AI prompts, API keys nor administrator roles can enable it.

Session idle timeout defaults to 30 minutes and absolute lifetime to 8 hours. Login failure threshold is 5, temporary lockout 15 minutes, minimum password length 12 with lowercase/uppercase/number, reset-token lifetime 30 minutes, administrator reauthentication window 5 minutes. Unsafe values and disabling password complexity are rejected. Sessions check account status, expiry and live permission/consent on every protected request/tool call. Reauthentication failures also lock out the account. Unlocking through account status `active` clears account/login-attempt locks and revokes old sessions.

Cookies are HttpOnly and SameSite=Strict. Set `COPILOT_HTTPS=yes` under HTTPS to add Secure. Do not trust proxy/client role, consent or forwarding headers as identity. Cookie-authenticated writes require `X-CSRF-Token`; cross-origin browser writes are rejected. Session Bearer clients use the same identity and checks without cookie CSRF. Most request bodies are capped at 4.1 MB; `/api/pos-import/stage` permits 14.1 MB for encoded uploads. Login/password-reset are the public JSON POST routes; static login styling and minimal health status are public.

The existing AuditLog format and SHA-256 hash chaining are reused for persistent SQLite audit events. Identity/security events contain only structured metadata (actor, role, merchant, action, target, result, reason and correlation ID). No passwords, sessions, reset tokens, transaction descriptions or raw uploaded rows are included. Financial tool calls retain the original audit/execution logs and add a safe event to the central audit. System Admin sees administrative metadata; Owner and Bank audit views are separately merchant/resource scoped. Audit filtering supports actor/action/result/target/time; latest 500 matching events are returned. Monitoring reports the latest 500 events in the last day. Hash chains are tamper-evident, not protection against a fully compromised database/service.

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
| GET `/api/applications?merchant=...` | Owner or authorized routed Bank packets; Staff use drafts |
| POST `/api/applications/{id}/review` | Denied legacy mutation; Bank review is read-only |

See [MCP_SETUP.md](MCP_SETUP.md) for authenticated HTTP and stdio clients. API keys alone grant nothing in authenticated mode.

## Verification and limitations

Use [isolated testing](TESTING.md), [current workflow](SECURITY_SME_BANK_WORKFLOW.md) and [known limits](KNOWN_LIMITATIONS.md). Older demo-browser scripts/reports are historical and do not provide current authenticated setup.

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


## Portable Security Administration

The existing Security Controls entry URL now provides seven sidebar sections and validated JSON policy sharing. See [SECURITY_CONFIGURATION.md](SECURITY_CONFIGURATION.md) for schema version 1, the additive migration, preview/reauthentication/atomic apply, local-data preservation, and team review/recovery guidance. Session/recovery infrastructure is retained; current Bank authorization, delegation and routing follow the four-role policy rather than the previous overlapping case rules.

Current delegation/draft/Bank API routes: [Bank review](BANK_FINANCIAL_REVIEW.md) and [Financing guide](task04/9%20README_Financing.md). Use [isolated verification](TESTING.md), not historical test counts in earlier reports.
