"""
Revenue-Based Financing calculator (EQUIP).

Generalises the reference "Capital Flex" calculator:
  * fee steps down as the advance grows (14% / 12% / 10%)
  * remittance rate = 6% + (advance / max advance) * 12%
but sizes everything relative to the merchant's *verified* (digitally captured)
sales so it works in any ASEAN currency, and replays the merchant's real daily
sales history to estimate the payoff period instead of using a fixed example.

Repayments are deducted only from sales captured on ecosystem rails (QR Pay,
Tap Pay, Pay Link) because those are the only sales the lender can see and
auto-deduct.  On a zero-sales day the repayment is zero.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from copilot import config

R = config.RBF


def _daily_series(merchant, as_of: date, days: int, ecosystem_only: bool) -> list[float]:
    start = as_of - timedelta(days=days - 1)
    by_day = defaultdict(float)
    for t in merchant.transactions:
        d = date.fromisoformat(t["date"])
        if start <= d <= as_of and (not ecosystem_only or config.CHANNELS[t["channel"]]["ecosystem"]):
            by_day[d] += t["amount"]
    return [by_day[start + timedelta(days=i)] for i in range(days)]


def verified_monthly_sales(merchant, as_of: date, days: int = 90) -> dict:
    eco = _daily_series(merchant, as_of, days, True)
    allv = _daily_series(merchant, as_of, days, False)
    digital = sum(t["amount"] for t in merchant.transactions
                  if (as_of - timedelta(days=days - 1)) <= date.fromisoformat(t["date"]) <= as_of
                  and config.CHANNELS[t["channel"]]["digital"])
    total = sum(allv) or 1
    if total>0 and not (0<=digital/total<=1 and 0<=sum(eco)/total<=1):
        raise ValueError("The net-sales channel mix cannot support a bounded verified-sales share; reconcile the records before financing analysis")
    return {"ecosystem_monthly": sum(eco) / days * 30,
            "total_monthly": sum(allv) / days * 30,
            "verified_share": digital / total,
            "ecosystem_share": sum(eco) / total}


def limits(merchant, as_of: date) -> dict:
    v = verified_monthly_sales(merchant, as_of)
    base = max(0.0, v["ecosystem_monthly"])
    return {"min_advance": round(base * R["min_advance_multiple"], -2),
            "max_advance": round(base * R["max_advance_multiple"], -2),
            "basis_monthly_ecosystem_sales": round(base, 2), **{k: round(x, 4) for k, x in v.items()
                                                                 if k.endswith("share")}}


def eligibility(merchant, as_of: date) -> dict:
    reasons = []
    if not merchant.transactions:
        return {"eligible":False,"reasons":["No recorded transaction history is available."],"history_days":0}
    first = min(date.fromisoformat(t["date"]) for t in merchant.transactions)
    history = (as_of - first).days + 1
    v = verified_monthly_sales(merchant, as_of)
    if sum(_daily_series(merchant,as_of,90,False))<=0:
        reasons.append("Positive recorded net sales are required for a financing simulation.")
    if history < R["min_history_days"]:
        reasons.append(f"Needs at least {R['min_history_days']} days of transaction history (has {history}).")
    if v["verified_share"] < R["verified_share_floor"]:
        reasons.append(f"Only {v['verified_share']:.0%} of sales are digitally verified; "
                       f"at least {R['verified_share_floor']:.0%} is required so repayments can track sales.")
    if merchant.repayment_on_time_ratio < 0.85:
        reasons.append("Recent repayment record needs improvement (below 85% on-time).")
    return {"eligible": not reasons, "reasons": reasons, "history_days": history}


def quote(merchant, as_of: date, advance: float, incentive_tier: int = 0) -> dict:
    lim = limits(merchant, as_of)
    if advance <= 0:
        raise ValueError("advance must be positive")
    if advance > lim["max_advance"]:
        raise ValueError(f"advance exceeds maximum of {lim['max_advance']:,.0f} {merchant.currency}")
    base = lim["basis_monthly_ecosystem_sales"] or 1
    multiple = advance / base
    fee_rate = next(rate for upper, rate in R["fee_tiers"] if multiple <= upper)
    fee_rate = max(0.0, fee_rate - R["incentive_fee_discount"].get(incentive_tier, 0))
    remit = min(R["remit_rate_floor"] + (advance / max(lim["max_advance"], 1)) * R["remit_rate_span"],
                R["remit_rate_cap"])
    fee = round(advance * fee_rate, 2)
    total = advance + fee

    # replay real daily ecosystem sales (last 90 days, cycled) to estimate payoff
    hist = _daily_series(merchant, as_of, 90, True)
    remaining, day, schedule = total, 0, []
    while remaining > 0.005 and day < R["max_term_days"] * 2:
        sales = hist[day % len(hist)]
        pay = min(max(0.0, round(sales * remit, 2)), remaining)
        remaining -= pay
        if day < 14:
            schedule.append({"day": day + 1, "ecosystem_sales": round(sales, 2), "repayment": round(pay, 2)})
        day += 1
    payoff_days = day if remaining <= 0.005 else None

    nonzero = [s for s in hist if s > 0]
    examples = {
        "strong_day": {"sales": round(max(hist), 2), "repayment": round(max(hist) * remit, 2)},
        "typical_day": {"sales": round(mean(nonzero), 2) if nonzero else 0,
                        "repayment": round(mean(nonzero) * remit, 2) if nonzero else 0},
        "slow_day": {"sales": round(min(nonzero), 2) if nonzero else 0,
                     "repayment": round(min(nonzero) * remit, 2) if nonzero else 0},
        "no_sales_day": {"sales": 0, "repayment": 0},
    }
    # comparison: fixed daily instalment over the same term
    fixed_daily = total / payoff_days if payoff_days else None
    stress_days = sum(1 for s in hist if fixed_daily and s * merchant.gross_margin < fixed_daily)

    warnings = []
    if payoff_days is None or payoff_days > R["max_term_days"]:
        warnings.append("Estimated payoff exceeds the maximum term; choose a smaller advance.")
    elif payoff_days > R["target_term_days"]:
        warnings.append("Payoff exceeds 12 months at current sales; consider a smaller advance.")
    effective_annualised = (fee_rate / (payoff_days / 365)) if payoff_days else None

    return {
        "currency": merchant.currency,
        "advance": round(advance, 2), "fee_rate": round(fee_rate, 4), "fee": fee,
        "total_repayable": round(total, 2),
        "remittance_rate": round(remit, 4),
        "remittance_basis": "daily sales captured on QR Pay / Tap Pay / Pay Link",
        "estimated_payoff_days": payoff_days,
        "effective_annualised_cost": None if effective_annualised is None else round(effective_annualised, 4),
        "first_14_days": schedule, "examples": examples,
        "fixed_instalment_comparison": {
            "equivalent_fixed_daily_payment": None if fixed_daily is None else round(fixed_daily, 2),
            "days_in_last_90_where_fixed_payment_exceeds_daily_gross_profit": stress_days,
        },
        "incentive_tier_applied": incentive_tier,
        "limits": lim, "warnings": warnings,
        "disclaimer": "Indicative simulation only. Not a credit offer or approval; final terms are set by the lender.",
    }


def recommend_advance(merchant, as_of: date, purpose_amount: float | None = None) -> float:
    """Largest advance whose estimated payoff stays within the target term."""
    lim = limits(merchant, as_of)
    hi = lim["max_advance"] if purpose_amount is None else min(purpose_amount, lim["max_advance"])
    lo = max(lim["min_advance"], 1)
    if hi <= lo:
        return round(hi, -2)
    best = lo
    for _ in range(30):
        mid = (lo + hi) / 2
        q = quote(merchant, as_of, mid)
        if q["estimated_payoff_days"] and q["estimated_payoff_days"] <= R["target_term_days"]:
            best, lo = mid, mid
        else:
            hi = mid
    return round(best, -2)
