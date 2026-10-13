"""
Financing option matching.

Ranks a generic, provider-neutral catalog of ASEAN MSME financing and support
products against the merchant's stage, binding constraints and readiness.

score = 0.45*constraint_fit + 0.25*stage_fit + 0.15*readiness + 0.15*affordability

Constraint fit carries the most weight because the framework requires
interventions to target the constraint blocking the next stage, "rather than
simply adding more products".
Hard eligibility filters run first; excluded products are returned with the
reason so the owner sees a path to qualify ("why not yet").
The copilot recommends; it never approves credit.
"""
from __future__ import annotations

from datetime import date

from copilot.modules import rbf

CATALOG = [
    {"id": "WALLET", "name": "Business Wallet with savings pocket", "type": "non-credit",
     "provider_type": "Bank / e-money issuer", "stages": [1, 2, 3], "fits": ["cash_flow", "limited_management_capability"],
     "min_credit_readiness": 0, "indicative_cost": 0.0, "size_multiple": 0},
    {"id": "CREDIT_BUILDER", "name": "Credit-builder micro-loan with literacy module", "type": "credit",
     "provider_type": "Microfinance institution / government-guaranteed program", "stages": [1, 2],
     "fits": ["cash_flow", "limited_management_capability", "low_digital_adoption"],
     "min_credit_readiness": 20, "indicative_cost": 0.06, "size_multiple": 0.5},
    {"id": "GOV_WC", "name": "Government-guaranteed working-capital microloan", "type": "credit",
     "provider_type": "Bank under public guarantee scheme", "stages": [2, 3, 4],
     "fits": ["cash_flow"], "min_credit_readiness": 40, "indicative_cost": 0.06, "size_multiple": 1.0},
    {"id": "RBF", "name": "Revenue-based financing (repay as % of daily digital sales)", "type": "credit",
     "provider_type": "Bank / fintech on ecosystem rails", "stages": [3, 4, 5],
     "fits": ["cash_flow", "production_bottleneck"], "min_credit_readiness": 50,
     "indicative_cost": 0.12, "size_multiple": 1.5, "requires": "rbf_eligible"},
    {"id": "LEASE", "name": "Equipment lease-to-own", "type": "credit",
     "provider_type": "Bank / leasing company / vendor financing", "stages": [3, 4, 5],
     "fits": ["production_bottleneck", "manual_processes"], "min_credit_readiness": 45,
     "indicative_cost": 0.14, "size_multiple": 2.0},
    {"id": "PO_FIN", "name": "Purchase-order financing", "type": "credit",
     "provider_type": "Bank / supply-chain fintech", "stages": [3, 4, 5],
     "fits": ["confirmed_orders_no_capital"], "min_credit_readiness": 55,
     "indicative_cost": 0.10, "size_multiple": 1.0, "requires": "confirmed_orders"},
    {"id": "INVOICE", "name": "Invoice / receivables financing", "type": "credit",
     "provider_type": "Bank / invoice-financing platform", "stages": [2, 3, 4, 5, 6],
     "fits": ["cash_flow"], "min_credit_readiness": 50, "indicative_cost": 0.11,
     "size_multiple": 0.8, "requires": "receivables"},
    {"id": "REVOLVER", "name": "Revolving working-capital line", "type": "credit",
     "provider_type": "Bank", "stages": [4, 5, 6], "fits": ["cash_flow", "confirmed_orders_no_capital",
                                                           "limited_market_access"],
     "min_credit_readiness": 65, "indicative_cost": 0.09, "size_multiple": 2.0},
    {"id": "EXPANSION", "name": "Multi-unit / branch expansion term loan", "type": "credit",
     "provider_type": "Bank / development finance institution", "stages": [5],
     "fits": ["expansion_ready", "limited_market_access"], "min_credit_readiness": 70,
     "indicative_cost": 0.085, "size_multiple": 4.0},
    {"id": "POS_BUNDLE", "name": "Partner POS + inventory tool bundle (subsidised, financing-eligible)",
     "type": "non-credit", "provider_type": "Ecosystem software partner", "stages": [2, 3, 4, 5],
     "fits": ["manual_processes", "low_digital_adoption"], "min_credit_readiness": 0,
     "indicative_cost": 0.0, "size_multiple": 0},
    {"id": "MARKET_LINK", "name": "E-commerce & delivery partner onboarding", "type": "non-credit",
     "provider_type": "Ecosystem partner", "stages": [2, 3, 4], "fits": ["limited_market_access"],
     "min_credit_readiness": 0, "indicative_cost": 0.0, "size_multiple": 0},
    {"id": "SUCCESSION", "name": "Succession planning & successor onboarding package", "type": "non-credit",
     "provider_type": "Bank relationship team + advisory partner", "stages": [5, 6],
     "fits": ["succession_risk"], "min_credit_readiness": 0, "indicative_cost": 0.0, "size_multiple": 0},
]


