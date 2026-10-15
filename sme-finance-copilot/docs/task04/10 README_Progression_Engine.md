# Progression Engine — Merchant Financing Journey

Current access rules: [four-role permissions](../SECURITY_PERMISSIONS.md). These user instructions use the current baseline; earlier dated results remain historical.

## Overview

The Progression Engine brings the five-step financing journey into the existing Financing module:

**Identify → Profile → Place → Activate → Measure**

It displays authorized business evidence, missing requirements, next actions, and links to existing modules. The AI Financial Partner explains the same merchant-scoped backend journey data. The current enhanced implementation is on `feature/progression-engine-enhancement`.

**Current limitation:** stage-completion rules have not been implemented. The application must therefore show **Not Yet Assessed** for accessible steps rather than claim that a merchant has completed them. This is expected behavior, not evidence that the merchant is financially unqualified.

These five process steps are separate from the application's existing six business maturity stages. They must not be interpreted as the same classification.

## Where to open it

1. Sign in with an account authorized to access financing for the merchant.
2. Select the intended merchant in the application header.
3. Expand **Financing** in the left sidebar.
4. Select **Progression Engine**.
5. The main content displays **Merchant Financing Journey**.

The Financing submenu order is **Overview, Progression Engine, RBF Calculator, Applications**. The journey's direct path is `/financing/progression`; authentication and merchant authorization still apply to direct navigation.

## The five steps

| Step | Purpose | Existing views used when authorized | Suggested action |
| --- | --- | --- | --- |
| Identify | Understand financing needs | Cash Flow | Review cash flow and identify your financing need. |
| Profile | Review merchant financial information | Dashboard; Transaction History when permitted | Review recorded sales, expenses, and transaction sources. |
| Place | Explore matched financing options | Financing Overview | Review existing financing matches and their limitations. |
| Activate | Review or submit simulated financing applications | Applications | Review saved applications. An Owner may propose a consent-authorized simulated application through the existing application workflow. |
| Measure | Monitor financial outcomes | Cash Flow; Dashboard when permitted | Review Dashboard and Cash Flow after business data changes. |

The journey links navigate to existing modules. Opening a link does not complete a step, alter financial records, submit an application, or approve financing.

## Supporting evidence and missing requirements

Each stage card now shows **Supporting evidence**, source/as-of/provenance information, **Missing requirements**, and its next action. Evidence is loaded through existing permission-aware backend capabilities; having journey access does not authorize every evidence source.

| Step | Evidence currently displayed when authorized and available | Missing completion specification |
| --- | --- | --- |
| Identify | Existing diagnosed business constraints and their contributing evidence from `assess_business`. | Rule linking diagnosed constraints to completion of Identify. |
| Profile | Existing six-stage business maturity result, composite score, credit-readiness score, recorded history days, and digital share. | Sufficient-profile criteria for this five-step journey. |
| Place | Existing indicative financing matches and match scores, plus excluded options and their reasons. | Rule defining an accepted financing placement. |
| Activate | Count of authorized saved simulated applications. | Rule mapping confirmed sandbox submission to journey completion. |
| Measure | Current estimated minimum modeled cash-flow balance, in merchant currency. | Post-activation baseline, comparison period, and outcome/success criteria. |

If a source is unavailable or unauthorized, the page explains that missing evidence rather than inventing a result. Assessment attributes and thresholds remain demo/provisional. The Measure forecast is an estimate of current modeled conditions; it does not demonstrate that financing improved outcomes. Legacy in-memory maturity comparisons are not post-financing outcome measurements.

The **as-of** date follows available business data and can differ from today. Provenance describes sources such as synthetic seed, imported/manual activity, simulated application, or forecast. It does not certify bank settlement.

## Incentive milestone panel

The page now includes **Incentive milestone**. When the account is authorized for the existing incentive tool, it shows:

- **Provisional demo rules** status.
- Existing tier name and tier number.
- The existing next milestone name, when available.
- Any existing base-history note, plus as-of date and provenance.

The backend reuses the calendar-month ecosystem-sales growth calculation from `incentive_status`; no new incentive policy or discount is introduced. The page explains that this is not a journey stage, eligibility approval, or paid reward. An unavailable or unauthorized incentive source is explicitly marked **Unavailable**.

Existing RBF calculations can use their established incentive discounts. That relationship does not make incentive tiers, six maturity stages, and the five journey steps equivalent. The journey does not award cash or change financing terms.

## Reading the status and recommendations

| Current status | Meaning | What to do |
| --- | --- | --- |
| Not Yet Assessed | A linked view is accessible, but no implemented completion rule determines whether the journey step is complete. | Review the evidence in the linked module. Do not treat the label as an eligibility decision. |
| Blocked | The account cannot access the linked business views for that step. | Ask the Owner or an appropriate administrator to review access. This does not indicate business ineligibility. |

The verification layer recognizes additional status labels, but the current journey provider does **not** assign Completed, In Progress, or Not Started. There are no documented completion thresholds behind those labels in this implementation.

The current stage cannot be determined. The next suggested action comes from the first accessible step in the five-step order; it is not a personalized readiness score or an inferred completed milestone.

If an authorized saved simulated application exists, the Activate explanation acknowledges it. Application submission still does not mark Activate complete. If application data is unavailable to the account, the journey must not disclose it.

## Ask the AI Financial Partner

Select **Ask AI About My Journey**, when available. This opens the existing AI panel and asks:

> What is my current financing journey stage, and what should I do next?

You can also try:

- What stage am I currently on?
- Show my financing progression.
- Why am I at this stage?
- What have I completed?
- What requirements are missing?
- What incentive milestone have I reached?
- How can I progress toward financing?
- What should I do next?
- What do I need before applying for financing?

