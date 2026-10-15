> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# SME Owner AI Financial Partner

Current implementation reference for the Owner drawer. This extends the existing
Gemini planner, typed evidence verifier, domain services and authorization model.
It does not replace them. See [security permissions](../../technical/security-permissions.md) and
[user guide](../task04/4%20README_AI_Copilot.md).

## User workflow

1. Select an authorized merchant in the header, then open the AI icon.
2. Choose an empty-state suggestion to populate the composer, or type a question.
3. Press Enter to send; Shift+Enter adds a newline. Close with the upper-right X
   or Escape. Mobile uses a dismissible modal drawer with keyboard focus wrapping.
4. Financial answers include backend values, currency, period, provenance and
   limitations. Expand evidence details before relying on a finding.
5. Guidance answers identify the actual navigation path and maintained help content.
   Follow the source module's validation and confirmation steps to make changes.
6. Sensitive suggestions explain workflows. They do not create payments, submit
   applications, approve credit, change permissions, import records or grant consent.

The compact welcome and 14 suggestions appear only when the selected conversation
is empty. The header and composer stay visible while messages scroll. HTTP errors
show a safe generic message and allow question retry; provider internals are hidden.

## Coverage inventory and implementation matrix

“Existing” below means code inspected before this task, not a newly connected module.
Read services return authoritative values directly; the model does not total them.

| Module | Existing AI support | Missing capability found | Current implementation |
|---|---|---|---|
| Business Overview | Canonical totals, status counts and comparisons via `get_dashboard` | Capture/channel breakdown not rendered as typed facts; weak help | Existing dashboard capture fractions and canonical payment-method totals now exposed as verified facts for explicit breakdown questions; period-control help |
| Merchant Transactions | Saved ledger feeds canonical totals and reports | Manual-entry/history and mapping guidance | Grounded navigation/workflows; no arbitrary raw-ledger export or individual-row search tool added |
| Bulk POS Import | Committed imports feed canonical projection; generic upload help | Worksheet, profile, mapping and rejection guidance | Maintained import instructions; no analysis of an unsaved local file or import commit from chat |
| Digital Payments | Latest simulator status and recorded completed payments | Complete application-help path | Grounded simulator guidance; latest-payment tool retained; no new payment action |
| Cash Flow | Existing forecast and rule alerts | Navigation and assumptions guidance | Existing calculations retained; help describes source view and forecast limitations |
| Financing Overview | Existing indicative matching | Actual navigation guidance | Existing matching retained; help explains limitations |
| RBF Calculator | Existing exact quote, fee and repayment evidence | Calculator workflow guidance | Existing formulas retained; help describes indicative calculator |
| Progression Engine | Existing five-stage journey evidence and provisional incentive status | Navigation/workflow help | Existing journey retained; missing completion rules remain unassessed |
| Financing Applications | Latest submitted packet status only; Staff blocked | Draft and multiple-application reads | HTTP read adapter calls existing draft and application services; Owner sees authorized records, Staff only delegated own drafts; current Applications module can prioritize an ambiguous status question |
| Bank Authorization | No conversational Owner read | Scoped consent status and help | Existing consent service supplies recorded categories and active/expired/revoked status; Owner-only help and read |
| Own-business User Management | No conversational Owner read | Scoped staff grants and help | Existing Owner staff service supplies assigned accounts and independent merchant grants; no editing from AI |
| Transaction Settings | No conversational read | Current settings and help | Existing settings service supplies currency/timezone/date format/lock status; no setting changes |
| Data Quality & Monitoring | Existing unresolved-alert and failed-validation counts | Monitoring UI explanation | Existing count tool retained; help covers tabs and limitations. No unrestricted run-log or row-detail tool added |

## Existing tools and new read adapters

