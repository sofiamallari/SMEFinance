> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# SME Owner header and navigation

Current shared navigation and explicitly labeled Username/Role fields are documented in [Shared Owner/Bank navigation](PORTAL_NAVIGATION_PROFILE.md).

Implemented on `feature/security-sme-bank-workflow`, inspected HEAD `12a721007e35435f51ca34a9b87b82a83a8e6755`. No commit, push, merge, reset or discard performed. Existing root README changes and ZIP were preserved.

## User guide

- Header: application identity, authorized merchant selector, compact AI icon and profile icon at the far right. There is no role selector.
- **Profile icon:** shows the authenticated username, public role label **SME Owner**, and **Sign out**. Enter/Space opens the native disclosure; Escape closes it and restores focus; outside click closes it. Staff uses the same workspace shell with the public **SME Staff** label.
- **AI icon:** opens or focuses the existing AI Financial Partner. Close/Escape/backdrop behavior remains available. Opening/focusing/closing does not reset its conversation. Existing merchant-scoped conversation behavior is reused.
- **Bank Authorization** and **Own-business User Management** are now single links in the existing left navigation, at `/consents` and `/owner/users`. They remain Owner-only and additionally require the existing merchant permissions. On mobile, open Navigation to find them.
- The merchant selector still uses backend-authorized memberships and refreshes effective capabilities and financial context through the existing selection handler.

Role labels come from the authenticated session, not a UI choice. Internal compatibility identifiers are not shown as role labels. Screenshot display name `owner` is the deliberately synthetic account's actual display name; its role is displayed separately as SME Owner.

## Implementation and files

| File | Change |
|---|---|
| `web/index.html` | Responsive three-column header, native profile disclosure, moved Owner-only links, public role labels, removal of all role-select bindings |
| `web/financial-partner.js` | Existing launcher opens/focuses the existing panel instead of toggling it closed |
| `scripts/verify_owner_header.cjs` | Repeatable isolated browser checks and screenshot capture |
| This guide, docs index and login quick guide | Current navigation instructions |
| `evidence/owner-header/` | Actual synthetic screenshots and assessment |

Existing tokens, the bot icon sprite, and consistent stroked profile icons are reused; no dependencies added. No backend permission, financial formula, Bank portal file or chatbot implementation was changed. Existing sign-out still calls the authenticated logout API and invalidates the session. Existing route/backend authorization remains authoritative; hiding links is not the security boundary.

## Actual verification

**48 browser checks PASS**, headless Microsoft Edge, temporary synthetic identities/journals/logs. Desktop 1600px, tablet 900px, mobile 390px and small mobile 320px: no horizontal overflow, visible merchant selector, one-row account actions and fitting profile dropdown. AI focus/Escape/history, profile keyboard/outside-click, mobile administration navigation, authorized merchant changes, inaccessible foreign merchant, both Owner routes, hidden/denied Staff administration, real logout and absence of JavaScript errors were checked.

The existing four-role browser journey also passed: platform provisioning, Owner delegation/authorization, Staff draft editing without submission, explicit confirmed routing, Bank review/CSV/AI, isolation and revocation. JavaScript syntax and Git whitespace checks passed. Full backend regression and live Gemini were **not rerun for this UI-only task**; earlier results remain historical.

[Actual assessment](../../../evidence/owner-header/assessment.json) · [Desktop](../../../evidence/owner-header/desktop.png) · [Tablet](../../../evidence/owner-header/tablet.png) · [Mobile](../../../evidence/owner-header/mobile.png) · [320px mobile](../../../evidence/owner-header/small-mobile.png). Earlier local capture iterations are preserved in timestamped sibling folders.

## Run and validate

From `sme-finance-copilot/`, start `python -m copilot.server --host 127.0.0.1 --port 8000`, sign in with your Owner account, select an authorized merchant, open each sidebar administration link, open the AI icon twice and check the conversation remains, then use Profile → Sign out. Test with keyboard and at mobile/tablet widths. Staff must not see either Owner link and direct requests must remain denied.

Optional verification with Python, Node, Playwright and Edge installed: `node scripts/verify_owner_header.cjs`. It starts/stops the disposable fixture on port 8126, never provisions production accounts, and preserves earlier screenshots on rerun. Run it sequentially with other fixture scripts. Runtime overrides: `COPILOT_TEST_PYTHON`, `COPILOT_PLAYWRIGHT_MODULE`.

## Limits

Existing administration pages retain their own layouts and navigation; this task changes the merchant workspace header/sidebar only. Long merchant names are constrained by the compact select width; the selected option remains accessible through the native selector. No production browser certification or fresh live-provider connectivity is claimed.
