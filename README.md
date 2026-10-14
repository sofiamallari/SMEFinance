# SMEFinance

SME Finance Copilot v1.2 for the Shenzhen International FinTechathon.

The complete application is in [sme-finance-copilot](sme-finance-copilot).

## Run

Requires Python 3.10 or later. No runtime dependencies.

```bash
git clone https://github.com/sofiamallari/SMEFinance.git
cd SMEFinance/sme-finance-copilot
python -m copilot.auth migrate
python -m copilot.auth bootstrap --username admin --email your-email@example.com  # first install only; password prompt
python -m copilot.server
```

Open http://127.0.0.1:8000.

## Test

```bash
python -m unittest discover -s tests -v
```

Run the complete regression suite with the command above. Security tests use isolated temporary databases and synthetic data.

## Included

- Business Owner, Staff and consent-scoped Financing Agent roles
- Single income/expense entry and persistent transaction management
- CSV and Excel (.xlsx) upload previews, validation, duplicate checks and explicit confirmation
- Merchant Intelligence Dashboard with revenue, expenses and net income
- Digital Payments Simulator and Revenue-Based Financing Calculator
- Permission-checked AI reports, risk alerts, revenue projections and financing recommendations

Read [the application guide](sme-finance-copilot/README.md) and [transaction limitations](sme-finance-copilot/docs/TRANSACTIONS.md). Default authentication uses local SQLite accounts and server sessions. Financial data remains synthetic with fixed date 2026-09-30 and sandbox payments. External OAuth/MFA and production certification remain outside this MVP.

[Download the packaged project](downloads/SME-Finance-Copilot-v1.2-FinTechathon.zip).

Security Administration includes seven sections and portable, validated JSON policy sharing between local installations. Read the [team configuration guide](sme-finance-copilot/docs/SECURITY_CONFIGURATION.md). Import never copies user credentials or financial records.

The complete regression suite passes **188 tests**. See the [implementation report](sme-finance-copilot/docs/SECURITY_ADMIN_REPORT.md) for actual unit/API/browser results and review limits.


## Merchant Transactions (Task 02)

The sixth sidebar module contains Single Transaction, Bulk POS Import, Transaction History and Data Quality & Monitoring. The five-step wizard supports multi-file/folder CSV/XLSX acquisition, explicit mapping, decimal normalization, duplicate detection, count/financial reconciliation, signed staging and durable confirmation. Scoped grants protect Staff actions; administrator roles do not inherit business access. See the [complete workflow, APIs, guarantees and demo guide](sme-finance-copilot/docs/POS_TRANSACTION_IMPORT.md). New canonical records are intentionally prepared for Task 03 downstream integration; existing demo financial calculations remain unchanged.

[Task 02 verified implementation report](sme-finance-copilot/docs/TASK02_REPORT.md).
