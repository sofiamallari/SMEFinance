# Modular Bank portal — delivery and verification

Repository: `C:\Users\User\source\repos\SMEFinance`  
Application: `sme-finance-copilot/`  
Branch: `feature/security-sme-bank-workflow`  
Inspected HEAD: `44bf35bf5a3b8e470e6e4eaf7be0e29e0e682ba3`  
Delivery: uncommitted working-tree changes. No commit, push, merge, reset or discard was performed. Existing documentation work, local `.env`, prior financial/security/AI implementations and old ZIP were preserved.

## Delivered

The long `/bank` report was replaced with an Owner-compatible three-part shell: collapsible labeled/icon sidebar, selected module content and persistent read-only AI panel. Six modules are **Overview, Authorized Merchants, Financing Applications, Financial Review, Reports & Exports, Review Activity**. AI is not a seventh navigation page. Direct hash URLs, merchant selection, active navigation, preferences, responsive layouts and keyboard access are supported.

Existing financial tools, canonical aggregates, consent/category checks, routed packet boundaries and audited CSV remain authoritative. No financing formula, scoring rule, financial mutation permission, new approval rule, migration or framework was introduced. A small guarded metadata endpoint supplies individual current Owner-grant dates/categories and permitted own last-review timestamps; submission dates come from the existing saved table.

Separate files own pure presentation helpers, six module renderers and authenticated routing/state/chat. Styling uses the existing common tokens and icon sprite; the existing backend AI infrastructure is reused rather than duplicating financial or security logic. Owner's browser script depends on Owner-specific globals/actions, so Bank has a separate read-only adapter with the same panel patterns and backend.

Conversations remain merchant/user scoped in page memory across module navigation. Revocation, expiry, category changes, session invalidation and failed authorization validation clear protected state. Old asynchronous responses are discarded after scope changes. Bank cannot alter authorization, decide financing, submit applications or move funds. Audit permission is independently enforced even for last-review metadata; an unavailable audit feed does not prevent a separately authorized financial review.

## Actual verification

| Verification | Actual result |
|---|---|
| Full isolated backend regression | 290/290 PASS; 0 failures, 0 errors, 0 skips |
| Modular Bank browser suite | 55 PASS checks; headless Microsoft Edge, isolated synthetic data |
| Existing four-role browser journey | PASS: System Admin provisioning, Owner delegation/authorization, Staff create/edit without submit, confirmed routed submission, Bank review/CSV/AI, route/API denial, revocation and mobile layout |
| Python compilation and new JavaScript syntax | PASS |
| Live Gemini | NOT TESTED; UI AI exercised existing deterministic backend |

[Final regression evidence](../evidence/bank-portal-regression-delivery.json) · [Browser evidence](../evidence/bank-portal/assessment.json). Earlier regression artifacts are retained: the first 317-test run included repeated inherited discovery; final discovery contains the unchanged original 285 tests plus five new focused metadata/authorization tests. The intermediate 289-test run preceded the additional independent-audit test. Use the delivery artifact as final regression status.

The browser suite verifies all six routes/active states, four canonical metrics, recorded/estimated charts, seven backend assessment values, five separate journey stages, collapsed sections, module/merchant chat scoping, search/sort/empty states, CSV/status, reload/preferences, mobile overlay/Escape/overflow, foreign merchant and operational-route denial, withheld categories, expiry, revocation, inactive Bank, audit errors, authorization-service errors/recovery and absence of JavaScript errors. Failure injection covers client presentation only; backend denial rules are also tested directly against isolated real auth stores.

## Screenshots

Actual synthetic browser captures, visually reviewed:

- [Overview — desktop](../evidence/bank-portal/overview-desktop.png)
- [Financial Review — desktop](../evidence/bank-portal/financial-desktop.png)
- [Reports & Exports — mobile](../evidence/bank-portal/reports-mobile.png)

Earlier successful browser captures are preserved in `evidence/bank-portal-history/`; they are not separate deliverable UI versions.

## Files changed for this portal task

- Backend: `copilot/bank_workflow.py`, `copilot/auth.py`, `copilot/server.py`.
- UI: `web/bank.html`, `web/bank.css`, `web/bank-components.js`, `web/bank-views.js`, `web/bank-portal.js`.
- Verification: `tests/test_bank_portal.py`, `scripts/verify_bank_portal.cjs`, `scripts/verify_four_role_browser.cjs`, `scripts/serve_four_role_ui_test.py` and the evidence linked above.
- Maintained documentation: `docs/BANK_FINANCIAL_REVIEW.md`, this report, `docs/ARCHITECTURE.md`, `docs/README.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/TESTING.md`, `docs/SECURITY_SME_BANK_WORKFLOW.md`, `docs/task04/12 README_Bank_Financial_Review.md`, `docs/task04/possible scenarios/12_Bank_Financial_Review.md`.

There are other pre-existing uncommitted documentation files in Git status; they were not discarded or attributed to this portal task. Temporary editing helpers live in the old workspace's `.journey-work/`, not production import paths.

## Manual validation

1. From your clone's `sme-finance-copilot`, run `python -m copilot.server --host 127.0.0.1 --port 8000` and open `http://127.0.0.1:8000/login`. Use existing properly provisioned accounts; there is no shared password.
2. Owner: select an assigned merchant, open `/consents`, choose an active scoped Bank, categories and future expiry, authorize. This is not application routing.
3. Bank in a separate session: open `/bank`, select that merchant; visit all six modules, expand financial evidence, collapse navigation/AI and reload a child hash URL.
4. Owner: explicitly confirm an existing draft to that Bank using Financing → Applications. Bank: open Financing Applications, search/sort/select its reference, expand read-only packet evidence.
5. Bank: Reports & Exports → Download CSV; Review Activity → inspect the own export event after refresh. Ask a permitted financial question in the right panel; navigate modules and switch authorized merchants to verify conversation scope.
6. Owner: revoke or expire access. Bank: refresh/wait for detection; protected content/chat must clear, with no automatic scope substitution. Direct API/export/tool attempts must be denied. Withhold only forecasts: reports remain readable and forecast evidence is absent.
7. System Admin: deactivate the isolated test Bank. Its session/review must become unavailable. System Admin and Staff must not gain Bank review authority.
8. Test at desktop and 390-pixel mobile width; navigate with keyboard, open AI overlay and close with Escape/backdrop. Review errors/empty states without exposing unrelated data.

Use [testing instructions](TESTING.md) for disposable automated fixtures; do not use fixture provisioning against shared data. [Bank guide](BANK_FINANCIAL_REVIEW.md) owns the full user/component/API reference and [permissions](SECURITY_PERMISSIONS.md) owns policy.

## Limits

Remote revocation detection is periodic/on-focus/request based, not push; backend guards remain live on every request. Downloads/screenshots cannot be recalled. Financial snapshots update on Refresh review; authorization polling is not automatic financial refresh. Chat is page memory, not persistent across reload. Audit listing is the existing latest 100 own merchant events.

No PDF/XLSX/email, arbitrary reporting-period export, cross-merchant portfolio calculation, lending decisions, new incentive criteria, journey completion rules, actual settled-bank history or post-financing outcomes were added. Existing forecasts, scores and synthetic attributes remain provisional POC evidence. Real Gemini connectivity and production security certification are not established by these tests.
