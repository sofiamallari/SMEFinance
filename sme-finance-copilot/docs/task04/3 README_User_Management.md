# User Management and Owner delegation

## System Admin: platform accounts

Open `/admin/users` → Create user → enter identity fields → choose System Admin, SME Owner, SME Staff or Bank → choose appropriate status/organization/memberships → private temporary password → Save account → reauthenticate. Bank requires an organization/demo scope; System Admin cannot hold merchant memberships. New users change their password on first login.

Search/filter and inspect account details/history. Supported account actions include edits, activation/deactivation, session revocation and administrator-issued password reset. System Admin cannot change its own authority/status through this page or remove the last active System Admin. Provisioning Bank membership does not authorize merchant financial access.

## SME Owner: own-business delegation

Open `/owner/users` → select the owned business → review assigned Staff → select only necessary supported actions → Save delegated access. Staff must sign in again. Only that merchant's grants change; there is no platform user creation, role change or unrelated membership management here.

For draft-only Staff, select `use_copilot`, `view_applications`, `create_financing_draft`, `edit_financing_draft`. Other reads, payments, entry/import and quality actions require separate grants. Upload requires both optional upload permission and merchant grant, maintained by the management form. Platform role policy/tier can further restrict all grants.

Use the Bank Authorization link for active scoped Bank recipients, grants/revocation and history. Own-business access history shows scoped metadata. New Staff account/membership provisioning is requested from System Admin; Owner account creation/membership approval is pending team rules.

Staff and Bank cannot manage accounts or grant themselves authority. Unmapped historical roles need explicit System Admin review; no automatic privileged mapping occurs.

[Canonical permissions/API enforcement](../SECURITY_PERMISSIONS.md) · [Complete journey](../SECURITY_SME_BANK_WORKFLOW.md) · [Recovery](1%20README_Login_Admin_User_and_Password_Reset.md).
