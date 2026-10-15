# Login and password recovery

All four roles use `/login` on the running application. See [setup/session details](../AUTHENTICATION.md) and [role boundaries](../SECURITY_PERMISSIONS.md).

1. Sign in with your assigned username/email and private password.
2. New accounts must change their temporary password, then sign in again.
3. System Admin uses platform administration; Bank lands at `/bank`; SME users see only permitted merchant modules. Changing a visible role label cannot change backend authority.
4. Sign out before demonstrating another account. Migration, password/security account changes and delegation changes can invalidate sessions.

An administrator-issued reset token is a private, expiring, single-use secret for one account's password recovery. It is not a session token, Gemini key or financing approval token. Authorized System Admin issues it through User Management; the intended user chooses the reset option on `/login`, enters the token and a compliant new password, then signs in. Never put tokens/passwords in Git or screenshots. Default lifetime is 30 minutes; current policy controls the actual expiry. Used/expired/replaced tokens are rejected.

Bootstrap is only for a database with no users. Do not delete an existing database to recover an account. Coach/demo_guest/restricted legacy user_admin remain denied until explicit supported-role mapping; they are not selectable demo access paths.

[Testing](../TESTING.md) · [Known limits](../KNOWN_LIMITATIONS.md).
