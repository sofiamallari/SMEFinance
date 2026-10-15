> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# SME Finance Copilot

SME Finance Copilot v1.2 is the Shenzhen International FinTechathon POC for merchant transactions, recorded financial analytics, cash-flow estimates, AI financial guidance and simulated SME-to-Bank financing.

The application is in [sme-finance-copilot](../../../README.md). Its four authoritative roles are **SYSTEM_ADMIN, SME_OWNER, SME_STAFF and BANK**. Owners control their merchant's Staff delegation and Bank authorization; Banks receive read-only, category-scoped information and explicitly routed applications. Platform administration grants no financial access.

## Local setup

Requires Python 3.10+ with SQLite and scrypt support. Application runtime uses the standard library; Node/Playwright is optional for browser verification.

```powershell
git clone https://github.com/sofiamallari/SMEFinance.git
cd SMEFinance/sme-finance-copilot
python -m copilot.auth migrate
python -m copilot.server --host 127.0.0.1 --port 8000
```

On a completely new database only, bootstrap the first System Admin before starting the server:

```powershell
python -m copilot.auth bootstrap --username admin --email admin@example.test
```

Choose a private password at the prompts. Existing installations use their existing accounts; bootstrap is not password recovery. Open `http://127.0.0.1:8000/login`. Stop an older server before migrating; preserve private database/ledger backups. Role migration revokes existing sessions. Git transfers code, not accounts, passwords, local data or provider keys.

## Architecture and scope

The existing HTML/JavaScript workspace calls a standard-library HTTP backend. SQLite holds identities, sessions, grants, Bank authorizations, applications and audits; canonical transaction journals feed existing financial calculations. `Principal`, `PolicyGuard` and a single four-role policy enforce action, merchant, category and resource scope for APIs and AI tools. The Bank review service reuses these calculations and exports an audited CSV.

Merchant profiles may combine synthetic assumptions, imported/manual records and simulated payments. Forecasts and financing terms remain estimates/provisional POC rules. No real payment, lending approval or disbursement occurs. Five-step progression completion rules remain undefined; evidence does not imply completed stages.

## Documentation navigation

| Need | Read |
|---|---|
| All guides and historical material | [Documentation index](../../README.md) |
| Setup, migration, sessions and recovery | [Authentication](../implementation-notes/AUTHENTICATION.md) |
| Components, stores and processing flows | [Architecture](../implementation-notes/ARCHITECTURE.md) |
| Role/module matrix, delegation and authorization | [Security and permissions](../../technical/security-permissions.md) |
| Complete SME-to-Bank demo | [Business workflow](../implementation-notes/SECURITY_SME_BANK_WORKFLOW.md) |
| Bank review and export | [Bank Financial Review](../implementation-notes/BANK_FINANCIAL_REVIEW.md) |
| Transaction, payment, financing and AI user guides | [Module guide index](../task04/README.md) |
| Testing and actual evidence | [Verification](../implementation-notes/TESTING.md) |
| Pending decisions and security gaps | [Known limitations](../implementation-notes/KNOWN_LIMITATIONS.md) |

## Verification

Run from the application directory:

```powershell
python scripts/verify_four_role_workflow.py
python scripts/verify_four_role_workflow.py --full
```

The verifier isolates even server initialization from local application databases. The latest recorded implementation run passed **285 tests** and the synthetic browser journey; these are recorded results, not a new run caused by documentation edits. Live Gemini was not tested in that run. Use the linked testing guide for evidence and optional browser setup. Existing ZIP packages are historical exports and are not guaranteed to include current uncommitted changes.
