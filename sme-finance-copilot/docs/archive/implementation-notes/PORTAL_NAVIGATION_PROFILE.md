> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Shared Owner and Bank navigation and profiles

Implemented on `feature/security-sme-bank-workflow`. Existing work is preserved; no commit, push, merge, reset or discard was performed.

## Implemented behavior

Owner and Bank reuse `web/portal-navigation.js` and `web/portal-navigation.css`. The hamburger is a compact 36px accessible button. Desktop sidebars expand to 220px and collapse to 68px; the same 850px breakpoint controls mobile navigation. Mobile menus expand in the page flow, avoiding content overlap, and close after selection, Escape or outside click. Desktop preferences are stored separately for each portal. Active routes and existing role-specific menus are preserved.

Both profile dropdowns explicitly label **Username:** and **Role:**. Username comes from the authenticated session; public roles are **SME Owner** and **Bank**. Staff retains its public SME Staff label. Profile keyboard/outside-click behavior and authenticated Sign out remain available. No UI role switching exists.

Owner retains its business navigation, Bank Authorization and Own-business User Management. Bank retains its six review modules. Merchant selectors and existing AI panels remain connected to their existing handlers; merchant isolation and authorization are unchanged. The server change serves only the two shared static assets.

## Modified application and test files

- `web/portal-navigation.js`, `web/portal-navigation.css`: shared controller and styles.
- `web/index.html`, `web/financial-partner.js`: Owner integration and parent-menu expansion.
- `web/bank.html`, `web/bank-portal.js`: Bank integration and session-derived profile labels.
- `copilot/server.py`: fixed static asset routes.
- `scripts/verify_portal_navigation.cjs`: isolated responsive and interaction checks.
- `scripts/verify_bank_portal.cjs`: profile assertion updated for the labeled role element.

No financial formulas, backend permissions, account-management rules or financial APIs were changed.

## Actual verification

Headless Microsoft Edge using temporary synthetic users/data:

| Check | Result |
|---|---|
| Shared navigation/profile verification | 75 checks PASS |
| Existing Bank portal verification | 84 checks PASS |
| Existing Owner header verification | 48 checks PASS |

Widths tested: 1600px desktop, 900px tablet, 390px mobile and 320px small mobile. Checks include matching hamburger styles, expanded/collapsed widths, no horizontal overflow, mobile close behavior, active navigation, profile labels, keyboard behavior, merchant switching, existing AI focus, Owner/Staff/Bank access separation and real session logout. JavaScript syntax, Python server compilation and Git whitespace checks passed.

[Assessment](../../../evidence/portal-navigation/assessment.json) · [Owner desktop profile](../../../evidence/portal-navigation/owner-desktop-profile.png) · [Owner mobile navigation](../../../evidence/portal-navigation/owner-mobile-navigation.png) · [Bank desktop profile](../../../evidence/portal-navigation/bank-desktop-profile.png) · [Bank mobile navigation](../../../evidence/portal-navigation/bank-mobile-navigation.png).

Run `node scripts/verify_portal_navigation.cjs` from the application directory with Node, Playwright, Edge and Python installed. Optional runtime overrides: `COPILOT_PLAYWRIGHT_MODULE` and `COPILOT_TEST_PYTHON`. Run fixture scripts sequentially because they use port 8126.

## Manual validation and limits

Sign in separately as Owner and Bank. Expand/collapse navigation, select each authorized module, switch merchants, open the AI icon and profile, then sign out. Repeat at mobile width with keyboard navigation. Staff should see only permitted entries; direct unauthorized routes must remain denied.

Mobile navigation deliberately expands in the page flow. Only Edge was exercised; no fresh live Gemini request or full backend suite was run for this UI task. Synthetic screenshot usernames describe fixture accounts, not production identities. Existing permission and financial assumptions are documented in [Security and permissions](../../technical/security-permissions.md) and [Known limitations](KNOWN_LIMITATIONS.md).
