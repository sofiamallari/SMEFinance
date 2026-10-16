# Generalized AI Financial Partner: local integration evidence

Date: 2026-10-16. Branch: `feature/ai-governance-chatbot-v2`. HEAD: `60cb1224ab099e52cbab9268ea210705bf73cf73`.

## Scope and status

Direct integration is active locally through the existing authenticated `/api/chat`. There is no new feature flag or alternate chat API. No commit, push, merge, deployment, production configuration change or active demo-data edit was performed. Existing unrelated working-tree changes are preserved. This is a local engineering verification, not a production-readiness certificate.

## Request architecture

Authenticated endpoint and existing entry policy → session/merchant binding and permission fingerprint → structured Gemini interpretation using literal source IDs → independently typed conversation-state updates → backend-selected, authorized read tools → schema-constrained Gemini narration → unchanged independent claim verifier → verified response and trusted backend connection metadata → existing drawer. Each provider call and overall turn retain existing bounded budgets.

## Root causes and corrections

- Active orchestration previously used purchase-specific assumptions and response sequences rather than the prepared typed state. `Partner.reply` now invokes the single `Conversation` engine. `review_reply` is only a compatibility alias. Retired purchase orchestration is no longer executed; reusable claim validation remains.
- Model-invented source IDs and rewritten quotes are prevented by interpretation schemas restricted to actual literal source spans and valid entity/type combinations. Financial narration selects supplied claim IDs; it cannot declare arbitrary provenance.
- Generic subjects and pronouns were accepted as business subjects. Subject validation now excludes generic plan/summary and action/pronoun phrases; arbitrary actual subjects are still source-derived.
- Short payment choices and explicit dates could be blocked while a cash question was pending. They now retain their distinct types without filling the pending money field. Bare monetary replies remain bound to the pending money entity.
- Full cash statements while a cash question was pending were rejected. Explicit available-cash wording is now accepted narrowly, remains an unverified user assumption, and cost/salary/credit wording remains excluded.
- Negative percentage direction could be lost when the model selected only a numeric span. Validation uses nearest literal source direction, separately for each percentage.
- Reporting-period changes could retain stale comparison periods. A new primary period clears the prior comparison unless an explicit replacement is supplied. Relative dates are resolved by backend business date; next month retains month precision.
- Hiring and educational prose collided with existing qualitative-business-claim patterns, including `profit is`. Narration instructions now require uncertainty for business-position statements and impersonal educational definitions. The verifier patterns and trust semantics were not changed. Hiring and education subsequently passed live verification.
- Existing grounded help and consent-only research proposal paths were reattached to the single engine. No external search is executed merely by a question.

## Files changed in this integration

| File | Purpose |
|---|---|
| `copilot/governed_partner.py` | Direct dispatch to one generalized engine; retire old purchase orchestration. |
| `copilot/conversation_review.py` | Active structured orchestration, bounded calls, grounded help, metadata, contextual fallback and safe verification. |
| `copilot/conversation_state.py` | Generic typed entities, pending answers, subjects, relative/comparison periods and corrections. |
| `tests/conversation_support.py` | Structured-provider test double; never a live provider. |
| `tests/test_conversation_state.py` | Generic state and source-validation coverage. |
| `tests/test_conversation_integration.py` | Integration, permissions, help and research consent checks. |
| `tests/test_ai_governance.py` | Migrate obsolete provider-protocol fixtures to the structured contract; retain direct security checks. |
| `tests/test_affordability_claims.py` | Preserve independent verifier tests and migrate old purchase integration fixtures. |
| `tests/test_provider_connectivity.py` | Retain transport checks and update failure-routing fixtures. |
| `docs/technical/conversation-state-staging.md` | Mark prior staging findings as historical. |
| This report and technical index | Current implementation and actual evidence. |

The backend endpoint, UI, financial formulas, authorization services, gateway permissions and independent verifier were not edited for this integration. Existing unrelated changes to those files in the working tree predate this task. Test helpers and screenshots are under the existing external `.journey-work` directory, not application runtime code.

## Test results

