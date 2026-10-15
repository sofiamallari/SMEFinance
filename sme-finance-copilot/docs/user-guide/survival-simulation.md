# Financial Survival Simulation — Business Stress Test

Current implemented guide · 15 October 2026.

## Purpose

Compare hypothetical sales and expense changes with a recorded operating baseline.

## Access and prerequisites

Owner only, required financial reads and FINANCIAL_SURVIVAL_SIMULATION_ENABLED enabled by the operator.

## Navigation

Dashboard -> Survival Simulation; heading Business Stress Test. Existing AI scenario-review buttons open this tab.

## Step-by-step instructions

1. Review Your Monthly Baseline and its actual months-used badge; expand About Your Data as needed.
2. Adjust sales (-80% to +50%) and expenses (-30% to +80%) in 5% steps. Defaults are -20% and +10%.
3. Choose 1, 3 or 6 months; default 3.
4. Select Run Simulation. Sliders and Reset do not submit by themselves.
5. Compare monthly operating result, change from baseline and cumulative result in the cards and graph.
6. After changing assumptions, treat the previous result as stale until a successful rerun.
7. Expand exact chart values, Detailed Analysis and Assumptions & Limitations. Reset restores the original controls.

## Understanding results and statuses

Operating surplus/shortfall is different from improvement/deterioration versus baseline. The chart contains backend monthly cumulative operating points, not available cash or survival runway.

## Common errors and troubleshooting

No eligible complete-month data disables Run. Partial recent coverage remains a warning. Currency comes from backend/merchant configuration; never convert an old amount by changing its label.

## Important limitations

Constant percentages, no compounding, expense proxy and unverified coverage apply. Existing AI-assisted verified explanation selection is optional; Rule-based guidance is labeled honestly. No hypothetical inputs become transactions.

## Related guides

[AI Financial Partner](ai-financial-partner.md) · [Cash Flow](cash-flow.md) · [Dashboard and Business Overview](dashboard.md) · [User-guide index](README.md) · [Canonical permissions](../technical/security-permissions.md)
