# System architecture

Python standard-library ThreadingHTTPServer serves the existing static HTML/CSS/JavaScript UI, authenticated JSON routes and HTTP MCP. There is no replacement frontend framework or new banking engine. Python 3.12 is the documented deployment/runtime baseline; Babel and tzdata are runtime dependencies.

| Layer | Current components and responsibilities |
|---|---|
| Owner/Staff UI | web/index.html, merchant-transactions.js, transaction-settings.js, dashboard-tabs.js, financial-partner.js, survival-simulation.js |
| Bank UI | bank.html, bank-portal.js, bank-components.js, bank-views.js; three-module navigation and dialog tabs |
| Administration | shared admin-shell.html, admin/security/user/merchant page adapters |
| Transport/identity | server.py, auth.py, authorization.py, security.py; live sessions, roles, grants, categories, confirmation |
| Workflow | bank_workflow.py, partner_state.py; drafts, explicit routing and append-only simulated review |
| Canonical records | pos_extract.py, report_profiles.py, canonical_transactions.py, pos_import.py, transaction_journal.py, financial_data.py |
| Financial services | modules/dashboard.py, cashflow.py, assessment.py, matching.py, rbf.py, reporting.py, payments.py |
| AI | ai_agent.py, verified_agent.py, reliability.py, tools_spec.py, owner_partner.py, partner_help.py |
| Simulation | survival_simulation.py; optional Owner-only ephemeral operating scenario |
| Dataset/defaults | demo_environment.py, cny_demo.py, data/shenzhen_reference.json; fixed synthetic scenario generator |

SQLite holds users/sessions, memberships, policies, consent, import lifecycle, quality alerts, payment/wallet state, drafts, applications and review rows. SQL migrations 001–010 are tracked by filename; four-role policy migration also has its recorded marker. Canonical transactions are in a checksummed append-only JSONL journal. Synthetic seed history and eligible canonical rows form a projection; seed rows are not blindly reinserted into the journal. No distributed transaction spans SQLite plus JSONL; recovery/idempotency mechanisms and version checks reduce, but do not eliminate, cross-store risks.

Default active storage is logs/shenzhen_cny_demo resolved from the application location. Missing initialization fails closed. Railway requires an explicit persistent root. One process/replica is the POC topology; HTTP MCP is preferable to independent stale writing processes.

Owner Dashboard has four internal tabs. Maturity is in Business Growth, while the five-step financing journey backend remains preserved but hidden in normal navigation. Owner Financing has Overview/RBF Calculator/Applications. Bank has Overview/Financing Applications/Authorized Merchants; there is no Bank AI UI. All transport paths still enforce [one role policy](security-permissions.md).

Source entry points: [server](../../copilot/server.py), [canonical projection](../../copilot/financial_data.py), [dataset selector](../../copilot/demo_environment.py), [Bank workflow](../../copilot/bank_workflow.py). See [data model](data-processing.md), [algorithms](financial-algorithms.md), [AI](ai-safeguards.md) and [API contracts](api-contracts.md).
