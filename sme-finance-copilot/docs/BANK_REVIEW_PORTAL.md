# Bank Review Portal — final sandbox workflow

Current route: `/bank`. Navigation contains **Overview**, **Financing Applications**, **Authorized Merchants**. Bank AI UI/chat entry points are removed; SME Owner AI is unchanged. Existing Bank read-only financial APIs remain category/consent protected.

## Bank workflow

1. Sign in as Bank. Overview counts all currently routed, merchant-scoped submitted application records; Reviewed means at least one recorded review, Awaiting means none. Authorized Merchants counts currently permitted merchants, not application routing.
2. Open Financing Applications, optionally filter merchant/application status/review status, then View Application.
3. The wide dialog has Request Details, Financial Review, Bank Review, History. Financial Review reuses existing reports, forecasts, assessments, RBF/matching, provenance and CSV export services. Missing categories display restricted/unavailable states.
4. In Bank Review select **Reviewed**, **More Information Needed**, or **Ready for Further Assessment**. Notes are required only for More Information Needed, maximum 1000 characters. Save Bank Review records identity/time on the server; it never changes the financing application lifecycle.
5. History displays submission and append-only Bank review events. Owner → Financing → Applications → View Details displays Latest Bank Review, notes, reviewer/Bank and recorded history. Owner refreshes the application list to retrieve feedback recorded after its last load.

All main Bank tables and the event history offer 10/25/50 rows. Filters apply to the complete authorized request dataset before client-side pagination. No approval, rejection, disbursement, payment or SME resubmission workflow was added.

## Security boundaries and persistence

- Routed request metadata is separate from financial-data authorization. A Bank needs an active account/session, enabled `view_bank_review`, live merchant membership, an active merchant and an application addressed to its own user ID. Routed metadata is explicitly whitelisted; stored score/stage snapshots are excluded.
- Only the addressed Bank can append reviews, with both `view_bank_review` and new `record_bank_review` permissions. Only existing `SUBMITTED_FOR_LENDER_REVIEW` application records are reviewable. Drafts, other Banks' applications, unknown merchants and nonreviewable states are denied.
- Financial evidence/exports still require existing live category-specific Owner consent and permissions. Application routing or review does not grant consent. No unauthorized category tool is called by the existing financial service; final export authorization checks remain.
- Existing `application_reviews` records are reused without destructive schema changes. Actor user ID is the reviewer/Bank identity; the parent application's immutable recipient identifies the routed Bank. Timestamp is generated server-side. Every save appends a row and a `financing_review_recorded` audit event. Existing legacy outcome records remain readable; they cannot be newly selected.
- Additive migration `010_simulated_bank_review.sql` enables `record_bank_review` for Bank only; no AI write tool or prohibited credit-decision capability is introduced. Existing session/CSRF/origin validation applies. Review text is escaped when rendered.

## API changes

- `GET /api/bank/applications`: own routed request metadata and review history.
- `GET /api/bank/applications/{application_id}`: live-scoped detail.
- `POST /api/applications/{application_id}/review`: existing route, now accepts only `{outcome, note}` with outcomes `reviewed`, `more_information_needed`, `ready_for_further_assessment`.
- Owner application list adds reviewer display name and Bank organization to existing review entries.
- Existing `/api/bank/merchants`, `/api/bank/review`, `/api/bank/export` and merchant audit APIs remain. Financial Review/Reports are consolidated in detail dialogs. Relevant submission/review activity appears in History; the broader own-merchant audit API remains available, without a standalone Review Activity menu.

## Verification and limits

Isolated disposable data was used; persistent demo records and credentials were unchanged. Normal `python -m copilot.server --host 127.0.0.1 --port 8127` startup passed. Focused checks confirmed routed Bank access, safe metadata, financial denial without consent, other-Bank denial, Owner write denial, required/optional notes, saved feedback, unchanged application state, append-only history and persistence after server restart.

Focused Edge browser flow passed: three menus/no Bank AI, four detail tabs, restricted financial state, review save/history, Owner Latest Bank Review, and no JavaScript errors. Python compilation and JavaScript syntax passed. Full regression suites, new automated regression tests, cross-browser testing and broad responsive/category-permission verification were not performed.

Financial views are retrieved afresh on opening. Consent expiry closes the dialog at the recorded expiry; authorization is also revalidated on focus/visibility and every 15 seconds. Revocation is immediate on the backend; an already delivered visible browser snapshot can remain until the next revalidation (up to 15 seconds). No server-push invalidation was introduced. Authorized financial rendering/export reuse existing implementations but were not exercised across every category in this focused run. Bank AI backend compatibility was not removed from shared APIs; its portal UI is absent.

Restart the development server to load code and apply its normal additive startup migration. No commit, push or merge was performed.
