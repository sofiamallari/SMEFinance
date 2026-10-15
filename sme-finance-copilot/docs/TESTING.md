# Testing and recorded evidence

From the application directory:

```powershell
python scripts/verify_four_role_workflow.py
python scripts/verify_four_role_workflow.py --full
python scripts/verify_four_role_workflow.py --full --evidence evidence/my-verification.json
```

Use a new evidence filename; existing results are preserved. This script isolates server initialization, identities, journals and logs in synthetic temporary stores. Prefer it to raw unittest discovery on a shared/local installation because server imports can otherwise initialize configured stores.

## Browser verification

With Node, Playwright and Microsoft Edge installed, run `node scripts/verify_four_role_browser.cjs`. It starts/stops a disposable localhost fixture on port 8126. Python defaults to `python`; `COPILOT_TEST_PYTHON` and `COPILOT_PLAYWRIGHT_MODULE` can select local testing runtimes. Never deploy `serve_four_role_ui_test.py` as the application. The core application does not require Node/Playwright.

The browser checks platform provisioning, Owner delegation/Bank authorization, Staff draft creation/editing without submission, explicit confirmed routing, Bank cards/charts/CSV/read-only AI, direct-route/API denials, revocation and mobile layout.

## Recorded results

- [Final security regression](../evidence/four-role-security-assessment-final.json): 285 passed, zero failures/errors/skips.
- [Browser assessment](../evidence/four-role-browser-assessment.json): recorded successful synthetic journey.
- `four-role-security-assessment.json` preserves an earlier failing run; its obsolete fixture failure was corrected. It is not final status.
- Task 01/02/03 reports and Gemini assessments remain historical evidence for their inspected code/baselines. They are not fresh checks of the current security implementation.

Those earlier documentation updates did not rerun implementation tests or prove live Gemini connectivity. Provider tests using mocks/local endpoints are distinct from real requests. Live Gemini was not tested in the final four-role run. Optional live assessment scripts make real provider calls; inspect their scope and use local secrets/synthetic data before running them.

Coverage includes migration/unmapped-role denial, auth/session/recovery, delegation, drafts, explicit recipient routing, category filtering, expiry/revocation, exports/audits, AI/MCP restrictions and preserved financial/POS/payment/journey behavior. Finite tests do not certify production security or all possible adversarial inputs.

## Modular Bank portal verification

The portal delivery ran **290 backend tests** with zero failures/errors/skips and **55 browser checks**. [Delivery report](BANK_PORTAL_REPORT.md) describes the exact scope, screenshots, changed files and limitations. [Current backend evidence](../evidence/bank-portal-regression-delivery.json) and [Bank browser evidence](../evidence/bank-portal/assessment.json) supersede earlier portal iterations. The existing four-role browser workflow was also rerun successfully. These runs use synthetic isolated stores; live Gemini remains NOT TESTED.

```powershell
python scripts/verify_four_role_workflow.py --full --evidence evidence/my-bank-verification.json
node scripts/verify_bank_portal.cjs
node scripts/verify_four_role_browser.cjs
```

Run browser scripts sequentially because both disposable fixtures use localhost port 8126. The Bank verifier retains earlier successful captures before replacing its current evidence. Five focused tests in `tests/test_bank_portal.py` cover the guarded merchant directory, current/expired/inactive grants, stored submission timestamps and independent audit permission. No production database or provider secret is needed for these checks.

## Transaction settings and intelligent import

Use `python scripts/run_isolated_regression.py` (optional `--pattern test_transaction_settings.py` or `--pattern test_worksheet_detection.py`). Set `COPILOT_BAO_WORKBOOK` to run the supplied-workbook checks. Run `node scripts/verify_transaction_settings_ui.cjs`, `node scripts/verify_detection_review.cjs` and `node scripts/verify_multi_worksheet_ui.cjs` sequentially against their disposable fixtures. See [module behavior and safeguards](MULTI_WORKSHEET_IMPORT.md) for dependencies, API confirmations and limitations; actual recorded results are under `evidence/transaction-settings/`.
