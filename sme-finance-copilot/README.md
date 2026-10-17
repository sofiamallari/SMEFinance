# SME Finance Copilot ("Shifu")

An AI financial partner for small-business owners, built for the Shenzhen International FinTechathon (International Track, Topic E: SME Finance Copilot).

Shifu combines a small-business finance workspace (dashboard, transactions, digital payments, cash-flow forecasting and alerts, financing matches and an RBF calculator) with an **AI Financial Partner** chat. The chat answers questions and models decisions such as "Can I afford to hire two staff from December?" or "Should I expand now, reduce the budget or postpone?" using only the business's own authorised, read-only data. Google Gemini interprets the question and words the reply; the Python backend owns identity, permissions, every financial figure, every calculation and the final verification of each answer.

- **Repository:** https://github.com/sofiamallari/SMEFinance
- **Data:** a synthetic CNY dataset with six merchants (M001 to M006). Payments and bank reviews are simulated; nothing moves real money or makes a credit decision.
- **Roles:** business owner, staff (delegated access), bank (consent-scoped) and system administrator.

## Quick start

Python 3.12, from this folder (Windows PowerShell shown; see the deployment guide for macOS/Linux):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# First time only: create the synthetic demo data and accounts (see the deployment guide)
.\.venv\Scripts\python.exe -m copilot.cny_demo seed
.\.venv\Scripts\python.exe -m copilot.server --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/login and sign in as `demo_owner`, `demo_staff`, `demo_bank` or `demo_admin`. The seed command needs a password you choose, passed privately in `COPILOT_CNY_DEMO_PASSWORD`; the [deployment guide](docs/operations/deployment.md) shows how.

**Live AI (optional):** put `COPILOT_GOVERNED_LIVE=yes` and the `COPILOT_LLM_BASE_URL`, `COPILOT_LLM_MODEL` and `COPILOT_LLM_API_KEY` settings in a local `.env` file (never commit it). Without them the chat runs in a deterministic, backend-only mode. See [.env.example](.env.example).

## Deployment instructions

[docs/operations/deployment.md](docs/operations/deployment.md): local install, Docker and Railway, with the status of each. Details: [local setup](docs/operations/local-setup.md), [Railway](docs/operations/railway.md), [environment variables](docs/operations/environment.md).

## Tests

```bash
COPILOT_LOAD_LLM_ENV=no python -m unittest discover -s tests
```

The tests use temporary databases, synthetic data and provider doubles; they never call Gemini or touch the demo data. [Test cases](docs/hackathon/test-cases.md) lists the happy-path and unhappy-path cases per role and the automated test that checks each one. Optional browser checks are the Playwright scripts in `scripts/`.

## How it is built

- **Backend:** Python 3.12 standard-library HTTP server; Babel, tzdata and jsonschema are the only runtime packages.
- **Front end:** static HTML, CSS and vanilla JavaScript in `web/`.
- **Storage:** SQLite for identity, roles, sessions, consents and workflow state; checksummed JSON Lines files for the transaction ledger and audit logs (`logs/shenzhen_cny_demo/`).
- **AI:** Google Gemini through its OpenAI-compatible endpoint, behind a governance policy (`config/ai_governance_policy.json`), a governed tool gateway that authorises every call, and an independent answer verifier.
- **Agents:** an authenticated MCP server exposes the same governed, read-only tools.

## Documentation

| Topic | Document |
|---|---|
| System architecture (Word) | [docs/deliverables/System_Architecture.docx](docs/deliverables/System_Architecture.docx) |
| Core algorithm (Word) | [docs/deliverables/Core_Algorithm_Description.docx](docs/deliverables/Core_Algorithm_Description.docx) |
| AI orchestrator design | [docs/technical/ai-orchestrator-design.md](docs/technical/ai-orchestrator-design.md) |
| AI governance and tool contracts | [docs/technical/ai-governance.md](docs/technical/ai-governance.md) |
| Roles, delegation and bank consent | [docs/technical/security-permissions.md](docs/technical/security-permissions.md) |
| Security self-assessment | [docs/hackathon/security-self-assessment.md](docs/hackathon/security-self-assessment.md) |
| Test cases | [docs/hackathon/test-cases.md](docs/hackathon/test-cases.md) |
| Hackathon overview and demo scenarios | [docs/hackathon/README.md](docs/hackathon/README.md) |
| Walkthrough recordings | [docs/gifs](docs/gifs/README.md) |
| User guides per role | [docs/user-guide/README.md](docs/user-guide/README.md) |
| Known limitations | [docs/technical/known-limitations.md](docs/technical/known-limitations.md) |
| All documentation | [docs/README.md](docs/README.md) |

## Security notes

Never publish `.env`, API keys, session or reset tokens, credential files, `logs/` or database backups. Only the allow-listed AI settings are read from `.env`; other settings must be set in the process or hosting service. Financial and security parameters are a proof-of-concept baseline: there is no live bank verification, no lending decision and no guaranteed forecast.