- Focused state/integration/governance/provider/verifier/presentation suite: **148 passed**, 51.335 seconds on final code. Test-double outputs use `test_double`, never `live`.
- Real API acceptance run: **21 verified live replies**, one intentionally injected timeout; next turn recovered. All 42 actual provider calls in that acceptance run returned HTTP 200.
- Final subject/date/period correction retest: **13 verified live replies**, 26 actual HTTP 200 provider calls, maximum provider-call duration 1.844 seconds.
- No automatic provider retries were added. The controlled timeout replaces one test-process transport call; it is not evidence of a real Gemini outage.
- Additional existing `tests.test_owner_partner`, `tests.test_authentication`, `tests.test_security_agent`: **75 ran; 3 failures, 7 errors**, 249.390 seconds. This broader regression is NOT passing. Failures are: legacy draft assertion expects IDR but service returns CNY; migration assertion expects migration 008 but current schema ends at 010; legacy PHP formatting expectation differs from current shared formatter. Errors are: six HTTP fixture/server imports conflict with `COPILOT_IDENTITY_DB` under the CNY storage guard, and one consent test sends an unsupported legacy Bank-review outcome. Those production paths and tests were not changed in this integration. These are existing-contract/fixture gaps, not waived checks; a clean full regression is not established.
- Final Python AST syntax checks: 9 changed Python files passed. `git diff --check`: passed.
- No live API success should be confused with full regression completion. The 148 focused tests are passing; the additional suite above remains unresolved.

## Security API evidence

| Check | Actual result |
|---|---|
| unauthorized_merchant | HTTP 403 |
| identity_injection_field | HTTP 400 |
| prompt_injection | HTTP 403 |
| unauthorized_payment | HTTP 403 |
| old_merchant_conversation | HTTP 403 |
| new_context | success; no prior purchase value returned |
| logout | success |
| staff_restricted_financing | HTTP 403 |

Restricted Staff fixture is denied at assistant entry; delegated-tool restrictions and Bank/Admin restrictions are separately covered by automated tests. M001/M002 are synthetic; M999 is unauthorized. Forged identity fields return HTTP 400 before orchestration. Merchant switching invalidates the old conversation reference.

## Browser evidence

Actual existing drawer testing used isolated synthetic Owner sessions. Verified hiring opener, recurring salary and next-month follow-up with the visible `Live provider · authorized backend tools` label. Verified educational live response after contract correction, New Conversation, and merchant-switch conversation clearing. Browser console error query returned no errors. Other detailed multi-turn scenarios below were exercised through the real application API, not all repeated through the browser. Final subject/date backend adjustments were retested by API and automated tests.

Screenshots are in the external test-work directory: `generalized-hiring-browser.png` and `generalized-education-browser.png`. No frontend changes were required.

## Remaining limitations

The direct integration and live-response path are implemented and exercised. The complete definition of done is not claimed: conversational polish and the additional legacy regression failures remain unresolved.

- Gemini sometimes emits awkward fragments around complete typed-claim sentences despite the response instructions. No unverified post-verification rewrite was added. Conversation polish is incomplete.
- Responses may repeat transaction counts and cautionary explanations unnecessarily. They must not be interpreted as a complete affordability assessment.
- No approved one-time-purchase affordability or loan amortization model was added. Financing responses correctly request missing rate/terms rather than invent repayment amounts.
- No real inclusion question arose in the tested live conversations, so `all` was not sent out of context. Typed pending-boolean behavior is covered by automated tests only.
- The existing independent qualitative verifier remains conservative and heuristic. Safe fallback remains possible for valid but unsupported wording; this work does not certify arbitrary financial prose.
- Public research remains limited to existing consent-controlled scope; no general web-research capability was introduced.
- Full regression, cross-browser and production deployment verification were not run.

## Actual final-code correction replies

These are exact final response bodies returned by `/api/chat` using real Gemini, not scripted expected answers.

### 1. equipment — Can my business afford a refrigerator worth CNY 15000?

Elapsed: 3.56s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> Business subject: refrigerator (as you stated).
>
> One-time cost: ¥15,000.00 CNY (RMB).
>
> It is uncertain if the business has sufficient liquidity for this purchase because the current available cash balance is unknown.
>
> What is the current amount of available cash for your business?

### 2. equipment — cash

Elapsed: 3.14s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> The business subject is a
>
> Business subject: refrigerator (as you stated).
>
> with a cost of
>
> One-time cost: ¥15,000.00 CNY (RMB).
>
> The current available cash balance remains uncertain as no verified records are provided.
>
> What is the current amount of available cash for your business?

### 3. equipment — I have CNY 40000 available.

Elapsed: 3.28s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> The following information regarding your business position is currently incomplete.
>
> Business subject: refrigerator (as you stated).
>
> One-time cost: ¥15,000.00 CNY (RMB).
>
> Cash you reported; not independently confirmed: ¥40,000.00 CNY (RMB).
>
> Future cash flow projections remain uncertain and do not reflect actual available balances.

### 4. equipment — Actually, it costs CNY 18000.

Elapsed: 3.56s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> The following details reflect the information provided regarding the
>
> Business subject: refrigerator (as you stated).
>
> and the
>
> One-time cost: ¥18,000.00 CNY (RMB).
>
> compared against the
>
> Cash you reported; not independently confirmed: ¥40,000.00 CNY (RMB).
>
> It remains uncertain how this expenditure aligns with future cash flow projections, as these figures are estimates and not actual available funds.

