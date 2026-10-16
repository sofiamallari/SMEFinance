# SME Finance Copilot

Synthetic CNY financial-management and SME-to-Bank review POC for the Shenzhen International FinTechathon. The existing Python/static-web architecture is preserved. This is not a live payment service or credit approval engine.

## Start locally

Use Python 3.12 from this application directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# First-time source-only ZIP/clone: follow the private-password seed procedure below.
.\.venv\Scripts\python.exe -m copilot.cny_demo verify
.\.venv\Scripts\python.exe -m copilot.server --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/login. A source-only download normally excludes initialized logs: **seed before verify/start**, using [the complete setup guide](docs/operations/local-setup.md). Existing initialized copies use their matching assigned credentials. Bootstrap is not a password reset. A preparer-specific credentials JSON file is private and not guaranteed on another machine; the supported CLI uses the seed password supplied by that recipient.

## Modules and architecture

Owner/Staff workspace: Dashboard (Overview, Sales & Payments, Business Growth, Alerts); Merchant Transactions (single, CSV/XLSX import, history, monitoring, settings); Digital Payments; Cash Flow; Financing (Overview, RBF Calculator, Applications); existing AI Financial Partner and optional Owner-only Business Stress Test. Owner also manages Bank Authorization and delegated Staff access.

Bank portal: Overview, Financing Applications, Authorized Merchants, with request/financial/review/history dialog tabs. System Admin: accounts, merchant profiles and bounded security configuration, without merchant financial authority. Current simulated Bank outcomes never approve/reject or disburse financing.

The standard-library HTTP server serves the static UI, JSON API and authenticated MCP. SQLite stores identity, scoped policy and workflow/payment state; checksummed JSONL stores canonical transactions and audit/execution evidence. Active default storage is logs/shenzhen_cny_demo. Missing initialization fails closed. Shared formatting uses CNY codes and ¥ display; original foreign-currency evidence is inactive in private backups.

## Documentation

- [AI Financial Partner 2.0: local governance, tool contracts and limitations](docs/technical/ai-governance.md)

- [User guides](docs/user-guide/README.md)
- [Canonical roles, delegation and Bank consent](docs/technical/security-permissions.md)
- [Architecture and financial algorithms](docs/technical/README.md)
- [Setup, environment, recovery and Railway preparation](docs/operations/README.md)
- [Hackathon overview, six scenarios and end-to-end journey](docs/hackathon/README.md)
- [Evidence and verification scope](docs/hackathon/evidence.md)
- [Known limitations](docs/technical/known-limitations.md)
- [Historical archive](docs/archive/README.md)
- [Full documentation navigation](docs/README.md)

Do not publish .env, API keys, session/reset tokens, credential files or private DB/backups. Seed code and reviewed synthetic examples can be distributed; recipients initialize their own password. General storage/hosting variables require process/service configuration; only the supported LLM/feature allowlist auto-loads from .env. Runtime dependencies are in requirements.txt. Node/Playwright are optional verification tools.

Financial/security parameters are a provisional POC baseline. No live cash/bank verification, lending decisions or guaranteed forecasts. Docker build/volume permissions, secure hosting and provider availability remain separate deployment checks; nothing is deployed by this documentation consolidation.
