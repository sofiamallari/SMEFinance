# Progression Engine — Merchant Financing Journey

## Overview

The Progression Engine brings the five-step financing journey into the existing Financing module:

**Identify → Profile → Place → Activate → Measure**

It helps users find the relevant business information and financing screens, and lets the AI Financial Partner explain the same backend-provided journey information.

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
- What should I do next?
- What do I need before applying for financing?

The AI uses the same authorized backend journey provider as the page. Its verified journey response must acknowledge missing completion rules rather than invent a completed stage, lender approval, readiness score, or financial outcome. An insufficient-evidence classification is appropriate when the current stage cannot be established.

Journey questions use read-only information. Any application action must continue through the existing permission, consent, and explicit-confirmation controls. Asking the AI a question does not submit an application or transfer money.

If the LLM is unavailable, a deterministic response can explain the backend journey state. That fallback is not evidence of a successful live Gemini request.

## Practical user walkthrough

1. Select your authorized merchant and open the journey.
2. Use Identify to review Cash Flow and understand your financing need.
3. Use Profile to inspect Dashboard and, where permitted, Transaction History. Correct source data through the existing authorized transaction workflows.
4. Use Place to inspect Financing Overview. Treat matches according to the existing module's assumptions and limitations.
5. Open the RBF Calculator separately from the Financing submenu if you want to explore its existing quotation calculations. A quote is not an approval.
6. Use Activate to review Applications. If permitted, use the existing simulated application process, including required consent and confirmation.
7. Use Measure to revisit Cash Flow and Dashboard after underlying business data changes.
8. Return to the journey or refresh it to retrieve current authorized information. Expect Not Yet Assessed until actual completion rules are implemented.

## Permissions and safety

- **Business Owner (`owner`):** may access the journey for authorized merchants and follow permitted module links.
- **Staff (`staff`):** does not gain financing access from this page. The current role boundary denies journey access.
- **Financing Agent (`lender_analyst`) and compatible Coach (`coach`) workflows:** remain subject to existing role boundaries, merchant scope, applicable consent, and the permissions of each linked view.
- **User Administrator and Security Administrator:** do not automatically gain merchant financial access from their administrative roles.

The backend checks access; hiding a menu is not the security boundary. Requests for another merchant remain unauthorized without the required scope. Application visibility is restricted: an Owner sees authorized merchant applications, while other permitted accounts see applications addressed to them. The journey adds no new role grant, approval rule, or exception to prohibited actions.

## Technical reference

| Component | Responsibility |
| --- | --- |
| `copilot/financing_journey.py` | Builds the five steps, checks linked-view permissions, reads authorized saved application information, and produces the trusted explanation. |
| `GET /api/financing/journey?merchant=<merchant_id>` | Returns the authenticated, authorized merchant journey. |
| `financing_journey` AI tool | Exposes the same provider as a read-only financing tool under existing authorization. |
| `copilot/authorization.py`, `copilot/security.py` | Apply existing action boundaries, merchant access, and policy controls. |
| `copilot/verified_agent.py`, `copilot/reliability.py` | Integrate journey evidence and verify typed claims before returning the trusted response. |
| `web/index.html`, `web/financial-partner.js` | Display navigation, the journey view, and its connection to the existing AI panel. |

The response includes stage explanations and permitted links, an assessment status, a suggested action, an authorized application count when available, and data/journey versions. The provider currently returns no determined current stage. Version checks help detect changed journey evidence during an AI request.

This integration introduces no journey database tables or persisted completion records. It derives the view from existing application data and access controls. It adds no financial formula, incentive eligibility, milestone score, or lending decision.

## Troubleshooting and limitations

- **Menu or page unavailable:** verify the signed-in role, merchant selection, and existing financing authorization. Administrative access alone is insufficient.
- **A step is Blocked:** review its linked-view permission; do not interpret this as a declined loan.
- **All accessible steps remain Not Yet Assessed:** expected while completion rules are absent.
- **Submitting an application does not advance the stage:** expected; submission is not an implemented completion rule.
- **AI cannot identify a current stage:** expected; asking differently cannot supply missing backend rules.
- **Results changed after refresh:** review changes to merchant scope, consent, authorized applications, and underlying data.

Implemented: five-step view, authorized navigation, shared read-only AI evidence, truthful status explanations, and existing security integration.

Not implemented by this lightweight integration: automatic stage advancement, approved completion criteria, progression scoring, incentive eligibility, persisted milestone history, or proof that financing improved business outcomes. These require separately reviewed business rules and implementation; this README does not propose thresholds.

## Verification scope

The integration was checked with focused syntax, synthetic authorization/provider, mocked LLM claim-verification, and browser checks. Checks covered the five steps, direct navigation, refresh/merchant context, AI/provider agreement, rejection of fabricated completion claims, unauthorized access, linked navigation, and mobile behavior.

These focused checks do not represent a new full regression run or a live Gemini connectivity assessment. This README documents the current implementation and does not change application behavior.
