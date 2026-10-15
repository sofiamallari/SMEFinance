# System Administration

Current implemented guide · 15 October 2026.

## Purpose

Manage accounts, merchant configuration and bounded platform security policy.

## Access and prerequisites

An active System Admin with the relevant administrative permissions; sensitive actions may require reauthentication.

## Navigation

`/admin/security`, `/admin/users`, `/admin/merchants`; shared profile and sidebar.

## Step-by-step instructions

1. Use Merchant Management to search/view merchants and create or edit supported profile/settings fields.
2. Use User Management to create accounts and assign supported roles and merchant memberships.
3. Search/filter accounts; use Details/Edit, Suspend, Reset password or Revoke sessions as needed.
4. Give reset tokens privately to the intended user; never publish them.
5. Use Security Controls, Roles & Permissions, AI & MCP Controls and Audit & Monitoring for their authorized administration tasks.
6. For policy JSON, export or validate an import, review the full difference preview and explicitly confirm. Cancel if the change is not intended.

## Understanding results and statuses

An active account is not an unrestricted account. Policy imports contain role-level security configuration, not users, passwords, Staff grants or Bank consent.

## Common errors and troubleshooting

Reauthenticate when requested. Invalid configuration, unsupported role assignments or currency changes protected by existing financial activity are rejected.

## Important limitations

Administration grants no merchant financial access or AI authority. No automatic grants or production banking certification are implied. New merchant provisioning does not automatically assign an Owner.

## Related guides

[Getting Started, Login and Recovery](getting-started.md) · [Staff Access and Delegation](staff-access.md) · [Bank Authorization](bank-authorization.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
