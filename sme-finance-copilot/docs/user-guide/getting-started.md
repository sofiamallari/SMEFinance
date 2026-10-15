# Getting Started, Login and Recovery

Current implemented guide · 15 October 2026.

## Purpose

Sign in to the correct role and recover account access.

## Access and prerequisites

An assigned active account and a running initialized application. New ZIP recipients should follow the [local setup guide](../operations/local-setup.md) first.

## Navigation

Open `/login`. Use your assigned username or email; the profile identifies your authenticated role.

## Step-by-step instructions

1. Enter your assigned username and password, then select Sign in.
2. If prompted to change a temporary password, enter the current password and matching new passwords. Sign in again afterward.
3. For the initialized CNY demo, use the assigned `demo_owner`, `demo_staff`, `demo_bank` or `demo_admin` account. Use the seed password privately supplied by the person who initialized that dataset.
4. If you cannot sign in, ask System Admin for a reset token. Expand Use an administrator-issued reset token, enter the single-use token and a new password, then sign in.
5. Use the profile menu to Sign out when finished.

## Understanding results and statuses

Role comes from the authenticated session. An administrator-issued reset token permits a password reset; it is not a password, account invitation or merchant-access grant.

## Common errors and troubleshooting

Old pre-cutover credentials belong to the archived identity database. A local `logs/cny-demo-credentials.json` may exist on the preparer’s installation; the seed command does not promise to create that file for every recipient. Repeated invalid attempts can lock an account; contact Admin rather than retrying indefinitely.

## Important limitations

There is no self-service signup, emailed recovery or MFA in this POC. Never send passwords, reset/session tokens or API keys through public chat/GitHub.

## Related guides

[SME Owner Portal](owner-portal.md) · [System Administration](system-administration.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