The existing verified planner allowlist contains `financing_journey`,
`assess_business`, `get_dashboard`, `financial_report`, `match_financing`,
`rbf_quote`, `cashflow_forecast`, `incentive_status`, `data_quality`,
`latest_payment`, and `application_status`. Cash-flow alert evidence is retrieved
through the existing `cashflow_alerts` tool alongside its forecast. Actual exposure
is filtered per principal, merchant, permissions, consent and AI tier by PolicyGuard.

New HTTP-session read adapters are `transaction_settings_read`,
`staff_delegation_read`, `bank_authorization_read`, and
`financing_applications_read`. They are not new external MCP tools and are not
model-selected write tools. They reuse live application services plus PolicyGuard;
application reads require advisory tier, metadata reads read tier. Both retrieval
and return enforce access. Audit records identify capability and merchant, without
adding raw provider payloads. Bank continues through existing consent-aware tools;
System Admin cannot access merchant chat.

`copilot/partner_help.py` is the maintained registry: module, actual path, permission,
supported workflow steps and limitations. Update it and route-coverage tests whenever
the corresponding UI changes. It uses reviewed keyword routing; arbitrary natural
language understanding across every paraphrase is not guaranteed. Unknown questions
continue through the existing finance-domain policy. Flagged injection requests
cannot reach the help/read adapters. Other merchant IDs cannot override selected scope.

## Conversation and freshness

In-page Owner navigation preserves the mounted drawer. `GET /api/partner/conversation`
restores plain messages on return/reload from separate Owner pages. The server keeps
at most 40 messages per user/session/merchant in bounded process memory, with a
30-minute idle expiry and 1,024-conversation cap. Live authorization and permission/
tier fingerprints invalidate inaccessible history. Different sessions do not share it.
No chat transcript is stored in browser local/session storage. Restarting the server,
expiry or eviction loses this convenience history; this is not cross-session storage.

Restored messages are historical text, without live action buttons or old approval
tokens. Their evidence details must be refreshed by asking again. An explicit notice
marks restored findings. Merchant changes clear visible messages immediately; late
responses for a different merchant are discarded. Existing backend financial follow-up
preferences and data-version checks remain separate and authoritative.

## Security and action boundaries

- Application help checks the required live merchant permission before describing a
  restricted module. Staff need explicit delegation; Owner governance stays Owner-only.
- Existing financial tools still use authorization, PolicyGuard, typed verification,
  consent categories, period/currency checks and audit records. No financial formula
  or underlying permission boundary was changed.
- Owner drawer sends `explain_actions: true`; action requests receive guidance.
  Existing proposal/confirmation endpoints remain available to their existing authorized
  source workflows. This flag cannot grant permission or bypass confirmation.
- Suggested questions populate the composer; clicking a chip never executes an action.
- Loan approval, fund disbursement and other prohibited T4 operations stay prohibited.
- Provider failure does not authorize fabrication. Guidance is deterministic and labeled;
  financial fallback renders validated service evidence or explains its absence.

## Verification

Use a project Python environment with installed requirements. All scripts below use
disposable fixture data; never point tests at shared or production databases.

```powershell
$env:COPILOT_LOAD_LLM_ENV='no'
$env:COPILOT_AGENT_MODE='auto'
python scripts/run_isolated_regression.py --pattern test_owner_partner.py
python scripts/run_isolated_regression.py
```

For browser checks, configure `COPILOT_TEST_PYTHON` to that Python executable and
`COPILOT_PLAYWRIGHT_MODULE` if Playwright is not on Node's module search path:

```powershell
node scripts/verify_owner_partner.cjs
```

For an explicitly live Gemini check in a fresh terminal using the ignored local
`.env` (never paste keys into chat or logs):

```powershell
python scripts/verify_owner_partner_gemini.py
```

Evidence is in `evidence/owner-partner/`; backend runner reports are also in
`evidence/transaction-settings/`. The live check records only safe status metadata,
model, tool names and evidence count. Provider availability is a point-in-time result,
not inferred from configuration. The live attempts returned HTTP 503 and a timeout; authentication and model capability remain unverified until a successful request.

