# Financial claims and conversational purchase assessment

Local branch: `feature/ai-governance-chatbot-v2`. This extends the approved governance policy/schema without changing either file, financial formulas, permissions, storage or deployment configuration. No `saif` references were found. [Governance reference](ai-governance.md).

## Failure trace and root cause

The prior live adapter rejected every digit in final model prose, including accurate user prices, dates and numbered lists. It also treated every `ValueError`/`AccessDenied` as one verification failure. Consequently a valid hypothetical oven price could trigger the same fallback as an invented business cash balance. Fallback selected a generic warehouse question, retrieved an unrelated default-period summary and displayed its Python period dictionary. Retry controls offered the same invalid response path again.

The historical model response was intentionally not retained. Therefore **the exact original model reply, tool-call sequence and triggering exception cannot be reconstructed from the screenshot**. The blanket-number gate is confirmed in source and reproduced with a controlled numeric response; this is not proof that it was the sole trigger in that historical request. The previous timeout and a verification rejection are different conditions.

Current lifecycle for the oven example:

1. Existing authenticated session, `use_copilot`, selected merchant, policy and role checks execute first. Affordability requires `expansion_assessment` and existing report access. Staff cannot obtain restricted financial data by framing the request as a purchase.
2. Parse the user-stated oven, RMB 10,000 price and October 15, 2026 assessment date. The supplied date takes precedence over the word “today”; it is a requested historical date, not evidence of a cash-account snapshot.
3. Retrieve only an authorized summary with the existing 90-day reporting convention ending on that date. For this example the period is July 18–October 15, 2026. Model-supplied reporting dates cannot replace the requested period. This is a reporting window, not a new affordability formula.
4. Build a per-turn catalog from user assumptions and already minimized authorized tool results. Only relevant tools are exposed for purchase discussion; unrelated financing records and current cash-flow forecasts are not fetched as historical liquidity evidence.
5. The configured existing OpenAI-compatible provider receives the question, bounded conversation history, permitted tools and typed claim records. Limits remain 30 seconds per model request, 60 seconds per chat turn and 10 seconds per financial tool.
6. Validate the model's source references, kind, metric, value, currency and reporting period. Render numerical statements using server-owned labels and formatting. This does not reject a response merely because it contains numbers.
7. Add the authoritative limitation and one material missing-assumption question. Do not declare affordability from net sales.
8. If necessary, allow **one** format-only correction within the existing tool-round/time budget. A second invalid candidate fails safely; no repeated automatic provider retries or automatic research are introduced.

## Claim contract

Final model output is a `segments` object. A segment is either connective explanation/clarification text or a reference to a typed source record. Example:

```json
{
  "segments": [
    {"claim":"user.purchase_price","kind":"user_assumption","value":"10000.00"},
    {"claim":"user.assessment_date","kind":"user_date","value":"2026-10-15"},
    {"claim":"fact0.net_sales","kind":"backend_fact"},
    {"text":"Cash availability and upcoming commitments need verification."}
  ]
}
```

The browser receives conversational text, **not this internal JSON**. IDs select a current, server-owned record; they do not authorize retrieval or let the model specify a merchant. Optional echoed metadata must match its source. Equivalent numeric formatting normalizes within that typed record only. Repeating a user price never establishes cash, an expense or a verified business fact. Numbered explanatory lists are allowed.

| Classification | Source / acceptance |
|---|---|
| User assumption | Explicit parsed purchase price, additional costs, down payment or reported cash; rendered as unverified, never promoted to business truth |
| User date | Explicit valid ISO or English month/day/year; rendered naturally as the requested assessment date, not a historical cash snapshot |
| Backend fact | Current-turn minimized authorized tool output, with original metric, currency, application scope and reporting period |
| Deterministic result | Existing engine-calculated baseline/forecast/channel-share result; preserves estimated/calculated meaning |
| Simulation output | Actual approved Survival Simulation result only; explicit request, complete assumptions, existing limits and engine remain required |
| External source-backed fact | Requires a server-owned record with approved-search provenance, actual source URL and retrieval time; unsupported rate extraction is not invented |
| Unsupported claim | Unknown source ID, wrong kind/value/metric/currency/period, invented cash or simulation result, unsourced factual numbers, or unsupported positive affordability/approval verdict: reject |

Free numerical assertions in connective text must be reformatted to reference a source; this is a provenance requirement, not a blanket ban on numerical answers. Model-provided numerical equality alone is insufficient. The backend controls the displayed label so a net-sales record cannot be presented as available cash. Cautionary statements such as “I cannot determine your available cash” remain valid. Text guards are conservative; they are not a mathematical proof of every possible qualitative statement, and further live/red-team evaluation remains necessary.

