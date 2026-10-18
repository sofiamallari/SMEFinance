# Bank access, simulated financing decisions and simulator isolation

Local delivery report · 16 October 2026

> **Superseded (18 October 2026):** the simulated Approve / Reject decisions described in this report have been removed from the app. Banks now record reviews only (Reviewed, More Information Needed, Ready for Further Assessment); `approved` and `rejected` are no longer accepted outcomes, and the app does not simulate underwriting. Older records saved as approved or rejected are shown as Review Closed. The current behaviour is in [Bank review](../user-guide/bank-review.md) and [security permissions](security-permissions.md); the rest of this report is kept as a dated record.

Repository: `C:\Users\User\source\repos\SMEFinance\sme-finance-copilot`. Branch: `feature/ai-governance-chatbot-v2`. HEAD unchanged: `60cb1224ab099e52cbab9268ea210705bf73cf73`. The existing uncommitted generalized AI work was preserved. No feature flag, second application, commit, push, merge or deployment was introduced.

## Implemented

- Owner → Bank Authorization → Create / Link Bank User. New accounts use existing BANK role, account validation, password hashing and single-use activation/reset-token mechanism. Existing active Bank is looked up by exact email, linked only to an owned merchant, and never reset or edited. Linking alone grants no financial access.
- Explicit Authorize Bank form continues to select categories, purpose and expiration. Existing consents store Bank/merchant/granting Owner/granted/revoked/expiry data. One Bank can hold multiple individually scoped merchant authorizations.
- Bank → Merchant Dashboard reuses existing authorized report projection, KPI renderer, recorded revenue chart, channel breakdown and estimated cash-flow chart. Switching clears previous financial content and updates business identity; async responses are bound to the selected merchant. Financial, assessment and financing sections retain separate category restrictions.
- Download Financial Review (CSV) reuses authenticated `/api/bank/export`, authoritative source services, reporting period and export audit event. It is a download, not a public link.
- Existing Owner draft → proposal → explicit confirmation → SUBMITTED_FOR_LENDER_REVIEW workflow is preserved. Routed Bank can record preliminary feedback or final simulated APPROVED / REJECTED. Rejection requires a reason. Owner sees status, Bank reviewer, timestamp, notes and history after refresh/sign-in.
- Final decisions use `BEGIN IMMEDIATE` and one database transaction for packet update, review history and audit. Finalized requests cannot be reviewed/decided again through this workflow. Concurrent decisions yield one final result and one conflict.
- Digital Payments Simulator remains a pure sandbox. Success/failure/refund/pending status and wallet state persist in dedicated simulator SQLite tables, with no new canonical financial records. Historical simulator ledger evidence is retained but excluded from canonical financial projection. Simulator wallets/timestamps/status do not invalidate financial evidence or change recorded counts, cash flow or reports.

## Database and API changes

No new migration/table was needed. Existing `memberships`, `consents`, `reset_tokens`, `applications`, `application_reviews`, `audit_events`, `simulated_payment_state`, `simulated_wallet_state` and `simulated_refund_state` are reused. Application packet adds backend-generated `decision_at`, `decision_by`, `decision_note` and `simulated_decision` on finalization. Existing schema stores status in the packet.

New endpoint: `POST /api/owner/banks/invite`. Allowed input is merchant, email, username, display_name and organization only; new-account fields are validated through the existing account creator. CSRF/session controls remain active. Response returns an activation token only for a newly created account. The token is hashed in storage and is never written to audit records.

Existing `POST /api/applications/{id}/review` accepts additional outcomes `approved` and `rejected`. Existing preliminary outcomes remain supported. Decision identity is session-derived; client actor/ownership fields are rejected. BANK role plus active applications consent plus recipient routing are all required. Owner, Staff and System Admin cannot record Bank decisions.

Audit events include `bank_invitation_created`, `bank_membership_assigned`, `consent_granted`, `consent_revoked`, `bank_report_exported`, `financing_review_recorded`, `financing_simulated_approved` and `financing_simulated_rejected`; applicable actor, target/request, merchant and timestamp come from backend context.

## Verification results

