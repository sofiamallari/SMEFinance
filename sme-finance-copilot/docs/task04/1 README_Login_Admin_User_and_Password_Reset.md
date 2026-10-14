# SME Finance Copilot Login Guide

This guide explains administrator access, business-user access, and the
**Use an administrator-issued reset token** option on the login screen.
It describes the implemented authenticated application. No passwords or tokens
are included in this file.

## 1. Where to sign in

Start the application from the `SMEFinance/sme-finance-copilot` folder:

```powershell
python -m copilot.server --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/login**.

Administrators and business users use the **same login page**. Enter your assigned
username or email and password. The application uses your saved account role to
decide which pages you can access. There is no separate administrator password
shared by all accounts, and no public self-registration.

For the owner's current checkout, the application folder is:

`C:\Users\User\source\repos\SMEFinance\sme-finance-copilot`

Teammates should use their own clone location. Pulling Git transfers code, not
another installation's accounts, passwords, API key or local database.

## 2. What is administrator access?

| Account role | Main page | What it can do |
|---|---|---|
| User Administrator | `/admin/users` | Create and manage permitted business accounts, merchant memberships, Staff grants, password-reset tokens and sessions. Cannot manage privileged administrator accounts. |
| Security Administrator | `/admin/security`, also `/admin/users` | Manage bounded security policies, role permissions, AI tier ceilings, audit/configuration controls and administrator-authorized account actions. |

Sensitive changes ask the administrator to re-enter their own password.

**Administrator authority does not grant financial access.** An administrator
account does not automatically operate Dashboard, payments, financing or the
financial chatbot. To operate a business, use a separately authorized business
account with merchant membership.

On a completely fresh installation, create the first Security Administrator with:

```powershell
python -m copilot.auth migrate
python -m copilot.auth bootstrap --username admin --email admin@example.test
```

Choose a private password at the terminal prompts. The username above is an
example; it does not create a universal default password.

If the message says **Bootstrap is available only before the first user exists**,
use the existing administrator account. Do not delete the database or rerun
bootstrap to reset an existing password.

## 3. What is business-user access?

| Account role | Main purpose | Important restrictions |
|---|---|---|
| Business Owner | Review assigned merchant Dashboard, transactions, payments, cash flow, financing and AI analysis; manage consent and confirm sandbox applications. | Requires merchant membership and enabled permissions. Cannot approve actual credit or move real funds. |
| Staff | Perform permitted operational work for assigned merchants. | Transaction entry requires an explicit merchant grant. Upload requires optional bulk-upload permission plus a merchant bulk-upload grant. Financing is restricted. |
| Financing Agent | View assigned, consent-authorized financing information and review assigned sandbox applications. | Cannot encode transactions or simulate payments. Needs current consent and the required assignment. |

The administrator creates these accounts in User Administration and assigns
appropriate roles and merchants. Menus may differ between users.

To test another role, **sign out and sign in with that role's separate account**.
Changing the visible role selector does not change authenticated authority.

## 4. First login with a temporary password

1. Obtain your assigned username and temporary password privately from the administrator.
2. Sign in on `/login`.
3. If **Change your password** appears, enter the current temporary password,
   a new password, and its confirmation.
4. Click **Change password**.
5. Sign in again using the new password.

The default minimum is 12 characters with uppercase, lowercase and a number.
The administrator may configure a longer requirement. Password changes invalidate
existing sessions, so signing in again is expected.

## 5. What is an administrator-issued reset token?

A reset token is a **temporary, single-use secret code for resetting one account's
password**. An authorized administrator generates it when the account holder
needs password recovery.

It is different from your normal password, the Gemini API key, a login-session
token and a financing action's approval token.

The default reset lifetime is **1,800 seconds (30 minutes)**. Your installation's
security policy may change this; the administrator's issuance message shows the
actual expiry duration. A used, expired or replaced token is rejected.

The token identifies the target account, so the reset form does not ask for a
username or the old password. Anyone possessing a valid token can reset that
account's password. Share it privately with the intended account holder only;
do not put it in Git, a public screenshot or a shared team document.

### Administrator steps to issue a token

1. Sign in as an authorized User Administrator or Security Administrator.
2. Open **User Administration** at `/admin/users`.
3. Find the correct user in **User accounts**.
4. Click **Reset password** for that user.
5. Re-enter your own administrator password when requested.
6. Copy the **Single-use reset token** from the resulting message, together with
   its expiry duration, and share it privately with that account holder.

Issuing a new token invalidates earlier reset tokens for that account and revokes
its existing sessions. User Administrators cannot reset privileged administrator
accounts; those targets require an appropriately authorized Security Administrator.
The application does not automatically email the token.

### User steps to reset a password

1. Obtain the token privately from the administrator.
2. Open `/login`.
3. Expand **Use an administrator-issued reset token**.
4. Paste it into **Single-use reset token**.
5. Enter a new password meeting the current policy.
6. Click **Reset password**.
7. After **Password reset. Sign in with your new password**, sign in normally with
   your assigned username or email and the new password.

Successful reset consumes all outstanding reset tokens for the account and
revokes its sessions. It does not change role, merchant membership, consent or
grants, and it does not automatically reactivate a suspended account.

## 6. Common questions

| Message or situation | What to do |
|---|---|
| Reset token is invalid or expired | Ask the administrator to issue a new token. Copy it exactly and use it before expiry. |
| New password rejected | Follow the displayed/current password requirements; ask the administrator about any stricter policy. |
| No administrator-issued token | Use normal sign-in. The reset section is optional, not required for every login. |
| Administrator cannot see Dashboard or Financing | Use an authorized Business Owner account; account/security administration does not grant business authority. |
| Staff cannot upload or encode | Ask the administrator to check membership, role policy and explicit merchant grants. Resetting the password will not fix permissions. |
| Financing Agent access denied | Check membership, assigned application and current category consent with the Owner/administrator. |
| Account suspended or temporarily locked | Ask an authorized administrator to review status, or follow the configured lockout policy. Do not assume password reset changes account status. |
| Fresh clone has no existing users | Bootstrap the first administrator for that installation, then create separate business accounts. |

## Implementation references

Verified against the merged Task 03 implementation:

- `web/login.html`: sign-in, mandatory password change and reset-token forms.
- `web/users.html`: administrator Reset password action and issuance message.
- `copilot/auth.py`: `account_action`, `reset_password`, `change_password` and authorization.
- `copilot/server.py`: authentication and administration routes.

This README changes documentation only. No account, password or reset token was
created or changed to produce it.