## Remaining boundaries

No new write-capable AI tool, FX conversion, real-money processing, bank credit
decision, unsaved-workbook analysis, tax/credit-score inference or new progression
completion rule was implemented. Currency locking, financial reconciliation, refunds,
transaction status classification, financing math and lender restrictions use existing
business rules. Guidance does not remove those restrictions. Broader paraphrase
coverage, durable cross-session transcripts and new financial data capabilities need
separate scope and review.

## Delivery assessment — 15 October 2026

Branch: `feature/security-sme-bank-workflow`. HEAD unchanged:
`7e36f57fd89bd1b5aa7528d8ed9a2b3258a09846`. Existing unrelated working changes
were preserved. No commit, push, merge, reset or persistent demo-data modification.

| Check | Actual result |
|---|---|
| Full isolated backend regression, including existing AI/financial/authorization tests | PASS: 368 tests, 0 failures, 0 errors, 0 skips; 242.74 seconds |
| New Owner assistant backend cases | Included in full regression: 22 methods covering guidance, reads, data/role/tier/session isolation, sensitive actions, injection, capture agreement and fallback |
| Existing progression regression | PASS: 10 tests after preserving the financial progression question route |
| Dedicated drawer browser checks | PASS: 46 checks, desktop/tablet/mobile/320px, no JavaScript errors |
| Existing four-role browser journey | PASS: provisioning, Owner delegation/authorization, Staff drafts, explicit submission, Bank review/charts/export/AI, route/API isolation, revocation, mobile |
| Python compilation and drawer JavaScript syntax | PASS |
| Live Gemini | BLOCKED: first actual request HTTP 503; second actual request timed out. Key is locally present and ignored by Git; authentication and model generation are NOT VERIFIED |
| Deterministic application-help/provider-failure path | PASS through isolated backend and browser tests; financial outputs stay grounded in existing services |

**Implemented and verified:** compact drawer, accessible close, welcome/chips,
multiline composer and scrolling, safe errors/retry, in-page and same-session page-
return history, merchant switching, maintained application guidance, authorized read
adapters, existing calculations and permission boundaries. New capture facts agree
with the existing dashboard service. Sensitive suggestions do not execute operations.

**Implemented but not live-provider verified:** Gemini planning/explanation with this
local key during this delivery. Existing mocked-provider/verifier regressions pass,
but they do not prove present Google availability or authentication. No model/key
changes were made to hide the blocker.

**Not implemented:** new write-capable tools, raw-row conversational search, unsaved
file analysis, durable cross-session history, real-money actions or lender decisions.
The coverage matrix above identifies the available source per module; module names
in help are not evidence of arbitrary live financial integrations.

**Requires separate approval/business rules:** new financing or progression eligibility,
real credit decisions, FX sources, new AI write actions and production deployment.
No such changes were required for this task.

### Files changed for this task

- Backend: `copilot/agent.py`, `copilot/authorization.py`, `copilot/reliability.py`,
  `copilot/verified_agent.py`, `copilot/server.py`, new `copilot/partner_help.py`,
  new `copilot/owner_partner.py`.
- UI: `web/index.html`, `web/financial-partner.js`.
- Verification: new `tests/test_owner_partner.py`, `scripts/verify_owner_partner.cjs`,
  `scripts/verify_owner_partner_gemini.py`.
- Documentation: this reference, `docs/README.md`,
  `docs/task04/4 README_AI_Copilot.md`.
- Generated evidence: `evidence/owner-partner/` and isolated backend runner JSON
  reports under `evidence/transaction-settings/`.

Screenshots: [empty desktop](../../../evidence/owner-partner/empty-desktop.png),
[long desktop conversation](../../../evidence/owner-partner/desktop.png),
[tablet](../../../evidence/owner-partner/tablet.png),
[mobile](../../../evidence/owner-partner/mobile.png),
[320px mobile](../../../evidence/owner-partner/small-mobile.png).