Public research still requires separate exact-query, expiring, single-use approval. Its current adapter returns untrusted public excerpts and citations, not independently verified lending rates. No arbitrary external numerical fact becomes trusted merely because a model supplies a URL. Search approval references are still excluded from model context. The new catalog does not add an external rate extractor or change the existing consent mechanism.

## Purchase conversation state

Recognized items include ovens/equipment, inventory, machinery, vehicles, shops/branches, warehouse/property and general investments/affordability. Price, date, funding, stated costs, down payment and repayment term remain merchant/session-scoped assumptions. Cash follow-ups do not overwrite the oven price; USD/PHP assumptions are not relabeled CNY or converted. Delivery/installation assumptions and down payment are not automatically summed or classified as recorded expenses.

The assistant asks the next missing material question instead of every question:

- Funding unknown: cash or financing?
- Financed and term missing: repayment period, with the amortization limitation.
- Price unknown: purchase price/currency?
- Other costs unknown: delivery, installation and other costs included?
- Costs/funding provided but verified liquidity absent: clarify verified cash source and commitments. A user-reported balance remains an assumption, not a verified account.

No purchase is recorded. No loan is submitted. No consent is changed. No affordability verdict or automatic reserve threshold is invented. The existing operating-result simulator still does not model equipment depreciation, one-time capital purchase cash movements, loan amortization, complete liabilities or verified bank cash. Historical as-of purchase simulations are unavailable rather than silently using a later/current baseline. Current supported simulations remain usable through the existing approved path.

## Safe example

**User:** “If I were to buy an oven worth RMB 10,000, can I afford it as of today, October 15, 2026?”

**Assistant:** “Your proposed oven price is ¥10,000.00 CNY (RMB), a user assumption. Your requested assessment date is October 15, 2026. I can review recorded results for that period, but recorded sales do not establish available cash. Will you pay in cash or use financing?”

**User:** “I will pay in cash; the price includes installation.”

**Assistant:** “The proposed price and cash funding are noted. I cannot yet establish affordability because verified available cash and full upcoming commitments are unavailable. Can you provide a verified cash position and obligations due before your next expected receipts?”

Actual authorized recorded figures may also appear with their source period. No example financial amount beyond the user's proposed price is invented here.

## Diagnostics and verification

Safe failure categories are separate: `timeout`, `provider_error`, `model_error`, `authorization`, `response_validation`. Existing audit records store the category, short diagnostic code and policy version, never raw model text, full prompts, tool payloads, keys or tokens. Verification rejection does not imply Gemini is disconnected. UI advice does not expose diagnostic internals. Only provider/timeout failures offer the ordinary retry control; invalid financial claims are not repeatedly resubmitted automatically.

Run focused tests from the application directory:

```powershell
$env:COPILOT_LOAD_LLM_ENV="no"
python -B -m unittest tests.test_affordability_claims tests.test_ai_governance -v
git diff --check
```

These use disposable CNY identities, records and explicit provider doubles. The existing timing test fixture now returns a valid summary envelope instead of an empty mocked result; its time-budget assertions are unchanged.

Live status: the isolated live harness reported configuration unavailable before making an API request. **No live Gemini response was obtained for this change.** Normal application configuration was not edited, and this harness result is not a diagnosis that the running application's key is invalid. Typed response routing, format repair, provider failures and numerical checks were exercised with doubles. No production data or credentials were used or exposed. Full regression/deployment was not performed.

Changed files for this follow-up: `copilot/governed_claims.py`, `copilot/governed_partner.py`, `tests/test_affordability_claims.py`, `tests/test_ai_governance.py` (valid timing fixture), this reference and its link/update in `ai-governance.md`. All preceding uncommitted work is preserved. No commit, push, merge or deployment.

Final local results: 79 focused claim/affordability and governance tests passed; 27 existing focused reliability/configuration/security checks passed; 24 isolated browser checks and focused role HTTP checks passed. Browser fixture file hashes confirmed the active CNY database, ledger, audit, execution and metadata remained unchanged. Python syntax and git diff --check passed; supplied governance JSON/schema unchanged. Live Gemini was not exercised successfully: the isolated live harness stopped at configuration availability without an API response. Full regression and deployment were not run.


## Live response contract verification - 2026-10-16

The adapter keeps gemini-3.1-flash-lite, the existing endpoint, 30-second request timeout,
and 60-second turn budget. Governed chat requests now supply a strict JSON response schema:
segments contain either a numeric-free explanatory text or a claim ID and provenance kind.
Claim IDs are restricted to supplied records; the backend independently checks those records
and owns the rendered values, labels, currency and reporting periods. Minimal connection
probes remain plain text. No network retries were added; the existing one-time format
correction remains bounded.

Public kinds are user_assumption, backend_fact, derived_calculation, simulation_result,
external_fact and unsupported_claim. Existing internal user_date, deterministic_result and
simulation_output kinds map to the corresponding public kinds without changing their source.
A self-declared kind never establishes provenance. Unsupported IDs and unsupported_claim
are rejected. Derived/simulation statements can only select existing authorized domain-service
outputs; this change adds no purchase formula or model arithmetic. External facts still require
approved research provenance and cannot be invented by this schema.

