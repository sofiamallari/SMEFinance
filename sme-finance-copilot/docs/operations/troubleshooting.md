# Troubleshooting

| Symptom | Safe next step |
|---|---|
| ModuleNotFoundError: babel | Install requirements with the same virtual-environment Python used to start the server |
| Windows Python alias cannot run | Use an installed Python 3.12 executable or .venv/Scripts/python.exe; do not assume another person’s local runtime path |
| Dataset not initialized | Follow source-only ZIP seeding; do not fall back to retired identity/journal paths |
| Conflicting storage path | Clear stale individual storage overrides; use the dedicated selected data root |
| Bootstrap available only before first user | The store already has users; sign in or use supported Admin reset/provisioning, not another bootstrap |
| Invalid credentials after cutover | Use demo_owner/demo_staff/demo_bank/demo_admin with the password for that dataset; archived owner credentials do not apply |
| No cny-demo-credentials.json | Supported seed CLI uses the password you supplied; it does not guarantee writing this preparer-specific convenience file |
| Empty Staff navigation | Confirm explicit grants and membership, then sign in again after delegation changes |
| Empty Bank recipient/merchant list | Check active Bank role, scope and current Owner grant; do not select unrelated users |
| Import blocked | Read actionable fields/duplicates/reconciliation findings, correct source or mapping, validate again |
| Temporary import capacity | Cancel abandoned sessions through supported workflow or wait for expiry; do not disable the limit or delete staging rows manually |
| Survival missing | Check Owner role, required reads and feature flag; insufficient baseline disables Run |
| Old controls after update | Refresh browser for frontend changes; restart server for backend changes |
| Gemini unavailable | Check local private provider configuration; labeled deterministic fallback is not a live connectivity pass |
| Address already in use | Stop your existing local app with Ctrl+C or choose a free port; do not kill unrelated processes |

[Setup](local-setup.md) · [recovery](authentication.md) · [permissions](../technical/security-permissions.md).
