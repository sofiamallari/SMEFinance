# Role-based security and permissions

This is the canonical reference for the **provisional four-role POC baseline**. It documents implemented enforcement, not production banking certification. Module guides link here rather than redefine the policy.

## Roles and compatibility

| Stored authoritative role | Internal compatibility identifier | Authority |
|---|---|---|
| SYSTEM_ADMIN | security_admin | Platform account/security administration and administrative audit only. |
| SME_OWNER | owner | Assigned merchant operations, Staff delegation, Bank authorization and confirmed application submission. |
| SME_STAFF | staff | Explicitly delegated merchant actions; permitted financing drafts, never submission. |
| BANK | lender_analyst | Owner-authorized data categories and explicitly routed submitted packets; read-only review/export. |

`copilot/authorization.py` defines `POLICY` once; compatibility identifiers resolve to it. They do not supply independent privileges. Migration 007 maps unambiguous old Owner/Staff/Financing Agent/Security Administrator records, records original roles, preserves financial/audit history and revokes existing sessions. Coach, demo_guest and restricted legacy user_admin records remain unmapped and denied until a System Admin explicitly reviews a supported mapping. Their historical safeguards are retained; environment flags cannot enable them. Client role headers, demo identities and MCP API keys cannot establish authority.

## Module visibility

| Module | System Admin | SME Owner | SME Staff | Bank |
|---|---|---|---|---|
| Dashboard; transactions, single entry, POS import, history and quality | None | Own merchant | Explicit delegation | None |
| Digital Payments | None | Own merchant | Delegated, sufficient tier | None |
| Cash Flow; financing Overview, RBF, Progression Engine | None | Own merchant | Explicit delegation | Authorized categories through Bank review |
| Applications | None | Draft/edit/confirmed submit | Delegated own drafts only | Routed, authorized submitted packets |
| Bank Financial Review | None | None | None | Authorized merchant/categories |
| AI Financial Partner | None | Authorized tools | Delegated tools | Authorized read-only tools |
| User Management | Platform | Own-business Staff delegation | None | None |
| Security Administration | Platform | None | None | None |
| Bank Authorization | None | Own merchant | None | None |
| Audit | Administrative | Own merchant | None | Own authorized events |

Backend enforcement is authoritative. Hiding a submenu does not authorize records/actions. Bank direct URLs to original SME operational screens are denied; its financial views are at `/bank`. Undefined permissions fail closed.

## Authorization sequence

Every protected request resolves a live session and active account, authoritative role, enabled action, merchant membership/Owner scope, any required Staff grant or Bank authorization, applicable tier and resource ownership/routing. Cookies require CSRF on writes and same-origin protection. Existing exact action confirmation is required for simulated financing submission. T4 credit approval, real disbursement and real limit changes remain prohibited.

System Admin has no merchant memberships or financial tool authority. Owners cannot change platform policy. Staff cannot submit, authorize Banks, administer accounts or delegate permissions. Bank cannot mutate transactions/payments, submit for SMEs, administer users or record financing recommendations/declines as decisions. The legacy review mutation endpoint is denied; historical review records remain stored.

## Staff delegation

System Admin provisions accounts/memberships. Owner opens `/owner/users` and changes only an existing Staff member's grants for that owned merchant. Staff grants reuse `merchant_transaction_grants`; despite its legacy name it now covers delegated read, write, AI and draft actions. Role-level enabled actions bound those grants; permissions cannot exceed `STAFF_ACTIONS`.

For a draft-only workflow, delegate `use_copilot`, `view_applications`, `create_financing_draft`, `edit_financing_draft`. Additional reads/operations require their own explicit grants. Upload also requires individual optional `bulk_import` plus its merchant grant; the management UI maintains that optional grant from scoped upload assignments. Saving delegation revokes affected Staff sessions. Staff edit only their own permitted drafts; Owners can edit merchant drafts. Owner account creation/membership approval remains pending; Owners do not gain platform provisioning.

## Bank authorization versus routing

Owner manages `/consents`, now **Bank Authorization**. Existing consent storage is reused for named Bank, purpose, categories, expiry and revocation. Only active merchant-scoped Bank recipients are eligible. Selected Bank status/role/membership is rechecked when authorization is used. Purpose is 1–250 characters; choose at least one supported category and a future expiry within 366 days.

| Category | Protected capability |
|---|---|
| reports | Existing financial reports and Bank historical summaries/trends |
| assessment | Existing financial assessment/maturity/score evidence |
| forecasts | Cash-flow estimates and rule-based alerts |
| financing | Matching, RBF and journey information, each with its own action checks |
| applications | Submitted application packets routed to that Bank |

General financial reads do **not** need case assignment. Authorization never makes all merchant applications visible: packet recipient identity is checked separately. Owner explicitly selects the Bank in the draft/proposal; no first-consent automatic routing. Submission does not automatically authorize a Bank. Bank review/export checks each source category again before returning results; application assessment fields are withheld when assessment authorization is absent. Revocation/expiry blocks subsequent protected reads, exports and AI; it cannot recall prior downloads/screenshots.

## AI and policy configuration

`use_copilot` alone does not grant a financial tool. Each tool uses the same live action/merchant/category restrictions through `Principal`, `PolicyGuard` and `require`. Analysis tools are read-only; simulated writes use separate exact confirmation. Existing typed claim verification and freshness checks remain unchanged.

Maximum tiers: Owner T3, Staff T2, Bank T1, System Admin T0. Tier ceilings cannot add permissions. Portable policy JSON uses exactly four compatibility keys: `owner`, `staff`, `lender_analyst`, `security_admin`. It exports role-level policy, not accounts, Staff delegation, individual authorizations or credentials. See [configuration](SECURITY_CONFIGURATION.md).

## References

[Authentication](AUTHENTICATION.md) · [SME-to-Bank journey](SECURITY_SME_BANK_WORKFLOW.md) · [Bank review/APIs](BANK_FINANCIAL_REVIEW.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [Limits](KNOWN_LIMITATIONS.md).
