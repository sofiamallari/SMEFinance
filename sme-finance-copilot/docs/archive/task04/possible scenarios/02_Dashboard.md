> **Historical snapshot — superseded.** Use [current documentation](../../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Dashboard — scenario pathways

Entry: /dashboard. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../5%20README_Dashboard.md); rules: [permissions](../../../technical/security-permissions.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 02-01: Same-period review

**Path:** Owner or explicitly delegated Staff selects merchant/dates → Apply → inspect source/currency.

**Expected result / boundary:** Recorded totals are not bank cash.

## 02-02: Import integration

**Path:** Confirm valid synthetic POS import → refresh matching-period Dashboard.

**Expected result / boundary:** Completed eligible records affect calculations, not merely previewed rows.

## 02-03: AI comparison

**Path:** Grant appropriate AI/read actions → ask same merchant/dates → compare definitions.

**Expected result / boundary:** Counts/revenue/cash can differ by definition; inspect evidence.

## 02-04: Refund/empty period

**Path:** Review records including refunds or no completed activity.

**Expected result / boundary:** Do not infer real-world revenue from missing records.

## 02-05: Bank or admin direct route

**Path:** Attempt original SME Dashboard as Bank/System Admin.

**Expected result / boundary:** Denied; Bank uses category-authorized review summaries.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../implementation-notes/TESTING.md) for recorded evidence.
