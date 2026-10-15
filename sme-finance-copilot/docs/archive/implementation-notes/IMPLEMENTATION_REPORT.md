> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Implementation report — SME Finance Copilot v1.2

> Historical snapshot: retained for chronology and original evidence. Role, consent, menu, API and test instructions below may be superseded. Use [current documentation](../../README.md) for the four-role baseline.

Modified the existing application directly in `sme-finance-copilot`. The transaction module, financial calculations, payment simulator, merchant data and unified application remain in place.

## Phases delivered

1. **Authentication:** SQLite migrations, scrypt hashes, login/logout, server sessions, account-status checks, idle/absolute expiry, first-login password change, reset tokens, failed-login and reauthentication lockouts, HttpOnly/SameSite cookies, optional HTTPS Secure flag, CSRF and same-origin writes. Explicit CLI bootstrap, no production default credentials.
2. **User management:** dedicated page and API for search/filter, account creation/details/history/edit, roles and merchant assignments, staff upload grants, statuses/lock/unlock, reset issuance and session revocation. Independent administrator roles, no self-authority changes, no User Administrator escalation to Security Administrator, last active Security Administrator protection. Owner staff-access requests are recorded for administrator review.
3. **Security controls:** dedicated permission matrix, bounded authentication settings and T0–T3 ceilings, permanent T4 denial, persisted hash-chain audit records, filtered audit viewer and monitoring. Individual, category-specific, expiring/revocable owner consents and assigned sandbox financing applications/reviews.
4. **Integration:** session-derived HTTP and MCP principals, ignored production demo headers/environment identities/API keys, live action/scope/consent checks on financial and AI calls. Original transaction routes and JSONL persistence preserved; owner entry/edit/delete and explicitly granted staff imports remain integrated with dashboard/cash-flow/reports. Original approval-token workflow creates persistent sandbox application assignments. Existing HTTP/MCP regressions now authenticate where applicable; legacy demo-key tests explicitly opt into demo mode.

## Changed files

- Added `copilot/auth.py`, `copilot/authorization.py`, and two SQL migrations.
- Extended `security.py`, `server.py`, `agent.py`, `ai_agent.py`, `mcp_server.py`, `tools_spec.py`, and transaction authorization/auditing.
- Added `web/login.html`, `web/users.html`, `web/security.html`, `web/consents.html`, common styling and shared administration helpers; extended the existing `web/index.html` with authenticated identity, permission visibility, consent navigation and application review.
- Added authentication fixtures/tests and optional disposable browser verification; migrated existing HTTP/MCP tests.
- Updated README, environment example, client examples and MCP/transaction documentation. Added packaging script and this report.

## Validation executed

- `python -m unittest discover -s tests -q`: **129 tests passed**, including all 103 existing financial/transaction regressions and 26 authentication/security tests. Final full-suite run: 138 seconds on the bundled Windows Python runtime.
- `node scripts/verify_auth_ui.cjs`: passed in headless Microsoft Edge. Verified administrator login, security-policy saving with password reauthentication, account creation, forced password change, staff transaction entry and disabled uploads without an individual grant, dashboard rendering, owner consent, existing approval-token submission, assigned Financing Agent simulated review, consent revocation and immediate financing-data denial. No JavaScript page errors.
- Visually inspected User Management and Security Controls screenshots; saved browser evidence also includes authenticated dashboard and financing review.
- Source compilation passed. ZIP packaging checks required authentication/migration/page/test files and archive integrity, excluding all runtime databases, credentials, local/test logs and generated UI ledgers.

## Material limits and unfinished production work

External IdP/OAuth, MFA, email delivery, refresh tokens and automated client-login adapters are not implemented. Password reset delivery is an administrator-mediated MVP. HTTPS requires external TLS deployment and explicit `COPILOT_HTTPS=yes`. SQLite identity/audit and the existing JSONL transaction ledger are separate stores; no multi-process or cross-store transaction guarantee is claimed. Standalone stdio MCP uses a startup ledger snapshot; use the running app's HTTP MCP for live transaction data.

Consent is per named individual; organization-wide blanket consent and multi-recipient application routing are not implemented. The first qualifying active owner consent selects the application recipient. Preparation/submission uses the established single approval-gated tool rather than a new draft workflow. Staff receive existing operational dashboard/forecast summaries, with confidential assessment/report/financing tools denied; configurable field-level redaction is not implemented. Audit viewer/monitoring limits are documented. Live external AI providers were not tested; model integration is verified against a mock endpoint. Existing synthetic date, XLSX restrictions, advisory projections and sandbox payment/financing limits remain.

No real payment processing, credit approval or disbursement was introduced. See [AUTHENTICATION.md](AUTHENTICATION.md) for installation, APIs and security boundaries.

## Scripted-bootstrap follow-up

Added optional environment-sourced bootstrap password support, documented in AUTHENTICATION.md. Two additional CLI tests passed: a password is hashed without being printed, and a missing environment secret creates no account. The suite now contains 131 tests; the prior 129-test full run plus the two focused follow-up tests passed.
