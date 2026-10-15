# Task 02 implementation report

> Historical snapshot: retained for chronology and original evidence. Role, consent, menu, API and test instructions below may be superseded. Use [current documentation](README.md) for the four-role baseline.

## Branch and baseline

All work is in `feature/pos-transaction-import`, created from the fetched latest `origin/main` at **f1792ca416ed139505d96861871becf60992af9f** (Security Administration merge). The working tree was clean before branch creation; no unrelated changes were discarded. Main is not committed/pushed/merged by this task. The delivery commit hash is reported in the final response and `git log -1`. No pull request is required by this task; the committed branch is left for user review.

## Reused architecture and compatibility

Reused the standard-library HTTP server/static app, Principal/PolicyGuard, SQLite identity/session/CSRF/consent/policy/audit, existing merchant context, legacy transaction API and authoritative JSONL ledger. The baseline had horizontal business tabs, so that same navigation/content is placed into one left sidebar rather than creating another shell. Dashboard, AI Copilot, Financing, Cash Flow and Payment Sandbox remain intact, with Financing Applications as a secondary link.

Existing staff rights become explicit migration grants; new staff default to read-only transaction history/quality. Existing security controls/portable schema continue working with added bounded actions. No OAuth, cloud database, microservice, real payment or loan decision was introduced.

## Delivered features

- Sixth sidebar Merchant Transactions parent with receipt/chevron, four indented subviews, active parent/child, accessible expand/collapse, direct routes and refresh/back/merchant context, mobile menu and a backend unresolved-alert badge.
- Shared decimal canonical model, authenticated manual entry, unique server IDs/provenance, required external reference and request-key duplicate-submission protection.
- Exact five-step wizard: Select Files → Map Columns → Validate → Preview → Import. Multi-CSV/XLSX and browser folder/nested-folder acquisition; removals/limits, samples/suggestions, explicit monetary meaning/defaults/date formats, same-schema mapping reuse and back-state preservation.
- Backend Extract → Stage → Transform → Validate → Reconcile → Preview → Commit → Monitor, with current permissions rechecked, actor/session/merchant-bound expiring staging, HMAC integrity, protected fields, exact dataset preview, explicit commit and deterministic journal markers.
- Merchant-scoped committed History with date/status/source/method filters and bounded pagination; DQ overview, persisted run history/details, source hashes/version/audit references, predefined checks, actual metric formulas, alerts/filtering/drilldown and reasoned acknowledgment/resolution.
- Deterministic missing/invalid, ambiguous-duplicate, reconciliation, corruption, interrupted-commit, duplicate-rate/invalid-rate/date-gap/high-value and actually evaluated expiry findings. No fabricated risk score or background-scheduler claim.

## Files changed

Added `copilot/canonical_transactions.py`, `pos_extract.py`, `pos_import.py`, `transaction_journal.py`, migration `004_pos_import.sql`, `web/merchant-transactions.js`, vendored `icons.svg`/Lucide license, POS fixture helpers/tests, `scripts/generate_pos_demo.py`, `scripts/verify_pos_ui.cjs`, this report, `docs/POS_TRANSACTION_IMPORT.md`, synthetic reports/folder/XLSX and task verification screenshots/JSON.

Updated `server.py`, `auth.py`, `authorization.py`, legacy `modules/transactions.py`, existing `web/index.html`/User Management grant controls, authenticated browser fixtures/expectations, migration-count expectations, security schema/safe example and README links. No financial calculation, assessment/matching, payment simulation, agent orchestration, immutable security or MCP transport files changed.

## Routes, APIs and canonical contract

Routes are `/merchant-transactions/single`, `/merchant-transactions/import`, `/merchant-transactions/history`, `/merchant-transactions/data-quality`, with explicit `?merchant=...` context and server authorization. Existing module routes remain available.

New endpoints: POST `/api/merchant-transactions/entry`; GET `/api/merchant-transactions/history`; POST `/api/pos-import/stage`; GET staged session/outcome; POST validate/cancel/commit and GET preview under `/api/pos-import/{batch_id}`; GET `/api/data-quality` and scoped run drilldown; POST scoped alert lifecycle. The guide documents payloads, statuses, filters and limits.

Canonical records include internal/merchant IDs, UTC/business dates, signed decimal amount/effective amount, currency/type/method/status, protected creator/time/source, external reference, gross/net adjustments and settlement, batch/file/hash/row/mapping lineage. Sales are positive; expenses/refunds/sale reversals negative. Only completed status has financial effect. Currency must match merchant, with no FX conversion. Net from mapped gross is gross − discount + tax − refund component; settlement is distinct. Counts are parsed = eligible + exact exclusions + invalid. Reliable source controls compare like monetary bases; absent controls are a visible warning, not invented totals.

