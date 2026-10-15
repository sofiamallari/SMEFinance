> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

> Historical implementation reference. The current three-menu portal and simulated review workflow are documented in [Bank Review Portal](BANK_REVIEW_PORTAL.md); earlier six-menu, read-only-only and Bank AI descriptions below are superseded.

# Bank Financial Review Portal

Sign in as **Bank**; `/` redirects to `/bank`. The portal is a read-only simulated review, not underwriting, approval or funds movement. [Security and permissions](../../technical/security-permissions.md) is the canonical policy reference. No financial formulas, scores, role bounds or consent categories were changed by the portal redesign.

## Navigation and user guide

Use **Reviewing Merchant** in the header to select an Owner-authorized business; its name appears in the selector and ID beneath it. The compact AI Review Assistant icon opens/focuses the existing AI panel; the profile icon contains authenticated name, Bank role and Sign out. See [header interactions and verification](BANK_HEADER_NAVIGATION.md). The left sidebar has six modules; the same AI Financial Partner stays on the right while navigating. Collapse navigation with **Navigation**; collapse the AI panel with its close button and reopen it from the header. Compact desktop navigation retains labeled icon tooltips. On smaller screens the AI is an overlay; Escape/backdrop closes it and keyboard focus is contained while open.

| Module / URL hash | Implemented behavior |
|---|---|
| Overview / `#overview` | Selected merchant only: recorded net sales, expenses, net income and completed transaction count; recorded revenue chart, compact existing risk alerts, recent routed applications, Owner authorization summary and links |
| Authorized Merchants / `#merchants` | Current Owner-authorized businesses; search, status filter, sorting and selection. Categories and individual grant/expiry dates are shown; last review comes from this Bank's recorded access event, or says not recorded; audit permission is separately enforced |
| Financing Applications / `#applications` | Search, status filter, sorting and read-only details of submitted packets routed specifically to this Bank; requested amount, stored submission time, product and status. Selecting a packet also scopes CSV export |
| Financial Review / `#financial` | Collapsed performance, estimated forecast, seven-dimension assessment, financing matches, RBF simulation, maturity/journey and missing-evidence sections |
| Reports & Exports / `#reports` | Existing CSV export with selected merchant, current categories, available recorded period, business-data date and optional selected packet; clear success/failure status |
| Review Activity / `#activity` | This Bank's own merchant-scoped event metadata only; search, action filter, sortable columns, collapsed details. Latest 100 events, with pagination of 10 visible records when needed |

Application, merchant and activity lists paginate after 10 records. Filters/sorts operate on the authorized response only; they do not query other merchants or expand permissions. Navigation and sidebar preference survive refresh; a merchant selected through the header appears in the URL, for example `/bank?merchant=M002#financial`. A direct URL never grants authorization.

### Financial Review

- **Performance:** existing canonical totals, payment-method net sales, recorded revenue trend, period, provenance and limitations. Revenue is not available cash.
- **Forecast:** existing opening/minimum/closing balances, buffer/runway and method, chart with date and currency axes, existing alerts, expandable daily inflow/outflow/balance table. All forecast values are estimates.
- **Assessment:** existing stage/composite and seven dimension scores, bars on their existing 0–100 scale, factors/constraints/signals. No new scoring or approval thresholds.
- **Matches:** existing ranking, size, annual cost, rationale, components and excluded-product reasons. Indicative, not an offer.
- **RBF:** existing advance, fee/rates, total repayable, remittance basis, estimated payoff, example days and first 14 simulated repayments, warnings and comparisons. No slider or new quote inputs were introduced for Bank.
- **Maturity/journey:** displays existing assessment maturity separately from Identify → Profile → Place → Activate → Measure, including existing evidence, missing requirements and blocked/not-assessed states. Completion criteria remain unimplemented; no successful progression or financing outcome is inferred.

Missing categories or evidence produce explicit unavailable messages. No raw JSON is the primary UI; nested evidence uses labeled fields and collapsed details. Monetary/date formatting and chart coordinates are presentation only; backend values remain authoritative.

## AI, freshness and security

The panel uses existing `POST /api/chat`, permission-aware tool exposure and backend claim verification. Bank's existing read-only permissions are unchanged. Financial evidence/provenance and response mode are expandable in the transcript; no proposal/approval controls are rendered.

