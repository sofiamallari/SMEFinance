# Canonical role and permission model

This is the single maintained permission reference for the provisional four-role POC baseline. User/module guides link here; source enforcement is [authorization.py](../../copilot/authorization.py), [auth.py](../../copilot/auth.py), [security.py](../../copilot/security.py) and [bank_workflow.py](../../copilot/bank_workflow.py).

| Stored role | Internal identifier | Scope |
|---|---|---|
| SYSTEM_ADMIN | security_admin | Administrative account, merchant configuration, bounded policy and administrative audit; no automatic financial access |
| SME_OWNER | owner | Assigned merchant operations, Staff delegation, Bank authorization and explicitly confirmed application submission |
| SME_STAFF | staff | Explicit per-merchant grants bounded by the role policy; own permitted drafts, never submission |
| BANK | lender_analyst | Assigned/routed requests and independently consent-authorized financial categories; permitted simulated review history |

## Enforcement and visibility

Live session → active account → supported authoritative role → enabled role action → active merchant membership → Staff grant or applicable Bank category consent → resource ownership/routing → tier and action confirmation. Cookie writes require the existing CSRF/origin checks. Undefined permissions deny. Hiding navigation is not authorization. System Admin remains without merchant financial membership/authority; Bank cannot use direct Owner routes to modify records.

| Capability | Owner | Staff | Bank | System Admin |
|---|---|---|---|---|
| Dashboard, transactions, import, quality, forecasts | Assigned merchant | Explicit relevant grants | Authorized financial summaries through Bank review, no operational mutation | None |
| Digital Payments / Owner AI | Authorized sandbox/financial tools | Explicit grants and applicable tiers | No visible Owner/Bank AI drawer; retained backend read capabilities remain guarded | None |
| Financing drafts | Merchant drafts | Own delegated drafts | No SME draft editing | None |
| Financing submission | Explicit Bank selection, current applications authorization and confirmation | Denied | Denied | Denied |
| Bank authorization / Staff delegation | Owned merchant | Denied | Denied | Provisions assignments, cannot substitute for Owner consent |
| Simulated Bank review | Reads feedback | Delegated application visibility only as implemented | Receiving Bank, record_bank_review, live assignment and submitted request | None |
| Account/merchant/security administration | No platform provisioning | None | None | Authorized administrative actions only |

The current Bank portal has three navigation modules and no AI panel. Backend compatibility tools are not a promise of a visible UI and cannot bypass category consent. Maximum compatibility tiers remain Owner T3, Staff T2, Bank T1 and System Admin T0; configured reductions cannot add authority. T4 real credit approval, disbursement and real limit changes remain prohibited.

## Delegation

System Admin creates accounts and memberships. Owner changes only supported grants for existing Staff in the selected merchant. STAFF_ACTIONS is the hard upper bound; live role policy can narrow it further. Upload needs its supported optional permission and merchant grant; existing management services synchronize these. Saving delegation revokes affected Staff sessions. No account receives financial access merely because it is an administrator. Source reference seed preserves a Staff account with no initial grants.

## Routing, financial consent and review are separate

Owner chooses an active assigned Bank and purpose, one or more categories and a future expiry within 366 days. Categories are reports, assessment, forecasts, financing and applications. Grants are individual-account scoped and subject to expiry/revocation and current parties/membership.

Current draft submission requires applications-category consent for the explicitly selected Bank; it does not auto-create any financial grant. Safe routed application metadata and simulated review history are available to the receiving Bank through BankWorkflow.applications without broad financial access. Detailed financial sections/CSV still reauthorize their own categories. Revocation can leave routing metadata visible while blocking protected financial reads. Prior exports/screenshots cannot be recalled.

Only the receiving scoped Bank with record_bank_review can append Reviewed, More Information Needed (note required) or Ready for Further Assessment. Review appends a row; it does not approve/reject, disburse, or change the submitted request lifecycle into a loan decision. Earlier documentation saying all review mutations are disabled is superseded.

## Identity, compatibility and AI

No client role headers, demo identity environment values or MCP API key establish identity in authenticated mode. Unmapped coach/demo_guest/restricted legacy administrator records remain denied pending supported role review. Compatibility identifiers are aliases, not extra privileges.

use_copilot alone does not authorize every financial tool. Live Principal/PolicyGuard checks, domain services, typed claim/evidence checks, source freshness and merchant-scoped context apply. Existing sensitive sandbox actions use separate proposals and explicit confirmation. Suggested questions are not authorization.

Policy JSON represents bounded role-level configuration; it is not users, passwords, Staff delegation or Bank grants. See [security configuration](security-configuration.md), [architecture](architecture.md), [limitations](known-limitations.md) and [account recovery](../operations/authentication.md).


## Local Bank workflow extension — 16 October 2026

SME Owner Bank Access Management uses existing `manage_consents` authority scoped to the selected owned merchant. `/api/owner/banks/invite` accepts only merchant and new-recipient identity fields. Existing active BANK accounts are looked up by exact email and linked without modifying passwords, reset tokens, profile or role. New accounts use existing account validation/password hashing and a hashed, expiring, single-use reset token for initial activation. There is no email delivery integration; the Owner must deliver that new-account token privately to the intended recipient. Email/organization identity is not independently verified; this is a local simulated POC, not bank identity assurance.

BANK financial reads continue through existing consent categories. Routed application metadata and review history additionally require current `applications` consent. Routing never substitutes for active consent. Owner/Staff/Admin cannot invoke Bank review decisions. `record_bank_review` remains the existing BANK permission; only the actual routed recipient can decide. Final simulated APPROVED/REJECTED packet updates, review history and audit inserts use the existing SQLite `BEGIN IMMEDIATE` transaction, preventing concurrent overwrites. Decision actor and time are backend-derived. No loans or funds are created.

Digital Payments Simulator writes only dedicated simulator state tables. Its rows, statuses, wallets and current timestamps are excluded from financial analytics/versioning. Existing historical simulator journal records are retained as evidence, not reclassified as business revenue.
