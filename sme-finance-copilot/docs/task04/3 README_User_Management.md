# SME Finance Copilot User Management Guide

Use this guide to create accounts, assign merchants and permissions, and manage
password recovery. It describes the current authenticated application.

## 1. Open User Management

1. Start the application from `SMEFinance/sme-finance-copilot`:

   ```powershell
   python -m copilot.server --host 127.0.0.1 --port 8000
   ```

2. Open **http://127.0.0.1:8000/login**.
3. Sign in with an authorized **User Administrator** or **Security Administrator** account.
4. Open **http://127.0.0.1:8000/admin/users**.

All roles use the same login page. Administrators manage accounts; they do not
automatically receive merchant financial access.

## 2. Who can manage users?

| Role | Authority |
|---|---|
| User Administrator | Manage permitted business accounts, merchant memberships and Staff grants; issue permitted password-reset tokens and revoke sessions. Cannot manage privileged administrator accounts. |
| Security Administrator | Broader account administration and Security Controls, within fixed server safeguards. |
| Business Owner | Operate assigned businesses and request Staff access changes. Does not directly administer accounts. |
| Staff / Financing Agent | Use their authorized business functions; cannot administer accounts. |

Current role permissions can be reduced by Security Controls. Sensitive actions
require the administrator to re-enter their own password.

## 3. Create a business account

1. Click **Create user**.
2. Enter a unique **Username**, **Email** and **Display name**.
3. Choose **Role**: Business Owner, Staff or Financing Agent.
4. Select **Status: active** for an account that should be able to sign in.
5. For a Financing Agent, enter the required **Financing organization / demo scope**.
6. Select the appropriate **Authorized merchant memberships**.
7. For Staff, select only the required transaction grants for each assigned merchant.
8. Enter a private **Temporary password** that meets the current password policy.
9. Click **Save account**, then confirm your administrator password when prompted.
10. Share the username and temporary password privately with the account holder.

The new user must change their temporary password at first login, then sign in
again. Do not place passwords in Git, shared documents or screenshots.

### Choose the correct role

| Business role | Main use | Important limits |
|---|---|---|
| Business Owner | Dashboard, transactions, payments, cash flow, financing and AI analysis for assigned merchants. | Applications require consent and explicit confirmation; no real credit approval or funds movement. |
| Staff | Permitted operational work for assigned merchants. | New Staff are read-only for transaction changes until granted access; financing is restricted. |
| Financing Agent | Assigned consent-authorized financing information and sandbox application review. | Cannot modify transactions or simulate payments; membership alone is insufficient. |

Administrators cannot hold merchant memberships in the current application.
Create a separate authorized Business Owner account to operate business modules.
Legacy Coach remains compatible, but new assignments are disabled by default.

## 4. Configure Staff transaction grants

In **Staff transaction grants by merchant**, assign permissions separately for
each merchant the Staff account belongs to:

| Grant shown in the form | What it permits |
|---|---|
| create transactions | Save single transactions for that merchant. |
| bulk import | Stage, validate, preview and confirm permitted POS uploads for that merchant. |
| acknowledge quality alerts | Move an open quality alert to acknowledged with a reason. |
| resolve quality alerts | Move an acknowledged alert to resolved with supporting explanation. |

The current form derives the individual optional bulk-upload permission when a
Staff bulk-import grant is selected for an assigned merchant. The separate old
bulk-upload checkbox is hidden; use the merchant grant controls.

Backend upload authorization still requires all of the following:

- Active authenticated account and enabled role action.
- Membership in the selected merchant.
- Individual optional bulk-upload permission.
- Merchant-level bulk-import grant.

Giving access to Merchant A does not give access to Merchant B. Alert permissions
do not bypass import validation or change financial records.

## 5. Search and inspect accounts

1. Use **Search** for name, username or email.
2. Optionally select **Status** and **Role** filters.
3. Click **Search**.
4. Click **Details** for an account to inspect its current settings and change history.

The table shows role, status, assigned merchants, last login and available actions.
A temporary login lockout may be displayed beside the account status.