| Verification | Actual result |
|---|---|
| Bank delivery, portal, four-role workflow, simulator integration, existing financial/partner and module checks | 121 passed in 115.323 seconds. Offline financial formula fixtures used existing legacy_fixture mode; no application was served in that mode. |
| Existing focused generalized-chat state/integration/governance/provider/verifier/presentation compatibility | 148 passed in 53.518 seconds; provider fixtures/test doubles, no new live Gemini claims. |
| Existing selected authentication, reset-token, CSRF, revocation, role/consent/master-permission checks | 8 passed in 36.111 seconds. |
| Real local authenticated API journey on freshly seeded isolated CNY data | 15 checks passed; no mocked application server or financial services. |
| Additional real API security checks | Bank financial-record write 403; Bank payment creation 403; unauthenticated report export 401. |
| Concurrent finalization | Two simultaneous decisions: one success, one HTTP-equivalent 409; one final review/history row. |
| Before/after financial isolation | Dashboard metrics, report metrics/forecast, ledger and financing requests unchanged by simulator; final financing decisions do not change financial metrics or move money. |
| Syntax and whitespace | 8 changed Python files parsed; 4 changed JavaScript files passed Node syntax checks; git diff --check passed. |

The first 121-test run had two stale currency-format text assertions. They now use the existing shared formatter and additionally retain rejection of the fabricated repayment amount. Both individually passed, followed by the clean 121-test run above. Relevant simulator tests were intentionally changed from expecting financial revenue to expecting zero simulator financial contribution, matching this approved task; no financial formulas were changed.

## Real API journey evidence

| Check | Result |
|---|---|
| owner_invites_bank_activation_without_password_exposure | PASS |
| existing_bank_additional_merchant_without_account_reset | PASS |
| multi_merchant_distinct_authorized_data | PASS |
| financial_review_authenticated_download_reconciles | PASS |
| owner_confirmed_submission_visible_to_bank | PASS |
| demo_owner_unauthorized_decision_denied | PASS (HTTP 403) |
| demo_staff_unauthorized_decision_denied | PASS (HTTP 403) |
| demo_bank_unauthorized_decision_denied | PASS (HTTP 403) |
| approved_visible_to_owner | PASS |
| final_decision_immutable | PASS |
| rejected_reason_visible_to_owner | PASS |
| simulated_decisions_no_dashboard_financial_effect | PASS |
| simulated_payment_no_dashboard_report_or_application_effect | PASS |
| revocation_immediate_dashboard_report_request_denial | PASS |
| foreign_merchant_and_bank_self_authorization_denied | PASS |

## Browser evidence

Actual browser checks on isolated synthetic accounts: Owner opens invitation form and links the existing Bank; Owner logout; newly invited Bank login; authorized merchant dashboard and financial chart; switching M002 to M003 shows the second merchant values and matching ID; CSV download completed as `financial-review-M003.csv`; request details and Bank Review form; deliberate simulated approval; sign back in as Owner and view Approved · Simulated with Bank, date and remarks. Browser console error queries returned no errors. Screenshots are in the local external `.journey-work` verification folder.

Browser testing caught and fixed a stale merchant ID label and missing Owner final-status labels. The native browser confirmation dialog stalled during the final Revoke click, so that UI completion is **not counted as passed**. The temporary test tab was closed. Revocation passed through the real API and automated tests, including immediate dashboard/report/request/decision denial. Browser rejection and new-account activation were covered through actual API/service tests rather than repeated completely in the browser. Responsive and cross-browser testing were not performed.

## Validation walkthrough

1. Restart the local application to load changed backend code. Owner selects an owned merchant and opens Bank Authorization.
2. Create / Link Bank User. For a new account deliver the one-time token privately; recipient uses Set / reset password. Existing Bank retains its credentials.
3. Authorize the Bank with only needed categories and an expiration. Include applications for request submission/review; reports for financial report/chart; forecasts for forecast evidence. Linking a Bank or routing an application does not grant other categories.
4. Owner saves financing draft with Bank and valid amount, reviews proposal and explicitly confirms submission. Existing RBF limits still apply.
5. Bank signs in, selects an authorized merchant, opens Merchant Dashboard, checks data/period, downloads Financial Review (CSV), and filters Financing Applications.
6. Bank opens submitted request → Bank Review → deliberately chooses Approve · Simulated or Reject · Simulated; supplies rejection reason when rejecting; saves. Preliminary Reviewed remains default.
7. Owner opens Applications and View Details after refresh to inspect status, reviewer, date, remarks and history. A decision does not add sales or cash.
8. Owner revokes authorization. Subsequent protected Bank requests are denied; previously downloaded reports cannot be recalled. Repeat with a second merchant to verify independent grants.
9. Compare dashboard/report values before and after a sandbox payment: values remain unchanged. Record actual business activity only in Merchant Transactions.

