# API contract navigation

The authoritative contracts are request handlers and current service validation, not a generated OpenAPI promise: [server.py](../../copilot/server.py), [MCP server](../../copilot/mcp_server.py), [tool schemas](../../copilot/tools_spec.py). The table covers key implemented routes; inspect source before building a client. Existing error/status handling and method restrictions remain unchanged.

| Method / route | Contract boundary |
|---|---|
| POST /api/auth/login | Username/password; server session cookie, CSRF and account-change state; no client-selected role |
| GET /api/auth/me; POST /api/auth/logout | Live session/profile/capabilities and existing logout |
| POST /api/auth/password-reset | Single-use administrator-issued token and new password |
| GET /api/merchants | Authorized merchant list |
| GET /api/dashboard; GET /api/financial-metrics | Authorized merchant; supported start/end/granularity for dashboard; canonical metrics retain period/currency |
| POST /api/merchant-transactions/entry | merchant, entry and stable idempotency_key; existing required fields/normalization |
| POST /api/pos-import/stage | merchant plus supported file descriptors; secure temporary staging |
| POST /api/pos-import/{batch}/validate | merchant plus independent mappings; metrics, findings, valid flag and confirmation token when permitted |
| GET /api/pos-import/{batch}/preview | Authorized merchant/session batch, offset/limit; normalized rows and metrics; not a save |
| POST /api/pos-import/{batch}/commit | Current preview token and explicit confirmed=true; server rechecks state/integrity |
| GET /api/merchant-transactions/history | Merchant-scoped history and supported filters/pagination |
| GET /api/bank/applications; GET /api/bank/applications/{id} | Receiving Bank’s safe routed request metadata and reviews |
| GET /api/bank/merchants; GET /api/bank/review | Current grant-filtered financial review; each section requires its category |
| GET /api/bank/export | Existing consent-scoped CSV financial export |
| POST /api/applications/{id}/review | Authorized receiving Bank; supported outcome/note; append-only simulated review |
| GET /api/survival-simulation/baseline | Enabled, Owner-only authorized merchant baseline |
| POST /api/survival-simulation/run | merchant, supported sales_change_percent, expense_change_percent, months and confirmed=true; no financial writes |
| POST /api/chat; POST /mcp | Authenticated scoped AI/tool paths; source schemas and per-tool permissions apply |

Cookie-authenticated writes require the current CSRF header and same-origin checks. Bearer sessions have the same live role/merchant/consent restrictions. Unknown/unauthorized merchant responses must not be used to infer another business’s existence. No API key bypasses identity. [MCP clients](mcp.md) · [data lifecycle](data-processing.md) · [security](security-permissions.md).
