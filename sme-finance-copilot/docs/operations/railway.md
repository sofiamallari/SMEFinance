# Railway deployment â€” controlled CNY demo

This guide describes the container lifecycle implemented in `copilot/deployment.py`. It does not mean a Railway deployment has been verified. Use one process and one replica. Financial algorithms, authentication, consent and merchant permissions are unchanged.

## GitHub and build settings

| Railway setting | Value |
|---|---|
| Repository | sofiamallari/SMEFinance |
| Branch | main, after the deployment changes are reviewed and committed |
| Root Directory | /sme-finance-copilot |
| Builder | Dockerfile |
| Dockerfile | Dockerfile relative to the service root |
| Build context | sme-finance-copilot/ |
| Config file, when explicitly selected | /sme-finance-copilot/railway.toml |
| Start Command | Clear an old override to use Docker CMD; alternatively set exactly `python -m copilot.deployment` |
| Health check | /login |
| Initial health-check timeout | Allow 300 seconds for first seed; adjust only after measuring |
| Volume | Mount at /data |
| Replicas / application processes | 1 / 1 |
| Public networking | Generate an HTTPS domain after private preparation |

The image uses Python 3.12-slim and installs requirements.txt. No Node build or start.sh is required. Docker CMD runs `python -m copilot.deployment`; that process eventually execs `python -m copilot.server` with Railway's PORT and HOST=0.0.0.0. Static assets are served by the same Python server.

railway.toml retains builder, health and restart settings but deliberately has no startCommand. Config-as-code can override dashboard settings; do not restore a dashboard seed-then-server command or point directly at copilot.server, because both bypass the deployment safeguards. Railway's current documentation marks legacy config-as-code deprecated; confirm its acceptance and effective settings on the actual service. If the service does not load this file, enter the table's settings in Railway. Do not assume Root Directory also selects the config file.

Repository edits cannot attach a volume, configure private variables, select the GitHub connection/branch, generate a domain, set mounted storage capacity/backups, or establish actual account permissions. Those require Railway setup and separate deployment authorization.

## Environment variables

Set these as Railway service variables, not only in a local .env. Never put real secret values in Git, Dockerfile, build arguments, screenshots or chat.

| Variable | Requirement / example | Secret | When |
|---|---|---|---|
| COPILOT_DATASET | shenzhen_cny_demo | No | Initialize + runtime |
| COPILOT_DATA_DIR | Required: /data/shenzhen_cny_demo | No | Initialize + runtime |
| COPILOT_AUTH_MODE | authenticated; bypass rejected | No | Initialize + runtime |
| COPILOT_HTTPS | Required on Railway: yes | No | Runtime; needed for Secure cookies and origin validation |
| COPILOT_APPROVAL_SECRET | Required: private stable random value, at least 32 characters; prefer 64 random hex characters | Yes | Initialize + every restart |
| COPILOT_INITIALIZE_CNY | yes only on the first empty-volume start; then no or unset | No | First initialization only |
| COPILOT_CNY_DEMO_PASSWORD | Private 12â€“256 characters, with uppercase, lowercase and digits | Yes | First initialization only; remove after saving privately |
| COPILOT_LOAD_LLM_ENV | Recommended: no | No | Runtime |
| COPILOT_AGENT_MODE | off without provider; auto to enable configured Gemini | No | Runtime |
| COPILOT_LLM_BASE_URL | Optional: https://generativelanguage.googleapis.com/v1beta/openai/ | No | Runtime if provider enabled |
| COPILOT_LLM_API_KEY | Optional private provider key | Yes | Runtime if provider enabled |
| COPILOT_LLM_MODEL | Optional provisional gemini-3.1-flash-lite; verify availability separately | No | Runtime if provider enabled |
| FINANCIAL_SURVIVAL_SIMULATION_ENABLED | true to show the Owner simulation; otherwise false | No | Runtime |
| HOST | 0.0.0.0 | No | Runtime; image default |
| PORT | Railway-injected port; do not hardcode if supplied | No | Runtime |

Leave COPILOT_IDENTITY_DB, COPILOT_TRANSACTION_FILE, COPILOT_AUDIT_LOG and COPILOT_EXEC_LOG unset. They are derived from COPILOT_DATA_DIR; conflicting overrides fail closed. No MCP demo identity or API key bypass is supported. Standalone stdio MCP is not a second process in this deployment.

