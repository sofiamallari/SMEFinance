# Shenzhen CNY demonstration — staged replacement and Railway preparation

## Approved cutover completed — 2026-10-15

The active default is now `shenzhen_cny_demo`. Running `python -m copilot.server` from the project uses `logs/shenzhen_cny_demo` without dataset/storage environment variables. The root is resolved from the application location, not the shell directory. Missing/uninitialized CNY storage fails closed; normal application startup cannot fall back to legacy financial seed data. Custom storage overrides must agree with the selected CNY directory. Railway still requires an explicit persistent data directory.

Final active paths (project-relative):

- Database: `logs/shenzhen_cny_demo/identity.sqlite3`
- Canonical ledger: `logs/shenzhen_cny_demo/transactions.jsonl`
- Audit: `logs/shenzhen_cny_demo/audit.jsonl`
- Execution: `logs/shenzhen_cny_demo/execution.jsonl`
- Configuration/validation: `logs/shenzhen_cny_demo/dataset.json`, `cutover.json`

Fresh verified backup: `logs/backups/pre-cny-20261015T083637Z/`. It includes original SQLite, ledger, audit and execution evidence; all four hashes verified and temporary restoration loaded 203 original canonical records through the current ledger service. Earlier `pre-cny-20261015T081820Z` remains intact too. Post-inventory changes were session and audit activity only; the original ledger/financial records were unchanged. The fresh snapshot retains that newer evidence.

Exactly five approved originals were moved, without permanent deletion, from `logs/` into `logs/backups/retired-original-20261015T083825Z/`: `identity.sqlite3`, `manual_transactions.jsonl`, `manual_transactions.jsonl.lock`, `audit.jsonl`, `execution.jsonl`. No other original/user-created data was retired. No Copilot writer process was present at cutover. Exclusive read/write-denying handles, a hash check against the fresh preflight and same-volume moves guarded retirement; failures during the move would restore moved files and the prior selector code.

Application source changed for cutover: `copilot/demo_environment.py` (CNY default, application-relative local path, fail-closed activation), `copilot/cny_demo.py` (CLI matches the default), `.env.example`, and documentation. The previous selector/CLI sources are retained under `activation-code/` in the retirement directory. Temporary orchestration and verification scripts were created in the session's writable workspace `C:\Users\User\source\repos\sme-finance-copilot-v1.2-transactions\.journey-work`; those are not another application checkout receiving production edits. All application code edits target `C:\Users\User\source\repos\SMEFinance\sme-finance-copilot` on `feature/security-sme-bank-workflow`.

Post-cutover focused validation passed: default-path startup without dataset overrides, all six CNY merchant identities, scoped histories and dashboards, distinct merchant totals, financial reconciliation, forbidden Admin/Staff/Bank access, two routed CNY applications with review feedback, authorized Bank review, consent revocation in a disposable copy, Survival baseline/calculation, restart persistence, no ledger reseeding and appended audit/execution logs. The 35 disposable-copy workflow checks also passed again. Full regression/new test suites were not run.

**Audit limitation:** existing `AuditLog` begins a new GENESIS hash-chain segment per process. Each active segment verifies, and append/preservation checks passed, but the complete cross-restart file is not one continuous chain. No original or new evidence was rewritten to hide this. Continuous cross-process chaining is a separate hardening item; SQLite security audit remains governed by its existing implementation.

To run locally:

```powershell
cd C:\Users\User\source\repos\SMEFinance\sme-finance-copilot
python -m copilot.cny_demo verify
# Optional, to show the existing experimental Owner simulation tab:
$env:FINANCIAL_SURVIVAL_SIMULATION_ENABLED='true'
python -m copilot.server --host 127.0.0.1 --port 8000
```

Use the new synthetic accounts; the private `logs/cny-demo-credentials.json` contains their seed password. Original credentials were not copied. Do not publish that file or use the shared demo password for a public service. Any stale process variables pointing at `logs/identity.sqlite3` or `logs/manual_transactions.jsonl` must be cleared; conflicting paths are rejected rather than mixed.

Rollback is recoverable but requires stopping all Copilot writers first: preserve the current CNY directory; restore `copilot/demo_environment.py` from retirement `activation-code/`, restore the five original files from the retirement directory into their original `logs/` locations, clear dataset/storage overrides, and start the prior configuration. Alternatively restore the fresh database/journals snapshot (plus the preserved lock file). Do not combine the original identity database with the CNY journal. No rollback was needed.

Railway remains un-deployed. Docker image build is unverified because the local Docker engine is unavailable; mounted-volume permissions for non-root `appuser`, secure configuration/unique credentials and single-replica persistence must be verified before hosting. Live Gemini was not exercised in these cutover checks. Existing financial formulas, roles, grants and sandbox boundaries were unchanged.

