# SME Finance Copilot Security Controls and JSON Configuration

This guide explains the Security Administration menus and how to export,
validate, preview and import supported security settings. It describes the
current application; no security policies are changed by downloading this guide.

## 1. Open Security Controls

1. Start the application from `SMEFinance/sme-finance-copilot`:

   ```powershell
   python -m copilot.server --host 127.0.0.1 --port 8000
   ```

2. Open **http://127.0.0.1:8000/login**.
3. Sign in with an authorized **Security Administrator** account.
4. Open **http://127.0.0.1:8000/admin/security**.

A User Administrator account does not automatically have Security Controls access.
Administrator authority also does not grant merchant financial access.

On desktop, select sections from the left Security Administration menu. On smaller
screens, use the **Security section** dropdown. The header also links to
**User Management** and **Sign out**.

## 2. What each menu contains

| Section | Purpose | Can it change settings? |
|---|---|---|
| Overview | Recorded security indicators, current policy status and recent administration events. | Primarily review; no invented risk/compliance score. |
| Authentication | Password requirements, session lifetimes, lockout, reset-token expiry and reauthentication settings. | Yes, within fixed supported ranges. |
| Roles & Permissions | Enabled actions for each supported role. | Yes, within immutable role boundaries. |
| AI & MCP Controls | Role AI tier ceilings and explanations of authentication and immutable restrictions. | Tier ceilings can be changed within fixed maxima; authentication requirements/restrictions are read-only. |
| Consent Policies | Explains Owner consent, categories, expiry, Agent assignment and merchant isolation. | Read-only; individual consent is managed by Owners at `/consents`. |
| Audit & Monitoring | Filter recorded events by actor, type, result and dates. | Review only; not an editable audit ledger. |
| Configuration | Export current policy JSON; validate/preview/import approved JSON. | Import saves only after explicit application and administrator reauthentication. |

## 3. Authentication settings

Open **Authentication**, adjust supported values, click **Save authentication
policy**, and re-enter your own administrator password when prompted.

| Setting | Source default | Supported range |
|---|---|---|
| Idle session timeout | 1,800 seconds / 30 minutes | 300–3,600 seconds |
| Maximum session lifetime | 28,800 seconds / 8 hours | 900–86,400 seconds |
| Failed-attempt threshold | 5 | 3–10 |
| Lockout duration | 900 seconds / 15 minutes | 60–3,600 seconds |
| Minimum password length | 12 characters | 12–128 |
| Mixed password requirement | Enabled | Cannot be disabled |
| Password-reset token expiry | 1,800 seconds / 30 minutes | 300–3,600 seconds |
| Administrator reauthentication window | 300 seconds / 5 minutes | 60–600 seconds |

These are **source defaults**, not a claim about your installation's currently
saved values. The screen shows the current policy. Maximum session lifetime must
be at least the idle timeout. Unsupported or unsafe values are rejected.

Passwords remain hashed. Cookie sessions remain HttpOnly/SameSite. Secure cookies
for HTTPS are controlled by local deployment configuration, not this JSON form.

## 4. Roles and permissions

1. Open **Roles & Permissions**.
2. Review the actions enabled for each role.
3. Change only the necessary supported permissions.
4. Click **Save role permissions** and reauthenticate.

The server rejects actions outside each role's fixed boundary. Essential Security
Administrator controls cannot be disabled. Enabling an action does not bypass
merchant membership, Staff grants, current consent or action confirmation.

Examples:

- Staff uploads still require individual optional upload permission and an explicit
  merchant-level bulk-import grant, assigned through User Management.
- Financing Agents still require assigned scope/application and current category consent.
- Administrators cannot inherit financial permissions through this matrix.

Permission policy and business approval are separate: an implemented setting is
not automatically a formally approved institutional security policy.

## 5. AI and MCP controls

| Tier | Meaning |
|---|---|
| T0 | Authorized reads. |
| T1 | Advice and deterministic financing quotes. |
| T2 | Authorized sandbox writes, such as simulated payments. |
| T3 | Owner approval required for permitted application preparation. |
| T4 | Permanently prohibited real credit approval, real disbursement and limit changes. |

Default maximums are Owner T3, Staff T2, Financing Agent/legacy Coach T1,
and administrative roles T0. An administrative T0 ceiling does not grant
financial-read permissions.

Open **AI & MCP Controls**, review or reduce supported role ceilings, click
**Save AI tier ceilings**, and reauthenticate. A ceiling cannot exceed that role's
fixed maximum; T4 cannot be enabled through the UI or JSON.

MCP callers require server-authenticated sessions and the same merchant/consent
checks. API keys and environment-selected demo identities do not create merchant
authorization in authenticated mode. Session tokens and provider keys are not
shown or exported by this page.

## 6. Consent policies

This section explains existing enforcement; it does not edit global consent rules.

Business Owners grant/revoke recipient-specific consent at `/consents`, with
purpose, permitted categories and expiry. Financing Agents additionally require
membership, assigned application and enabled permissions. Expired/revoked consent
stops new access. Individual grants are not included in portable security JSON.

## 7. Audit and monitoring

1. Open **Audit & Monitoring**.
2. Optionally enter **Actor ID**, **Event type**, **Result**, **From** and **Through**.
3. Click **Filter audit**.
4. Review time, actor/role, merchant, action/target, result/reason and request ID.

The UI shows the latest 500 matching records. For JSON operations, useful event
types include `security_config_export`, `security_config_validate`,
`security_config_import` and `security_policy_changed`.