Conversation is stored **only in page memory**, keyed by authenticated user and merchant. Module navigation retains it; merchant switching restores only that merchant's thread. Refresh closes the in-memory session history; logout or session invalidation clears it. Hidden pages clear protected content/history and revalidate on return. Conversations are not saved to localStorage; only sidebar/panel preferences are.

Authorization metadata is rechecked on refresh, chat, export, window focus and every 15 seconds. The nearest active grant expiry triggers invalidation/revalidation. Changed grants clear protected sections and conversations. Authorization polling does not automatically refresh financial totals; use Refresh review to retrieve a new financial snapshot. A revoked/expired selection remains empty until another authorized merchant is explicitly selected. Account/session denial redirects to login and clears protected state. Failed authorization checks clear displayed financial evidence; request timeouts prevent indefinitely stalled validation. Epoch checks/abort handling discard old review/chat/export results after merchant changes or invalidation.

Backend checks still occur on **every** protected request/tool/export. UI detection of remote revocation is polling-based, not instantaneous push; it can lag a polling interval plus request latency. Existing screenshots/downloads cannot be recalled. The UI is not an alternative authorization boundary.

Routing and category authorization remain separate: a submitted packet must name the Bank recipient, and the Bank must have the current `applications` category. Merchant-level categories can be reviewed without a packet. Owner alone controls Bank authorization. No Approve/Reject/Submit/Pay controls or mutation permissions were added; legacy stored review notes remain historical.

## Components and APIs

| Component | Responsibility |
|---|---|
| `web/bank.html` | Three-part semantic shell; existing common stylesheet and icon sprite |
| `web/bank.css` | Scoped Owner-compatible palette, spacing, responsive layouts, states and accessibility |
| `web/bank-components.js` | Safe field/table/chart/date/currency presentation helpers |
| `web/bank-views.js` | Six distinct module renderers; no requests or financial calculation engine |
| `web/bank-portal.js` | Authenticated request adapter, routing, merchant/context lifecycle, tables, CSV and chat state |
| `copilot/bank_workflow.py` | Current Owner grants directory, independently guarded existing financial tools, review/export and own event metadata |

| Route | Purpose |
|---|---|
| GET `/bank` | Bank-only authenticated page |
| GET `/api/bank/merchants` | Bank's current scoped merchant names/currencies, its own active Owner-grant categories/dates and own last recorded review time; no unrelated user directory |
| GET `/api/bank/review?merchant=M002` | Authorized merchant sections and specifically routed packet list |
| GET `/api/bank/review?merchant=M002&application_id=<id>` | Specifically routed, authorized packet selection |
| GET `/api/bank/export?merchant=M002&application_id=<id>` | Audited UTF-8 BOM CSV; packet selection optional |
| GET `/api/merchant/audit?merchant=M002` | Bank's own authorized merchant event metadata, independently permission-checked |
| POST `/api/chat` | Existing permission-aware read-only financial assistance |

The merchant metadata endpoint uses the same live Bank membership, active Owner role/membership and unrevoked/unexpired consent conditions as existing authorization. It returns individual grants, not an invented consolidated expiry. `submitted_at` is the existing applications table timestamp; no new persistence or migration was needed.

CSV contains existing metadata, independently authorized sections, selected packet if requested, classifications and missing-evidence notes. It excludes credentials, raw transaction exports and unrelated merchants; formula-like cells are escaped. JSON-valued CSV cells preserve nested existing evidence. It is not a PDF/Excel presentation report. Audits include existing `bank_review_accessed` and `bank_report_exported` codes.

## Validation and limits

See [testing and actual evidence](TESTING.md), [screenshots and implementation report](BANK_PORTAL_REPORT.md), [end-to-end SME-to-Bank workflow](SECURITY_SME_BANK_WORKFLOW.md) and [known limits](KNOWN_LIMITATIONS.md).

Manual verification: start the app, sign in as Owner and authorize a scoped Bank with desired categories; sign in as Bank separately; exercise all six modules, collapse panels, select a routed packet, download CSV and ask a read-only financial question. Switch merchants and check transcript isolation. Revoke/expire the grant or deactivate the Bank, then refresh: protected sections/chat/export must be unavailable. A withheld category must not appear in backend sections. Original SME/Staff/System Admin functions remain in their existing workspaces.

PDF/XLSX/email export, arbitrary reporting-date selection, cross-merchant portfolio aggregates, new lending decisions, historical settled-bank balances and post-financing outcome baselines are not implemented. Browser tests use deterministic synthetic data; they do not establish fresh live Gemini connectivity.
