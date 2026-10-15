# Environment and secrets

[.env.example](../../.env.example) lists available examples; it contains no actual key. The allowlisted loader reads COPILOT_LLM_BASE_URL, COPILOT_LLM_API_KEY, COPILOT_LLM_MODEL, COPILOT_AGENT_MODE and FINANCIAL_SURVIVAL_SIMULATION_ENABLED. Process values take precedence. COPILOT_LOAD_LLM_ENV=no disables local loading. General identity/storage/HOST/PORT/HTTPS configuration is **not** automatically loaded from .env.

| Variable | Use |
|---|---|
| COPILOT_DATASET | Active default shenzhen_cny_demo; normal app rejects legacy environments |
| COPILOT_DATA_DIR | Optional dedicated local directory; required persistent root on Railway |
| COPILOT_AUTH_MODE | authenticated; CNY environment rejects a demo bypass mode |
| COPILOT_IDENTITY_DB / TRANSACTION_FILE / AUDIT_LOG / EXEC_LOG | Derived from the selected data root; conflicting explicit paths fail closed |
| HOST / PORT | Local 127.0.0.1/8000 unless overridden; Railway needs 0.0.0.0 and supplied PORT |
| COPILOT_HTTPS | yes only behind actual HTTPS; enables Secure cookies |
| COPILOT_INITIALIZE_CNY | Docker lifecycle only: yes for first empty-volume initialization, then no/unset; see [Railway lifecycle](railway.md) |
| COPILOT_CNY_DEMO_PASSWORD | Private seed-time synthetic password; remove after initialization |
| COPILOT_APPROVAL_SECRET | Private stable approval-signing secret; never example placeholder values |
| COPILOT_LLM_BASE_URL / API_KEY / MODEL | Optional OpenAI-compatible provider configuration; no credentials in docs |
| FINANCIAL_SURVIVAL_SIMULATION_ENABLED | Optional Owner simulation, false by default unless configured |

Gemini connection settings in prior assessments used `https://generativelanguage.googleapis.com/v1beta/openai/` and provisional `gemini-3.1-flash-lite`. Current availability is not guaranteed by this document. No-key operation can use existing deterministic guidance; do not call that a live provider pass.

Publish source/seed code and synthetic scenario manifests if appropriate. Never publicly publish `.env`, credential files, session/reset tokens, original identity backups or API keys. A trusted private initialized-demo handoff must transfer a matching storage set and credentials separately through an appropriate private channel. [Setup](local-setup.md) · [Railway](railway.md).
