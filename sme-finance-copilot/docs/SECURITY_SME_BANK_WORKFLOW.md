# Four-role security and SME-to-Bank POC workflow

Branch: `feature/security-sme-bank-workflow`. Permission/module matrix is the team's provisional POC baseline. All lending outputs are simulations or existing advisory calculations, never a credit decision.

## Policy prerequisites

Use the canonical [security/permissions guide](SECURITY_PERMISSIONS.md) for roles, migration, the module matrix and authorization. Bank review/API details are in [Bank Financial Review](BANK_FINANCIAL_REVIEW.md). This guide focuses on the end-to-end journey.

## Run locally

From your clone's `sme-finance-copilot` directory, stop any old server before migrating. Back up the local identity database privately if it already exists; do not commit the backup. Then run:

```powershell
python -m copilot.auth migrate
python -m copilot.server --host 127.0.0.1 --port 8000
```

Sign in at `http://127.0.0.1:8000/login`. Existing accounts must sign in again following migration. For a completely new database only, bootstrap the first System Admin with `python -m copilot.auth bootstrap --username admin --email admin@example.test`; choose a private password at the prompts. There is no shared default password.

Provider settings stay private in the existing `.env`. No Gemini connectivity is required for the deterministic demo. HTTPS deployments must explicitly enable the existing Secure-cookie setting (`COPILOT_HTTPS=yes`) and provide TLS outside this local server.

## Validate each role and the complete journey

1. **System Admin:** open `/admin/users`; create Owner, Staff and Bank accounts. Assign only intended merchant memberships; Bank requires organization/demo scope. New users change temporary passwords. Open `/admin/security` and administrative audits. Attempt `/api/financial-metrics?merchant=M002`: expect denied.
2. **Owner:** sign in separately, select the assigned business and open `/owner/users`. Delegate only needed actions. For draft-only Staff, enable `use_copilot`, `view_applications`, `create_financing_draft`, and `edit_financing_draft`; operational permissions can be delegated separately. Saving permissions invalidates Staff sessions.
3. **Staff:** sign in again; open Financing → Applications; save/edit an RBF draft with a scoped Bank selection. No submission control should appear. Submission, Bank authorization, user management and security API attempts must be denied. Additional merchant modules appear only when explicitly delegated.
4. **Owner financial operations:** record/import synthetic transactions through existing confirmation/validation controls; compare matching-period Dashboard, Cash Flow and AI evidence. Existing financial formulas and Progression Engine completion limitations remain unchanged.
5. **Owner Bank authorization:** open `/consents` (now titled Bank Authorization). Select an active merchant-scoped Bank, purpose, categories and future expiry; authorize. This does not submit an application or create automatic routing. Banks can read granted financial categories without needing an application case first.
6. **Owner submission:** Financing → Applications → review/edit the draft → explicitly select the Bank → Review submission proposal → review exact merchant/amount/product/recipient/expiry → confirm. A simulated `SUBMITTED_FOR_LENDER_REVIEW` packet is saved and the draft becomes submitted. Expired, changed, foreign or unauthorized proposals cannot execute.
7. **Bank:** sign in separately; `/` redirects to `/bank`. Review authorized merchant summaries, historical revenue trends, estimated cash-flow chart, existing assessments, risk indicators, matches, RBF and journey evidence where categories permit. Open Financing Applications and select a routed packet to inspect its collapsed evidence; unrelated applications are unavailable. Original SME operational screens are denied. No Approve/Reject control exists.
8. **Bank export/AI:** open Reports & Exports and select Download CSV; the right-side AI Financial Partner remains available in every module. Export checks permissions/categories again and audits the event; the report is labeled simulated, not an official lending decision. Ask an authorized read-only financial question. No category or merchant bypass is allowed. CSV data is protected against spreadsheet formula injection.
9. **Revocation:** Owner revokes authorization in Bank Authorization. New Bank reviews, exports and consent-dependent AI requests are denied. The portal clears protected sections and conversations when its live check detects the change (polling, focus, refresh, chat/export or expiry); it does not push remote revocations instantly. Prior downloads/screenshots cannot be recalled. Historical applications and audits remain preserved.
10. **Audit:** Owner reviews own-business access history; Bank sees only its own authorized review event metadata; System Admin reviews administrative logs. Passwords, provider keys and tokens must not be shared in evidence.

## Verification

```powershell
python scripts/verify_four_role_workflow.py
python scripts/verify_four_role_workflow.py --full --evidence evidence/four-role-local-verification.json
```

The verification script isolates even server initialization in temporary synthetic databases. Choose a new evidence filename for each run. Mocked/local LLM tests are not live Gemini verification. Recorded delivery results belong in `evidence/four-role-security-assessment-final.json`; browser observations are separately recorded in `evidence/four-role-browser-assessment.json`.

## Optional repeatable browser verification

The browser check uses the isolated fixture on localhost port 8126 and deliberately synthetic test accounts. Never deploy the fixture as the application. With Node.js, Playwright and Microsoft Edge installed, run:

```powershell
node scripts/verify_four_role_browser.cjs
```

The Python executable defaults to `python`; set `COPILOT_TEST_PYTHON` locally if needed. Playwright is an optional testing dependency, not an application runtime requirement. `COPILOT_PLAYWRIGHT_MODULE` can point to an existing Playwright installation. The browser check provisions a synthetic Bank, delegates Staff drafts, edits a draft, confirms Owner submission, checks Bank charts/CSV/AI, denies direct unauthorized routes and verifies revocation. It stops its disposable server on exit.

## Related security and limitations references

[Session/recovery](AUTHENTICATION.md) · [Permissions](SECURITY_PERMISSIONS.md) · [Known limits/pending rules](KNOWN_LIMITATIONS.md) · [Recorded testing](TESTING.md). Historical guides below do not override the current four-role policy.

## Delivery file manifest

- `copilot/authorization.py`
- `copilot/auth.py`
- `copilot/security.py`
- `copilot/server.py`
- `copilot/mcp_server.py`
- `copilot/agent.py`
- `copilot/partner_state.py`
- `copilot/bank_workflow.py`
- `copilot/migrations/007_four_role_workflow.sql`
- `web/index.html`
- `web/consents.html`
- `web/users.html`
- `web/security.html`
- `web/bank.html`
- `web/owner-users.html`
- `tests/auth_support.py`
- `tests/test_four_role_workflow.py`
- `tests/test_authentication.py`
- `tests/test_security_configuration.py`
- `tests/test_security_agent.py`
- `tests/test_mcp_ai_agent.py`
- `tests/test_financial_partner.py`
- `tests/test_pos_import.py`
- `tests/test_transactions.py`
- `scripts/verify_four_role_workflow.py`
- `scripts/serve_four_role_ui_test.py`
- `scripts/verify_four_role_browser.cjs`

This guide and the sanitized evidence JSON files are also deliverables. The first `four-role-security-assessment.json` records an earlier failing test run and is retained; use the `-final` report for final regression results. No financial formula modules, `.env` secrets, existing journal data, or Progression Engine business logic were rewritten. No commit/push/merge is performed.