### 5. equipment — Summarize my purchase plan.

Elapsed: 3.58s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> The purchase plan involves the following items.
>
> Business subject: refrigerator (as you stated).
>
> One-time cost: ¥18,000.00 CNY (RMB).
>
> Cash you reported; not independently confirmed: ¥40,000.00 CNY (RMB).
>
> It is uncertain how this expenditure aligns with your broader financial position, as other potential obligations remain unknown.

### 6. hiring — Can I afford to hire another employee?

Elapsed: 2.83s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> Business subject: another employee (as you stated).
>
> The current cash position remains uncertain as no balance information is available.
>
> Forecasted inflows and outflows for the period indicate variable liquidity.
>
> How much cash do you currently have available for this hire?

### 7. hiring — CNY 6000 per month.

Elapsed: 2.92s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> Business subject: another employee (as you stated).
>
> Recurring operating expense: ¥6,000.00 CNY (RMB).
>
> The current cash position remains uncertain as no balance information is available.
>
> How much cash do you currently have available for this hire?

### 8. hiring — Starting next month.

Elapsed: 2.8s. Status: `live`. Verification: `passed`. Tools: `get_cash_flow`.

> Business subject: another employee (as you stated).
>
> Recurring operating expense: ¥6,000.00 CNY (RMB).
>
> Intended start: November 2026.
>
> The current available cash balance remains uncertain.
>
> How much cash do you currently have available for this hire?

### 9. hiring — What if sales decline by 15%?

Elapsed: 3.25s. Status: `live`. Verification: `passed`. Tools: `none`.

> The following analysis considers the potential impact of a sales decline on the proposed hiring of
>
> Business subject: another employee (as you stated).
>
> starting in
>
> Intended start: November 2026.
>
> with a monthly commitment of
>
> Recurring operating expense: ¥6,000.00 CNY (RMB).
>
> The scenario assumes a
>
> Assumed sales change: -15% (your assumption).
>
> Financial outcomes remain uncertain as current cash reserves are not provided.
>
> How much cash do you currently have available for this hire?

### 10. sales — How are my sales performing?

Elapsed: 3.42s. Status: `live`. Verification: `passed`. Tools: `get_financial_summary`.

> The following data reflects the business subject identified.
>
> Business subject: sales (as you stated).
>
> Recorded net sales: ¥59,231.93 CNY (RMB), for July 3, 2026 to September 30, 2026. Revenue is not profit or available cash.
>
> Sales/payment transaction count: 5,091, for July 3, 2026 to September 30, 2026. Transaction volume is not cash balance.
>
> It is uncertain how these figures compare to prior periods as historical data is missing.
>
> What reporting period would you like to review for your sales?

### 11. sales — Last month.

Elapsed: 3.8s. Status: `live`. Verification: `passed`. Tools: `get_financial_summary`.

> The following data reflects the requested period.
>
> Requested reporting period: September 1, 2026 to September 30, 2026.
>
> Recorded net sales: ¥21,002.39 CNY (RMB), for September 1, 2026 to September 30, 2026. Revenue is not profit or available cash.
>
> Sales/payment transaction count: 1,796, for September 1, 2026 to September 30, 2026. Transaction volume is not cash balance.
>
> It is uncertain if these figures represent the complete financial position as additional operational costs remain unknown.

### 12. sales — Compare that with the previous month.

Elapsed: 3.81s. Status: `live`. Verification: `passed`. Tools: `get_financial_summary`.

> The following comparison reflects the requested periods.
>
> Recorded net sales: ¥21,002.39 CNY (RMB), for September 1, 2026 to September 30, 2026. Revenue is not profit or available cash.
>
> Recorded net sales: ¥20,959.71 CNY (RMB), for August 1, 2026 to August 31, 2026. Revenue is not profit or available cash.
>
> Sales/payment transaction count: 1,796, for September 1, 2026 to September 30, 2026. Transaction volume is not cash balance.
>
> Sales/payment transaction count: 1,803, for August 1, 2026 to August 31, 2026. Transaction volume is not cash balance.
>
> Financial conclusions regarding performance trends remain uncertain due to missing operational expense data.

### 13. sales — Actually, use the last 30 days.

Elapsed: 3.23s. Status: `live`. Verification: `passed`. Tools: `get_financial_summary`.

> The following data reflects the requested period.
>
> Business subject: sales (as you stated).
>
> Requested reporting period: September 17, 2026 to October 16, 2026.
>
> Recorded net sales: ¥10,061.92 CNY (RMB), for September 17, 2026 to October 16, 2026. Revenue is not profit or available cash.
>
> Sales/payment transaction count: 859, for September 17, 2026 to October 16, 2026. Transaction volume is not cash balance.
>
> Financial position remains uncertain as operating expenses and liabilities are not included.