The sections below retain preparation/background detail; this approved-cutover status supersedes their staging and pending-approval wording.

## Preparation record and entry points

Prepared on `feature/security-sme-bank-workflow`, starting HEAD `7e36f57` with substantial existing uncommitted work preserved. No commit, push, deployment, original-data deletion, or default-dataset cutover was performed.

The replacement is explicitly selected. It is staging, not a second running application. The original default remains available solely pending the required retirement approval. Never run the old and replacement stores as one dataset.

## Architecture and dependencies

Python 3.12 standard-library `ThreadingHTTPServer` serves static HTML/CSS/JavaScript and authenticated JSON/MCP endpoints. SQLite stores users, sessions, policies, memberships, consent, import staging/history, quality alerts, payment state, drafts, applications and reviews. An append-only checksummed JSONL journal stores canonical transactions; separate JSONL files store financial audit/execution evidence. Existing SQL migrations run through `AuthStore`.

`COPILOT_DATASET` → deterministic scenario generator → `Copilot` → SQLite identity/authorization + canonical journal → financial projection → dashboard/cashflow/RBF/maturity/AI/Survival. POS imports commit through the existing stage/validate/preview-token/confirmation pipeline. Sandbox payment completion is journaled once through existing callbacks. Bank routing remains distinct from financial-data consent. Reviews remain append-only simulated outcomes.

## Storage and backup

All paths below are relative to `C:\Users\User\source\repos\SMEFinance\sme-finance-copilot`.

| Purpose | Location |
|---|---|
| Original identity, workflow and payment database | `logs/identity.sqlite3` |
| Original canonical ledger | `logs/manual_transactions.jsonl` |
| Recoverable pre-change snapshot | `logs/backups/pre-cny-20261015T081820Z/` |
| Replacement staging directory | `logs/shenzhen_cny_demo/` |
| Replacement database / journal | `identity.sqlite3` / `transactions.jsonl` inside that directory |
| Readable validation evidence | `validation.json`, `focused-checks.json`, `owner-cny-smoke.png` inside staging |
| Proposed exact retirement inventory | `retirement-inventory.json` inside staging |
| Newly generated local demo credentials | `logs/cny-demo-credentials.json` — private, ignored, never publish |

Backup uses SQLite's online backup API, verified with `PRAGMA integrity_check`, plus copies of the canonical/audit/execution journals. The manifest records SHA-256 checksums. Original database logical contents and journal bytes were compared after verification and remained unchanged. Backup contains sensitive identity hashes: preserve privately; do not upload it to Git or Railway.

Original inventory: four users, 18 memberships, six profiles, two consents, two IDR applications, zero reviews, 18 import runs (four committed, 14 expired), three IDR payment states (two paid, one pending), 203 IDR canonical records (200 imports, one manual, two simulated collections). Source generator also contains PHP/THB/VND/MYR personas: replacing the original environment retires more than IDR records alone.

## New synthetic scenarios

Stable merchant IDs, names, sectors, original countries and nonmonetary business characteristics remain. These are fictional ASEAN reference businesses with freshly budgeted RMB activity, not claims of Chinese registration or Chinese tax treatment. Six months of growth, adoption, weekly seasonality, operating costs, debt-service, receivables and payables are regenerated using the original generation logic with seed offset `20261015` and fixed assessment date `2026-09-30`.

| Merchant | Fresh starting daily sales (CNY) | Synthetic opening wallet | Scenario |
|---|---:|---:|---|
| M001 — Lola Nena's Kakanin Stall | 680 | 430 | Micro stall, closures, informal books, pressure |
| M006 — Bayanihan Sari-Sari Store | 1,850 | 8,600 | Retail, gradual digital adoption |
| M002 — Tani Coffee & Tofu House | 3,600 | 19,800 | Growth, capacity pressure, late receivables |
| M003 — Baan Rattan Crafts | 8,200 | 96,000 | Orders, production and financing readiness |
| M004 — Sen Lotus Bakery Group | 26,500 | 580,000 | Multi-unit expansion |
| M005 — Warisan Batik House | 11,800 | 245,000 | Mature business and succession gap |

Budgets are scenario assumptions selected by business scale, not exchange-rate conversion or relabeled legacy amounts. Opening wallets are explicitly synthetic starting assumptions, not reconstructed bank balances. The original scoring, financing and cash-flow formulas are unchanged; resulting maturity stages may change because financial inputs have changed. No stage is forced.

