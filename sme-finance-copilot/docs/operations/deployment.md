# Deployment instructions

How to install and run SME Finance Copilot ("Shifu"). The application is one Python process that serves the web pages, the JSON API and the AI Financial Partner. There is no separate front-end build.

| Option | Use it for | Status |
|---|---|---|
| A. Local install | Judges, teammates and the demo (http://127.0.0.1:8000) | Verified on Windows with Python 3.12 |
| B. Docker container | Running the same image anywhere Docker is available | Image build not verified (see below) |
| C. Railway (cloud) | A public HTTPS demo | Configuration prepared; a live Railway deployment has not been verified |

## Requirements

- Python 3.12 (the Docker image uses `python:3.12-slim`).
- The packages in [requirements.txt](../../requirements.txt): Babel, tzdata, jsonschema (pytest is optional).
- Optional: a Google Gemini API key for the live AI Financial Partner. Without it, the chat uses its deterministic, backend-only mode.
- Optional: Node.js with Playwright, only for the browser verification scripts in `scripts/`.

## A. Local install

### 1. Get the code

```bash
git clone https://github.com/sofiamallari/SMEFinance.git
cd SMEFinance/sme-finance-copilot
```

### 2. Create a virtual environment and install the packages

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS or Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The remaining Windows commands use `.\.venv\Scripts\python.exe`; on macOS or Linux use `.venv/bin/python` instead.

### 3. Create the synthetic CNY demo data (first time only)

A fresh clone has no data or accounts. The seed command creates six synthetic merchants (M001 to M006) and four demo accounts, `demo_owner`, `demo_staff`, `demo_bank` and `demo_admin`, all with a password you choose. The password must be 12 to 256 characters and contain uppercase letters, lowercase letters and digits.

Windows (PowerShell), which keeps the password out of the command history:

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

macOS or Linux:

```bash
read -rs -p 'Choose a strong synthetic demo password: ' COPILOT_CNY_DEMO_PASSWORD; echo
export COPILOT_CNY_DEMO_PASSWORD
.venv/bin/python -m copilot.cny_demo seed
unset COPILOT_CNY_DEMO_PASSWORD
.venv/bin/python -m copilot.cny_demo verify
```

The data is stored in `logs/shenzhen_cny_demo/` (`identity.sqlite3`, `transactions.jsonl`, `audit.jsonl`, `execution.jsonl`). Seeding again does not duplicate records or reset passwords. More detail: [local setup](local-setup.md) and [CNY dataset](cny-dataset.md).

### 4. Optional: enable the live AI (Google Gemini)

Create a file named `.env` in the `sme-finance-copilot` folder. Only these settings are read from it; never commit this file.

```text
COPILOT_GOVERNED_LIVE=yes
COPILOT_AGENT_MODE=auto
COPILOT_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
COPILOT_LLM_MODEL=gemini-3.5-flash
COPILOT_LLM_API_KEY=<your Gemini API key>
```

Leave `COPILOT_GOVERNED_LIVE` unset (the default is `no`) to run without any calls to the AI provider. See [.env.example](../../.env.example) for all settings.

### 5. Start the server

```powershell
# Optional: show the Owner-only Business Stress Test tab
$env:FINANCIAL_SURVIVAL_SIMULATION_ENABLED='true'
.\.venv\Scripts\python.exe -m copilot.server --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/login and sign in with one of the demo accounts and the password from step 3:

| Account | Lands on |
|---|---|
| `demo_owner` | Merchant workspace (dashboard, transactions, cash flow, financing, AI Financial Partner) |
| `demo_staff` | Merchant workspace, limited to the grants the owner gives (none at first) |
| `demo_bank` | Bank portal at `/bank` |
| `demo_admin` | Security administration at `/admin/security` |

Stop the server with Ctrl+C. Restart it after changing Python code or `.env`.

### 6. Check that it works

- Sign in as `demo_owner`; the dashboard shows merchant M002's figures in CNY.
- Open the AI Financial Partner and ask "How much were my sales last month?". The answer lists its sources under "Sources & Tools".
- Run the tests (see [test cases](../hackathon/test-cases.md)):

```bash
python -m unittest discover -s tests
```

## B. Docker container

The image starts `python -m copilot.deployment`, which checks the settings, prepares the data folder, drops root privileges and then starts the server on port 8000. Data must live on a volume mounted at `/data`.

```bash
docker build -t sme-finance-copilot .
docker run --rm -p 8000:8000 -v copilot-data:/data \
  -e COPILOT_DATA_DIR=/data/shenzhen_cny_demo \
  -e COPILOT_APPROVAL_SECRET=<private random value, at least 32 characters> \
  -e COPILOT_INITIALIZE_CNY=yes \
  -e COPILOT_CNY_DEMO_PASSWORD=<private seed password> \
  sme-finance-copilot
```

Use `COPILOT_INITIALIZE_CNY=yes` and the seed password only on the first start with an empty volume. For later starts, set `COPILOT_INITIALIZE_CNY=no` and remove the seed password. The health check is `GET /login`.

> **Not verified:** the Docker engine was not available on the development machine, so the image build, volume ownership and non-root start have not been tested end to end.

## C. Railway (cloud)

The repository contains a [Dockerfile](../../Dockerfile) and [railway.toml](../../railway.toml) for Railway. In short:

1. Create a Railway service from `sofiamallari/SMEFinance`, branch `main`, Root Directory `/sme-finance-copilot`, builder Dockerfile.
2. Attach a volume at `/data`.
3. Set the variables: `COPILOT_DATA_DIR=/data/shenzhen_cny_demo`, `COPILOT_HTTPS=yes`, `COPILOT_APPROVAL_SECRET`, and for the first start only `COPILOT_INITIALIZE_CNY=yes` and `COPILOT_CNY_DEMO_PASSWORD`. Add the `COPILOT_LLM_*` variables and `COPILOT_GOVERNED_LIVE=yes` to enable Gemini.
4. Deploy, wait for a healthy `/login`, then set `COPILOT_INITIALIZE_CNY=no` and remove the seed password.
5. Sign in and change the four demo passwords before sharing the public URL.

The full guide, including every variable, the volume layout, troubleshooting and backups, is [railway.md](railway.md).

> **Not verified:** a live Railway deployment, its HTTPS cookies and restart persistence have not been tested.

## Security notes

- Never commit `.env`, API keys, the seed password, `logs/` or database files.
- Passwords are stored as scrypt hashes; sessions use Secure (with HTTPS), HttpOnly, SameSite=Strict cookies with CSRF checks.
- The demo uses synthetic data only. Digital payments and bank reviews are simulated; nothing moves real money or makes a credit decision.

[Operations index](README.md) · [Environment variables](environment.md) · [Troubleshooting](troubleshooting.md)