## Remaining limits and security gaps

- Activation invitations have no SMTP delivery, verified Bank email/domain, regulated-institution validation or separate second-person identity assurance. Deliver only to the intended recipient. Owner-created Banks and decisions are local POC simulations, not genuine bank underwriting or lending authority.
- New-account token is shown once and expires under the existing reset policy. Lost/expired invitation requires the established administrator reset process; Owner cannot reset an existing Bank.
- No new loan object, funds movement, real gateway, automatic repayment calculation or reopened-final-decision workflow was added. Existing financing request fields do not include a new purpose field.
- Financial Review remains CSV with the existing reporting period and authorized categories. PDF/Excel/email/custom report periods were not added.
- Historical simulator ledger records are retained for evidence and omitted from finance. The simulator has no live gateway. Financial input selection changed as explicitly required; financial calculation formulas did not.
- Full regression and production deployment were not run. Earlier unrelated legacy full-auth/HTTP fixture gaps from the AI task are not represented as resolved by the selected authentication checks here.
- The generalized AI engine is preserved and its 148 compatibility checks pass. Its previously reported wording/polish gaps remain a separate follow-up; no additional AI architecture or provider changes were made for this task.

## Active-storage preservation check

The test server used a fresh temporary dataset and was stopped. Final byte-hash comparison of the active demo directory was **not identical**. Read-only investigation found exactly two new `access_denied` audit entries for `/` and `/api/auth/me` in the original active SQLite database. Their timing is consistent with the shared localhost browser cookie/session contacting the already-running app on port 8000 when the temporary test tab closed. No active users were created/updated, no applications/reviews/consents/drafts were created/updated during the test window, and the canonical transaction ledger still has its original 15 October modification time. No test Bank accounts exist in the active database. The audit entries were preserved; nothing was reset or discarded. Existing localhost browser tabs may need sign-in again. Financial/user dataset records were not replaced, reseeded or migrated. Future browser test sessions should use a distinct hostname/cookie scope.

## Files changed

| File | Purpose |
|---|---|
| `copilot/bank_workflow.py` | Owner-scoped create/link invitation; current applications-consent checks; atomic final simulated decisions. |
| `copilot/server.py` | One Owner invitation route; existing routes retained. |
| `copilot/financial_data.py` | Exclude historical simulator rows, simulator statuses/wallets/time from finance; simulator persistence only, no financial ledger append. |
| `copilot/agent.py` | Disconnect simulator refund lookup from financial journal. |
| `copilot/modules/payments.py` | Roll back simulator memory if persistence/validation fails; retain dedicated-table persistence and idempotency. |
| `web/owner-management.js` | Create / Link Bank User form and private one-time activation-token presentation. |
| `web/index.html` | Owner invitation control and explicit Digital Payments Simulator labeling. |
| `web/bank-portal.js` | Merchant Dashboard, safe switching/header identity, final decision controls, scoped report download and polling behavior. |
| `web/bank-views.js` | Financial Review download labeling, current format/period limitations. |
| `web/bank.html` | Explicit simulated-decision/no-real-loan wording. |
| `web/financing-applications.js` | Owner final status labels and decision feedback. |
| `tests/test_bank_delivery.py` | New isolated invitation, no-takeover, consent, report, decision, concurrency and simulator-isolation tests. |
| `tests/test_financial_partner.py` | Update simulator analytics expectations to new requested isolation contract and use shared formatter in two old text assertions. |
| `tests/test_partner_integration.py` | Simulator restart/concurrency/crash tests now verify dedicated simulator persistence and financial-ledger isolation. |
| `docs/user-guide/bank-authorization.md` | Account linking/activation and separate category grants. |
| `docs/user-guide/bank-portal.md` | Authorized merchant dashboard and current access boundary. |
| `docs/user-guide/bank-review.md` | Final simulated decisions and active application consent. |
| `docs/user-guide/digital-payments.md` | Standalone simulator and excluded financial analytics. |
| `docs/user-guide/financing-rbf.md` | Owner-visible simulated Bank decisions. |
| `docs/technical/security-permissions.md` | Bounded Owner provisioning, category checks, transaction and identity limitations. |
| `docs/technical/bank-workflow-delivery.md` | This delivery report. |

Technical documentation navigation was also updated in `docs/technical/README.md`.