## Financing, topic switching and recovery replies

The following were captured before the final subject/date-only corrections; their pathways were not modified by those corrections.

### financing — I want financing for CNY 50000 of equipment.

Elapsed: 2.94s. Status: `live`. Verification: `passed`.

> The requested financing amount is noted as follows.
>
> Financing amount you are considering: ¥50,000.00 CNY (RMB).
>
> This figure remains an unconfirmed assumption and does not represent an established financial position or approval.
>
> What is the intended duration for this financing?

### financing — 12 months.

Elapsed: 2.75s. Status: `live`. Verification: `passed`.

> Financing amount you are considering: ¥50,000.00 CNY (RMB).
>
> Proposed financing duration: 12 months (your assumption).
>
> The total cost of borrowing remains uncertain without the applicable interest rate.
>
> What is the annual interest rate for this financing?

### financing — What would the monthly repayment be?

Elapsed: 2.81s. Status: `live`. Verification: `passed`.

> Financing amount you are considering: ¥50,000.00 CNY (RMB).
>
> Proposed financing duration: 12 months (your assumption).
>
> The monthly repayment amount remains uncertain because the annual interest rate is missing.
>
> What is the annual interest rate for this financing?

### topics — What were my recent sales?

Elapsed: 3.28s. Status: `live`. Verification: `passed`.

> The following figures represent the recorded sales activity for the specified period.
>
> Recorded net sales: ¥59,231.93 CNY (RMB), for July 3, 2026 to September 30, 2026. Revenue is not profit or available cash.
>
> Sales/payment transaction count: 5,091, for July 3, 2026 to September 30, 2026. Transaction volume is not cash balance.
>
> These figures do not reflect available cash or net profit.
>
> For which period would you like to review your sales?

### topics — Explain the difference between revenue and profit.

Elapsed: 3.47s. Status: `live`. Verification: `passed`.

> Revenue refers to the total amount of money generated by the sale of goods or services before any expenses are deducted.
>
> Profit refers to the remaining financial gain after all operating costs, taxes, and other expenses have been subtracted from the total revenue.
>
> The distinction between these two figures is essential for understanding the financial health of an entity.

### topics — Going back to my sales, how did last month perform?

Elapsed: 3.39s. Status: `live`. Verification: `passed`.

> The following data summarizes the performance for the requested period.
>
> Business subject: sales (as you stated).
>
> Requested reporting period: September 1, 2026 to September 30, 2026.
>
> Recorded net sales: ¥21,002.39 CNY (RMB), for September 1, 2026 to September 30, 2026. Revenue is not profit or available cash.
>
> Sales/payment transaction count: 1,796, for September 1, 2026 to September 30, 2026. Transaction volume is not cash balance.
>
> It remains uncertain how these figures relate to overall profitability or liquidity.

### recovery — Can I buy a freezer for CNY 12000?

Elapsed: 4.03s. Status: `live`. Verification: `passed`.

> The following information pertains to your inquiry regarding
>
> Business subject: a freezer (as you stated).
>
> with a stated cost of
>
> One-time cost: ¥12,000.00 CNY (RMB).
>
> Financial records indicate
>
> Recorded net sales: ¥59,231.93 CNY (RMB), for July 3, 2026 to September 30, 2026. Revenue is not profit or available cash.
>
> and
>
> Sales/payment transaction count: 5,091, for July 3, 2026 to September 30, 2026. Transaction volume is not cash balance.
>
> It is uncertain if current cash balances support this expenditure as net sales do not represent available cash.
>
> How much cash do you have available for this purchase?

### recovery — cash

Elapsed: 0.22s. Status: `fallback`. Verification: `timeout`.

> I can't reach a verified live answer right now. How much cash do you have available for this purchase?

### recovery — I have CNY 30000 available.

Elapsed: 3.34s. Status: `live`. Verification: `passed`.

> The following information summarizes the financial details provided.
>
> Business subject: a freezer (as you stated).
>
> One-time cost: ¥12,000.00 CNY (RMB).
>
> Cash you reported; not independently confirmed: ¥30,000.00 CNY (RMB).
>
> The reported cash balance remains unconfirmed.
>
> Recorded net sales: ¥59,231.93 CNY (RMB), for July 3, 2026 to September 30, 2026. Revenue is not profit or available cash.
>
> Sales/payment transaction count: 5,091, for July 3, 2026 to September 30, 2026. Transaction volume is not cash balance.
>
> Revenue figures do not represent available cash or net profit.