Records are hash-chained and omit passwords, reset/session tokens and imported
configuration payloads from the audit metadata. This is local recorded-event
monitoring, not an independent security certification or continuous external SOC.

## 8. Export JSON configuration

1. Open **Configuration**.
2. Under **Export Configuration**, click **Export Configuration**.
3. Save the downloaded **security-config.json** from your browser.
4. Label it with the installation/date and have the team review policy changes
   before using it elsewhere.

Export reads current supported global policy; it does not change settings.
An authorized session is required. Export itself does not ask for the password
confirmation used by sensitive policy changes.

### What the JSON includes

- `schema_version`: currently `1`.
- `application`: `sme-finance-copilot`.
- `authentication`: all supported authentication policy settings.
- `permissions`: enabled action lists for every supported role.
- `ai_tiers`: configured ceilings for every supported role.

The supported roles in the configuration are `owner`, `staff`, `lender_analyst`,
`coach`, `user_admin` and `security_admin`. Legacy coach must be represented for
schema compatibility; `demo_guest` is not a portable authenticated role.

### What the JSON does not include

Passwords/hashes, API keys, environment secrets, sessions, reset tokens, users,
merchant memberships, Staff account grants, individual consents, transactions,
applications, audit records and machine-specific paths are not exported.

This JSON is a **policy configuration**, not an account/database backup. Sharing it
does not share the Owner's login, Gemini key or merchant data.

## 9. Import JSON configuration

1. Export the receiving installation's current configuration first so you can
   review or restore its supported policies later.
2. Obtain the team's approved JSON file.
3. Open **Configuration → Import Configuration** and select the file.
4. Click **Validate and preview**.
5. Review every row in **Complete configuration difference preview**: Current,
   Imported, and Changed/Unchanged.
6. If incorrect, click **Cancel**. No policy changes are saved by preview/cancel.
7. If approved, click **Apply Configuration**.
8. Re-enter your own Security Administrator password.
9. Check the confirmed application message and review current policy/audit events.

Preview expires after **10 minutes** and is bound to the administrator, session,
and current policy revision. If policy changed since preview, validate again.
Closing/reloading or restarting may lose the pending preview; validate again.

Applying replaces only the supported global policy settings, inside a database
transaction. It preserves local users, grants, memberships, consents and business
records. If the file already matches, no policy changes are needed.

An earlier export can be validated and applied again to restore its supported
settings. This is not a general undo of account edits or financial records.

## 10. JSON validation rules

- File must be nonempty `.json`, valid UTF-8, and no larger than **64 KiB**.
- Top-level fields must match the five documented fields exactly.
- Schema version and application identifier must match this installation's supported schema.
- Authentication must contain all supported settings and no unknown settings.
- Permissions and AI tiers must include every supported role and no unknown role.
- Duplicate JSON property names, duplicate permission actions and nonfinite numbers
  are rejected. Normal JSON comments and trailing commas are not valid syntax.
- Authentication values must satisfy safe ranges; password complexity cannot be disabled.
- Actions cannot exceed role boundaries; essential administrator controls remain enabled.
- AI ceilings cannot exceed role maxima; T4 remains prohibited.

Use an actual export as the starting point rather than writing an incomplete JSON
fragment. A snippet missing settings/roles is not an importable configuration.

## 11. Downloadable example JSON

The companion **security-config.example.json** contains the source-default policy
and has been checked by the application's configuration validator.

It is **not an export of your installation's current policy**, a backup, or an
approved team policy. Importing it can change enabled permissions and timeouts.
Review the full difference preview before applying. Use your actual exported
configuration when transferring an approved team policy.

## 12. Suggested team workflow

1. Security Administrator exports the current local policy.
2. Team reviews intended differences and documents business/security approval.
3. Receiving teammate sets up their own installation/accounts privately.
4. Receiving Security Administrator validates and previews the approved JSON.
5. Administrator explicitly applies it and reviews the audit.
6. User Management separately assigns accounts, merchants and Staff grants;
   Owners separately grant consent.

JSON portability does not introduce centralized hosting or automatically update
other laptops. Each installation keeps its own local SQLite database.

## 13. Troubleshooting

| Situation | Action |
|---|---|
| Security Controls access denied | Verify Security Administrator role, enabled permission and current session. |
| File button disabled | Select a nonempty `.json` file within 64 KiB. |
| Validation failed | Check exact schema, required roles/settings, duplicate keys, safe ranges and boundaries. |
| Preview expired/unavailable | Validate the file again in the current session. |
| Policies changed since preview | Refresh and validate against the new current policy. |
| Administrator reauthentication required | Enter your own administrator password when applying/saving. |
| Import rejects T4 or expanded role authority | Expected protection; do not bypass the immutable boundaries. |
| Teammate imported policy but still cannot upload | Configure their account membership and Staff merchant grants separately. |
| Agent still has no access | Verify current category consent, assigned application and merchant membership. |
| Team expected users or transactions in export | Security JSON is not a database backup; local records are intentionally excluded. |

## References and scope

Inspected implementation: `web/security.html`, `web/security-admin.js`,
`copilot/security_configuration.py`, `copilot/auth.py`, `copilot/authorization.py`,
`copilot/security.py` and the security routes in `copilot/server.py`.

Related guides: `README_User_Management.md` and
`README_Login_Admin_User_and_Password_Reset.md` in this folder.

No security configuration was exported from the live owner database or imported
while producing this README/example. No accounts, permissions or keys were changed.
