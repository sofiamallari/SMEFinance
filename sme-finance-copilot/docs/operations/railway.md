# Railway preparation — not deployed

Service root: sme-finance-copilot. Existing [Dockerfile](../../Dockerfile) uses Python 3.12-slim, installs requirements, retains non-root appuser, serves the static frontend from the Python process and starts `python -m copilot.server`. [railway.toml](../../railway.toml) checks /login. HOST must be 0.0.0.0; Railway supplies PORT. No separate Node frontend service is required.

Attach persistent storage at /data and set COPILOT_DATA_DIR=/data/shenzhen_cny_demo. Set authenticated mode, HTTPS Secure-cookie configuration behind actual TLS, unique approval secret and optional provider settings via service secrets. For first initialization, use a private seed-time password in an approved one-off shell with the same volume mounted; run `python -m copilot.cny_demo seed`, then `verify`. Remove the seed password variable and rotate shared synthetic account passwords before public access. Do not run seed automatically on every start or upload the original private backup.

Use one replica/process with the existing threaded server and persistent SQLite plus JSONL stores. Migrating only SQLite to PostgreSQL would not solve canonical-journal coordination; horizontal scaling needs separate architectural approval. Verify the volume is writable by appuser; image-time chown does not guarantee mounted-volume ownership. Never depend on ephemeral container storage for financial records.

Outstanding recorded checks: Docker build was not verified because the local engine was unavailable; volume ownership, live TLS/cookies, unique credentials/secret, actual restart persistence and provider configuration require candidate-environment verification. No service was created, deployed or billed by documentation work. .dockerignore excludes logs, private databases, journals, .env, evidence and ZIPs; do not deliberately copy them into a public image.

[Environment](environment.md) · [backup/recovery](backup-recovery.md) · [known gaps](../technical/known-limitations.md).