Replacement counts: 4 users; 18 memberships; 6 profiles; 5,361 seed sales rows; 2,722 seed expense rows; 29 receivables; 18 payables; 221 canonical transactions; 22 import/manual runs; 4 quality alerts; 2 consents; 2 applications; 6 review entries; 6 payment states. Seed daily aggregates are separate historical activity, not the same receipts as the 200 synthetic imported sales and distinct sandbox checkouts. They are not copied into the canonical journal, avoiding double ingestion.

CSV and XLSX each contain 100 fresh receipts, a committed import and a duplicate-review preview. Each merchant also has a sale, expense and refund manual example. Imports are representative new demonstration sources dated September 24; they do not recreate every historical source row or the 14 abandoned original sessions. Payment scenarios cover QR, Tap, Pay Link, paid/pending/cancelled/expired and a separate POS-cart checkout. Successful payment amounts reconcile to fee plus net settlement using existing stage MDR rules. Zero cart tax is the central `config.CURRENCIES` sandbox assumption, **not Chinese VAT**. No tax-law or FX model was introduced.

Accounts are `demo_admin`, `demo_owner`, `demo_staff`, `demo_bank`, with new synthetic credentials. No original password hashes, tokens, email addresses, display names, review notes or PII were copied. Membership and consent relationship structures are represented by a sanitized packaged manifest. Source Staff had no explicit grants: this is preserved. Owner must delegate operational grants before Staff can use those actions. Focused verification exercised delegation only in a disposable copy. Admin remains without merchant memberships.

Both applications route to the synthetic Bank; each demonstrates Reviewed → More Information Needed → Ready for Further Assessment. These are simulated review history, never approval/rejection/disbursement. Owner grants are separate, expire after 180 days from first seeding and are not extended by repeat seeding. Bank has no financial-data access to other merchants merely through membership. Original account IDs are replaced consistently with new IDs.

## Local preview (does not delete or replace the original)

From the project directory in PowerShell, using a functioning Python 3.12 environment:

```powershell
python -m pip install -r requirements.txt
$env:COPILOT_DATASET='shenzhen_cny_demo'
$env:COPILOT_DATA_DIR=(Join-Path (Get-Location) 'logs\shenzhen_cny_demo')
$env:COPILOT_AUTH_MODE='authenticated'
Remove-Item Env:COPILOT_IDENTITY_DB,Env:COPILOT_TRANSACTION_FILE,Env:COPILOT_AUDIT_LOG,Env:COPILOT_EXEC_LOG -ErrorAction SilentlyContinue
$env:FINANCIAL_SURVIVAL_SIMULATION_ENABLED='true'
python -m copilot.cny_demo verify
python -m copilot.server --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/login`. Read the newly generated password locally from the private credentials file. No credential values belong in documentation or chat. The Admin bootstrap created here is already complete; do not run bootstrap again. Existing LLM variables/key remain owner-supplied and untouched. General dataset/storage variables must be process/service variables: the existing `.env` loader only loads its supported LLM/feature settings.

For a fresh empty directory, set `COPILOT_CNY_DEMO_PASSWORD` to a strong synthetic password through a secure prompt/service secret, then run:

```powershell
python -m copilot.cny_demo seed
Remove-Item Env:COPILOT_CNY_DEMO_PASSWORD
```

The packaged `copilot/data/shenzhen_reference.json` contains only synthetic structural relationships. No original database is needed on Railway. Optional `--source-database PATH` reads relationship structure from a local backup without copying credentials; it is intended for this reviewed six-persona/four-account baseline. Other role/merchant topologies require review. Seeds are financially deterministic and repeat initialization validates without inserting duplicates. Security identifiers, password salts, references and audit timestamps are intentionally fresh. Partial initialization fails safely and is not automatically replayed; inspect or preserve that directory and choose a fresh empty target.

## Validation results and limitations

35 focused checks passed: CNY records, database integrity/references, six merchant financial reconciliations and assessments, payment state restoration/settlements, CNY cashflow, Owner feedback, Bank consent/revocation, routing separation, Admin restrictions, Staff delegation/isolation, unsupported-currency rejection, three complete Survival baseline months, deterministic scenario arithmetic/no ledger writes, deterministic AI read, Admin provisioning and authenticated HTTP startup.

Additional checks passed: fresh seed using only the portable manifest matches canonical financial values/counts; repeat seed leaves ledger bytes unchanged; normal server reload restores financial state. Browser: Owner login, ¥ KPIs, AI drawer, Survival baseline/defaults and mobile overflow check passed with zero page errors. No new test suite was added.

