"""
Graduation Pipeline engine: Identify -> Profile -> Place (-> Activate -> Measure).

Scores the seven framework dimensions (0-100) from observable signals, places
the MSME in one of six stages, diagnoses binding constraints and maps them to
EQUIP / EXPAND / ENTICE / SUSTAIN interventions (Constraint-Intervention Map).

Every score carries its contributing factors so the result is explainable to
the owner and auditable by a coach or lender.  Behavioural signals add context
but never replace traditional underwriting (framework principle).
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from statistics import mean, pstdev

from copilot import config
from copilot.modules import cashflow, dashboard


def _clip(x: float) -> float:
    return max(0.0, min(100.0, x))


def _daily_totals(merchant, as_of: date, days: int) -> list[float]:
    start = as_of - timedelta(days=days - 1)
    tot = {start + timedelta(days=i): 0.0 for i in range(days)}
    for t in merchant.transactions:
        d = date.fromisoformat(t["date"])
        if d in tot:
            tot[d] += t["amount"]
    return list(tot.values())


def signals(merchant, as_of: date) -> dict:
    d90 = _daily_totals(merchant, as_of, 90)
    m_sales = sum(d90) / 3
    first30, last30 = sum(d90[:30]), sum(d90[-30:])
    cap = dashboard.capture_metrics(dashboard.filter_period(merchant.transactions,
                                                            as_of - timedelta(days=89), as_of))
    fc = cashflow.forecast(merchant, as_of)
    draws = sum(e["amount"] for e in merchant.expenses if e["category"] == "household_draw"
                and as_of - timedelta(days=89) <= date.fromisoformat(e["date"]) <= as_of)
    first_txn = min(date.fromisoformat(t["date"]) for t in merchant.transactions)
    return {
        "monthly_sales": m_sales,
        "sales_cv": (pstdev(d90) / mean(d90)) if mean(d90) else 9,
        "sales_growth_90d": (last30 - first30) / first30 if first30 else 0,
        "zero_sales_days": sum(1 for x in d90 if x == 0),
        "digital_share": cap["digital_share"], "ecosystem_share": cap["ecosystem_share"],
        "buffer_days": fc["buffer_days"] or 0, "runway_days": fc["runway_days"],
        "household_draw_ratio": draws / sum(d90) if sum(d90) else 1,
        "debt_service_ratio": merchant.monthly_debt_service / m_sales if m_sales else 1,
        "history_days": (as_of - first_txn).days + 1,
        "channels_used": len({t["channel"] for t in merchant.transactions
                              if date.fromisoformat(t["date"]) > as_of - timedelta(days=30)}),
        "overdue_receivables": sum(1 for r in merchant.receivables
                                   if not r["paid"] and date.fromisoformat(r["due"]) < as_of),
        "overdue_amount": sum(r["amount"] for r in merchant.receivables
                              if not r["paid"] and date.fromisoformat(r["due"]) < as_of),
    }


def score_dimensions(merchant, s: dict) -> dict:
    m = merchant
    f = {}
    # 1 Financial health
    f["financial_health"] = {"gross_margin": min(m.gross_margin / 0.45, 1) * 25,
                             "sales_stability": _clip(100 - s["sales_cv"] * 150) * 0.25,
                             "cash_buffer": min(s["buffer_days"] / 30, 1) * 20,
                             "fund_separation": max(0, 1 - s["household_draw_ratio"] / 0.3) * 15,
                             "debt_load": max(0, 1 - s["debt_service_ratio"] / 0.4) * 15}
    # 2 Formalization
    f["formalization"] = {"business_registered": 35 if m.business_registered else 0,
                          "tax_registered": 25 if m.tax_registered else 0,
                          "bookkeeping": {"none": 0, "manual": 15, "digital": 30}[m.bookkeeping],
                          "separate_account": 10 if m.separate_business_account else 0}
    # 3 Digital maturity
    f["digital_maturity"] = {"digital_share": s["digital_share"] * 50,
                             "ecosystem_share": s["ecosystem_share"] * 25,
                             "pos_adopted": 15 if m.pos_adopted else 0,
                             "device_access": 10 if m.has_smartphone else 0}
    # 4 Market access
    f["market_access"] = {"online_marketplaces": min(m.online_marketplaces, 3) * 12,
                          "payment_channels": min(s["channels_used"], 6) / 6 * 20,
                          "locations": min(m.units, 4) / 4 * 15,
                          "b2b_customers": 10 if m.receivables else 0,
                          "growth": _clip(50 + s["sales_growth_90d"] * 250) * 0.19}
    # 5 Operational capacity
    f["operational_capacity"] = {"team_size": min(math.log1p(m.employees) / math.log1p(30), 1) * 30,
                                 "systems": (15 if m.pos_adopted else 0) + (15 if m.bookkeeping == "digital" else 0),
                                 "multi_unit": min(m.units - 1, 3) / 3 * 20,
                                 "capacity_headroom": max(0, 1 - max(m.capacity_utilization - 0.6, 0) / 0.4) * 20}
    # 6 Credit readiness
    f["credit_readiness"] = {"on_time_repayment": _clip((m.repayment_on_time_ratio - 0.6) / 0.4 * 100) * 0.35,
                             "lateness": max(0, 1 - m.max_days_late / 30) * 15,
                             "credit_history": min(m.prior_loans, 4) / 4 * 15,
                             "verified_data": min(s["digital_share"] / 0.6, 1) * 20,
                             "debt_capacity": max(0, 1 - s["debt_service_ratio"] / 0.4) * 15}
    # 7 Sustainability
    f["sustainability"] = {"years_operating": min(m.years_operating / 10, 1) * 35,
                           "trajectory": _clip(50 + s["sales_growth_90d"] * 250) * 0.25,
                           "continuity": (20 if m.succession_planned else 0 if m.owner_transition_expected else 15),
                           "consistency": max(0, 1 - s["zero_sales_days"] / 20) * 20}
    scores = {k: round(_clip(sum(v.values())), 1) for k, v in f.items()}
    return {"scores": scores, "factors": {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in f.items()}}


def place_stage(merchant, scores: dict) -> dict:
    comp = round(sum(scores[k] * w for k, w in config.DIMENSION_WEIGHTS.items()), 1)
    stage = 1
    for lb, st in config.STAGE_THRESHOLDS:
        if comp >= lb:
            stage = st
    capped_by = []
    while stage in config.STAGE_GATES:
        unmet = [d for d, floor in config.STAGE_GATES[stage].items() if scores[d] < floor]
        if not unmet:
            break
        capped_by.append({"stage": stage, "unmet_gates": unmet})
        stage -= 1
    if merchant.owner_transition_expected and stage >= 4:
        stage = 6
    return {"stage": stage, "stage_name": config.STAGES[stage], "composite_score": comp,
            "gate_adjustments": capped_by}


CONSTRAINT_MAP = {  # Appendix H constraint -> intervention (generic names)
    "cash_flow": ("EQUIP", "Business Wallet + Revenue-Based Financing for timing gaps"),
    "low_digital_adoption": ("EQUIP/ENTICE", "QR Pay onboarding, digital-literacy module, Entry Milestone incentives"),
    "production_bottleneck": ("EXPAND", "Equipment financing / lease-to-own"),
    "confirmed_orders_no_capital": ("EQUIP", "Purchase-order financing"),
    "manual_processes": ("EXPAND", "POS, digital bookkeeping and inventory tools via partner providers"),
    "limited_management_capability": ("EMPOWER", "Training, business advisory and mentoring"),
    "limited_market_access": ("EXPAND", "Market linkage, e-commerce and delivery partnerships"),
    "succession_risk": ("SUSTAIN", "Succession planning, successor onboarding, relationship transfer"),
    "expansion_ready": ("EXPAND", "Multi-unit / branch expansion financing"),
}


def identify_constraints(merchant, s: dict, scores: dict) -> list[dict]:
    m, out = merchant, []

    def add(code, evidence, priority):
        lever, iv = CONSTRAINT_MAP[code]
        out.append({"constraint": code, "lever": lever, "intervention": iv,
                    "evidence": evidence, "priority": priority})

    if m.capacity_utilization >= 0.9 and m.unmet_demand:
        add("production_bottleneck", f"Capacity {m.capacity_utilization:.0%} used with unmet demand.", 1)
    if m.confirmed_orders_value > 0 and m.confirmed_orders_value > m.wallet_balance:
        add("confirmed_orders_no_capital",
            f"Confirmed orders of {m.confirmed_orders_value:,.0f} {m.currency} exceed cash on hand.", 1)
    material_overdue = s["overdue_amount"] > 0.10 * s["monthly_sales"]
    if s["runway_days"] is not None or s["buffer_days"] < config.CASHFLOW["buffer_days_target"] \
            or material_overdue:
        ev = []
        if s["runway_days"] is not None:
            ev.append(f"cash projected negative in {s['runway_days']} days")
        if s["buffer_days"] < config.CASHFLOW["buffer_days_target"]:
            ev.append(f"buffer of {s['buffer_days']:.0f} days")
        if material_overdue:
            ev.append(f"{s['overdue_receivables']} overdue customer invoices")
        add("cash_flow", "; ".join(ev).capitalize() + ".", 2)
    if s["digital_share"] < 0.4:
        add("low_digital_adoption", f"Only {s['digital_share']:.0%} of sales are digital.", 2)
    if m.bookkeeping != "digital" or not m.pos_adopted:
        add("manual_processes", f"Bookkeeping: {m.bookkeeping}; POS: {'yes' if m.pos_adopted else 'no'}.", 3)
    if scores["formalization"] < 40 or scores["financial_health"] < 40:
        add("limited_management_capability",
            f"Formalization {scores['formalization']:.0f}/100, financial health {scores['financial_health']:.0f}/100.", 3)
    if scores["market_access"] < 45:
        add("limited_market_access", f"Market access {scores['market_access']:.0f}/100.", 3)
    if m.owner_transition_expected and not m.succession_planned:
        add("succession_risk", "Owner transition expected without a documented succession plan.", 1)
    if m.units >= 3 and m.unmet_demand and scores["financial_health"] >= 65:
        add("expansion_ready", f"{m.units} units operating with unmet demand and strong finances.", 1)
    return sorted(out, key=lambda c: c["priority"])


GRADUATION_TRIGGERS = {
    1: "Stable cash flow, basic financial records, consistent repayment, initial digital usage",
    2: "Consistent savings and cash flow, separated finances, regular digital transactions",
    3: "Verified sales growth, increased capacity, stronger digital footprint, improved credit readiness",
    4: "Sustained growth, diversified channels, higher transaction capture, stronger capacity utilisation",
    5: "Sustainable multi-unit operations, stronger management systems, succession readiness",
    6: "Successful successor onboarding and continued ecosystem participation",
}


def next_stage_gap(stage: int, scores: dict, composite: float) -> dict | None:
    if stage >= 5:
        return None
    target = stage + 1
    lb = dict((st, lb) for lb, st in config.STAGE_THRESHOLDS)[target]
    gates = config.STAGE_GATES.get(target, {})
    return {"target_stage": target, "target_name": config.STAGES[target],
            "composite_needed": lb, "composite_gap": round(max(0, lb - composite), 1),
            "dimension_gaps": {d: round(f - scores[d], 1) for d, f in gates.items() if scores[d] < f}}


def assess(merchant, as_of: date) -> dict:
    s = signals(merchant, as_of)
    sd = score_dimensions(merchant, s)
    placement = place_stage(merchant, sd["scores"])
    constraints = identify_constraints(merchant, s, sd["scores"])
    return {"merchant_id": merchant.merchant_id, "as_of": as_of.isoformat(),
            "signals": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()},
            **sd, **placement,
            "graduation_trigger": GRADUATION_TRIGGERS[placement["stage"]],
            "next_stage": next_stage_gap(placement["stage"], sd["scores"], placement["composite_score"]),
            "constraints": constraints,
            "note": "Behavioural signals add context to, but never replace, lender underwriting."}
