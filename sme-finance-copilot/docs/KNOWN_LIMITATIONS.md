# Known limitations and pending decisions

## Implemented POC versus production controls

Four roles, action bounds, scoped delegation, Owner Bank authorization, routing, draft-only Staff, session/CSRF protections, exact simulated confirmation, category-filtered review/export, AI evidence verification and audits are implemented. See [recorded verification](TESTING.md).

MFA, production TLS hosting, automated backup/restore operations, external security monitoring and incident-response procedures are not implemented by this POC. HTTPS Secure-cookie configuration exists but requires actual HTTPS hosting. Administrator-issued reset tokens exist; email/self-service password recovery does not. Hash-chained audits are tamper-evident, not protection against a fully compromised service/database.

## Pending business requirements

- The module/permission matrix is a provisional team POC baseline, not institutional approval.
- Owner Staff account creation/membership approval is undefined; System Admin provisions, Owner delegates existing memberships.
- Bank authorization is individual-account scoped, not organization-wide. Bank-initiated requests are deferred; existing expiry/category rules remain.
- Coach/restricted legacy User Administrator mapping needs explicit administrator/team review; records are preserved and denied.
- Five journey-step completion criteria and post-activation outcome measurement are undefined; stages are not inferred from page visits or submissions.
- Existing assessment, forecast/alert, matching, RBF, incentive, MDR/tax and synthetic-profile rules remain provisional business assumptions. Security approval does not approve these formulas.

## Financial and product boundaries

No real money movement, lending approval/rejection, disbursement, new underwriting engine, organization-wide Bank grant, confidential Bank assessment authoring, real email or survival simulation is introduced. PDF/Excel Bank export is deferred; CSV is implemented. Previously viewed/exported data cannot be recalled after revocation.

Historical bank cash and post-financing outcome baselines are unavailable. Imported revenue does not establish wallet settlement; synthetic obligations can remain. Accounting refunds do not automatically refund simulator wallets; linked simulator refund support has no end-user UI/API. POS Cash only displays a notice. Canonical History and synthetic aggregate history have different coverage.

Full transcript restoration after reload/logout and unrestricted multilingual/causal AI analysis are not implemented. Provider availability is external; deterministic fallback is not proof of connectivity. Older ZIPs and Word guides are historical snapshots; use [current navigation](README.md).

## Modular Bank portal

The [Bank guide](BANK_FINANCIAL_REVIEW.md) documents six modules and the persistent read-only AI panel. Remote access changes are detected by periodic/on-focus checks, not server push. Conversations are page-memory scoped; refresh clears them. Existing audit listing is limited to the latest 100 own merchant events. No PDF/XLSX/email, arbitrary date-range export, portfolio aggregation or new financing decisions were added. Chart formatting does not change backend financial formulas.
