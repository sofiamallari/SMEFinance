# Bank Authorization

Current implemented guide · 16 October 2026.

## Purpose

Control which Bank account can read selected financial categories for a business.

## Access and prerequisites

SME Owner of the selected merchant. Use Create / Link Bank User to provision a new Bank or link an existing active Bank by its exact email; System Admin assignments also remain supported.

## Navigation

Owner sidebar → Bank Authorization (`/consents`).

## Step-by-step instructions

1. Select the merchant and open Bank Authorization.
2. If needed, choose Create / Link Bank User. For a new account enter username, email, display name and organization. Deliver the one-time activation token privately to the intended recipient; they set their password using `/reset-password`. No email is automatically sent. Linking an existing Bank does not reset or change its account.
3. Choose an eligible Bank recipient in Authorize Bank.
4. Enter a purpose, select needed categories and set an expiry within the allowed future range.
5. Review and grant consent through the existing form.
6. Inspect active/expired/revoked grants; revoke when access is no longer appropriate.

## Understanding results and statuses

Categories independently cover reports, assessment, forecasts, financing and applications. Grants are individual-account scoped. Submission routing does not automatically create a financial-data grant.

## Common errors and troubleshooting

An empty recipient list requires Create / Link Bank User or account status, Bank role and merchant assignment review. Do not choose an unrelated user or bypass filtering.

## Important limitations

Revocation blocks future protected reads; it cannot recall prior downloads/screenshots. Current submission separately requires applications authorization for the selected Bank. No organization-wide grant or Bank-initiated access request is implemented. Creating/linking an account alone never grants financial data access. Only new accounts receive an activation token; existing users must use their existing credentials or the administrator reset process.

## Related guides

[Financing and Revenue-Based Financing](financing-rbf.md) · [Bank Portal](bank-portal.md) · [Staff Access and Delegation](staff-access.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
