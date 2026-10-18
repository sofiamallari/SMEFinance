# Bank Portal

Current implemented guide · 16 October 2026.

## Purpose

Review applications routed to your Bank and the financial information separately authorized by the Owner.

## Access and prerequisites

An active assigned Bank account. Financial categories require current Owner consent; routing alone is insufficient.

## Navigation

Sign in → `/bank`; sidebar: Overview, Merchant Dashboard, Financing Applications, Authorized Merchants.

## Step-by-step instructions

1. Open Overview for routed request counts and recent applications.
2. Use Financing Applications to filter requests and open View Details.
3. Review Request Details, Financial Review, Bank Review and History in the application dialog.
4. Open Authorized Merchants to inspect current grants and available authorized financial review.
5. Select an authorized business in Reviewing Merchant, then open Merchant Dashboard. Financial performance is expanded by default; other evidence remains category-scoped. Download Financial Review (CSV) uses the displayed period.
6. Record a review: Reviewed, More Information Needed (a note is required) or Ready for Further Assessment. Banks record reviews only. The app does not approve, reject or disburse financing, and it does not simulate underwriting; any credit decision happens outside the app.

## Understanding results and statuses

Submitted request metadata and review history require active applications-category consent as well as recipient routing. Revocation or expiry immediately blocks subsequent protected requests. Financial sections can independently be unavailable according to category grants.

## Common errors and troubleshooting

If a merchant or section disappears, check expiry, revocation, assignment and account status. Refresh rather than relying on a previous screen.

## Important limitations

There is no Bank AI panel or six-module Bank navigation in the current portal. There are no Approve or Reject actions: Banks record reviews only. The app does not approve, reject or disburse financing, and it does not simulate underwriting; any credit decision happens outside the app. Applications or reviews saved by an older version as approved or rejected are shown as **Review Closed**.

## Related guides

[Bank Financing Applications and Review](bank-review.md) · [Bank Authorization](bank-authorization.md) · [Financing and Revenue-Based Financing](financing-rbf.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
