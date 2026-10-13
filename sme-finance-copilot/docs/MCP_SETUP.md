# Connecting SME Finance Copilot to real AI agents (MCP)

The project ships two ways to put a real AI model in front of the copilot's tools.

| Option | What you get | Where you type questions |
|---|---|---|
| **A. AI agent mode in the web app** | The **Copilot tab** answers free-text questions by letting an LLM call the copilot's tools | `http://127.0.0.1:8000` → Copilot tab |
| **B. MCP server** | Any MCP-capable agent (Copilot Studio, GitHub Copilot agent mode in VS Code, Claude Desktop, others) discovers and calls the same tools | That agent's own chat |

Both use one tool catalog (`copilot/tools_spec.py`), and every call goes through the same
permission checks and hash-chained audit log as the web UI.

---

## A. AI agent mode in the Copilot tab

Set three environment variables before starting the server. Any **OpenAI-compatible**
`/chat/completions` endpoint with function calling works.

**Windows (Command Prompt)**
```bat
set COPILOT_LLM_BASE_URL=https://your-endpoint/v1
set COPILOT_LLM_API_KEY=your-key
set COPILOT_LLM_MODEL=your-model-or-deployment-name
python -m copilot.server
```
**Mac / Linux**
```bash
export COPILOT_LLM_BASE_URL=https://your-endpoint/v1
export COPILOT_LLM_API_KEY=your-key
export COPILOT_LLM_MODEL=your-model-or-deployment-name
python -m copilot.server
```
The Copilot tab badge changes from **Rule engine** to **AI agent connected**. Each AI answer shows
the tools it used.

How it behaves:
- The AI can only read data for the **merchant selected in the UI**. `merchant_id` is not even
  offered to the model, and any value it supplies is overridden.
- **Approve credit, move money, submit an application, create payments**, and any message flagged
  for prompt injection, **never reach the model**. The rule engine and approval-token flow handle them.
- If the model is unreachable or misbehaves, the app falls back to the rule engine automatically
  (logged as `ai_agent_fallback`).
- To force the rule engine, set `COPILOT_AGENT_MODE=off`.

---

## B. MCP server

### Tools exposed
`list_merchants`, `ask_copilot`, `assess_business`, `match_financing`, `rbf_quote`,
`cashflow_forecast`, `cashflow_alerts`, `get_dashboard`, `incentive_status`,
`create_sandbox_payment`, `payment_status`.

These are **not exposed**: credit approval, fund disbursement, limit changes, and application
submission (approval tier).

### Transports
| Transport | Start command | Endpoint |
|---|---|---|
| stdio (local agents) | started automatically by the client: `python -m copilot.mcp_server` | — |
| Streamable HTTP | `python -m copilot.server` (same process as the web app) | `POST http://127.0.0.1:8000/mcp` |
| Streamable HTTP, standalone | `python -m copilot.mcp_server --http --port 8001` | `POST http://127.0.0.1:8001/mcp` |

Protocol support: the `initialize` handshake (revisions 2025-03-26, 2025-06-18 and 2025-11-25) plus
`server/discover` and per-request `_meta` versioning from the stateless 2026-07-28 revision.
Responses are plain JSON (no SSE stream needed).

### Who the MCP caller is (set by configuration, never by the model)
| Variable | Values | Default |
|---|---|---|
| `COPILOT_MCP_ROLE` | owner · coach · lender_analyst · demo_guest | owner |
| `COPILOT_MCP_MERCHANTS` | comma list, e.g. `M002,M003` | all |
| `COPILOT_MCP_CONSENT` | yes · no | yes |
| `COPILOT_MCP_API_KEY` | any secret; clients send `Authorization: Bearer <key>` or `X-API-Key: <key>` | none |
| `COPILOT_MCP_ALLOWED_ORIGINS` | extra browser origins allowed to call `/mcp` | localhost only |

### 1. GitHub Copilot in VS Code (agent mode)
1. Open the `sme-finance-copilot` folder in VS Code.
2. Copy `examples/mcp-clients/vscode-.mcp.json` to the folder root and rename it **`.mcp.json`**.
   If your VS Code version uses `.vscode/mcp.json`, rename the top-level key `mcpServers` to `servers`.
3. Open Copilot Chat, switch to **Agent** mode, start the server when prompted, and trust it.
4. Ask: *"Using sme-finance-copilot, what financing fits Baan Rattan Crafts?"*

Note: your organisation's Copilot policy must allow MCP servers.

### 2. Microsoft Copilot Studio
Copilot Studio runs in the cloud and connects over **Streamable HTTP**, so it needs a public
**HTTPS** URL.
1. Start the server with an API key:
   `COPILOT_MCP_API_KEY=<long-random-secret> python -m copilot.server`
2. Expose port 8000 over HTTPS, using either:
   - a tunnel, such as VS Code **Ports → Forward a Port → set to Public** (dev tunnels) or ngrok, or
   - a cloud deployment (see the Dockerfile; for example Azure Container Apps or App Service).
3. In Copilot Studio, open your agent → **Tools → Add a tool → New tool → Model Context Protocol**.
4. Enter the server name, a description (see `examples/mcp-clients/copilot-studio-agent-instructions.md`)
   and the server URL `https://<your-public-host>/mcp`. For authentication choose **API key**, with
   header `X-API-Key` (or Bearer).
5. Create the connection, add the tool to the agent, and make sure **generative orchestration** is on.
6. Test in the agent's test pane: *"How is Tani Coffee & Tofu House doing?"*

> Work tenants: creating agents and custom connectors may require your Power Platform admin and is
> subject to your organisation's data policies. For a competition demo, use a personal or developer
> environment. Never expose the server publicly without `COPILOT_MCP_API_KEY`.

### 3. Claude Desktop or other stdio clients
Use `examples/mcp-clients/claude_desktop_config.json` and change `cwd` to your project folder.

### Quick manual test (no AI client needed)
```bash
curl -s -X POST http://127.0.0.1:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"assess_business","arguments":{"merchant_id":"M002"}}}'
```

### Audit
MCP calls are logged with actor `mcp-<role>`: in `logs/audit.jsonl` when served over HTTP, and in
`logs/mcp_audit.jsonl` over stdio.
