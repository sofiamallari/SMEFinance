# SME Finance Copilot application

Start with the [repository README](../README.md) for installation and project scope, or the [documentation index](docs/README.md) for detailed guides.

Run commands from this directory. Migrate with `python -m copilot.auth migrate`, bootstrap only a fresh installation, then start `python -m copilot.server --host 127.0.0.1 --port 8000`. Sign in at `/login` using your own account. Bank accounts land at `/bank`; System Admin uses `/admin/security` and `/admin/users`; SME users use the existing merchant workspace.

Current modules: Dashboard, Merchant Transactions, Digital Payments, Cash Flow, Financing (Overview, Progression Engine, RBF Calculator, Applications), AI Financial Partner, own-business delegation/Bank authorization and platform administration. Their visibility and actions are governed by [one four-role policy](docs/SECURITY_PERMISSIONS.md).

Local `.env` automatically loads only the four LLM keys described in the [AI guide](docs/TASK03_FINANCIAL_PARTNER.md). Configure database paths, HTTPS and other server settings through process/service environment variables. Never commit `.env`, credentials, session tokens or private databases.

Use `python scripts/verify_four_role_workflow.py --full` for isolated regression verification. [Testing](docs/TESTING.md) covers browser verification and historical provider assessments.

The original long README is retained as a [historical snapshot](docs/history/README_before_four_role.md). It is not current security/setup guidance.
