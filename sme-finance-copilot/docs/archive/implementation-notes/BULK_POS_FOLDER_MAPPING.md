> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Bulk POS Import — folder-style column mapping

Branch: `feature/security-sme-bank-workflow`. Existing work retained; no commit,
push, merge, branch change, reset or production/demo data modification.

## Implemented

- Workbook filename appears once above compact, connected folder-style worksheet
  tabs. CSV sources retain their own group. One mapping panel is visible at a time.
  Tabs expose selection/status, arrow/Home/End keyboard controls and focusable
  entries for each workbook group. Mobile tab strips scroll horizontally.
- Mapping selections and financial confirmations are captured per source and survive
  switching tabs. The existing mapping API payload structure is retained.
- Five editable primary fields: recommended Transaction ID, Transaction Date,
  Transaction Amount, Transaction Type and Payment Method. Source columns and fixed
  worksheet values use separate option groups; no duplicate primary controls appear
  in Additional Fields.
- Detected report classification is compact. Change Type reveals its editor only
  when needed; uncertain classification requires selection and confirmation.
  Classification corrections preserve existing mappings/defaults, invalidate the
  classification/type/amount confirmations, and disable old preview/commit controls.
  A preserved default conflicting with the new profile stays blocked for review.
- Additional Fields (Optional) and Import Settings & Reconciliation are collapsed
  by default on rendering. All existing supported optional mappings remain editable.
  Required confirmations sit at the panel bottom; irrelevant confirmations are hidden.
- Financial help appears only on meaningful `?` controls: amount meaning, gross/net,
  refund component and settlement. Hover, focus and click/keyboard interaction show
  the help without adding a UI library.
- Only unfamiliar sampled payment labels need contextual translation controls.
  Existing verified normalization (including QR) is retained; no method is guessed
  for missing expense data. Saved translations remain in captured payloads even when
  redundant controls are not displayed.
- Readiness shows the real per-source mapping/confirmation preflight state. Known
  currency mismatch, missing fields, unconfirmed defaults/generic Amount and missing
  sampled-label resolutions block validation. Recorded blocking validation findings
  appear as Validation Error when returning to mapping. Ready means ready to request
  full backend validation, not that all transaction values have already passed it.

## Backend/API scope

Only an additive read-only `payment_method_aliases` field was added to the existing
merchant settings response (`copilot/transaction_settings.py`). It serializes the
existing canonical `METHODS` catalog so the frontend does not maintain a second
normalization rule table. No alias rule, permissions, import request contract,
financial formula, transaction sign, data model or database schema changed.

Validation, reconciliation, duplicate detection, monetary precision, per-row source
provenance, preview, explicit commit and audit remain in the existing backend.
No FX conversion or merchant currency change is introduced.

## Focused verification actually run

- PASS: modified JavaScript syntax and Python compilation; diff whitespace check.
- PASS: existing `scripts/verify_report_profiles.cjs`, updated only for the new UI:
  **48 checks**. Covers independent mappings, collapsed sections, five primary rows,
  type correction without silent mapping overwrite, required confirmations, direct
  edits, exact combined preview/commit, expense signs, fee/subcategory provenance,
  uncertain CSV mapping and desktop/tablet/mobile widths.
- PASS: **14 existing report-profile backend tests** via isolated regression runner,
  restricted to `test_report_profiles.py`; zero failures/errors/skips.
- PASS: brief actual Bao Burgers workbook smoke in a disposable IDR fixture: two
  selected XLSX worksheets under one workbook title, one active panel, independent
  confirmations, collapsed advanced controls, missing expense method blocked, missing
  required date blocked, CNY/IDR mismatch blocked and payload keys retained. No Bao
  transactions were committed. Mobile page-overflow check passed.
- NOT RUN: full backend regression, extensive browser suites, cross-browser testing.
- Frontend build: NOT RUN — this static frontend has no separate build script.

The focused browser test's old assertions about duplicate adjustment controls and
automatic profile-change overwrites were replaced with checks for their explicitly
requested replacements; financial validation/commit assertions remain intact.

## Known limits

Bao source CNY cannot be imported into an IDR merchant under the current policy.
Missing expense payment methods require trustworthy source data or an explicitly
verified supported default. The redesign intentionally does not bypass either blocker.
Frontend unfamiliar-label controls use returned value samples; backend validation
still checks all rows and may find additional unknown labels or row-value errors.
No currency conversion, fee-expense inference or additional accounting field was added.

Files changed: `web/transaction-settings.js`, `web/index.html`,
`copilot/transaction_settings.py`, `scripts/verify_report_profiles.cjs`, this report
and documentation index. Focused evidence is in `evidence/report-profiles/`,
`evidence/folder-mapping/` and the report-profile backend runner JSON.
