# Cash Flow — User Journey Scenarios

**Entry point:** /cash-flow. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 05-01: Routine forecast review

**Prerequisites:** Authorized view_forecasts; Agent additionally has current relevant consent/assignment.

**Pathway:** Select merchant → review opening balance, lowest 30-day projection, buffer, chart and alerts → ask AI for explanation.

**Expected result / boundary:** Forecasts are estimates based on weekday averages and scheduled items, not guaranteed cash.

## 05-02: Review an existing risk alert

**Prerequisites:** Synthetic merchant whose actual inputs trigger a rule.

**Pathway:** Read alert → inspect sales, obligations and source assumptions → consider advised next action in relevant module.

**Expected result / boundary:** Do not invent a cause or assume automatic bill payment/financing execution.

## 05-03: No alerts

**Prerequisites:** Authorized merchant with no triggered implemented rules.

**Pathway:** Review chart and assumptions as well as the empty alert list.

**Expected result / boundary:** No alerts is not a guarantee of financial health or permanent solvency.

## 05-04: Import changes sales assumptions

**Prerequisites:** Authorized import and forecast viewing.

**Pathway:** Commit completed POS rows → reload forecast → review version/date/source changes.

**Expected result / boundary:** Imported revenue does not establish bank/wallet receipt; synthetic obligations may still influence forecast.

## 05-05: Simulation affects internal wallet

**Prerequisites:** Authorized payment and forecast access.

**Pathway:** Complete own-rail simulated payment → reload Cash Flow.

**Expected result / boundary:** Internal simulated settlement differs from gross sales; external-channel sales do not credit this wallet.

## 05-06: Forecast versus revenue projection

**Prerequisites:** Authorized forecast/report access.

**Pathway:** Compare cash forecast with AI financial-report revenue projection.

**Expected result / boundary:** Balance path and repeat-recent-sales revenue projection are different calculations; they need not match.

## 05-07: Unavailable buffer or missing assumptions

**Prerequisites:** Inputs with zero estimated outflow or incomplete data.

**Pathway:** Read unavailable evidence and screen behavior → inspect assumptions.

**Expected result / boundary:** Unavailable buffer is not infinite safety; current UI may display null days.

## 05-08: Borrow-versus-cut-costs simulation

**Prerequisites:** User requests a survival plan.

**Pathway:** Use existing reports/forecast as advisory information only.

**Expected result / boundary:** Task 03.1 survival simulation and automatic scenario execution are not implemented.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Cash Flow guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
