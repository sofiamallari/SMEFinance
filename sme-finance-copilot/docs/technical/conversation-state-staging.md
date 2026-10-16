# General conversational context: historical staged integration review

> Superseded on 2026-10-16 by the user-approved direct integration. See [current integration and verification](generalized-conversation-integration.md). The inactive-flow statements below describe the earlier checkpoint, not current behavior.

## Historical status
Integrated locally through an explicit **Partner.review_reply** method only. NOT ACTIVATED.
The public Partner.reply, server routes and UI still use the existing flow. No environment
flag or HTTP route enables the new path. Do not activate without a separate reviewed change.
Branch: feature/ai-governance-chatbot-v2. HEAD: 60cb1224ab099e52cbab9268ea210705bf73cf73.
No commit, push, merge, deployment, production-data modification or provider-setting change.

The earlier automatic review rejection concerned an all-at-once active-flow replacement.
The user subsequently approved incremental integration with activation prohibited. This
implementation follows that approval; the rejected replacement was never applied.

## Design and actual defect fixes
The old flow lacked a typed pending question and used purchase-specific extraction/rendering.
The review path uses the same authenticated session row, merchant binding, fingerprint, idle
expiry, logout/reset behavior and lock, plus a general entity catalog and pending/resolved state.
It does not import purchase_context, assumptions or render_purchase and contains no product,
price or financial-scenario response sequence.

1. Interpretation: Gemini selects server-generated source-span IDs and an entity, never a
   rewritten quote or a model-computed financial value. The per-turn schema permits only
   entity/source combinations that the backend type and literal-source validators accept.
2. Commit validated user inputs: the backend parses money, percentages, durations, dates and
   choices, preserves user-assumption provenance, records corrections and partitions topics.
   A short answer stays bound to its pending entity even after that question is cleared.
   Corrections cannot overwrite unrelated values; explicit growth can replace a prior decline.
3. Tools: an intent-to-service registry selects existing read-only gateway operations. All
   existing role, merchant, consent, field filtering, calculation and simulation restrictions
   remain in Gateway. Model output cannot choose another merchant or arbitrary tool/argument.
4. Narration: Gemini receives only the validated current context and newly authorized results.
   Its schema enumerates the claim IDs that actually exist after interpretation and retrieval.
   This removes the earlier orchestration defect in which a model narrated before valid IDs
   existed or retyped financial figures as prose.
5. Verification: the existing verify_response still checks every displayed financial claim.
   A separately validated question is appended once. Additional review-only guards reject
   false claims of writing records and untyped month-name period statements. No exception
   was added to weaken the existing verifier or allow unsupported financial conclusions.
6. Fallback: consumes the same committed state; it never discards a valid answer or restarts
   an already resolved question. Unknown/ambiguous information is not invented.

Each turn uses at most one interpretation request and one narration request. No automatic
provider retries. Existing 30-second request/60-second turn budgets and resource limits remain.
Only the review method uses the new optional response_schema parameter on model_request;
existing adapter calls retain their previous behavior.

## Files changed for this integration
- copilot/governed_partner.py: attach typed state; optional adapter schema; explicit review method.
- copilot/conversation_state.py: typed-answer binding and percentage-direction correction.
- copilot/conversation_review.py: new inactive two-stage integration.
- tests/test_conversation_state.py: additional targeted state regressions.
- tests/test_conversation_integration.py: lifecycle, source contracts, authorization and fallback tests.
- docs/technical/conversation-state-staging.md: this report.

Three temporary synthetic test harnesses were retained under the original workspace:
C:/Users/User/source/repos/sme-finance-copilot-v1.2-transactions/.journey-work/
verify_staged_conversations.py, verify_staged_final.py, verify_staged_short_final.py.
These are local test runners, not application code, deployment files or persistent datasets.

## Real Gemini evidence
Model: gemini-3.1-flash-lite, unchanged endpoint/key. Tests called Partner.review_reply with
disposable authenticated identities and synthetic merchant M002. The actual provider and
unchanged Gateway/verifier executed; instrumentation wrapped real calls and did not mock
responses. No persistent demo merchant records were used or changed.

Latest eight-turn run: all sixteen provider calls returned HTTP 200. Seven displayed replies
passed independent verification and used the live review path. One safely used fallback.
Whole turns took 3.33-3.80 seconds; individual provider calls took 1.11-1.67 seconds.

| Journey | Latest actual evidence |
| --- | --- |
| Equipment | Four verified live turns: CNY 18000 cost, cash funding, bare CNY 35000 answer to pending cash question, correction to CNY 21000. Cost and cash stayed independent. |
| Employee hiring | CNY 3800 recurring expense retained. Initial narration rejected as unsupported_business_fact; pending cash question survived. CNY 28000 cash follow-up verified live and remained user-reported. Earlier runs also verified both hiring turns. |
| Sales analysis | Both turns verified live. Last month resolved to September 1-30, 2026; correction to this month resolved to October 1-16. Actual service returned CNY 168494.62 and zero respectively; no invented activity. |

The latest hiring rejection was the numeric-free sentence: "Reviewing this recurring commitment
requires comparing it against your actual cash position." The existing conservative verifier
classifies this wording as an unsupported business fact. This was NOT accepted automatically.
The fallback retained the salary assumption and the pending question. Initial experiments also
rejected prose containing "guaranteed" in a negative sentence, false record-update claims, and
an unsupported free-text month reference. Prompt and review-only guards were tightened; the
financial verifier was not relaxed. No claim is made that all natural wording now succeeds.

## Focused verification
Stage 1: 73 state/lifecycle/governance checks passed; git diff --check passed.
Stage 2: 80 state/lifecycle/adapter/governance checks passed; git diff --check passed.
Stage 3: 133 combined focused checks passed before final targeted additions. Later state,
review-path, topic-change, date-provenance and typed-correction additions were checked again.
Final combined focused run: 137 tests passed. After the last finance-only/research-retention guard, the final 34 state/integration checks passed. These are overlapping runs, not 171 distinct tests.

Tests cover valid claims, fabricated balances, source-ID schemas, short typed answers, correction,
role denial (Owner/Staff/Bank/Admin), finance-only scope, reset, merchant-context invalidation,
topic separation, safe provider/verification fallback, no false record-write claims and no
application access without existing permissions. Automated providers are doubles; the real
journeys above are separate live integration evidence. Python syntax and diff checks were run.
No full regression or browser activation test was run; there is intentionally no browser route.

## Remaining limitations / activation review
- Do not activate yet. Conservative qualitative false positives still intermittently cause
  safe fallback, particularly procedural wording about a user's cash position.
- Natural prose may remain verbose or fragmentary around typed claims; no fixed purchase
  renderer masks this behavior in the review path.
- The typed entity vocabulary and deterministic value parsers are deliberately bounded.
  Unsupported language or ambiguous amounts require clarification rather than guesswork.
- No independently verified current cash balance or approved affordability formula has been
  added. Neither a user-reported balance nor historical sales establishes affordability.
- The existing opaque-value sanitizer may redact long application references. Successful
  financing-reference UX needs review; Bank/Staff restrictions remain enforced.
- Two provider requests per turn introduce provider availability/latency risk, bounded by
  unchanged budgets. Browser/UI integration and activation require a separately reviewed step.
- The existing public conversation remains purchase-specific until activation is approved;
  this staged work does not silently replace its behavior.
