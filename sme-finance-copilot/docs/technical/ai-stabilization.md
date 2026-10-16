# AI Financial Partner stabilization

Local branch: `feature/ai-governance-chatbot-v2`. Baseline: `3f6580c83a968521ca5999fb0805df2f69f34be1`.

This is an incremental change to the existing `/api/chat` → `Partner.reply` → `Conversation.reply` path. There is no second engine, activation flag, new financial write API, or provider configuration change. No commit, push, merge or deployment is included.

## Behavior and root causes

| Original issue | Change | Verification |
|---|---|---|
| Capability questions entered financial analysis | Deterministic overview derived from currently authorized gateway definitions | Owner and Staff filtering tests |
| One-tool intent map limited analysis | Model-proposed tool list uses a per-user schema, strict tool names, intent relevance and validated arguments; at most three executions | Two-tool September/August pipeline and bounded execution tests |
| Comparative totals lacked deterministic changes | Decimal difference, percentage when denominator is nonzero, transaction-count difference, source references and explicit period lengths | Backend equality and zero-denominator tests |
| Best month unavailable despite trends | Backend maximum over returned authorized trend buckets, retaining all ties | Tie handling test; live interpretation blocked |
| Short replies/corrections/scenarios mixed | Existing typed pending answers retained; independent cost types partition assumptions; explicit combination restores cost assumptions; return-to-topic restores prior user context | Purchase → cash → correction → independent hiring integration test |
| Source follow-ups lost prior evidence | Reauthorize and explain previous answer's source records without representing them as a fresh retrieval | Source follow-up test |
| Cash Flow omitted forecast metrics | Governed output contract exposes synthetic opening, projected closing/minimum, runway, expense-coverage estimate and limitations | Policy/field contract tests |
| Numeric-only verifier missed qualitative cash verdicts | Reject untyped remaining-cash conclusions and unsupported missing-data assertions; narrow capability-explanation exception | Positive and negative verifier tests |
| Narration required uncertainty in every financial sentence | Replace blanket wording with typed calculation evidence requirements | Existing claim-contract regressions |

Option A was selected: do not advertise general expense analysis or a general risk-alert capability. Existing incentive/receivables highlights are described precisely. Merely having a module in the UI does not make it an AI tool.

## Financial architecture and tool coverage

User question → existing Gemini structured interpretation → literal-source typed context validation → currently authorized tool proposals → backend period/scenario binding → gateway authorization and schema validation → existing domain calculations → filtered tool results → server-owned typed facts/derived records → Gemini selects narration/claim references → independent verification → existing UI live/fallback metadata.

| Tool | Supported evidence |
|---|---|
| `get_financial_summary` | Recorded sales/counts, requested period, actual record-date coverage |
| `get_transaction_trends` | Existing reporting buckets; backend highest-period selection with ties |
| `get_payment_channel_mix` | Transaction-volume shares, not revenue shares |
| `get_cash_flow` | Existing forecast and explicit limitations |
| `get_business_highlights` | Existing receivables/incentive summaries; not a new alert engine |
| `get_financing_status`, `get_financing_details` | Specific authorized application; no new underwriting or approval capability |
| `run_survival_simulation` | Existing requested operating-result scenario, with its existing supported inputs |
| `run_cash_impact_scenario` | New governed D2, non-mutating incremental cost schedule |
| Public research | Existing exact-query approval path; never unrestricted model HTTP/search |

All calls retain merchant scoping, application authorization, governance field filtering and auditing. The shared turn deadline remains 60 seconds, including verification. There are no automatic provider retries.

## Dates and data reliability

- Current business date still comes from the backend clock in the merchant's configured timezone.
- Requested reporting periods are user assumptions; effective retrieved periods are recorded separately in conversation state.
- Month names, quarters, last quarter and rolling periods resolve on the backend. Previous comparable period preserves day count. Calendar-month comparisons disclose differing day counts and are not day-normalized.
- General sales default to the latest complete calendar month relative to available financial records and the business date. This does not promise complete source coverage; returned first/last record dates are disclosed separately.
- The synthetic opening wallet is reconstructed from `demo_environment.merchants` and referenced to `Copilot.as_of`. It is not reconciled by imported transactions. The latest transaction date is separate.

## Scenario calculation contract

`run_cash_impact_scenario` is a D2 read-only tool. Its schema bounds amounts to nonnegative finite cent values up to one billion CNY and its horizon to 1–180 days. The conversational default currently binds a 90-day horizon. A recurring cost needs an explicit start date. A cash-funded one-time purchase needs a resolved cash payment assumption; financing-funded acquisition amortization remains unsupported.

The small backward-compatible `cashflow.forecast(..., extra_outflows=None)` extension adds only explicit incremental outflows within the horizon. Same-day costs appear as a day-zero path entry; subsequent costs enter on their dates. Monthly charges recur on the start-date day, clamped to the last day of shorter months. Existing callers without hypothetical costs retain their behavior. Baseline and adjusted paths use identical scheduled obligations, so those obligations are not subtracted again.

