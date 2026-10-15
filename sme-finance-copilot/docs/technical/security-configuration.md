# Security configuration

System Admin uses `/admin/security` for Overview, Authentication, Roles & Permissions, AI & MCP Controls, Bank Authorization Policies, Audit & Monitoring and Configuration. Merchant Management/User Management are separate pages in the shared sidebar. There is no merchant selector or AI drawer for Admin.

The role/action upper bounds live in [one permission model](security-permissions.md). JSON import/export edits supported role-level configuration only; it cannot create accounts, memberships, Staff grants or Bank consent, increase immutable boundaries, or allow T4 actions. Existing schema: [security-config.schema.json](../security-config.schema.json); [example](../../examples/security-config.json). Example values are not an instruction to import without review.

Export current settings; for import, select JSON, validate it server-side, inspect the complete differences and confirm or cancel. Sensitive changes require recent reauthentication. Existing bounded authentication settings include password length/complexity, failed-attempt thresholds, session limits and reset-token lifetime. Current persisted policy, not an old screenshot, determines effective values. Import is atomic within the existing SQLite policy transaction and recorded in administrative audit.

Defaults and accepted bounds are defined in [auth.py](../../copilot/auth.py); configuration validation is in [security_configuration.py](../../copilot/security_configuration.py). No new security feature was introduced by documentation consolidation. [User administration](../user-guide/system-administration.md) · [known gaps](known-limitations.md).
