# Known limitations and business confirmation

This is a synthetic POC, not live payment/banking infrastructure, audited financial statements or production security certification.

- Module/action matrix, maturity weights/gates, incentive descriptions, MDR/tax assumptions, financing matching and RBF parameters are provisional business decisions. No documentation consolidation approves or changes them.
- Maturity stage-6 code uses owner_transition_expected and gated stage ≥4, while a config comment describes a stage-5-level score. Confirm the intended business rule before changing code; current guides describe actual execution.
- Five-step journey completion criteria and post-activation outcome measurement remain undefined. Backend evidence remains, but normal Owner navigation uses Dashboard Business Growth for six-stage maturity.
- CNY history ends at fixed 2026-09-30; recent canonical activity can extend some financial dates. Rolling complete-month Survival coverage will eventually age out. Regeneration/date changes require explicit seed/version review, not automatic reinitialization.
- Synthetic opening wallets/obligations and recorded expense proxies do not prove actual cash, audited profit, bank balances, tax liability or bookkeeping completeness. Unlinked POS/sandbox duplicate uncertainty remains.
- No real payments, financing approval/rejection/disbursement or production underwriting. Bank outcomes are only the three simulated review labels. PDF/XLSX/email Bank export is not implemented; existing CSV is supported.
- Admin provisions memberships; Owner delegates existing Staff. Individual Bank account grants are not organization-wide authorization; there is no Bank-initiated request workflow.
- No MFA, emailed/self-service password recovery or automated incident-response/backup service. Secure cookies require actual HTTPS configuration. Prior exports cannot be recalled after consent revocation.
- JSONL AuditLog starts a new GENESIS segment per process. Individual segments were checked in cutover evidence; continuous cross-restart chaining is not implemented. Do not describe the complete JSONL file as a single continuous chain. SQLite audit uses its own existing mechanism.
- SQLite plus canonical JSONL uses a one-process/one-replica persistent-volume POC topology. Cross-store writes are not a distributed atomic snapshot; horizontal scaling requires approved persistence/locking work.
- AI connectivity depends on provider/model/key availability. Deterministic responses and typed fallback do not prove live Gemini. Cross-session transcript restoration and unrestricted causal/multilingual financial analysis are not promised. Bank portal has no AI UI.
- Docker build was unverified in the recorded preparation because the local engine was unavailable. Non-root volume permissions, deployment credentials/HTTPS and restart behavior require deployment verification. Nothing has been deployed by documentation work.
- Historical tests/diagnostic scripts include legacy currency assumptions and may need an explicitly isolated current fixture. Historical pass counts do not establish current whole-suite success. No application regression was run in this documentation task.

[Security](security-permissions.md) · [algorithm definitions](financial-algorithms.md) · [deployment preparation](../operations/railway.md) · [evidence scope](../hackathon/evidence.md).