The projection, minimum, closing balance and first negative-balance day are recalculated by the existing forecast. Expense-coverage buffer retains its original variable-expense/averaged-debt meaning, adding the hypothetical cost's horizon average for adjusted scenarios. It is not an independently measured liquidity buffer and does not itself include every scheduled bill.

User-reported cash produces separate baseline/adjusted projections on a deep copy. It never replaces stored cash or the synthetic-opening projection. Tests compare the merchant projection and ledger before/after execution.

Material limitations are included in scenario evidence:

- Synthetic demo opening balance, not live spendable cash or bank evidence.
- Imports do not reconcile that opening balance.
- Variable-outflow history includes only `supplies`, `operating`, `household_draw`; imported/recorded `other` expenses are excluded.
- No distinct existing payroll category; proposed salary is incremental and existing payroll coverage is incomplete.
- Known payables/debt are already in the baseline. Users must not enter existing obligations as new incremental costs.
- Positive projections do not establish affordability or guarantee future performance.
- Digital Payments Simulator activity remains excluded from financial balances/reports.

## Governance change

Policy version is `0.6.0`, schema `1.0.0`. The existing schema already supports named capability/tool objects; no structural schema relaxation was necessary. New fields are registered consistently in `FIELD_CLASSES`, `OUTPUTS`, policy allowlists and server-rendered claim records. Unknown fields remain filtered. Staff's new capability is conditional on an explicit granular permission; Bank and System Admin are denied. This policy does not grant application permissions.

## Test evidence

Before edits: full suite **522 tests: 443 passed, 29 failed, 49 errors, 1 skipped** (546.23 seconds). Focused AI baseline: **148 passed**.

Focused after integration: **171 passed** (148 existing + 23 new). Final full suite: **545 tests: 466 passed, 29 failures, 49 errors, 1 skipped**, in 626.44 seconds. New failing test names versus baseline: **0**. Previously failing tests now passing: **0**.

Pre-existing full-suite categories include POS/report-profile/CNY expectations, simulator expectations, migration/MCP/legacy partner behavior, and conflicting storage environment variables. Expectations were not changed to hide those failures. Only two existing policy-version assertions were updated to reflect the explicit version bump.

Real-provider attempts: `gemini-3.1-flash-lite`, official OpenAI-compatible Google endpoint. Key presence was confirmed without disclosure. Sales, period comparison, best month and equipment/hiring turns reached HTTP **401**; no interpretation or verified live answer was returned. The credential update was retested and still returned HTTP 401. Real multi-turn acceptance is **BLOCKED**, not passed. Deterministic capabilities, safe fallback and provider-double financial tests are separate evidence.

No browser verification is claimed for this backend-focused change. Existing UI metadata still distinguishes verified `live`, `test_double`, deterministic capability guidance and provider fallback. No frontend files were modified.

## Suggested demo questions after authentication is fixed and live acceptance passes

1. “What can you help me with as a business owner?”
2. “Compare September with August.”
3. “What was my best-performing month?”
4. “Can I buy equipment for CNY 15000 today?” → “cash” → “Actually it costs CNY 18000.”
5. “Can I hire someone for CNY 6000 monthly starting next month?” → “I have CNY 40000 available in cash.”

These are validation prompts, not claims of current live demo readiness. Real Gemini interpretation, combined-topic behavior and narration of the expanded schema require successful live acceptance. Historical successful provider evidence in other documents does not verify this revision.


## Files in this change

| File | Purpose |
|---|---|
| `copilot/conversation_review.py` | Existing orchestration, authorized planning schema, capability/source replies, shared deadline |
| `copilot/conversation_state.py` | Typed period/date resolution and prior-topic assumption restoration |
| `copilot/conversation_evidence.py` | Bounded relevant tool requests, period binding, independent scenario assumptions |
| `copilot/governed_tools.py` | New read-only scenario adapter and expanded filtered evidence contracts |
| `copilot/governance_policy.py`, `config/ai_governance_policy.json` | Explicit capability, classifications, allowlists and version bump |
| `copilot/modules/cashflow.py` | Optional non-mutating outflow schedule; existing callers preserved |
| `copilot/cash_impact.py` | Bounded incremental cost schedules and separate user-cash projections |
| `copilot/governed_claims.py` | Backend-derived comparisons/best periods/scenario claims and verifier checks |
| `tests/test_ai_stabilization.py` | 23 synthetic regression tests |
| `tests/test_ai_governance.py` | Policy-version assertions updated |
| `docs/technical/ai-governance.md`, this document | Current contracts, limitations and evidence |

No UI, POS, transaction-settings, Bank User, financing-approval or persistent dataset files were changed by this task.


Final machine-recorded comparison (counts only; no credentials or financial records):

```json
{
  "baseline": {
    "tests": 522,
    "passed": 443,
    "failures": 29,
    "errors": 49,
    "skipped": 1,
    "seconds": 546.23
  },
  "final": {
    "tests": 545,
    "passed": 466,
    "failures": 29,
    "errors": 49,
    "skipped": 1,
    "seconds": 626.44
  },
  "new_failing_tests": [],
  "previously_failing_now_passing": []
}
```
