# Shared System Admin layout

Implemented on `feature/security-sme-bank-workflow`. Existing uncommitted work remains preserved. No commit, push, merge, reset or discard performed.

## One layout for both routes

System Admin has two existing page routes: `/admin/security` and `/admin/users`. Security controls, policy configuration and security audit are hash sections of `/admin/security`; account details/history remain in the existing User Management dialog. No new admin route, audit service or security feature was introduced.

Both page templates contain presentation placeholders. `Handler._page` renders their header/sidebar from **one file, `web/admin-shell.html`**, after the existing route authorization. There is no separate header markup per page. The fixed header reads SME Finance Copilot / Security Administration and contains only the profile icon. The profile dynamically displays authenticated Username, public System Admin role and Sign out; no demo value is hardcoded. Page-specific User Management appears inside main content.

The same permission-gated sidebar contains Overview, User Management, Security Controls, Roles & Permissions, AI & MCP Controls, Bank Authorization Policies, Audit & Monitoring and Configuration. Each uses existing routes/hash sections. Current navigation is highlighted on both pages. Mobile Navigation expands this same sidebar; the Security page additionally retains its existing section picker.

User Management retains search/status/role filters, creation/listing, details/account history, editing, suspension, reset password and session revocation. Its inline business handlers were compared against HEAD using UTF-8 and are unchanged. Reauthentication, CSRF, password hashing, immutable role bounds, audits and backend route/API checks remain authoritative. No merchant financial access, merchant header selector or financial assistant was added. Owner/Bank headers were not modified.

## Modified files

- `web/admin-shell.html`: single reusable header/sidebar fragment.
- `web/security.html`, `web/users.html`: shared-layout placeholders/content wrappers; user handlers untouched.
- `copilot/server.py`: presentation-only fragment substitution in `_page`; route authorization unchanged.
- `web/admin.js`: permission gating and active primary navigation using authenticated session.
- `web/security-admin.js`: existing section handling adapted to shared links; keyboard navigation skips hidden links.
- `web/common.css`: active shared links and page-title styles using existing tokens.
- `scripts/verify_shared_admin_layout.cjs`: isolated navigation/actions/responsive verification.
- `scripts/verify_security_ui_regression.py`: optional new evidence filename so prior results are preserved.
- This guide, admin/configuration/module guides and documentation index; evidence below.

## Actual verification

| Check | Result |
|---|---|
| Shared-layout browser suite | 47 PASS checks, headless Microsoft Edge, isolated synthetic data |
| Relevant backend regressions | 66/66 PASS; 0 failures, 0 errors, 0 skips |
| User Management handler comparison | Identical to HEAD; layout changes only |
| Python/JavaScript syntax and Git whitespace | PASS |

Browser checks exercise repeated Security → Users → Controls → Users → Audit → Overview → Users navigation; identical header markup, single header/sidebar, active menus, keyboard profile, logout, desktop 1600px/tablet 900px/mobile 390px/320px, contained horizontal scrolling, user creation/search/details/history/edit/suspend/reset/revoke/filtering, unauthorized Owner/Staff/Bank routes and denied Admin financial APIs. Account actions use synthetic data and real existing endpoints with password reauthentication. Reset-token values are excluded from screenshots/logged evidence.

[Browser evidence](../evidence/shared-admin-layout/assessment.json) · [Backend evidence](../evidence/shared-admin-backend.json) · [Desktop](../evidence/shared-admin-layout/users-desktop.png) · [Tablet](../evidence/shared-admin-layout/users-tablet.png) · [Mobile](../evidence/shared-admin-layout/users-mobile.png) · [320px](../evidence/shared-admin-layout/users-small-mobile.png).

Backend tests cover authentication, security configuration and four-role workflows; full backend discovery and live Gemini were not rerun for this presentation change. Screenshot fixture username is `security`; the actual local `security_admin` account will display its own username dynamically.

## Run and manually validate

Start the existing application, sign in as System Admin and open `/admin/security`. Navigate to User Management, Security Controls, Audit & Monitoring and back to Users. Confirm the same header/sidebar persists, the active link changes and User Management title is in main content. Use profile keyboard/outside dismissal and Sign out. Test user actions only against approved local/synthetic accounts; they retain their existing effects and reauthentication.

Repeatable isolated browser test: `node scripts/verify_shared_admin_layout.cjs`. Relevant isolated backend test: `python scripts/verify_security_ui_regression.py --evidence evidence/my-shared-admin-results.json`. Choose a new result filename. Browser fixtures use localhost 8126 and must run sequentially; runtime overrides are documented in [Testing](TESTING.md).

## Limits

The existing account table scrolls horizontally within its container on narrow screens; the page does not overflow. Desktop sidebar retains its existing expanded layout; mobile navigation collapses. Permission visibility is populated from the current authenticated session while every backend action rechecks authorization. Existing hash sections are not new standalone audit URLs. No production browser certification is claimed.
