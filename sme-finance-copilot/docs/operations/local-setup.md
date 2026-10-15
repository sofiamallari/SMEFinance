# Local setup and downloaded ZIP

Use Python 3.12. Extract/open the `sme-finance-copilot` application folder. Commands below run from that folder; do not use another person’s absolute Windows path.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Using the explicit virtual-environment executable avoids PowerShell activation-policy problems. Runtime dependencies include Babel and tzdata. Node/Playwright are optional verification tools, not application runtime requirements.

## Choose initialized data versus fresh seeding

If a private authorized handoff includes the initialized **matching** CNY database/journal, verify it:

```powershell
.\.venv\Scripts\python.exe -m copilot.cny_demo verify
```

Use the credentials privately supplied for that specific dataset. On the preparer’s existing machine an ignored `logs/cny-demo-credentials.json` may hold the seed password. That file is not a public distribution artifact and is not automatically produced by the supported seed CLI.

A source-only ZIP/Git checkout normally excludes logs and credentials. Initialize a new empty dataset using a password you choose privately:

```powershell
$secret = Read-Host 'Choose a strong synthetic demo password' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $env:COPILOT_CNY_DEMO_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    .\.venv\Scripts\python.exe -m copilot.cny_demo seed
} finally {
    Remove-Item Env:COPILOT_CNY_DEMO_PASSWORD -ErrorAction SilentlyContinue
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
.\.venv\Scripts\python.exe -m copilot.cny_demo verify
```

Keep the chosen password privately. The CLI creates `demo_admin`, `demo_owner`, `demo_staff`, `demo_bank` using that synthetic seed password; it does **not** promise to generate a credentials JSON file. Rotate to distinct account passwords before public hosting. No original user password/hash/token is copied. Current Staff grants start empty. An initialized dataset is not a fresh bootstrap: bootstrap is first-user-only and should not be rerun.

Seed uses the packaged synthetic relationship manifest; do not upload the original private backup to initialize another machine. Repeat seeding validates without duplicate insertion or password reset. A nonempty partial preparation stops safely; preserve/inspect it and select a new empty directory rather than deleting data or repeatedly forcing initialization. General storage variables must be set in the process/service, not merely copied into `.env`.

## Run

```powershell
# Optional existing Owner-only experimental tab:
$env:FINANCIAL_SURVIVAL_SIMULATION_ENABLED='true'
.\.venv\Scripts\python.exe -m copilot.server --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/login (no trailing asterisks). Owner uses the merchant workspace, Bank `/bank`, Admin `/admin/security`. Use `demo_owner` with the matching new seed password, not an archived `owner` account password. Stop with Ctrl+C. Refresh the browser after frontend updates; restart Python after backend changes.

Default active root is `logs/shenzhen_cny_demo`, resolved from the application location. Missing initialization fails closed instead of recreating IDR. Do not mix an old identity DB with the CNY journal. [Dataset](cny-dataset.md) · [environment](environment.md) · [troubleshooting](troubleshooting.md) · [login guide](../user-guide/getting-started.md).