## Persistence, duplicates, monitoring and permissions

One JSONL financial source remains authoritative. Checksummed batch events use thread/platform file locking and durable append. SQLite stores staging/intent/provenance/control aggregates and alerts, not a second committed-row ledger. Recovery finalizes matching durable markers; missing markers fail and require fresh authorized validation rather than silently replaying financial writes. Caught I/O failures truncate a partial append; torn/corrupt storage fails closed and requires verified recovery.

Stable merchant-scoped references and complete fingerprints detect duplicates within/across files and existing history. Exact known duplicates are visibly excluded. Missing-reference collisions remain ambiguous unless original byte-hash/row lineage proves exact replay. Commit rechecks current history under the writer lock; concurrent duplicate attempts cannot double count. Manual identical-key retries return the saved outcome; POS repeated commits are denied and the original result is read separately.

Latest validation per retained POS run defines metric denominators; valid=eligible+exact duplicates, rates null on no parsed rows. Import states/last-success/unresolved open+acknowledged count come from persisted records. Alerts use documented 20% duplicate and 10% invalid thresholds (≥2 rows), >7-day gaps and >10× historical median / >1,000 values with ≥5 saved completed records, without claiming fraud. Lifecycle/audit records preserve actor/time/reason; acknowledgment never edits finance or bypasses blockers.

Owners require current action/membership; staff require explicit merchant grants for writes/import/ack/resolve plus global role policy. Administrative and financing roles have no automatic access. New migration adds scoped grants, runs/intent, an installation signing key, alerts and lifecycle tables. Source/preview/session tampering, protected-field mass assignment, CSRF, arbitrary paths, unsafe spreadsheets/credentials and resource limits are enforced. No raw-storage or new unrestricted AI/MCP tool is exposed.

## Actual tests and demo verification

- `python -m unittest discover -s tests -q`: **188 tests passed in 190.300 seconds**. This includes the 157 prior regressions and 31 Task 02 tests with synthetic/isolated storage. Coverage includes types/precision/currency/date/status, CSV/XLSX/native dates/security/resource attacks, schema mapping, refunds/gross/net, actual thread concurrency, controls/exclusions/ambiguities, scoped grants/revocation/session/context, CSRF/protected fields, signed-source/dataset/mapping tampering, no partial finance, interrupted recovery/restart, retention, metrics/anomaly/lifecycle/isolation and legacy-text compatibility.
- `node scripts/verify_pos_ui.cjs`: passed. Verified six primary modules, collapse/active/context/direct refresh, manual/history, multi-file wizard, mapping back/reuse, exact duplicate preview, confirmation, folder/nested selection/cancel, monitoring/badge/drilldown/alert actions, all five original modules and mobile rendering; no JavaScript errors.
- `node scripts/verify_auth_ui.cjs`: existing authentication/User Management/first-password/consent/financing workflows passed with the new sidebar and explicit staff encoding grant.
- `node scripts/verify_security_ui.cjs`: existing Security Administration/config sharing workflow passed.
- Desktop preview and mobile DQ were visually inspected. Source syntax and `git diff --check` passed. Automated tests never opened the developer's live identity DB/ledger.

## Limits, Task 03 and demo instructions

Read the full guide and `examples/pos-reports/README.md`. Run the existing migrations/entry point, create separate business accounts and use M002/IDR synthetic reports. Configure scoped staff grants in User Management; never use administrator accounts as merchants. Existing local records remain in their own database.

Task 03 must consume permission-checked canonical completed/effective amounts plus provenance/quality, consolidate legacy/simulated sources and prevent double counting; POS sales alone are not complete cash flow. No new downstream adapter or Google Drive OAuth is implemented here, as explicitly required.

Known limits: transaction-level one-sheet values-only XLSX; aggregate/line-item imports unsupported; fixed explicit offsets rather than inferred IANA/DST; cooperative resource deadline rather than OS watchdog; conservative numeric-card detection may reject long numeric references; two-decimal amounts across supported currencies; JSONL/SQLite are not one distributed transaction and power-loss corruption is detected, not automatically repaired; process-local legacy projections and reviewed OS backups/permissions remain relevant. Canonical history is immutable; use distinct corrections/reversals rather than direct edits. Expiration is foreground-evaluated; raw filtered staging expires in 30 minutes, failed/abandoned metadata after 90 days, committed lineage/alerts/audit retained. Privileged filesystem/database compromise and secure-erasure certification remain outside this MVP. Security findings require team review.
