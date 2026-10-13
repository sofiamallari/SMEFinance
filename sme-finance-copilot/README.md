# SME Finance Copilot

An AI finance co-pilot for ASEAN micro, small and medium enterprises (MSMEs). It covers three things:

- **Financing option matching**: ranks financing and support options against the business's stage and its binding constraint.
- **Cash-flow management with alerts**: a 30-day forecast, runway estimate and rule-based alerts.
- **Business financial analysis**: a seven-dimension assessment, placement in a six-stage Graduation Pipeline, and a merchant intelligence dashboard.

It also includes three tools from the framework: a **Revenue-Based Financing calculator**, a **Merchant Intelligence Dashboard** and a **Digital Payments Simulator** (QR Pay, Tap Pay, Pay Link and a POS checkout).

**New in v1.1:** real AI agents can now use the copilot.
- **AI agent mode:** free-text questions in the **Copilot tab** are answered by an LLM that calls the copilot's tools.
- **MCP server:** the copilot works as a Model Context Protocol server for **Microsoft Copilot Studio, GitHub Copilot in VS Code, Claude Desktop** and other MCP clients.

See **[docs/MCP_SETUP.md](docs/MCP_SETUP.md)**.

> **Prototype scope.** Every merchant is synthetic and the payment rails are a sandbox. The copilot is advisory: it never approves credit, never moves real money, and every financing figure is indicative.

---

## 1. Quick start (no dependencies)

Requirements: **Python 3.10+**. The core runs on the Python standard library alone.

```bash
cd sme-finance-copilot
python -m copilot.server          # web UI at http://127.0.0.1:8000 · MCP at http://127.0.0.1:8000/mcp
```

| Command | Purpose |
|---|---|
| `python -m copilot.server` | Starts the web UI, JSON API and MCP endpoint (`/mcp`) |
| `python -m copilot.mcp_server` | Starts the MCP server over stdio (normally launched by an AI client) |
| `python -m unittest discover -s tests -v` | Runs the test suite (103 tests). `pytest -q` also works. |
| `python scripts/run_demo.py` | Runs the end-to-end scenario, including an MCP session, and writes evidence to `evidence/` |

Without an LLM configured, the Copilot tab runs on the deterministic **rule engine**. To switch to an AI model, set `COPILOT_LLM_BASE_URL`, `COPILOT_LLM_API_KEY` and `COPILOT_LLM_MODEL` (see `.env.example`).

## 2. Synthetic personas

| ID | Business (fictional) | Country | Stage | Binding constraint | Top match |
|---|---|---|---|---|---|
| M001 | Kakanin food stall | PH | 1 Survival Borrower | Cash flow, low digital adoption | Business Wallet |
| M006 | Sari-sari store | PH | 2 Striving Amateur | Manual processes, low digital adoption | POS + inventory bundle |
| M002 | Coffee & tofu house | ID | 3 Steady Upgrader | Production bottleneck, receivable timing gap | Revenue-based financing / lease-to-own |
| M003 | Rattan crafts maker | TH | 4 Opportunity Seizer | Confirmed orders but too little working capital | Purchase-order financing |
| M004 | Bakery chain (4 units) | VN | 5 Expanding Proprietor | Ready to expand | Multi-unit expansion loan |
| M005 | Batik retailer (28 yrs) | MY | 6 Heir Seeker | No succession plan | Succession package |

## 3. Project layout

```
copilot/
  config.py            every threshold and assumption ([PAPER] / [REF-APP] / [ASSUMPTION])
  agent.py             agent core: progression loop, intent router, tool registry, policy-checked calls
  ai_agent.py          AI agent mode: LLM function-calling loop for the Copilot tab
  tools_spec.py        one tool catalog shared by the MCP server and the AI agent
  mcp_server.py        MCP server (stdio + Streamable HTTP), origin and API-key checks
  security.py          permission tiers, roles, consent, HMAC approval tokens, hash-chained audit log, guardrails
  llm.py               optional narrator that rewrites rule-engine replies
  server.py            standard-library HTTP server: web UI, JSON API, /mcp
  data/synthetic.py    deterministic synthetic ASEAN merchants
  modules/             dashboard · rbf · payments · cashflow · assessment · matching
web/index.html         Unified UI (no external scripts or CDNs)
tests/                 Unit, security, agent, HTTP, MCP and AI-agent tests
examples/mcp-clients/  Ready-made configs for VS Code, Claude Desktop and Copilot Studio
scripts/run_demo.py    Generates execution evidence
docs/                  MODULE_DESIGN.md · MCP_SETUP.md
```

## 4. API

| Method | Path | Purpose |
|---|---|---|
| POST | `/mcp` | **MCP Streamable HTTP endpoint** (JSON-RPC: `initialize`, `server/discover`, `tools/list`, `tools/call`) |
| GET | `/api/health` | Status, including `agent_mode` and MCP role |
| GET | `/api/cycle` · `/api/dashboard` · `/api/cashflow` · `/api/match` · `/api/rbf/limits` · `/api/pos/catalog` | Module data (`?merchant=<ID>`) |
| POST | `/api/rbf/quote` · `/api/payments` · `/api/payments/pay` | Quotes and sandbox payments |
| POST | `/api/chat` `{merchant, message, approval_token?, history?}` | Copilot tab (AI agent or rule engine) |

## 5. Permission tiers

