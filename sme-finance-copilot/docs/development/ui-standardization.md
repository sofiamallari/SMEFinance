# Shared UI standardization

Local implementation on `feature/ai-governance-chatbot-v2`; no deployment or commit.

## Shared implementation

- `web/brand.css`: shared green tokens, neutral surfaces, underline horizontal tabs, compact buttons/tables/pagination, responsive modal styling and visible focus. Existing semantic statuses and financial indicators remain separate.
- `web/ui-standard.js`: progressively enhances existing table buttons in place. View/View Details/View Application/View Summary use an eye; Edit a pencil; Refresh a refresh icon; Authorization History a history icon; Download a download icon. Matching is deliberately limited to recognizable labels. Unrecognized and security-sensitive actions retain their labels.
- Remove/Delete table controls move into a native More disclosure. The original control and confirmation handler remain intact. The disclosure expands inline so it cannot be clipped as an absolutely positioned popup inside a scrolling table. It can increase row width while open; local horizontal scrolling may be needed on narrow screens.
- Existing tab click handlers still decide whether a step may change. Shared arrow/Home/End keyboard navigation invokes those handlers without changing consent, required fields or permissions.
- All complete HTML pages load the shared stylesheet and helper: index, Bank, login, password reset, users, merchants, security, legacy Owner users and consents. The Admin shell is a fragment composed into these pages, not an independent document.
- `web/owner-management.js`: merchant count disclosure retains complete names.
- `copilot/server.py`: registers the static shared helper only. No data API contract or authorization change in this UI task.

## Verification performed

- All existing web JavaScript files passed Node syntax checks before the final helper refinement; the refined helper also passed its syntax check.
- Focused isolated automated suites: `tests.test_owner_access` and `tests.test_channel_performance`: **21 passed**, no failures/errors/skips.
- Owner browser: sign in/out, Staff/Bank tabs, View/Edit icon handling, saved account values, linked identity read-only, Bank authorization three-step layout, mobile dialog, desktop/tablet overflow checks.
- Computed Owner active tab: transparent background, `rgb(8,102,61)` underline; inactive underline transparent. All inspected icon controls had accessible names and titles.
- Bank browser: exactly Overview and Financing Applications; application table, eye action opens details, Request Details/Financial Review tab selection and labeled decision controls preserved.
- Staff browser: dashboard-only synthetic grant for M002 uses the shared Owner design; only Dashboard appears in sidebar. Switching to M003 cleared previous merchant KPIs/charts and disabled export. No production permissions were changed.
- Responsive observations: 390px viewport / 375px document and 820px viewport / 805px document; no page-level horizontal overflow in inspected Owner views.
- Browser console: no errors observed during inspected flows.
- After screenshots were captured in the browser tool output for the Owner table, mobile authorization modal and Bank application detail. No before screenshots or standalone screenshot files were saved.

## Limits and outstanding checks

This is not an assertion that every page or workflow has received exhaustive visual QA. Full regression, cross-browser testing, screen-reader testing and every Admin/transaction/payment modal were not run in this styling pass. Browser Create/Link/Save/Remove/Approve/Deny submissions were not repeated; focused service tests cover access mutations and denial cases, but do not replace full browser acceptance.

The earlier broader access regression run reported 59/62 passing, with audit actor redaction, an application authorization expectation, and an MCP response-envelope error unresolved. That run is not reported as passing and this styling task does not change their backend behavior.

Icon conversion depends on recognized visible labels. New/localized labels must be explicitly added or keep text. No permissions are inferred from labels; backend enforcement remains authoritative.

## Manual acceptance checklist

1. Owner: exercise Create, exact-email Link, View/Edit, More > Remove confirmation; verify independent merchant permissions and cancellation.
2. Bank authorization: all three tabs by keyboard; missing category/purpose/expiry/consent prevents saving; independent merchant scope and download grants persist.
3. Financing: Owner View Details; Bank Request Details and Financial Review, review outcomes with a required note for More Information Needed, and Owner status tracking. There are no approve or deny actions.
4. Tables: filters, page sizes, Previous/Next, long emails/references, disclosures and More near the right edge on mobile.
5. Owner/Staff: merchant switching, restricted APIs, Cash Flow and Survival tabs; ensure no stale merchant values.
6. Admin: User Management, Merchant Management and Security Controls, all edit/create/reset/revoke dialogs, Escape and focus return.
7. Transaction modules: worksheet tabs, validation/preview, history and monitoring; payment simulator; ensure existing handlers remain intact.
8. Desktop/tablet/mobile and keyboard: focus ring, tab scrolling, modal body/footer, disabled/loading controls, semantic warning/error colors and financial negatives.