No RAILWAY_RUN_UID override is normally necessary: the image starts only its bootstrap as root, then irreversibly drops to appuser before importing the seeder or application. If the service has an existing UID override, inspect it rather than assuming it matches the image. Even with RAILWAY_RUN_UID=0, this entry point drops privileges before starting the server. Do not replace the entry point with a direct server command.

## Persistent volume and ownership

Mount /data, not the application source. The bootstrap may create and change ownership only inside /data/shenzhen_cny_demo. It does not recursively chown /data, /app or unrelated volume directories at runtime. Symbolic links, special files and hard-linked files in the data tree are refused. This assumes a trusted dedicated volume with no concurrent external writers.

Existing files receive private mode 0600 and directories 0700. The bootstrap drops supplementary groups, GID and UID to appuser and uses umask 077. Seeding, verification, database migrations and the normal server run after that drop. The application server never runs as root. The fixed privileged target is intentional; a custom root-owned path is rejected rather than broadly chowned.

All required persistent state stays under /data/shenzhen_cny_demo:

- identity.sqlite3 and SQLite sidecars (currently DELETE rollback journaling).
- transactions.jsonl and transactions.jsonl.lock (Linux flock plus checksum verification and fsync).
- audit.jsonl and execution.jsonl.
- dataset.json, preparation.json, validation.json and synthetic-cny.csv/.xlsx seed fixtures.
- Import staging, sessions, role grants, consents, settings, payment state, financing applications and Bank reviews are tables in identity.sqlite3.

Image-time chown does not fix mounted-volume ownership; the runtime bootstrap handles the dedicated child. Real Railway ownership and Linux privilege dropping must still be verified on a disposable candidate deployment. One volume does not make multiple replicas safe. Do not add workers or scale horizontally.

## First-time initialization

1. Confirm the reviewed code containing copilot.deployment is the deployed commit. Attach a new dedicated /data volume and configure variables above. Do not reuse an unknown populated volume.
2. Privately generate COPILOT_APPROVAL_SECRET and COPILOT_CNY_DEMO_PASSWORD. Copy the seed password to an appropriate private password manager; no credentials file is automatically generated.
3. Set COPILOT_INITIALIZE_CNY=yes. Clear obsolete Start Command overrides or use `python -m copilot.deployment`.
4. Deploy only when separately authorized. The volume is mounted at runtime, so do not seed during Docker build or a Railway pre-deploy command. No interactive Railway shell is required by this design.
5. After scoped ownership preparation and privilege drop, the lifecycle invokes the existing commands:

   ```sh
   python -m copilot.cny_demo seed
   python -m copilot.cny_demo verify
   ```

6. The lifecycle also checks dataset metadata, SQLite integrity/foreign keys, the six merchant profiles and four roles, persisted CNY values and canonical ledger checksums before starting the server. These are storage checks, not a full business regression suite.
7. Wait for the initialization-verified message and healthy /login. Confirm /api/health reports authenticated mode.
8. Set COPILOT_INITIALIZE_CNY=no (or remove it) and remove COPILOT_CNY_DEMO_PASSWORD from the service. Apply these changes together before the next restart. The running server already has the seed-password environment value removed by the lifecycle.
9. Privately sign in and rotate the four demo account passwords individually before public sharing. The initial accounts are demo_admin, demo_owner, demo_staff and demo_bank, using the supplied seed password. Staff still needs explicit delegated grants.

The seed uses the packaged synthetic reference manifest, not a local private database. It creates six CNY merchants and four roles, canonical transactions and import history, simulated payments, consents, applications and Bank review evidence. Financial source dates are fixed for reproducibility; rolling-window views may become stale. Random IDs, salts and timestamps mean it is not a byte-identical fixture.

An enabled initialization flag with an existing dataset deliberately stops without reseeding. If seed or verification fails, preserve the entire partial directory and logs. Never automatically clear it, retry over it, or delete its completion marker. Investigate and restore a verified matching backup or explicitly provision a separate clean volume after approval.

## Normal startup and restart persistence

Keep the same stable approval secret, authenticated configuration and volume. Initialization must be disabled and the seed password removed. The lifecycle runs read-only preflight before normal server startup; ordinary AuthStore migrations and import-intent recovery remain existing application behavior. It never invokes the seed on a normal restart.

