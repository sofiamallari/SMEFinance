# Documentation index

Current four-role documentation reviewed **15 October 2026 (Asia/Manila)** against the working implementation on `feature/security-sme-bank-workflow`. These pages describe implemented behavior; the role/module matrix and financial parameters remain provisional POC decisions.

## Start and develop

- [Repository overview/setup](../../README.md)
- [Authentication, migration and recovery](AUTHENTICATION.md)
- [Current technical architecture](ARCHITECTURE.md)
- [Role-based security, delegation and Bank authorization](SECURITY_PERMISSIONS.md) — canonical policy reference
- [Security policy JSON/configuration](SECURITY_CONFIGURATION.md)
- [Authenticated MCP setup](MCP_SETUP.md)
- [Testing and recorded evidence](TESTING.md)
- [Known limitations/pending requirements](KNOWN_LIMITATIONS.md)

## Business modules and journeys

- [Transaction History and Data Quality UI, pagination and verification](HISTORY_MONITORING_UI.md)

- [Merchant Transactions: worksheet selection, mapping and reconciliation](MULTI_WORKSHEET_IMPORT.md)

- [Business Overview Dashboard and verification](DASHBOARD_OVERVIEW.md)

- [Shared Owner/Bank navigation and labeled profiles](PORTAL_NAVIGATION_PROFILE.md)

- [Owner header, profile and navigation](OWNER_HEADER_NAVIGATION.md)
- [Bank header, reviewing merchant and profile](BANK_HEADER_NAVIGATION.md)
- [Shared System Admin layout across Security and User Management](SHARED_ADMIN_LAYOUT.md)
- [Account modal layout, permission grids and verification](ACCOUNT_MODAL_LAYOUT.md)
- [Initial Security Administration header verification](SECURITY_HEADER_NAVIGATION.md)

- [User module guides](task04/README.md)
- [SME-to-Bank end-to-end workflow](SECURITY_SME_BANK_WORKFLOW.md)
- [Bank Financial Review/APIs/export](BANK_FINANCIAL_REVIEW.md)
- [Modular Bank portal verification and screenshots](BANK_PORTAL_REPORT.md)
- [Canonical POS ETL/API details](POS_TRANSACTION_IMPORT.md)
- [Legacy transaction APIs and limitations](TRANSACTIONS.md)
- [AI architecture and financial evidence](TASK03_FINANCIAL_PARTNER.md)
- [Scenario pathways](task04/possible%20scenarios/README.md)

The role matrix is defined once in Security and permissions. Workflow/UI guides link to it. Templates reflect current source defaults, not team-approved policy. Use the [current JSON schema](security-config.schema.json) and [example](../examples/security-config.json); do not import older six-role examples blindly.

## Historical evidence and snapshots

These records retain their original scope, dates, calculations and test results; their old security/menu/API instructions are superseded:

- [Original application README](history/README_before_four_role.md)
- [Prototype module design](MODULE_DESIGN.md) — original financial context, historical architecture
- [Authentication implementation report](IMPLEMENTATION_REPORT.md)
- [Security administration report](SECURITY_ADMIN_REPORT.md)
- [Task 02 report](TASK02_REPORT.md)
- [Task 03 report](TASK03_REPORT.md)
- [Pre-Task 03 Gemini assessment](GEMINI_BASELINE_ASSESSMENT.md)
- [Business-logic provenance audit](task04/README_Business_Logic_Provenance_Audit.md)
- [Historical Word guides and diagrams](task04/HISTORICAL_DOCUMENTS.md)

Historical success counts do not replace the [final four-role evidence](../evidence/four-role-security-assessment-final.json). Older packaged ZIPs are snapshots and may omit current uncommitted implementation changes. Documentation maintenance does not update binary packages or claim fresh provider/test execution.
