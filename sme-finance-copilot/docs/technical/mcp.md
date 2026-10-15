# Authenticated MCP

Use the initialized active CNY dataset and normal application server. HTTP POST /mcp uses the authenticated session. Cookie clients send the current CSRF token and satisfy origin checks; legitimate non-browser clients can use a server-issued bearer session. An MCP API key or environment role/consent setting never substitutes for a live session.

Stdio entry point is `python -m copilot.mcp_server` with COPILOT_MCP_SESSION_TOKEN supplied privately. Dataset/storage selection must match the application’s active identity database and canonical journal; conflicting overrides fail startup. Never put tokens in Git, documentation or command transcripts. HTTP MCP on the running app avoids independent stale copies of transaction state; do not run multiple writing service processes against the same POC stores.

Tool names/schemas are in [tools_spec.py](../../copilot/tools_spec.py); transport handling in [mcp_server.py](../../copilot/mcp_server.py). Source/merchant/action/tier/category/confirmation checks apply to every authenticated call. [Permissions](security-permissions.md) · [environment](../operations/environment.md) · [AI safeguards](ai-safeguards.md).