Observed pre-fix rejections included purchase price and sales in plain text, reporting dates,
transaction counts, an unsupported approximate two-percent sales ratio, and invalid JSON
fields (explanation and clarification_question). Schema enforcement fixes format compatibility,
not financial authority. Exact generic assessment guidance and the existing negative-model
availability disclaimer are allowed; positive affordability conclusions remain rejected.

For purchase questions, today is resolved from the backend clock in the merchant's saved
Transaction Settings timezone (or its existing country default). Explicit dates take precedence.
The assessment date is not a cash snapshot. The existing ninety-day summary window remains
separately labeled. A summary is retrieved server-side; its tool is then omitted from the
model's purchase registry, preventing unrelated-period or duplicate model reads. A fallback
may independently reread the same authorized summary.

Real Gemini checks used disposable synthetic Owner/Staff accounts and temporary stores:
- Final initial oven question and cash-payment follow-up: live path, independently verified.
- Earlier detailed runs: HTTP 200 responses around 1.3-2.2 seconds per provider call.
- Explicit reported cash: live, labeled unverified; purchase price remained separate.
- Request to fabricate verified cash: no invented backend cash; instructions cannot replace
  purchase or reported-cash assumptions. A live refusal was independently verified.
- Sales-as-cash request: observed both a verified live refusal and a safe validation fallback
  across runs; no affordability approval or promotion of sales to available cash.
- Staff financing: denied with zero provider calls and zero financial reads.
- Conversation close/reset: old reference rejected; new history empty and no purchase state.
- Final minimal oven replay: both turns live without verification rejection.

The synthetic merchant used Asia/Jakarta and resolved today to 2026-10-16; production
merchant settings were not changed. Its historical summary was separately scoped to
2026-07-19 through 2026-10-16. No production/demo records were changed.

Focused tests: 96 passed (claim attribution, governance, adapter and new contract tests),
plus syntax parsing and git diff --check. Tests use provider doubles except the explicitly
identified live probes above. Browser rendering and full regression were not run.
Remaining limitation: a separate revenue-based-financing education probe received real
HTTP 200 responses but fell back with model_error after tool rounds. Qualitative response
verification remains conservative and may safely reject other unsupported wording.
The UI's existing live/fallback status mapping is unchanged.


## Conversational presentation - 2026-10-16

Technical-sounding purchase wording originated in assumptions()/tool_claims() display
strings, the deterministic purchase fallback, and the live purchase suffix. The drawer
rendered that backend prose directly; it did not originate the financial disclaimers.
Internal typed records and their original diagnostic descriptions remain intact.

Purchase answers now use render_purchase() after the Gemini response passes the existing
independent verifier. This deterministic presentation checks its own assumption references
against conversation state and revalidates the source-linked records for every displayed
amount and financial period. It does not trust model wording or rewrite it with another
unverified model call. The same renderer supports honest deterministic fallback; a fallback
is still labeled as fallback and is never promoted to live.

The initial answer acknowledges the purchase and can show the authorized net-sales value
and its period, explaining that sales alone do not establish available cash. Transaction
counts are omitted. Follow-ups retain price/funding/cost context without repeating sales,
internal claim terminology or disclaimers, and ask one next missing question. Reported cash
is phrased as something the user told the assistant and is explicitly unconfirmed. Included
costs are described generically because the existing context marker does not independently
record which individual cost components were included.

Provider instructions favor concise complete sentences and material figures. The live
structured JSON schema, source verification, tools, permissions, research consent, audit
controls and session-only retention are unchanged. Tool details remain inspectable in a
collapsed Sources & tools disclosure; the existing live/fallback status remains visible.

Final real Gemini replay: both oven turns returned through governed_live, with no fallback
reason. Initial response displayed the synthetic authorized net sales of CNY 400383.44 for
2026-07-19 through 2026-10-16; these are observed fixture results, never hardcoded defaults.
The cash follow-up asked only how much cash was available for business expenses and did not
interpret the purchase price as cash. An earlier instrumented replay measured provider HTTP
200 responses at 1.44 and 1.38 seconds for the two turns. A reported-cash test also exercised
a safe response_validation fallback; source verification remains conservative.

Checks: 102 focused automated tests passed, including six new final-presentation checks;
Python syntax, JavaScript syntax and git diff --check passed. Provider doubles are used in
the automated suites; the two-turn replay used actual Gemini. Existing security and reset
checks remain in the focused suite. Browser rendering and full regression were not run.
Generic non-purchase domain answers retain the existing source-specific rendering, and the
previously documented financing-education tool-round fallback remains unresolved.
No financial formula, governance policy, provider configuration or persistent data changed.
