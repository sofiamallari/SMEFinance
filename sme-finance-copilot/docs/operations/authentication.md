# Authentication, initialization and recovery

Current server identity comes from live SQLite sessions; there is no client-controlled role switching. Start with [local setup and CNY seeding](local-setup.md), not an old instruction to bootstrap before the selected dataset exists. The supported demo seed creates the initial four synthetic role accounts. `python -m copilot.auth bootstrap` is available only before the first user exists in an appropriately initialized/selected store; it is not a reset mechanism or a way to create a second Admin in the seeded database.

System Admin provisions additional users through existing User Management. Passwords use existing scrypt hashing; sessions/reset-token secrets use existing digests. Default minimum password length is 12 with lowercase/uppercase/number; actual persisted policy can be stricter. Do not copy a teammate’s private credentials or an archived password into a public guide.

Recovery: Admin selects the intended account, issues a supported single-use reset token after any required reauthentication, and gives it privately to the user. User opens the login token section and sets a new password. Token expiry, account status, session revocation and current role/merchant grants continue to apply. No email sending, self-service reset or MFA is implemented.

Failed sign-ins can cause temporary lockout. Do not brute-force guesses. Confirm username/dataset, ask Admin to inspect status, and use supported reset/unlock/session actions. Never edit the SQLite password hash to bypass the application.

Cookie sessions use HttpOnly/SameSite behavior and CSRF for writes; COPILOT_HTTPS=yes requires real HTTPS. Recovery/account actions and permissions are in [canonical security](../technical/security-permissions.md). [End-user login](../user-guide/getting-started.md) · [troubleshooting](troubleshooting.md).