def match(merchant, assessment: dict, as_of: date, top_n: int = 5) -> dict:
    stage = assessment["stage"]
    cr = assessment["scores"]["credit_readiness"]
    constraints = {c["constraint"]: c for c in assessment["constraints"]}
    monthly = assessment["signals"]["monthly_sales"]
    rbf_ok = rbf.eligibility(merchant, as_of)
    ranked, excluded = [], []
    for p in CATALOG:
        why_not = []
        if stage not in p["stages"]:
            why_not.append(f"designed for stages {p['stages']}, merchant is stage {stage}")
        if cr < p["min_credit_readiness"]:
            why_not.append(f"credit readiness {cr:.0f} below {p['min_credit_readiness']}")
        req = p.get("requires")
        if req == "rbf_eligible" and not rbf_ok["eligible"]:
            why_not.extend(rbf_ok["reasons"])
        if req == "confirmed_orders" and merchant.confirmed_orders_value <= 0:
            why_not.append("no confirmed purchase orders on record")
        if req == "receivables" and not any(not r["paid"] for r in merchant.receivables):
            why_not.append("no open customer invoices")
        if why_not:
            excluded.append({"id": p["id"], "name": p["name"], "why_not_yet": why_not})
            continue
        hits = [c for c in p["fits"] if c in constraints]
        stage_fit = 100  # in-range (hard filter above); out-of-range products are excluded
        constraint_fit = min(100, sum(100 if constraints[c]["priority"] == 1 else 70 if constraints[c]["priority"] == 2 else 40
                                      for c in hits)) if hits else 10
        readiness = min(100, 60 + (cr - p["min_credit_readiness"]))
        size = (rbf.limits(merchant, as_of)["max_advance"] if p["id"] == "RBF"
                else monthly * p["size_multiple"])
        monthly_cost = size * p["indicative_cost"] / 12
        afford = 100 if p["type"] == "non-credit" else max(0, 100 - (monthly_cost / monthly * 100) * 20) if monthly else 0
        score = round(0.45 * constraint_fit + 0.25 * stage_fit + 0.15 * readiness + 0.15 * afford, 1)
        ranked.append({
            "id": p["id"], "name": p["name"], "type": p["type"], "provider_type": p["provider_type"],
            "match_score": score, "addresses": hits,
            "indicative_size": round(size, -2) if size else None,
            "indicative_annual_cost": p["indicative_cost"] or None,
            "rationale": (f"Stage {stage} fit; addresses {', '.join(h.replace('_', ' ') for h in hits)}." if hits
                          else f"Stage {stage} fit; general support."),
            "components": {"stage_fit": stage_fit, "constraint_fit": constraint_fit,
                           "readiness": round(readiness, 1), "affordability": round(afford, 1)},
        })
    ranked.sort(key=lambda r: r["match_score"], reverse=True)
    return {"currency": merchant.currency, "stage": stage, "recommendations": ranked[:top_n],
            "not_yet_eligible": excluded,
            "disclaimer": "Recommendations are indicative. Final eligibility and pricing are decided by lenders."}
