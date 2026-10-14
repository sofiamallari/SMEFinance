# Merchant Transactions User Guide

## Purpose and menu

Expand **Merchant Transactions** to open:

| Submenu | Route |
|---|---|
| Single Transaction | `/merchant-transactions/single` |
| Bulk POS Import | `/merchant-transactions/import` |
| Transaction History | `/merchant-transactions/history` |
| Data Quality & Monitoring | `/merchant-transactions/data-quality` |

Owners need the enabled transaction permissions for assigned merchants. Staff
encoding/upload/alert actions require explicit per-merchant grants; upload also
requires the individual optional bulk-upload permission. Financing Agents and
administrators cannot modify transactions through administrative authority.

## 1. Save a single transaction

1. Select the merchant and open **Single Transaction**.
2. Enter date/time, net amount, type, payment method, status and external reference.
3. Add category and an optional description. Currency is fixed by the merchant.
4. Click **Save transaction** and inspect the backend-confirmed ID.
5. Open history and Dashboard with matching dates to check the result.

Enter a positive absolute amount. Type determines its sign: Sale/income is positive;
Expense, Refund and Reversal are negative internally. Only **completed** records
have financial effect. Pending, failed and voided records do not create revenue.

Amounts must be finite, no more than one trillion and exact to at most two decimal
places. Completed zero amounts, unsupported channels/statuses, incorrect currency,
invalid/future dates, protected fields and sensitive/formula-like text are rejected.
Do not enter card numbers, customer personal data, passwords or tokens.

## 2. Upload POS reports

The wizard is **Select Files → Map Columns → Validate → Preview → Import**.

1. Select transaction-level CSV/XLSX files or a browser-selected folder.
2. Click **Continue to Map Columns**.
3. Review each file's mapping. Map date and **net or gross amount** explicitly;
   supply supported currency/type/status/channel mappings or explicit defaults.
4. Select the correct date format/timezone. Reuse mapping only for matching schemas.
5. Click **Run validation** and inspect errors, duplicates and reconciliation.
6. Correct problems and validate again before continuing.
7. Open the exact normalized Preview and inspect signed amounts and source data.
8. Click **Confirm Import** and accept confirmation only if the preview is correct.
9. Inspect the confirmed outcome, history and Data Quality view.

No records are committed merely by selecting files, mapping, validating or previewing.
**Cancel** leaves that batch uncommitted; **Import Another Batch** starts a new wizard.

### File limits and known request-size gap

Extractor/UI limits: 10 files, 3 MB per file, 10 MB total, 5,000 rows and 30 columns.
The current HTTP body cap is about 4.1 MB and uploads contain base64 JSON overhead.
Therefore a multi-file batch can be rejected below the advertised 10 MB limit.
Use smaller combined batches when needed; this mismatch remains documented.

Only one transaction per row is supported. Aggregate daily/monthly summaries,
unsafe file paths, sensitive headers and unsupported workbook/formula content fail.
Folder selection does not give the application access to arbitrary host directories.

## 3. Monetary mapping and duplicate reconciliation

Where gross components are supplied:

`net = gross - discount + tax - refund component`

Mapped net must agree with this result. Adjustments must be nonnegative.
**Settlement is not sales revenue** and must not be mapped as sales net/gross.
Generic Amount requires an explicit interpretation.

- Exact duplicate records are excluded according to merchant-scoped references,
  fingerprints and source identity rules.
- Conflicting references/ambiguous matches block commit; they are not silently
  discarded as harmless duplicates.
- Count reconciliation is `parsed = eligible + duplicates + invalid`.
- Reported monetary controls are checked using the selected completed-net or
  nominal-net basis. Missing controls show a warning/not_available, not proven reconciliation.
- New ledger duplicates after preview force revalidation.

Staging expires after 30 minutes. A stale/changed/session-mismatched preview cannot
commit. An already-committed POS batch cannot be committed again; inspect its saved outcome.

## 4. Transaction History

Filter dates, status, source and payment method, then click **Filter**. Use page
controls for more records. The table shows ID/reference, time, signed net, type,
method, status, source and batch.

History contains committed canonical journal records, not all synthetic Dashboard
history. The Source dropdown currently lacks a simulated_payment option; use
**All** to view simulation entries. Obsolete text saying Task 03 integration is
deferred does not describe the current implemented integration.

There is no general edit/delete UI for canonical committed rows. Legacy transaction
management APIs use a different schema; do not assume they edit canonical POS rows.

## 5. Data Quality & Monitoring

1. Open the view and click **Refresh / Recheck**.
2. Review import metrics, unresolved alerts and available filters.
3. Open an import run to inspect source metadata, mapping version, findings,
   reconciliation, commit outcome and alert events.
4. If permitted, acknowledge an open alert with a reason.
5. Resolve an acknowledged alert only after checking evidence; provide 8–500 characters.

Alert lifecycle: **Open → Acknowledged → Resolved**. Alert status cannot bypass
validation or change financial records. The menu badge is the backend unresolved
count for the current authorized merchant. Monitoring runs during foreground
operations, not as a continuously scheduled background service.

## 6. Refunds and a worked example

Completed Sale100, Refund25 and Expense20 produce net sales75 and net income55.
Manual/POS refunds reduce accounting sales but are not automatically linked/capped
to an original payment and do not reverse sandbox-wallet settlement. Avoid importing
both a refund component already deducted from net and an additional refund row for
the same effect. Linked simulator refunds are backend-only; no refund button/API exists.

## Troubleshooting and implementation

Access denied: verify membership, role action and required Staff grants. Validation
failed: fix the identified source field/mapping. Expired preview: restage/revalidate.
Ledger integrity failure: stop and seek verified recovery; do not delete records.

UI: `web/merchant-transactions.js` and `web/index.html`. Backend:
`copilot/pos_extract.py`, `copilot/canonical_transactions.py`, `copilot/pos_import.py`,
`copilot/transaction_journal.py`. Main API families: `/api/merchant-transactions`,
`/api/pos-import` and `/api/data-quality`.
This guide did not import, alter or delete any transactions.
