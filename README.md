# SMEFinance

SME Finance Copilot v1.2 for the Shenzhen International FinTechathon.

The complete application is in [sme-finance-copilot](sme-finance-copilot).

## Run

Requires Python 3.10 or later. No runtime dependencies.

```bash
git clone https://github.com/sofiamallari/SMEFinance.git
cd SMEFinance/sme-finance-copilot
python -m copilot.server
```

Open http://127.0.0.1:8000.

## Test

```bash
python -m unittest discover -s tests -v
```

103 tests pass, including transaction validation, uploads, authorization, dashboard updates, existing modules, HTTP, MCP and mock AI tests. Browser smoke checks also passed.

## Included

- Business Owner, Staff and consent-scoped Financing Agent roles
- Single income/expense entry and persistent transaction management
- CSV and Excel (.xlsx) upload previews, validation, duplicate checks and explicit confirmation
- Merchant Intelligence Dashboard with revenue, expenses and net income
- Digital Payments Simulator and Revenue-Based Financing Calculator
- Permission-checked AI reports, risk alerts, revenue projections and financing recommendations

Read [the application guide](sme-finance-copilot/README.md) and [transaction limitations](sme-finance-copilot/docs/TRANSACTIONS.md). This is a synthetic-data demo with role-selection authentication, fixed data date 2026-09-30 and sandbox payments. Production authentication and database integration remain outside this delivery.

[Download the packaged project](downloads/SME-Finance-Copilot-v1.2-FinTechathon.zip).