## 6. Edit account access

1. Find the account and click **Edit**.
2. Update permitted account details, role, status, merchant memberships or Staff grants.
3. Click **Save account** and reauthenticate when asked.
4. Ask the affected user to sign in again.

Saving an account edit revokes its existing sessions. The new scope is checked by
the backend on subsequent requests, not just by hiding menu items.

Safeguards include:

- User Administrators cannot modify administrator accounts.
- Administrators cannot change their own authority or status.
- The last active Security Administrator cannot be removed or deactivated.
- Duplicate usernames/emails and unsupported roles or memberships are rejected.

## 7. Suspend or reactivate an account

### Suspend

1. Find the account.
2. Click **Suspend**.
3. Re-enter your administrator password.

The account is suspended and its sessions are revoked.

### Reactivate or clear a lock

1. Click **Edit** for the permitted target account.
2. Select **Status: active**.
3. Click **Save account** and reauthenticate.

The implemented update clears failed-attempt and lockout state; saving active
status also clears the account's tracked login-attempt entries. The user signs in
again. There is no separate **Unlock** button in the current User Management table.

## 8. Issue a password-reset token

1. Find the correct account and click **Reset password**.
2. Re-enter your own administrator password.
3. Copy the **Single-use reset token** and its expiry duration from the message.
4. Share it privately with that account holder.

The default lifetime is **30 minutes**, configurable by security policy. Issuing a
new token invalidates earlier reset tokens for the account and revokes sessions.
The application does not automatically email the token.

The account holder then:

1. Opens `/login`.
2. Expands **Use an administrator-issued reset token**.
3. Enters the token and a policy-compliant new password.
4. Clicks **Reset password**.
5. Signs in normally with their username/email and new password.

The token is single-use and account-specific. It is not a normal password, API key
or financing approval token. Password reset does not change roles, grants,
membership or consent, and does not automatically reactivate a suspended account.

## 9. Revoke sessions

1. Find the account and click **Revoke sessions**.
2. Re-enter your administrator password.

Existing sessions become invalid. The password and account permissions remain
unchanged; an active account can sign in again with its existing password.

## 10. Review Staff access requests

Owners submit requests from their **Financing consent** page's
**Request a staff access change** form. These appear under **Staff access requests**
in User Management.

Read the merchant and request details, verify the intended access with the Owner,
and use the relevant account's **Edit** form to apply an authorized change.
The request itself does not automatically grant access, and no dedicated
approve/reject workflow is implemented for these request records.

## 11. Financing Agent access checklist

Creating a Financing Agent account does not by itself unlock financing data.
Confirm:

1. The account is active and has a Financing organization / demo scope.
2. The Agent is assigned to the correct merchant.
3. The Owner grants current consent for the necessary categories.
4. The application is assigned to that Agent where required.
5. Role permissions and AI tier ceilings still allow the requested function.

Reviews are simulated: request information, sandbox recommendation or sandbox
decline. They do not approve actual credit or move money.

## 12. Troubleshooting

| Situation | Check |
|---|---|
| User Management access denied | Correct administrator role, enabled permission and valid session. |
| Administrator reauthentication required | Enter your own administrator password in the confirmation dialog. |
| Staff cannot encode/upload | Merchant membership, role action, explicit merchant grant and upload optional permission. |
| User logged out after an edit | Expected: account changes revoke sessions. Sign in again. |
| Reset token invalid or expired | Issue a new token and use it within the displayed lifetime. |
| Owner request appears but access did not change | Requests are informational; apply the change through Edit after verification. |
| Administrator cannot open financial modules | Use a separate authorized business account; administrative authority is independent. |
| New clone has no users | Bootstrap the first Security Administrator on that fresh installation, then create business accounts. |

## Reference and scope

Verified against `web/users.html`, `web/admin.js`, `copilot/auth.py`,
`copilot/authorization.py` and the administration routes in `copilot/server.py`.

Related guide: `README_Login_Admin_User_and_Password_Reset.md` in the same folder.
This README is documentation only. No accounts, permissions, passwords or tokens
were changed to produce it.
