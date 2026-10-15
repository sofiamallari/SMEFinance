# Merchant Transactions

Current implemented guide · 15 October 2026.

## Purpose

Record and inspect normalized financial activity with explicit import review.

## Access and prerequisites

Owner or appropriately delegated Staff, authorized merchant and compatible CNY source data.

## Navigation

Merchant Transactions → Single Transaction / Bulk POS Import / Transaction History / Data Quality & Monitoring / Transaction Settings.

## Step-by-step instructions

1. For Single Transaction, choose type, date, amount, method, status, reference and relevant details; validate and save. Merchant currency is fixed by configuration.
2. For CSV/XLSX import, upload files; select worksheets for Excel. Automatic detection excludes clear summaries and requires review when boundaries are uncertain.
3. Map each source independently; distinguish Revenue and Expense meaning. Confirm required mappings and review only unknown/ambiguous payment labels.
4. Validate: review five summary cards and one outcome. Correct actionable errors, duplicates, warnings and source-control failures. There is no Save Mapping Template section on this screen.
5. Continue to Preview: review Ready to Import and Net Transaction Total, normalized rows, sources and pagination. No Reconciliation Details section is shown here.
6. Use Back to Mapping or Back to Validate for corrections. Continue to Import retains the explicit confirmation prompt before saving.
7. Review Transaction History and Data Quality & Monitoring afterward.

## Understanding results and statuses

Net Transaction Total is the backend completed signed total, including negative expenses/refunds/reversals; it is not sales revenue. Exact duplicates can be excluded; conflicting identifiers, invalid rows or reconciliation failures can block the batch. Saved template support elsewhere is retained.

## Common errors and troubleshooting

Correct the source or mapping and validate again when blocked. Formula-based financial values are not evaluated as trustworthy transaction data. Unsupported currency is rejected without conversion. Missing required merchant settings require an authorized configuration review.

## Important limitations

Do not import the same sale and separately create its sandbox collection as a different unlinked sale. Independent source controls are never invented. Preview simplification does not remove backend reconciliation, security or audit checks.

## Related guides

[Dashboard and Business Overview](dashboard.md) · [Digital Payments](digital-payments.md) · [Staff Access and Delegation](staff-access.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
