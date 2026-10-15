> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Bank Financial Review — quick user guide

1. Sign in as **Bank** and open `/bank`. Select a currently Owner-authorized merchant in the header.
2. Use **Overview** for recorded totals/trend, risk summary and authorization context.
3. **Authorized Merchants** lets you search, sort and select a business; expand its individual grant dates/expiries. Owner alone can change authorization.
4. **Financing Applications** lists only submitted packets routed to your Bank. Search/filter/sort, then select a reference and expand its evidence.
5. **Financial Review** contains collapsed performance, estimated forecast, assessment, financing matches, RBF and maturity/journey sections. Expand only what you need. Missing categories/data are clearly unavailable.
6. **Reports & Exports** shows the current scope and downloads audited CSV; **Review Activity** shows your own merchant events with filtering/sorting.
7. Ask a financial question in the persistent right-side **AI Financial Partner**. It is read-only, category-limited and merchant-scoped. Changing modules retains the conversation; changing merchants shows that merchant's thread. Refresh clears page-memory history.
8. Collapse navigation/AI when needed. Mobile AI is an overlay; Escape closes it. Direct hashes such as `/bank?merchant=M002#financial` retain the view without granting access.

Revocation/expiry invalidates protected sections and chat when detected; every backend read/export/tool rechecks permissions immediately. Forecasts, scores and RBF are existing POC calculations, not credit decisions. No approval, rejection, submission or funds-movement control exists.

The [maintained module reference](../implementation-notes/BANK_FINANCIAL_REVIEW.md) owns APIs, component design, freshness and export details. [Permissions](../../technical/security-permissions.md) owns category/routing rules; [workflow](../implementation-notes/SECURITY_SME_BANK_WORKFLOW.md) describes the full SME-to-Bank demo; [verification](../implementation-notes/BANK_PORTAL_REPORT.md) records actual checks and screenshots.
