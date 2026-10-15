> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Bank Authorization and eligible recipients

The existing `/consents` route now displays **Bank Authorization**. Storage remains compatible with historical consent records; [permissions](../../technical/security-permissions.md) is the current category/routing reference.

## Authorize as SME Owner

1. Sign in as Owner and select the owned business.
2. Choose an active Bank assigned to that merchant.
3. Enter purpose, future expiry and needed financial data categories.
4. Select Authorize Bank and inspect authorization history.
5. When financing is needed, separately choose that Bank in an application draft and confirm the exact submission proposal.

General Bank financial reads do not require a case. Application packets remain recipient-routed and require their category. Neither Bank membership nor submission creates authorization automatically. The selected Bank's role/status/membership and authorization are rechecked. Revocation/expiry blocks subsequent protected access and exports; it cannot recall previous downloads.

## Empty or failed recipient list

The list includes only active merchant-scoped Bank accounts. If none exist, the form explains the empty state and disables submission. Ask System Admin to provision/assign a correctly scoped Bank in the intended local demo environment; do not create production demo accounts or disable RBAC. Unrelated users and unmapped Coach accounts are excluded.

Loading and API failures disable submission; retry by selecting the business. Older requests cannot replace a newer merchant's recipient list. Account changes after loading are rechecked on save/use.

To revoke, select Revoke in authorization history and confirm. Existing grant/revoke APIs and historical event codes remain; category, purpose and expiry requirements are described once in [the canonical security guide](../../technical/security-permissions.md).

[Bank review](../implementation-notes/BANK_FINANCIAL_REVIEW.md) · [Demo steps](../implementation-notes/SECURITY_SME_BANK_WORKFLOW.md) · [Recorded tests](../implementation-notes/TESTING.md).
