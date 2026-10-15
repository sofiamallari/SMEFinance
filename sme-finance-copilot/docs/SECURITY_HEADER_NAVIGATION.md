> Initial Security-header verification record. The later [shared Admin layout](SHARED_ADMIN_LAYOUT.md) now standardizes both Security Administration and User Management; use it for current navigation and test results.

# Security Administration header and navigation

Branch: `feature/security-sme-bank-workflow`. Existing Owner/Bank changes and unrelated working files were preserved. No commit, push, merge, reset or discard performed.

## Implemented behavior

Header left: **SME Finance Copilot**, subtitle **Security Administration**. Header right: a single profile icon. There is no standalone account text, Sign out, User Management link, merchant selector, role switcher or financial assistant.

The profile uses the authenticated session username and authoritative effective role. `SYSTEM_ADMIN` displays as **System Admin**. It shows **Username: <your username>**, **Role: System Admin**, and **Sign out**. No demo username is hardcoded. Enter/Space opens the native disclosure, Escape closes it and restores focus, and outside click dismisses it. Sign out retains the existing authenticated/CSRF logout call.

**User Management** is a single `/admin/users` link in the existing left navigation, shown only when the authenticated permission list includes `manage_users`. Backend route checks remain unchanged. On mobile, **Navigation** reveals the same sidebar/link; the existing security section picker remains available. All seven section buttons, URL fragments, keyboard arrows, configuration editors/export/import, monitoring and audits remain intact.

## Shared design and modified files

The existing shared `web/admin.js` owns session initialization and logout; it now initializes the profile only on pages that contain the new admin profile. Other admin pages retain their existing identity behavior. `web/common.css` owns scoped admin-header/profile styles using existing brand/teal/background/border tokens and the same stroked profile icon/disclosure pattern as Owner/Bank. No new dependency was added.

- `web/security.html`: simplified header, profile disclosure, permission-gated sidebar User Management link and mobile navigation toggle.
- `web/admin.js`: conditional authenticated profile/menu initialization; existing logout and other-page behavior retained.
- `web/common.css`: scoped responsive header, profile and sidebar-link styling.
- `scripts/verify_security_header.cjs`: isolated browser checks and screenshots.
- `scripts/verify_security_ui_regression.py`: isolated authentication/configuration/four-role regressions.
- This guide, docs index, configuration reference and quick guide: current instructions.
- `evidence/security-header/` and `evidence/security-header-backend.json`: actual verification.

No backend policies, role mappings, merchant permissions, financial calculations, Owner/Bank header source or additional admin capabilities changed.

## Actual results

| Verification | Result |
|---|---|
| Browser | 44 PASS checks, headless Microsoft Edge with temporary synthetic data |
| Relevant backend regressions | 66/66 PASS; 0 failures, 0 errors, 0 skips |
| Syntax/whitespace | PASS |

Browser coverage: desktop 1600px, tablet 900px, mobile 390px and 320px without overflow; profile username from actual session, public System Admin role, keyboard/outside dismissal, dropdown position, mobile User Management, all security sections, configuration export, User Management route, Owner/Staff/Bank admin denials, retained Owner/Bank headers, denied admin financial access, real logout and no JavaScript errors. Backend scope is authentication, security configuration and existing four-role workflow; a fresh full regression suite and live Gemini were not needed or executed for this header-only task.

[Browser evidence](../evidence/security-header/assessment.json) · [Backend evidence](../evidence/security-header-backend.json) · [Desktop](../evidence/security-header/desktop.png) · [Tablet](../evidence/security-header/tablet.png) · [Mobile](../evidence/security-header/mobile.png) · [320px](../evidence/security-header/small-mobile.png).

The synthetic test username is `security`, so screenshots show Username: security. An installation whose authenticated username is `security_admin` will display that actual username; the role label remains System Admin.

## Manual verification and limits

Start the existing app, sign in as System Admin and open `/admin/security`. Open the profile; compare its username with your session. Use User Management in the sidebar, return and visit all seven security sections. At mobile width open Navigation for User Management, or use the existing section picker. Try the profile with Enter/Space/Escape and outside click; use Sign out and verify protected APIs require a new session. Owner, Staff and Bank must remain unable to open admin pages; Admin must remain unable to read merchant financial data.

Optional repeatable checks, from the application directory: `node scripts/verify_security_header.cjs` and `python scripts/verify_security_ui_regression.py`. The browser uses port 8126; run browser fixture scripts sequentially. Runtime overrides and isolation details are in [Testing](TESTING.md). Preserve backend evidence before rerunning; the script refuses to overwrite it.

The subsequent shared-layout implementation removes User Management's prior header; both routes now render one fragment. Desktop sidebar remains the existing noncollapsible layout; mobile has a collapsible sidebar and the existing section picker. Role-policy visibility is initialized from current authenticated permissions; backend authorization remains authoritative. No production browser certification is claimed.
