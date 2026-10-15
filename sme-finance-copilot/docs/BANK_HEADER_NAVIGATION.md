> Historical implementation reference. The current three-menu portal and simulated review workflow are documented in [Bank Review Portal](BANK_REVIEW_PORTAL.md); earlier six-menu, read-only-only and Bank AI descriptions below are superseded.

# Bank header and account navigation

Current shared navigation and explicitly labeled Username/Role fields are documented in [Shared Owner/Bank navigation](PORTAL_NAVIGATION_PROFILE.md).

Branch: `feature/security-sme-bank-workflow`. The existing SME Owner header changes and other working-tree files are preserved. No commit, push, merge, reset or discard was performed.

## Implemented layout

Left: **SME Finance Copilot**, subtitle **Bank Financial Review**. Center: labeled **Reviewing Merchant** native selector showing the business name prominently, with the selected merchant ID displayed beneath it. Right: **AI Review Assistant** icon and profile icon. No standalone account name/role or Sign out remains in the header.

The profile menu shows the authenticated username, public role **Bank**, and Sign out. Native Enter/Space opens it; Escape closes it and restores focus; outside click closes it. The dropdown appears below the header, above the desktop AI panel, within the viewport. On mobile, the existing modal AI panel remains above the header and its keyboard/access controls are retained.

The AI icon opens or focuses the existing AI Financial Partner panel. No second chatbot or conversation reset was introduced. Close/Escape/backdrop remains available. Read-only, permission-aware tools and merchant-scoped threads remain unchanged.

The selector uses only the existing authorized Bank merchant response. Switching merchants continues to isolate financial evidence and conversations. Revocation, expiry, inactive account, stale request handling and failed validation use the existing lifecycle. With no authorized merchants, the selector is disabled and says **No authorized merchants**; the secondary label also makes this state explicit.

Design tokens, stroked icons and profile disclosure behavior match the [SME Owner header](OWNER_HEADER_NAVIGATION.md); no dependencies or shared backend changes were needed. This is a focused header update, not a replacement of `/bank` or its six modules.

## Modified files

- `web/bank.html`: semantic merchant label, separate ID, compact AI and native profile menu.
- `web/bank.css`: Owner-compatible responsive header/profile styles and correct layering.
- `web/bank-portal.js`: presentation of authenticated account/merchant identity, profile handlers, focus-existing-AI behavior. Existing APIs, authorization decisions, financial calculations and context lifecycle retained.
- `scripts/verify_bank_portal.cjs`: expanded existing browser checks for header/profile/logout and no-authorized-merchant state.
- This guide, docs index and current Bank module guide: current interaction instructions.
- `evidence/bank-portal/`: current actual captures and assessment; previous captures preserved in the existing history folder.

No backend files, permission policies, financial formulas or SME Owner source files were modified by this Bank-header task.

## Actual verification

**84 browser checks PASS**, headless Microsoft Edge with isolated synthetic identities and data. This includes the existing six-module portal checks plus desktop 1600px, tablet 900px, mobile 390px and small mobile 320px header checks: no overflow, one-row account actions, keyboard profile interaction, public role label, dropdown viewport/header placement, AI focus and real session-revoking profile logout.

Existing checks cover merchant/thread isolation, permitted financial evidence, withheld categories, all-grants-revoked empty state, expiry, revocation, inactive Bank, authorized CSV, authorization-service errors/recovery, foreign merchant and SME operational route denial, charts, backend-derived assessment values and no JavaScript errors. JavaScript syntax and Git whitespace checks passed. Full backend regression and live Gemini were not rerun for this frontend-only task; earlier backend results remain historical.

[Actual evidence](../evidence/bank-portal/assessment.json) · [Desktop header](../evidence/bank-portal/header-desktop.png) · [Tablet header](../evidence/bank-portal/header-tablet.png) · [Mobile header](../evidence/bank-portal/header-mobile.png) · [320px header](../evidence/bank-portal/header-small-mobile.png).

Screenshot account name `lender_analyst` is the synthetic fixture's authenticated username, not a displayed role identifier; its public role is Bank.

## Manual check and limitations

Start the existing app, sign in as a scoped Bank with active Owner grants, select a merchant, open the profile menu and AI icon, then switch to another authorized merchant. Verify only its evidence/thread appears. Revoke/expire grants and refresh; protected evidence must clear and the empty state must appear when none remain. Use Profile → Sign out, then verify the session no longer reads protected APIs.

Repeatable verification: `node scripts/verify_bank_portal.cjs` from the application directory with Python, Node, Playwright and Edge installed. Run fixture scripts sequentially; port 8126 is disposable testing only. See [testing](TESTING.md) for runtime overrides.

Long names are constrained by native selector width; full choices remain available through the selector. Remote revocation remains detected by the existing polling/focus/request mechanism, with backend checks on every protected request. No production browser certification or live provider connectivity is claimed. Your supplied task ended at “Do not replace”; no unspecified follow-on functionality was added.