Before restarting, record the six merchant IDs and a known transaction/application identifier. After restarting, confirm the same records remain, currencies are CNY, and no second seed has appeared. Session chat memory is not guaranteed to persist. Use private volume inspection or a matching snapshot for ledger hash comparisons; never publish database/log contents through HTTP.

The dedicated readiness preflight does not replace backups. The CLI `cny_demo verify` itself constructs application services and may run migrations/recovery; reserve it for controlled verification with no concurrent writers, not a public health check.

## Health, authentication and smoke checks

The Docker and Railway health check is GET /login using the configured PORT. GET /api/health returns basic configuration health; it is not a continuous database or reconciliation monitor. Verify HTTPS login actually sets Secure, HttpOnly and SameSite=Strict cookies, and test a browser request with Railway's forwarded Host/Origin behavior. Local cookie-header checks cannot prove the real proxy behavior.

After initialization, check Owner merchant selection and dashboard; Staff denial without grants; Bank denial outside category-specific active consent; Admin denial of merchant financial access; transaction history; financing applications; optional Business Stress Test; and restart persistence. Gemini is optional and deterministic grounded/help responses remain available without keys. Digital Payments and Bank review are simulated and need no real payment/banking credentials.

## Troubleshooting

| Symptom | Action |
|---|---|
| Railpack cannot identify the project | Set Root Directory to /sme-finance-copilot and use its Dockerfile |
| Railway requires COPILOT_DATA_DIR | Attach /data and inject the exact data-root variable |
| Dataset missing | On a confirmed empty dedicated volume, use explicit initialization and private password |
| Already initialized / initialization flag retained | Set flag to no and remove seed-password service variable; do not reseed |
| Partial/incomplete dataset | Stop; preserve files and inspect or restore a matching backup |
| Permission denied | Verify this commit's Docker lifecycle is active and inspect UID override/mount; never chmod 777 |
| Seed never runs | Remove old dashboard direct-server command and confirm effective Docker CMD/config |
| Login origin rejected / cookie not sent | Verify HTTPS=yes and real HTTPS Host/Origin; do not weaken CSRF |
| Startup times out | Inspect seed/permission errors first; allow measured initialization time |
| Provider unavailable | Use agent mode off or existing deterministic fallback; never expose the provider key |
| Generic preparation failure | Inspect storage/configuration privately; no stack traces or secrets are intentionally echoed by the entry point |

## Backup, recovery and limitations

Back up the entire dedicated directory consistently while writes are stopped, or use the existing SQLite backup mechanism plus a coordinated ledger/log snapshot. Retain audit and execution evidence. A SQLite-only copy does not preserve canonical transactions or their coordination with import state. Restore into a separate location, validate matching state, then activate only through an approved controlled recovery. Do not upload the original private local backup to the Docker build.

Audit JSONL restarts currently create separate GENESIS chain segments, not one continuous cross-process chain. The standard-library HTTP server and local stores are a constrained POC deployment. This work does not add production-grade HA, real payments, credit approval, new permissions or a new financial algorithm.

## Focused local verification — 15 October 2026

On Python 3.12.14, 35 disposable-storage checks passed: fresh seed and health, six merchant dashboards, four account logins and Secure-cookie headers, static assets, no-provider fallback, denied Staff/Bank/Admin financial reads, partial/missing dataset rejection, retained-flag rejection, tampered-ledger rejection, and normal restart with unchanged canonical ledger. Before/after hashes confirmed the existing local CNY dataset files were untouched. SQL reads in the preflight explicitly close their connections.

Python AST parsing, Railway TOML parsing and git diff --check passed. Mocked POSIX checks verified the supplementary-group/GID/UID drop order and rejection of an unrelated privileged path; these are not real Linux execution. Docker CLI is installed but its engine is unavailable, so image build, actual mounted-volume ownership, real non-root process execution and Railway HTTPS/restart persistence are NOT VERIFIED. No full regression suite or external provider request was run.

Focused local checks and their platform limitations are reported with the implementation. A Windows initialization/restart check is not proof of Linux UID dropping, Railway ownership, TLS, volume persistence or a successful Docker image build.

[Environment](environment.md) · [Backup/recovery](backup-recovery.md) · [Security model](../technical/security-permissions.md) · [Known limitations](../technical/known-limitations.md)
