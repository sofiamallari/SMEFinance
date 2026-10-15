> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Application-wide CNY consistency audit

Date: 2026-10-15. Repository: `C:\Users\User\source\repos\SMEFinance\sme-finance-copilot`. Branch: `feature/security-sme-bank-workflow`. Active dataset: `logs/shenzhen_cny_demo`.

## Result

59 focused currency checks passed, plus Python/JavaScript syntax, whitespace checks and an AST comparison confirming the report calculation is unchanged except for added merchant/currency metadata. No full regression suite, new test suite, live Gemini request, commit, push or deployment was performed. New imports, transactions and payments were tested in a disposable copy, not the active financial ledger.

All 221 active canonical transactions are CNY. All six seed histories and their merchant identities are CNY. Persisted currency declarations in applications, payment states, drafts, settings and import data are CNY. Source mapping fields named `currency` are column bindings, not currency declarations. No active IDR monetary records were found. The retired original default database/ledger/audit/execution paths were not recreated.

## Corrections

- Extended shared `MerchantCurrency` presentation with compact money formatting; full values remain two-decimal currency amounts.
- Dashboard/Cash Flow compact amounts and zero axis, Bank chart ticks, and Survival chart ticks use the shared formatter. Survival full-value tooltips, KPIs and backend-generated explanations agree in CNY/¥.
- Bank nested evidence formats explicitly recognized monetary fields with the shared formatter; ratios, scores, counts and rates remain numeric. Unknown field semantics are not guessed as money.
- Removed an unused legacy frontend currency-name dictionary and obsolete Bank migration notices in the CNY-only portal.
- Added `merchant_id` and canonical `currency` metadata to existing financial reports without changing calculations.
- Strengthened narrator currency-preservation instructions. Existing typed AI evidence checks, foreign-currency refusal, authorization and no-FX rules remain intact.
- Replaced the old POS demo generator and known generated CSV/XLSX examples with fresh CNY scenarios. Prior examples were first compared to the generator (including the preserved permissions documentation link) and archived. This is not relabeling: new amounts, CNY receipt references and source timestamps were authored. Fresh sales CSV totals CNY 102.75 and native-date XLSX CNY 78.90; both passed the real validation/confirmation pipeline in disposable storage.

## Coverage

| Area | Focused verification |
|---|---|
| Six merchant reports | Authorized tool result equals existing projected report calculation; merchant ID/CNY metadata and canonical sales/expense/net-income reconciliation checked individually |
| Dashboard | All six merchants' visible KPIs bound to their backend CNY metrics; Overview, Sales & Payments, Business Growth and Alerts checked for IDR/Rp |
| Transactions/POS/monitoring | CNY form default, history/import/quality screens, RMB alias normalization, foreign-currency refusal, real CNY CSV/XLSX validation and confirmed imports |
| Digital Payments | Screen, merchant-derived CNY proposal/confirmed payment; no actual financial transfer |
| Cash Flow/Financing/RBF/Applications | Screen currency checks, shared display paths, source currency metadata inspected; existing formulas unchanged |
| Bank Portal | CNY overview/request/financial review; expanded chart and nested money fields; rates not formatted as monetary amounts |
| Reports/exports | Six reports retain authoritative values; existing authorized Bank CSV includes machine-readable CNY metadata and no IDR/Rp |
| AI Financial Partner | Existing prompt/tool/typed-evidence paths inspected; deterministic authorized read returns CNY evidence. Live Gemini not tested |
| Survival | Actual baseline/run, monetary chart axes, circle tooltips, displayed KPI and explanation agree; mobile overflow check passed |
| Persistence | Normal startup/restart preserves the canonical journal hash; no IDR/duplicate reseeding |

Browser smoke checks had zero JavaScript page errors. Financial controls and permission policies were not changed. The existing audit per-process hash-chain continuity limitation is unaffected by this presentation audit.

## Remaining IDR references

| Classification | Location / meaning |
|---|---|
| Active functionality — intentional protective reference | `copilot/verified_agent.py` recognizes IDR and other foreign currencies so unsupported-currency requests are refused. Removing this reference would weaken validation |
| Active source — inactive compatibility definitions | `copilot/config.py` contains legacy catalog entries, but active CNY selection filters supported currencies to CNY. `copilot/data/synthetic.py` retains original persona templates; the CNY generator replaces their monetary budgets/currency **before** generating any active history. Normal server startup rejects a legacy environment |
| Archived evidence | Original SQLite/JSONL records, original audit/execution evidence, pre-audit source snapshots and old generated POS examples remain under `logs/backups/`. Both original snapshot manifests were rechecked successfully; no evidence removed or rewritten |
| Harmless historical documentation | Earlier baseline, Task 02, import and currency-migration reports describe former IDR behavior. They are retained as history, not current currency instructions. The current setup/cutover/audit guides supersede those examples |
| Offline historical verification fixtures | Legacy amounts remain in test fixtures and old diagnostic/browser scripts. These are not served data or automatic demo seeds. The current supported demo generator emits only CNY. Full compatibility testing of those historical scripts was outside scope |

The last category is deliberately explicit: source/test literals are not financial records, but they are also not physically archived files. Therefore “IDR only in backups” is verified for historical **persisted demonstration financial records and retired generated examples**, not as a promise that the repository has zero IDR text. No active frontend or current demo-generator/example text contains IDR/Rp. Unrelated historical documents, tests, binary screenshots and ZIP artifacts were not deleted or rewritten.

## Evidence and files

Focused evidence: `logs/shenzhen_cny_demo/currency-audit.json` (59 checks). Exact retained text-reference classification: `currency-reference-inventory.json` in the same directory. Original generated examples: `logs/backups/legacy-pos-examples-20261015T084830Z`. Prior edited sources: `logs/backups/currency-audit-source-20261015T084704Z`.

Files changed: `web/currency.js`, `web/index.html`, `web/survival-simulation.js`, `web/bank-components.js`, `web/bank-portal.js`, `web/merchant-transactions.js`, `copilot/modules/reporting.py`, `copilot/llm.py`, `scripts/generate_pos_demo.py`, its known generated `examples/pos-reports` files, this report and documentation links. All existing uncommitted work was preserved.