Live Gemini was **not tested**; read-only deterministic evidence/fallback was verified with provider disabled. No cross-browser/exhaustive UI testing, full regression suite or production load testing was run, per scope. Docker image build was **not run** because Docker Desktop's engine was unavailable. Historical activity ends September 30, 2026; the rolling Survival baseline will eventually have fewer/zero eligible recent months. Regeneration requires an explicitly reviewed seed-version/date update, not silent date shifting or reinitialization of existing data. There are no newly seeded expired/revoked consents; revocation was verified on a disposable copy. Original expired import sessions and original raw audit chains are preserved only in backup, not forged into fresh history.

## Railway preparation — no deployment performed

Use repository service root `sme-finance-copilot`, the supplied Dockerfile (`python:3.12-slim`) and `railway.toml`. Install command is `python -m pip install -r requirements.txt`; start is `python -m copilot.server`. Frontend is served by this same process; no separate Node service/build is required. `HOST=0.0.0.0`; Railway supplies `PORT`. Healthcheck `/login` is available without credentials.

Required service variables:

| Variable | Value/purpose |
|---|---|
| COPILOT_DATASET | `shenzhen_cny_demo` |
| COPILOT_DATA_DIR | `/data/shenzhen_cny_demo` |
| COPILOT_AUTH_MODE | `authenticated` |
| COPILOT_HTTPS | `yes` behind Railway HTTPS |
| HOST | `0.0.0.0` |
| FINANCIAL_SURVIVAL_SIMULATION_ENABLED | `true` if demo requires it |
| COPILOT_CNY_DEMO_PASSWORD | Fresh strong seed-time secret; remove after seed |
| COPILOT_APPROVAL_SECRET | Owner-generated secret, never the example placeholder |
| COPILOT_LLM_BASE_URL / API_KEY / MODEL | Optional existing Gemini configuration via service secrets |

The image retains the existing non-root `appuser`. The mounted volume must be writable by that user; image-time directory ownership alone does not guarantee ownership of a mounted volume. Verify or explicitly configure volume ownership before hosting. Do not bypass this by exposing a root-run service.

Attach a persistent Railway volume at `/data`. **All** SQLite, canonical ledger, wallet/payment state, consent, drafts, reviews, audit and execution paths must remain under the same persistent root; conflicting legacy path overrides fail startup. Do not seed on every application start. In an approved maintenance/one-off shell with the volume mounted, run `python -m copilot.cny_demo seed`, then `verify`, then start the service. An unseeded service fails closed. Do not upload old identity backups or local credential files; `.dockerignore` excludes logs, databases, journals, `.env`, evidence and ZIPs.

SQLite plus the existing inter-process journal lock is the simplest POC deployment: **one replica, one persistent volume, one application process**, with normal threaded request handling. PostgreSQL is not required for this limited topology. Horizontal replicas/shared multi-host writes require a separate approved persistence/locking design, including the JSONL ledger, not merely switching the identity DB. Back up SQLite using its backup API, and take coordinated ledger/audit snapshots with writers stopped or locked. Never rely on ephemeral service storage.

Before public hosting: approve cutover inventory, build the image, verify volume permissions/restart persistence, rotate the shared seed password to distinct synthetic account passwords and set a unique approval secret, verify secure cookies/HTTPS, test the supplied Gemini configuration separately if needed, and verify Owner/Staff/Bank/Admin journeys against the deployed candidate. No Railway connection, deployment or costs were initiated. Public multi-tenant production hardening, backups/monitoring automation and horizontal scaling remain outside this POC.

## Retirement approval gate

Exact files and hashes are in `logs/shenzhen_cny_demo/retirement-inventory.json`. Proposed retirement is the original database, ledger, audit/execution logs and ledger lock, **together**, after stopping all old writers and switching explicitly to the validated CNY environment. Retain the verified backup. Three inactive failed CNY preparation directories may also be removed after approval; they are never selected or served.

No source seed fixture is presently approved for deletion: legacy PERSONAS still support existing tests and the pending default runtime. After approval, update the normal launcher/default selection so restarts cannot recreate legacy data; retain necessary historical/test compatibility outside the active CNY generator. A blind `IDR`/`Rp` replacement would destroy historical definitions and tests and is deliberately not used.


Source files changed for this task: `copilot/demo_environment.py`, `copilot/cny_demo.py`, `copilot/data/shenzhen_reference.json`, `copilot/data/synthetic.py`, `copilot/server.py`, `copilot/auth.py`, `copilot/mcp_server.py`, `copilot/config.py`, `copilot/transaction_settings.py`, `.env.example`, `Dockerfile`, `.dockerignore`, `railway.toml`, this guide, `README.md` and `docs/README.md`. Existing UI files, financial formulas and permission policies were preserved. The earlier Import History Technical Details removal remains in place.


[Post-cutover application-wide currency audit](CURRENCY_CONSISTENCY_AUDIT.md): focused CNY verification, display corrections and classification of retained legacy references.
