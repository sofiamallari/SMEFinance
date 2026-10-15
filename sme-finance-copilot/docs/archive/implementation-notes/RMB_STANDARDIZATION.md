> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# RMB standardization — current compatibility implementation

New merchants use CNY, displayed as RMB / ¥ with two decimals. No FX conversion or historical relabeling is performed. CNY imports reject foreign currency declarations under existing merchant-match validation. RMB normalizes to CNY; a yuan symbol requires explicit trusted source context.

## Existing data strategy (documented before applying changes)

The six configured synthetic merchants retain their original PHP (two), IDR, THB, VND and MYR datasets. No synthetic dataset is regenerated, no amounts are rescaled, and no absolute business threshold is recalibrated. Existing data/wallets/payments/imports/applications/audits remain unchanged. These merchants remain explicitly labeled legacy compatibility workspaces, with original currency codes, not RMB totals. All reporting remains merchant-scoped, and no cross-currency total is introduced.

Automatic approval review rejected a proposed blanket block on existing non-CNY operations because it would disrupt reports, POS, payments and simulation. The safe delivered alternative preserves those operations with explicit legacy labeling. A complete CNY-only cutover, freezing legacy activity or migrating historical data remains pending further approval; this is not a claim that all existing merchants now operate in CNY.

System Admin can create a separate CNY merchant and explicitly assign users through existing User Management, then import verified CNY records. No accounts, permissions, sample financial records or assignments are generated automatically.

CNY cart tax is a provisional **0% sandbox/exempt configuration**, not a claim about Chinese VAT. Existing non-CNY tax configuration, payment algorithms, MDR and recorded settlement history remain unchanged.

## Read-only local inventory

Configured synthetic seeds: PHP ×2, IDR, THB, VND, MYR. Aggregate persisted-data currency counts from the local default storage at inspection:

```json
{
  "application_currency_counts": {
    "IDR": 2
  },
  "canonical_ledger_currency_counts": {
    "IDR": 203
  },
  "payment_currency_counts": {
    "IDR": 3
  },
  "saved_merchant_currency_counts": {}
}
```

No record values or currency codes were modified by this inspection. Custom storage paths were not inferred from secrets/environment files.


## Current implementation and file map

- Central metadata/formatting: `copilot/currency_policy.py`, `copilot/config.py`, served `web/currency.js`. ISO code stays CNY in financial API records; CNY display uses RMB / ¥ with two decimals. Legacy display retains the original code and is never presented as ¥.
- Source validation: `copilot/canonical_transactions.py`, `copilot/pos_import.py`. RMB is an alias of CNY. ¥/￥ require an explicitly verified Yuan context or a CNY source declaration. Existing foreign-currency merchant-match checks, duplicates, financial confirmations and provenance remain unchanged.
- New-merchant default/selection: `copilot/merchant_management.py`, `web/merchants.js`; metadata/Owner preferences: `copilot/transaction_settings.py`, `web/transaction-settings.js`. Only CNY is offered for new merchants. Existing foreign-currency records remain visible with migration flags; locked history cannot be relabeled by Admin.
- Shared asset route: `copilot/server.py`. Currency metadata is injected into the shared formatter, loaded by `web/index.html`, `bank.html`, `users.html`, `security.html`, `merchants.html`.
- Display integrations: `web/merchant-transactions.js`, `financing-applications.js`, `bank-components.js`, `bank-portal.js`, `financial-partner.js`; backend monetary prose in `copilot/agent.py`, `modules/cashflow.py`, `modules/assessment.py`, `verified_agent.py`, `survival_simulation.py`. Existing signs and calculations remain unchanged.
- Legacy disclosures: existing aggregate limitations in `copilot/financial_data.py` and Bank report/export disclaimer in `copilot/bank_workflow.py`. The Bank application table displays each record's original currency without cross-currency sums. The Owner workspace shows an explicit migration warning for foreign-currency merchants.
- AI instruction: `copilot/ai_agent.py` states preferred CNY, no invented FX rates, no relabeling. No provider change or permission change.
- Import History: removed the entire dynamic `run-technical` section from the Owner's Import Summary dialog. Validation findings, reconciliation, API data, audit records and stored evidence remain available; only that technical-details presentation was removed.

The existing payment adapter used the original synthetic merchant list to assess new merchants, even after canonical transactions existed; that empty list raised an error. For merchants with no seed transaction list, `agent.py` now passes the existing canonical projection to payment creation/MDR comparison. With no recorded sales it retains the simulator's existing stage-one default. Legacy seeded-merchant execution remains unchanged. No assessment/MDR/fee/settlement formula or approval rule was changed.

## Minimal verification

13 focused checks passed on disposable data: new merchant defaults to CNY, authoritative revenue/expense totals and RMB alias normalization, foreign source row rejection under CNY, normal server startup/restoration, explicitly confirmed CNY sandbox payment creation, authorized Bank CNY financial report, financing/Bank request currency context, Survival explanation RMB values, AI CNY evidence/response context, original legacy values with a disclosure, exact Owner `¥12,500.00` formatting, Import History modal without Technical Details, and no browser JavaScript errors.

Python compilation and JavaScript syntax checks passed. No new test suite or full regression was run. Live Gemini, exhaustive export formats, every payment lifecycle/currency-alias variation and every responsive view were not verified. Local default storage was inspected read-only; all functional checks used isolated fixtures.

## Remaining cutover decision

This delivery is additive and does **not** enforce a global CNY-only cutover for existing merchants. Legacy imports/payments/reports/simulations still operate in their original currency with explicit labeling. Their amounts are not included in CNY merchant totals. Disabling/freeze-migrating those existing workspaces requires further approval after automatic review rejected the broad disruption. No irreversible migration, FX conversion, reseeding, wallet reset or financial-history rewrite was applied.
