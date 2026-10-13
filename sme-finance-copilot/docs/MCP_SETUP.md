# Authenticated MCP setup (v1.2)

Authenticated mode is now the default for HTTP and stdio. First bootstrap identity using the application README and assign business accounts and memberships. Existing financial tool names, schemas and transports remain unchanged.

## HTTP

Start `python -m copilot.server --port 8000`. Use `/api/auth/login` to authenticate a business account. For cookie clients, retain the HttpOnly `sme_session` cookie and send the returned CSRF token as `X-CSRF-Token` on POST `/mcp`. Non-browser MCP clients may supply that same server-issued session token as `Authorization: Bearer <session-token>` instead of a cookie. Cookie sessions and bearer sessions have the same account, lifetime, merchant membership, permission and consent checks. There is no separate unrestricted MCP service account.

`COPILOT_MCP_API_KEY`, `X-API-Key`, `COPILOT_MCP_ROLE`, `COPILOT_MCP_MERCHANTS` and `COPILOT_MCP_CONSENT` cannot establish identity or bypass merchant authorization in authenticated mode. A configured API key is not a valid session token. Requests with browser Origin must match the application origin; CLI/server clients may omit Origin. Use HTTPS and `COPILOT_HTTPS=yes` outside local development.

## Stdio

Set `COPILOT_IDENTITY_DB` to the same identity database used by the web app, `COPILOT_TRANSACTION_FILE` to the same transaction ledger, and `COPILOT_MCP_SESSION_TOKEN` to a valid server-issued session token kept in a secret store. Start `python -m copilot.mcp_server`. Each financial tool call rechecks the live session, role, scope, policy and consent. Without a valid session, authenticated stdio startup fails closed.

The standalone MCP process loads transaction data at startup; restart it after transaction-ledger updates performed by another process. For live app data, use HTTP `/mcp` on the running application. Avoid running multiple transaction-writing processes against the same JSONL ledger.

## Client compatibility

The example client configs require secure injection of a server-issued session token; their placeholders are not usable credentials. Clients that require OAuth discovery rather than a session Bearer header need an adapter or future OAuth integration. OAuth, refresh tokens and automatic MCP-client login are not implemented in this MVP. Short-lived sessions expire and must be reauthenticated through the login flow.

## Legacy demo compatibility

Explicit `COPILOT_AUTH_MODE=demo` restores the original environment-selected MCP identity and optional demo API-key gate for synthetic, localhost-only testing. Legacy API keys are not production authentication. The legacy protocol tests explicitly configure this mode only where needed; authenticated transport and authorization tests verify that it cannot be activated by client headers or arguments.
