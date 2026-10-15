# Bank Authorization

Current implemented guide · 15 October 2026.

## Purpose

Control which Bank account can read selected financial categories for a business.

## Access and prerequisites

Owner of the merchant; an eligible active Bank must already be assigned by System Admin.

## Navigation

Owner sidebar → Bank Authorization (`/consents`).

## Step-by-step instructions

1. Select the merchant and open Bank Authorization.
2. Choose an eligible Bank recipient.
3. Enter a purpose, select needed categories and set an expiry within the allowed future range.
4. Review and grant consent through the existing form.
5. Inspect active/expired/revoked grants; revoke when access is no longer appropriate.

## Understanding results and statuses

Categories independently cover reports, assessment, forecasts, financing and applications. Grants are individual-account scoped. Submission routing does not automatically create a financial-data grant.

## Common errors and troubleshooting

An empty recipient list requires account status, Bank role and merchant assignment review. Do not choose an unrelated user or bypass filtering.

## Important limitations

Revocation blocks future protected reads; it cannot recall prior downloads/screenshots. Current submission separately requires applications authorization for the selected Bank. No organization-wide grant or Bank-initiated access request is implemented.

## Related guides

[Financing and Revenue-Based Financing](financing-rbf.md) · [Bank Portal](bank-portal.md) · [Staff Access and Delegation](staff-access.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
