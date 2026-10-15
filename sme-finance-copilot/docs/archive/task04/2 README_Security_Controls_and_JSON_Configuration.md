> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Security Controls and JSON configuration

Sign in as System Admin and open `/admin/security`. SME users and Bank cannot administer platform policy. Use the profile icon for authenticated username/role and Sign out; User Management is in the sidebar (Navigation on mobile), subject to permission. See [header guide](../implementation-notes/SECURITY_HEADER_NAVIGATION.md).

Sections: Overview, Authentication, Roles & Permissions, AI & MCP Controls, Bank Authorization Policies, Audit & Monitoring, Configuration. Bank Authorization Policies is explanatory/read-only; actual grants belong to SME Owners at `/consents`.

To share policy: Export Configuration → review the nonsecret JSON → on another installation choose Validate and preview → inspect every difference → Apply Configuration with explicit confirmation and administrator reauthentication. Validation/preview/cancel do not save policy. Expired/stale/substituted/reused previews are rejected.

Portable schema v1 now requires exactly four compatibility keys: `owner`, `staff`, `lender_analyst`, `security_admin`. They resolve to the authoritative roles in [permissions](../../technical/security-permissions.md). Older six-role files are not current import templates. Use a current export or the [example](../../task04/security-config.example.json), reviewing settings before applying them.

JSON contains bounded global authentication, role action and tier settings. It does not copy credentials, accounts, Staff delegation, merchant memberships, Bank authorizations, applications or financial records. Enabling a role action never bypasses those local checks; T4 cannot be enabled. Templates are provisional defaults, not approved team policy.

The full [configuration reference](../../technical/security-configuration.md) owns schema/ranges/APIs/preview guarantees; [authentication](../implementation-notes/AUTHENTICATION.md) owns sessions/recovery; [testing](../implementation-notes/TESTING.md) owns recorded evidence.