| Tier | Meaning | Owner | Coach | Lender analyst | Demo guest | Exposed to AI / MCP |
|---|---|---|---|---|---|---|
| T0 Read | Analytics, forecasts, assessment | ✔ | ✔ with consent | ✔ with consent | ✔ | Yes |
| T1 Advise | Quotes, rankings | ✔ | ✔ with consent | ✔ with consent, financing only | ✔ | Yes |
| T2 Sandbox write | Create or simulate payments | ✔ | ✖ | ✖ | ✔ | MCP only (sandbox) |
| T3 Approval required | Package a financing application | ✔ + consent + single-use token | ✖ | ✖ | ✖ | **No** |
| T4 Prohibited | Approve credit, disburse, change limits | ✖ | ✖ | ✖ | ✖ | **No** |

Controls for AI callers:
- MCP identity comes from server configuration, never from the model.
- The in-app AI is locked to the merchant selected in the UI.
- Sensitive intents and prompt-injection-flagged messages never reach the model.
- `/mcp` validates the Origin header and supports an optional API key.
- Every AI tool call is written to the hash-chained audit log.

## 6. Deployment

```bash
# Local / VM
HOST=0.0.0.0 PORT=8000 COPILOT_APPROVAL_SECRET=<64-hex> COPILOT_MCP_API_KEY=<secret> python -m copilot.server
# Docker
docker build -t sme-finance-copilot .
docker run -p 8000:8000 -e COPILOT_APPROVAL_SECRET=change-me -e COPILOT_MCP_API_KEY=change-me sme-finance-copilot
```
For production, put the server behind TLS, set persistent secrets, ship `logs/*.jsonl` to write-once storage, and replace demo auth (`principal_from_request`) with your identity provider. For Copilot Studio, the `/mcp` URL must be public HTTPS (see docs/MCP_SETUP.md).

## 7. Framework traceability

| Framework element | Implementation |
|---|---|
| EQUIP: revenue-based financing | `modules/rbf.py`: fee steps down from 14% to 12% to 10%; remittance rate is 6% + 12% × (advance ÷ max), capped at 18%; nothing is paid on a zero-sales day |
| EQUIP: business wallet | Cash-flow buffer, fund-separation alert, settlement into the wallet |
| EQUIP: payment channels | `modules/payments.py`: standalone and POS pathways covering QR, tap and link |
| EQUIP: dashboard | `modules/dashboard.py`: channel mix, trends, capture ratio, timing delay vs. default |
| EXPAND | POS / tool bundles, lease-to-own, market linkage, operational-capacity dimension |
| ENTICE: 15% / 30% / 50% MoM tiers | `dashboard.incentive_status()`, with an anti-gaming minimum base |
| Graduation Pipeline (6 stages × 7 dimensions) | `modules/assessment.py` |
| Identify → Profile → Place → Activate → Measure | `Copilot.run_cycle()` |
| Risks: digital divide, MDR, data integrity, cybersecurity | Device-access factor and assisted roles · tiered MDR · engagement-washing flags · `security.py` |

## 8. Known limitations

- Synthetic data shows how the logic works, not whether it holds up against real outcomes. Weights and thresholds need calibration on a pilot.
- QR payloads use a scheme-style TLV layout tagged `SANDBOX` and are not valid on any network. The rendered QR is a placeholder.
- Sandbox payments reset on restart. Encoded/imported transactions and owner edits/deletions persist in the transaction ledger.
- The `server/discover` result fields follow the 2026-07-28 changelog's description. Clients that use the `initialize` handshake are the primary target.
- AI answers depend on the configured model. Numbers come from tools, but wording quality varies by model.


## Transaction Management v1.2 — Shenzhen International FinTechathon

The existing app, role selector, Digital Payments Simulator, Merchant Intelligence Dashboard, RBF Calculator and AI/MCP integrations remain in place.

Run from this directory with Python 3.10+: `python -m copilot.server`, then open http://127.0.0.1:8000. No runtime dependencies required. Run all tests with `python -m unittest discover -s tests -v` (103 tests).

Use the Transactions tab to encode income or expenses with date, amount, payment method, category, description and optional reference. Owners can view, edit and delete saved entries; staff can encode and upload for merchants in their authorized scope. Financing Agent uses the existing `lender_analyst` role and requires owner sharing consent; its AI tools only return authorized financing information, never transaction modification or raw ledger access.

Upload CSV UTF-8 or Excel `.xlsx` (one worksheet). Headers: required `date,type,amount`; optional `channel,category,reference,description`. Aliases `payment_method` and `reference_number` are accepted. Dates must be ISO text YYYY-MM-DD and no later than the reproducible demo date **2026-09-30**. Type is income or expense. Amount must be positive with at most two decimals. Methods: cash, qr_pay, tap_pay, pay_link, external_wallet, external_card. Blank method defaults to cash; blank category defaults to other. Limit: 1,000 rows and 3 MB. XLSX formulas and native Excel serial dates are not supported: paste values and format dates as ISO text. A CSV template is available in the tab.

The server validates the whole upload and detects repeated normalized rows and reference numbers within a batch and against saved entries for that merchant. Errors prevent importing the batch. The preview shows all accepted rows and row errors; press Confirm bulk import and approve the browser confirmation. Server preview tokens bind actor, role and merchant, expire after 10 minutes, and are single-use. Import revalidates duplicates to handle overlapping uploads. Preview never saves transactions.

Transactions, edits and deletions persist to `logs/manual_transactions.jsonl` (`COPILOT_TRANSACTION_FILE` override) and replay on restart. Dashboard revenue, expenses, net income, counts and revenue payment-method breakdowns use saved data. Existing cash-flow, risk alerts, assessments and financing calculations use the same merchant ledger. Ask Copilot “Analyze uploaded transactions” or “Generate a financial report” for financial totals, risk alerts and a 30-day revenue projection; ask for financing options for ranked recommendations. The `financial_report` tool is also available to AI and MCP clients, with every tool call passing through the existing policy guard.

See [docs/TRANSACTIONS.md](docs/TRANSACTIONS.md) for API details and limitations.
