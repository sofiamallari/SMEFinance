# Dashboard — User Journey Scenarios

**Entry point:** /dashboard. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 02-01: Review recorded performance

**Prerequisites:** Authorized view_dashboard permission and merchant membership.

**Pathway:** Select merchant → choose reporting dates and granularity → Apply → review cards, trends and provenance.

**Expected result / boundary:** Totals describe recorded data for that period; they are not verified bank balances.

## 02-02: Import-to-dashboard journey

**Prerequisites:** Authorized POS import and Dashboard access.

**Pathway:** Import an approved synthetic batch → inspect committed outcome → Dashboard → include its dates → Apply.

**Expected result / boundary:** Completed records affect reporting; pending/failed records do not increase revenue.

## 02-03: Compare Dashboard with AI

**Prerequisites:** Dashboard and use_copilot access.

**Pathway:** Apply dates → ask AI for recorded sales using the same two ISO dates → compare merchant, currency and evidence.

**Expected result / boundary:** Use equivalent metrics. Dashboard activity counts and AI completed-record counts can have different definitions.

## 02-04: Refund and expense example

**Prerequisites:** Authorized synthetic transactions.

**Pathway:** Record completed sale 100, refund 25 and expense 20 → review matching reporting period.

**Expected result / boundary:** Net sales 75; expenses 20; net income 55. Net income is not wallet settlement.

## 02-05: No activity or negative net channels

**Prerequisites:** Reporting period with no completed records or refunds exceeding sales.

**Pathway:** Apply period → read totals and chart notes.

**Expected result / boundary:** Zero means no recorded activity, not proof of zero real revenue. Nonpositive channel totals may not support a pie chart.

## 02-06: Wrong dates or merchant

**Prerequisites:** Authorized account with relevant scope.

**Pathway:** Correct selected merchant and dates → Apply; start date must not exceed end date.

**Expected result / boundary:** Do not compare different currencies or periods as if they were identical.

## 02-07: Unauthorized direct route

**Prerequisites:** A role/account without dashboard access.

**Pathway:** Open Dashboard directly in a controlled test.

**Expected result / boundary:** Backend denies access; administrative role alone is insufficient.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Dashboard guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
