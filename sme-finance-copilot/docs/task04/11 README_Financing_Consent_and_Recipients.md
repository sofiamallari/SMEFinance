# Financing Consent — Recipient Setup and User Guide

## Purpose

The Business Owner uses **Grant consent** to authorize an assigned Financing Agent or legacy Coach to access specified financing-related data for a stated purpose and limited time. Consent does not approve a loan, move funds, or replace other role and merchant authorization checks.

Open `/consents` on the running application, for example `http://127.0.0.1:8000/consents`, and sign in as an authorized Business Owner.

## Why the recipient dropdown was empty

At the time of investigation, the local `logs/identity.sqlite3` database contained an active Owner and a Security Administrator, but no Financing Agent or Coach account. The API correctly returned no eligible recipients.

The frontend defect was that it rendered this valid empty result as a blank required dropdown without explaining how to proceed.

The corrected form now:

- Shows a loading message while retrieving eligible recipients.
- Shows an explicit selection placeholder when recipients exist.
- Explains when no eligible recipients exist and directs the user to User Administration.
- Disables submission when the list is empty or cannot be loaded.
- Displays a clear failure message if the API request fails.
- Prevents an older merchant request from replacing the current merchant's recipient list.

Backend filtering and consent authorization rules were preserved.

## Who appears in the list?

A recipient must meet all of these existing conditions:

1. Have the internal role `lender_analyst` (Financing Agent) or `coach` (legacy Coach).
2. Have account status `active`.
3. Have a merchant membership for the business currently selected on the consent page.

Owners, Staff, administrators, inactive accounts, suspended accounts, locked-status accounts, and Financing Agents assigned only to another merchant are excluded. New Coach assignments are disabled by default; use the supported Financing Agent role for a new demo account.

Listing an account does not itself grant financial access. Other applicable permissions, consent categories, and application-assignment requirements still apply.

## Set up a recipient for the local demo

Perform these steps only in the intended local demo environment, using an account authorized to manage users. Do not create demo users in production or assign unrelated merchants.

1. Sign in as an authorized User Administrator or Security Administrator.
2. Open **User Management** at `/admin/users`.
3. Select **Create user**, or edit an existing appropriate Financing Agent.
4. Enter the username, email, and display name.
5. Select **Financing Agent** as the role and **active** as the status.
6. Enter the **Financing organization / demo scope**, such as a clearly identified synthetic demo lender. This field is required for Financing Agents.
7. Under **Authorized merchant memberships**, select only the merchant needed for the demo. It must match the business that the Owner will select on the consent page.
8. For a new account, enter a temporary password that satisfies the configured password policy. Do not put passwords in this README or commit them to Git.
9. Select **Save account** and complete the existing administrator reauthentication prompt.
10. If the Agent needs to sign in, provide the temporary password securely. New accounts must change it at first login.
11. Sign in as the Owner, reopen the consent page, and select the same merchant. The active assigned Agent should appear.

The bug fix did not automatically create a persistent account or change local membership records. No persistent demo provisioning mechanism was found during the investigation; account setup uses the existing User Management workflow.

## Grant consent as the Owner

1. Sign in as the Business Owner and open `/consents`.
2. Select the intended **Business**.
3. Wait for recipient loading to finish.
4. Select an eligible **Recipient Financing Agent / coach**.
5. Enter a specific **Purpose**, for example a synthetic sandbox financing assessment.
6. Choose a future **Expires** date and time.
7. Select the required **Permitted data categories**:
   - Financial reports
   - Business assessment
   - Forecasts and alerts
   - Financing recommendations and RBF
   - Sandbox financing applications
8. Select **Grant consent**.
9. Confirm the success message and the new entry in **Consent history**.

Existing validation requires a purpose of 1–250 characters, at least one supported category, and an expiration after the current time and within the backend's 366-day limit. The backend rechecks recipient role, active status, and merchant assignment when saving, even if an account was listed earlier.

Financing Agents additionally require an assigned sandbox application for relevant financial access. Consent alone is not a replacement for that assignment. Use the existing Owner-approved simulated application workflow when needed; granting consent does not automatically submit an application.

## Revoke consent

In **Consent history**, select **Revoke** on the relevant entry and confirm the prompt. The existing application stops access based on revoked or expired consent. Revoking consent does not delete the application or approve/reject financing.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| No eligible recipients | An active Agent or legacy Coach must be assigned to the selected business. Ask authorized User Administration to review the account. |
| Unable to load recipients | Retry by selecting the business again. Check the local server and authenticated session. |
| Agent exists but is missing | Check the account role, account status, and exact merchant membership. |
| Recipient rejected while saving | Account status or membership may have changed since loading. Refresh and select an eligible account. |
| Owner cannot open the page | Check authentication, Owner permissions, and authorized merchant membership. |
| Agent still cannot access financial information | Check applicable consent categories, expiration, role permissions, merchant scope, and assigned sandbox application. |

Do not solve an empty list by disabling RBAC, displaying every account, enabling unrestricted demo identity headers, or granting all-merchant access.

## Technical reference and verification

- UI: `web/consents.html` — the only application file changed for this bug fix.
- Recipient API: `GET /api/consents?merchant=<merchant_id>`.
- Save API: `POST /api/consents`.
- Revoke API: `POST /api/consents/<consent_id>/revoke`.
- Existing backend: `copilot/auth.py`, methods `consents`, `grant_consent`, and `revoke_consent`.

Focused checks passed against disposable synthetic data: Owner sign-in, eligible Agent and legacy Coach display, recipient selection, consent saving and history refresh, exclusion of unrelated/suspended/locked-status accounts, unauthorized role and cross-merchant denials, and empty/API-failure states. Browser checks reported no JavaScript errors.

These checks did not create accounts in the local demo database. No full regression suite was run for this focused fix. No commit, push, or merge was performed.
