# AI Financial Partner 2.0 — local governance implementation

Local feature: `feature/ai-governance-chatbot-v2`. Local policy: **0.6.0**, schema **1.0.0**. The supplied policy's `proposed` metadata is preserved; user approval covers local implementation/testing, not production readiness. No `saif` directory was found by a case-insensitive repository search.

## Boundaries and discovery

Authentication and existing application authorization remain authoritative. The approved JSON policy is an additional restriction, never a permission grant. `owner`, `staff`, `lender_analyst` and `security_admin` still map to the four canonical roles. Missing/invalid policy disables governed conversations and tools; it never falls back to the old unrestricted chat flow. Existing financial modules, transactions, formulas and business-page confirmations remain in place.

Existing integration: `ai_agent.py` uses OpenAI-compatible function calls, including Gemini configuration loaded by `llm_config.py`; `agent.py`, `tools_spec.py` and `mcp_server.py` supplied the original tools. The new path reuses existing authentication, PolicyGuard, financial services, provider configuration and drawer. Its tool registry replaces the broad registry **for authenticated AI/MCP calls**. Legacy internal agent services remain for compatibility and native business workflows; they are not fallback tools for this assistant.

| Module/source | Governed support | Deliberate boundary/gap |
|---|---|---|
| Business Overview | Net sales, sales/payment counts, period and currency | Expenses/net income are not in the approved summary allowlist |
| Transactions/POS | Existing canonical projection feeds summary/trends | No raw ledger, descriptions, customer identities or import writes |
| Digital Payments | Separate sandbox payment state; excluded from canonical financial reporting | No QR/payment creation or execution tool |
| Cash Flow | Forecast inflows/outflows, synthetic opening, closing/minimum, runway and expense-coverage estimate | Synthetic/unreconciled opening; incomplete expense coverage; no verified current cash |
| Business highlights | Existing receivables explanation and incentive label | No new maturity/eligibility engine or full assessment tool |
| Financing | Specific submitted application reference, submission status/requested amount | Approved amounts/terms/decisions are unavailable in this adapter, returned null; no inferred company-wide financing total |
| Survival Simulation | Existing operating-result engine, explicit requested assumptions | No property amortization, credit approval, verified liquidity or actual cash runway |
| Bank authorization / Staff delegation / settings / import monitoring | Existing permission-checked application-help registry | No new reads of private user records, policy internals, consent mutation or import commit |
| External research | Fixed public Shenzhen SME lending-rate topic and exact-query approval | No arbitrary URLs, private queries, automatic follow-up search or live-provider verification |

## Role/capability intersection

| Role | Available subset | Denied / blocked |
|---|---|---|
| SME Owner | Authorized merchant read tools, public education/help/research proposal; enabled and requested Survival Simulation | Other merchants, financial execution, unmodeled financial conclusions |
| SME Staff | Education, authorized explain-only application help, public research approval when existing `use_copilot` grant permits | Financing always denied. Conditional operational/simulation/expansion capabilities remain denied because exact `finance.*` permissions are absent |
| Bank | Public education/research through an already authorized session/merchant API or MCP context | Conditional financing tools remain denied despite existing consent; exact `finance.financing.*` permissions are absent. No general merchant summaries/cash flow |
| System Admin | Existing administration portal | Existing backend does not grant `use_copilot` or merchant financial scope. Even policy-allowed D0 assistant access is therefore unavailable; no automatic role expansion |

These are safe prerequisite gaps, not successful Staff/Bank financial integrations. Existing application grants are not renamed or promoted into the missing granular permissions. The Bank portal still has no new chat drawer.

## Policy, gateway and data minimization

`governance_policy.py` loads only the fixed `config/ai_governance_policy.json` and schema. JSON Schema validation and semantic checks reject unknown roles/capabilities/tools/effects, unsafe mappings, financial execution, unclassified/D4 output, default-allow, unsafe persistence/approval flags, or excessive reviewed limits. Browser/model input cannot select a policy path. Changes require server restart and review.

`governed_tools.py` validates strict arguments, derives identity from the live server session, checks membership, capability and existing action permission, reuses existing PolicyGuard where applicable, and filters fields before any model invocation. A supplied `merchant_id` argument is rejected. Financing uses the existing recipient/merchant/consent-aware application service, with one exact reference. Scope and permissions are checked again after retrieval. Results are structurally validated and bounded to at most 100 records and 64 KiB. Public research is at most five results. Financial/research worker response deadlines remain bounded to ten seconds and four concurrent workers; Gemini requests allow thirty seconds within a sixty-second chat-turn budget. Remaining time bounds subsequent model/tool calls and timeout fallback does not start new financial retrieval after the deadline; a timed-out read worker may finish in the background, but cannot execute a financial write. There is no automatic provider retry.