The AI uses the same authorized backend journey provider as the page. Its verified journey response must acknowledge missing completion rules rather than invent a completed stage, lender approval, readiness score, or financial outcome. The response now includes authorized stage evidence, missing requirements, the available incentive milestone, and a suggested next action. Existing assessment scores may be reported, but they are not newly invented journey readiness scores. The overall journey response remains classified as **INSUFFICIENT_EVIDENCE** because the current journey stage cannot be established. Completed journey steps are not established by implemented rules.

Journey questions use read-only information. Any application action must continue through the existing permission, consent, and explicit-confirmation controls. Asking the AI a question does not submit an application or transfer money.

If the LLM is unavailable, a deterministic response can explain the backend journey state. That fallback is not evidence of a successful live Gemini request.

## Practical user walkthrough

1. Select your authorized merchant and open the journey.
2. Read Identify’s diagnosed constraints and missing completion rule. Use its Cash Flow link to review your financing need.
3. Read Profile’s existing maturity, score, history and digital-share evidence. Use its links to inspect Dashboard and, where permitted, Transaction History. Correct source data through the existing authorized transaction workflows.
4. Read Place’s matches and exclusions, then open Financing Overview. Treat matches according to the existing module's assumptions and limitations.
5. Open the RBF Calculator separately from the Financing submenu if you want to explore its existing quotation calculations. A quote is not an approval.
6. Use Activate to review Applications. If permitted, use the existing simulated application process, including required consent and confirmation.
7. Read Measure’s current estimated minimum balance and missing outcome criteria. Use its links to revisit Cash Flow and Dashboard after underlying business data changes. Review the separate provisional incentive panel.
8. Return to the journey or refresh it to retrieve current authorized information. Expect Not Yet Assessed until actual completion rules are implemented.

## Permissions and safety

Owner accesses assigned merchants; Staff need explicit financing delegation and relevant evidence-source grants. Bank receives the shared read-only journey through Bank review with permitted categories, not direct SME routes. System Admin and unmapped legacy roles have no financial access. Links and supporting evidence remain independently permission-checked. See [canonical security rules](../SECURITY_PERMISSIONS.md).

Packet routing, category authorization and confirmation remain separate; saved application evidence never marks a journey step complete.


## Technical reference

| Component | Responsibility |
| --- | --- |
| `copilot/financing_journey.py` | Builds the five steps, retrieves guarded assessment/matching/incentive/forecast evidence and authorized saved application information, lists missing specifications, and produces the trusted explanation. |
| `GET /api/financing/journey?merchant=<merchant_id>` | Returns the authenticated, authorized merchant journey. |
| `financing_journey` AI tool | Exposes the same provider as a read-only financing tool under existing authorization. |
| `copilot/authorization.py`, `copilot/security.py` | Apply existing action boundaries, merchant access, and policy controls. |
| `copilot/verified_agent.py`, `copilot/reliability.py` | Integrate journey evidence and verify typed claims before returning the trusted response. |
| `web/index.html`, `web/financial-partner.js` | Display navigation, the journey view, and its connection to the existing AI panel. |

The response includes each stage’s `evidence`, `missing_requirements`, and `completion_rule_status`, stage explanations and permitted links, an assessment status, a suggested action, authorized application count, `as_of`, an incentive object, and data/journey versions. Evidence items contain `source`, `summary`, `as_of`, and `provenance`. The provider currently returns no determined current stage. Version checks help detect changed journey evidence during an AI request.

This integration introduces no journey database tables or persisted completion records. It derives the view from existing application data and access controls. It adds no financial formula, incentive eligibility, milestone score, or lending decision.

## Troubleshooting and limitations

- **Menu or page unavailable:** verify the signed-in role, merchant selection, and existing financing authorization. Administrative access alone is insufficient.
- **A step is Blocked:** review its linked-view permission; do not interpret this as a declined loan.
- **All accessible steps remain Not Yet Assessed:** expected while completion rules are absent.
- **Submitting an application does not advance the stage:** expected; submission is not an implemented completion rule.
- **AI cannot identify a current stage:** expected; asking differently cannot supply missing backend rules.
- **Results changed after refresh:** review changes to merchant scope, consent, authorized applications, and underlying data.

Implemented: five-step view, authorized navigation, per-stage supporting evidence and missing requirements, current forecast context, provisional existing incentive display, shared read-only AI guidance, truthful status explanations, and existing security integration.

Not implemented by this lightweight integration: automatic stage advancement, approved five-step completion criteria, a new progression score or incentive policy, persisted journey milestone history, or proof that financing improved business outcomes. These require separately reviewed business rules and implementation; this README does not propose thresholds.

## Verification scope

The enhancement passed **18 focused automated tests** across `tests.test_financing_journey` and `tests.test_reliability`. These covered evidence availability, merchant isolation, role/consent restrictions, incentive agreement with the existing tool, application evidence without inferred completion, all seven requested AI questions using a mocked LLM, read-only refresh consistency, empty records, and rejection of fabricated Completed claims.

Focused browser checks passed for five-stage rendering, evidence and missing-requirement sections, provisional incentive labeling, direct routing and refresh, existing module links, Financing Overview and Applications access, shared AI/page results, and mobile layout without JavaScript errors. Four affected Python files passed syntax checks, and `git diff --check` passed during implementation.

These are recorded enhancement checks, not a new test run for this documentation edit. No full regression suite or live Gemini assessment was run for the enhancement. This README update changes documentation only; no financial data, formulas, permissions, migrations, commits, pushes, or merges are performed by updating it.