Field classification is explicit in `FIELD_CLASSES`: period/count/channel metadata are D1, net sales and cash-flow values D2, financing fields D3, public citations D0. Simulation nested results are D2 and nested schemas exclude extra fields. No D4 fields are registered. Unknown fields are dropped; unexpected nested content fails validation. Whole database records, transaction descriptions, account secrets and unrestricted workflow packets are never model context.

| Approved tool | Input contract | Output boundary |
|---|---|---|
| `get_financial_summary` | Optional ISO `start`, `end`, supported `granularity` | Approved period, CNY, recorded net sales, count, retrieval timestamp |
| `get_transaction_trends` | Same; ordered range no longer than 366 days | Existing dashboard buckets, sales/payment count and recorded sales; shorter range required over record limit |
| `get_payment_channel_mix` | Same | Period/channel/count/share of transaction volume, not revenue share |
| `get_cash_flow` | Empty object | Forecast metrics, opening/latest-data dates and limitations; `net_cash_flow` and `available_cash_if_verified` remain null |
| `run_cash_impact_scenario` | Bounded dates/horizon, one-time or incremental monthly costs, optional separate user cash | Hypothetical baseline/adjusted summaries, explicit schedule and limitations; see [calculation contract](ai-stabilization.md#scenario-calculation-contract) |
| `get_business_highlights` | Optional reporting fields | Existing receivables/incentive information; reporting filters do not redefine assessment dates |
| `get_financing_status` | Required `application_reference` (`APP-…`) | Authorized submitted application reference, submission status/as-of |
| `get_financing_details` | Same | Requested amount; unsupported approved amount, repayment terms, decision and decision date null |
| `run_survival_simulation` | Required sales change −80…50%, expense change −30…80%, five-point steps; months 1/3/6 | Existing engine results, explicit assumptions/baseline period/limitations; separate server-side user-request gate |
| `search_public_financial_information` | `topic: "sme_lending_rates"` only | Proposes approval; never executes a search itself |

Executable input/output schemas are maintained in `governed_tools.py`; output field names remain those of the supplied policy. `source_timestamp` is retrieval time, not proof of up-to-date bookkeeping. Cash-flow currency and reporting dates remain explicit. Net sales/counts match existing dashboard services; revenue is not relabeled as profit or cash. No FX conversion is performed.

## Conversation and provider behavior

The current [claim-aware verifier and purchase conversation reference](ai-affordability.md) supersedes the earlier blanket digit rejection. It documents the exact source contract, historical-date binding, failure categories and remaining affordability limitations.

The existing drawer now uses `/api/partner/v2/conversations`, `/api/chat`, `/api/partner/v2/close`, `/api/partner/v2/research` and the read-only `/api/partner/v2/tools` descriptor endpoint. POSTs preserve existing CSRF/Origin/session checks. No client role, alternate tool registry or financial-action approval token is accepted. The old conversation GET returns no restored transcript.

Conversations are opaque, session/user/merchant-bound references in server memory, capped at 512 contexts, 30 messages and 30-minute idle timeout. There is one active conversation per login session: creating a new page/merchant conversation invalidates the previous one, including another tab using that login. Close/reopen and in-page navigation retain history. Refresh, page exit, logout, expiry, merchant change, New Conversation or detected permission changes invalidate access. Page exit requests are best effort; a new page invalidates the old context and abandoned memory expires. Permissions are rechecked on every turn/tool call. There is no transcript endpoint, SQLite/JSONL transcript persistence, localStorage or sessionStorage transcript. Audit events retain policy version, action outcome and hashed opaque approval references, not prompts/results/secrets. Existing non-chat business audit behavior is preserved.

`COPILOT_GOVERNED_LIVE=no` is the default, even when Gemini keys exist. Deterministic mode can retrieve permitted backend figures, explain actual application workflows, ask limited expansion/simulation follow-ups and enforce research consent. It is labeled as deterministic, not live AI. It is a bounded fallback, not equivalent to general LLM reasoning.

With explicit live opt-in and configured existing LLM variables, OpenAI-compatible calls use exactly the same gateway. Numerical statements now use typed source references: user assumptions/dates, authorized backend facts and existing deterministic/simulation outputs remain distinct. Optional values and metadata are checked against current authorized sources and backend-rendered with their metric/period labels. Untyped numerical prose receives at most one format correction; unknown/mismatched sources and unsupported conclusions fail safely. See the claim-aware reference for external provenance limits. This conservative approach does not formally prove every qualitative statement; further live reasoning/red-team evaluation remains necessary. No claim of successful Gemini connectivity is made by mocked tests.

The warehouse conversation first checks expansion authority, clarifies funding/costs and repayment assumptions, and discloses missing verified cash/property financing support. It does not calculate property affordability. Later material guidance uses verified position/decision/assumptions/base/downside/risks/conditional recommendation/next step headings; unsupported base/downside models are explicitly unavailable. Only an explicitly requested, sufficiently specified operating-result simulation can run. Its existing optional provider narration is bypassed on the governed path so an unfiltered baseline cannot leave through a secondary LLM call; arithmetic is unchanged.

## Public research

Optional adapter: Tavily's documented [Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search), fixed HTTPS endpoint with no redirects. Configure `COPILOT_RESEARCH_PROVIDER=tavily` and local secret `COPILOT_RESEARCH_API_KEY` to enable proposals. No provider is configured by default. Do not commit keys. Review provider retention/training arrangements before use; sensitive live tests are not authorized by this implementation and should remain synthetic.

The query is constructed from a fixed public topic/year, never merchant records or arbitrary user text. UI displays purpose, exact query, public-information notice, expiry and Approve/Decline. Approval is single-use, at most 120 seconds, and bound to user/session/merchant/tool/query digest. Consumption occurs before the request, including failure. Query substitution, replay, expiry, a different conversation or logout is denied. Each additional search needs fresh approval. Only actual returned HTTPS public-source URLs, titles, publication dates when provided, retrieval time and excerpts appear. No fabricated dates/citations. Excerpts are escaped, labeled untrusted and never fed back into tool/model execution. Citation URLs are not fetched by the application.

The adapter contract and approval controls are implemented; a live Tavily request has **not** been verified. Browser research verification used an explicitly synthetic provider adapter.

## MCP compatibility change

Authenticated HTTP and stdio MCP now use the same approved gateway. Old broad tool names (including `ask_copilot` and payment/action tools) are unavailable to authenticated MCP clients. Clients must migrate; this is an intentional local security restriction, not an invisible compatibility fallback.

1. Authenticate through the existing login/session mechanism.
2. Send JSON-RPC `conversation/start` with `params: {"merchant":"M002"}`; the server authorizes the selection.
3. Use returned `conversation` in `params._meta.conversation` for `tools/list` and `tools/call`.
4. Call an allowed name with strict `arguments` and no merchant identity inside arguments. Discovery lists only permitted functions. Starting a conversation is lifecycle management, not a financial tool.

MCP research only proposes approval; the human approval endpoint/UI executes separately. Simulation calls without a conversational user-request marker are denied. Native dashboard maturity/notification UI now uses `/api/assessment` and `/api/business-alerts`, which call the same existing authorized services, so native UI does not require broad AI tools. There is no new assessment/alert calculation.

## Local run and focused checks

From the application directory, using the existing initialized CNY demo:

```powershell
python -m pip install -r requirements.txt
$env:COPILOT_GOVERNED_LIVE="no"
python -m copilot.server --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/login`; use your existing assigned `demo_owner`, `demo_staff`, `demo_bank` or `demo_admin` account and its privately supplied seed/reset password. No universal password is embedded here. Do not reseed an initialized directory. For a fresh clone follow [local setup](../operations/local-setup.md).

```powershell
$env:COPILOT_LOAD_LLM_ENV="no"
python -B -m unittest tests.test_ai_governance -v
```

New tests use disposable CNY identities, ledger state and provider doubles. Existing focused reliability/configuration/PolicyGuard tests are run separately with their offline legacy fixtures; this does not reactivate legacy data in the application.

Manual checks: Owner asks for sales, then warehouse funding/repayment assumptions; asks for a supported sales/expense scenario; closes/reopens drawer; navigates tabs; refreshes; switches merchant; starts New Conversation; logs out. Staff asks “How much financing has our company applied for?” and variations; no restricted tool executes. Bank financing retrieval is blocked by the missing granular permissions even with consent. Admin cannot create a merchant assistant context. Public research without a provider reports unavailable; with an approved provider, each exact query needs separate approval.

## Verification and remaining work

See the final local report for executed counts. No full regression suite, live Gemini/Tavily request, production deployment, privacy certification or exhaustive prompt-injection evaluation is implied. Existing legacy MCP client expectations need migration to the narrowed registry; no legacy write tools are silently restored. Missing granular Staff/Bank permissions and Admin D0 access require a separate reviewed authorization decision. Optional simulation flag remains controlled by existing configuration. Property financing, verified cash, complete liabilities, approved terms and new financial execution are not implemented.

[Technical index](README.md) · [Existing security model](security-permissions.md) · [User instructions](../user-guide/ai-financial-partner.md)


## Executed local evidence — 16 October 2026

- New focused governance suite: **50 passed**. Covers policy failure/default deny, all role boundaries, Staff financing variants, field minimization before a model double, approval references excluded from model context, merchant/session/user isolation, permission revalidation after retrieval, actual role/grant changes, expiry/logout/new context, deterministic simulation and single-use user assumptions, public query approval/replay/expiry/failure, citation safety, backend financial binding and sanitized audits.
- Existing reliability, LLM configuration, PolicyGuard and guardrail selection: **27 passed**.
- Existing MCP protocol/HTTP security and financial-partner acceptance selection: **57 run, 55 passed, 2 failed**. `test_T01_empty_records_zero_revenue` expects the old currency-free string; actual text includes `IDR 0.00`. `test_T15_wrong_repayment_total_rejected` expects unformatted digits; actual text includes formatted `IDR 11,300,000.00`. Both failures were reproduced in an untouched temporary HEAD archive at baseline `60cb1224ab099e52cbab9268ea210705bf73cf73`. Tests/calculations were not weakened or rewritten to hide these failures. Offline IDR fixtures are test compatibility data, not active demo records.
- Browser: **20 passed checks**, Edge at desktop and mobile widths, with actual isolated CNY server/authentication and a clearly labeled synthetic research adapter. Includes header/drawer, message send, module navigation, close/reopen, New, refresh, merchant clearing, research approval/citation escaping, no execution, mobile composer, multiline input, logout and no JavaScript errors.
- Focused HTTP: Owner read succeeds; Bank financial tool denied; System Admin assistant entry denied; fresh demo Staff entry denied because the reference seed has no Staff Copilot grant. Authorized-Staff financing denial is verified separately in disposable unit fixtures. Identity-field tampering, invalid merchant and post-logout requests are denied.
- Active local CNY dataset file hashes (database, ledger, audit, execution and metadata) remained unchanged across isolated browser/HTTP verification.
- Python AST checks, both modified JavaScript syntax checks and `git diff --check`: passed.
- Live Gemini: **NOT TESTED**. Live Tavily: **NOT TESTED**. Provider failure and tool-calling checks use explicit doubles. Provider retention/training approval remains outstanding before sensitive live use.
- Full regression, full stdio subprocess compatibility migration, cross-browser evaluation and production deployment: **NOT RUN**. No production-readiness claim.

### Changed project files

- `.env.example`, `requirements.txt`, `README.md`
- `copilot/governance_policy.py`, `copilot/governed_tools.py`, `copilot/governed_research.py`, `copilot/governed_partner.py`
- `copilot/auth.py` (bounded audit metadata only), `copilot/llm_config.py`, `copilot/mcp_server.py`, `copilot/server.py`, `copilot/survival_simulation.py` (optional narration switch only)
- `web/index.html`, `web/financial-partner.js`, `web/dashboard-tabs.js`
- `tests/test_ai_governance.py`
- `docs/technical/ai-governance.md`, `docs/technical/README.md`, `docs/technical/mcp.md`, `docs/user-guide/ai-financial-partner.md`

The supplied policy/schema, `.env`, Railway lifecycle/configuration and financial source records were not modified. All changes remain uncommitted on the feature branch. No push, merge, PR or deployment occurred.


### Follow-up: bounded live response timing

Gemini HTTP requests and model workers now allow 30 seconds. The complete chat processing budget is 60 seconds, including tool rounds and fallback retrieval; it is not an unlimited wait. Financial tools retain their policy-defined 10-second maximum and may receive less when the turn budget is nearly exhausted. The drawer shows “Still analyzing…” after 10 seconds, retains failed/fallback questions in the composer, and offers a Retry question control that prepares the question without automatically resending. Timeout, response-validation rejection and other provider failures have distinct safe UI labels. Restart the local server to activate the change.

Timing follow-up verification: 53 focused governance tests passed; 24 isolated browser checks passed, including delayed loading, preserved question, nonautomatic retry and accurate timeout labeling. Focused role HTTP checks passed. Active CNY file hashes remained unchanged. Python/JavaScript syntax and git diff --check passed. No live-provider success is claimed by these synthetic checks.


Current incremental behavior and acceptance status: [AI stabilization](ai-stabilization.md). This includes the governed cash-impact tool, expanded forecast evidence and current live-provider blocker.
