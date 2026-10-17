"""
Merchant Intelligence Dashboard (EQUIP).

Re-implements the reference dashboard's four views (volume mix, revenue split,
volume trend, revenue trend) on real (synthetic) ledger data instead of random
numbers, and adds the behavioural signals the framework says credit models are
missing: digital-capture ratio, ecosystem share, MoM digital growth, incentive
tier, and a timing-delay vs. default distinction.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from copilot import config


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _bucket_key(d: date, granularity: str) -> str:
    if granularity == "daily":
        return d.isoformat()
    if granularity == "weekly":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if granularity == "monthly":
        return f"{d.year}-{d.month:02d}"
    if granularity == "quarterly":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    if granularity == "yearly":
        return str(d.year)
    raise ValueError("granularity must be daily|weekly|monthly|quarterly|yearly")


def filter_period(txns: list, start: date, end: date) -> list:
    if start > end:
        raise ValueError("start date must be on or before end date")
    return [t for t in txns if start <= _d(t["date"]) <= end]


def channel_mix(txns: list) -> dict:
    vol, rev = defaultdict(int), defaultdict(float)
    for t in txns:
        vol[t["channel"]] += t["count"]
        rev[t["channel"]] += t["amount"]
    tv, tr = sum(vol.values()) or 1, sum(rev.values()) or 1
    return {
        "total_transactions": sum(vol.values()),
        "gross_revenue": round(sum(rev.values()), 2),
        "by_channel": {
            ch: {"label": config.CHANNELS[ch]["label"],
                 "transactions": vol[ch], "volume_share": round(vol[ch] / tv, 4),
                 "revenue": round(rev[ch], 2), "revenue_share": round(rev[ch] / tr, 4)}
            for ch in sorted(rev, key=rev.get, reverse=True)
        },
    }


def trend(txns: list, granularity: str = "monthly", expenses: list | None = None) -> list:
    agg = defaultdict(lambda: {"transactions": 0, "revenue": 0.0, "expenses": 0.0})
    for t in txns:
        k = _bucket_key(_d(t["date"]), granularity)
        agg[k]["transactions"] += t["count"]
        agg[k]["revenue"] += t["amount"]
    for e in expenses or []:
        agg[_bucket_key(_d(e["date"]), granularity)]["expenses"] += e["amount"]
    return [{"period": k, "transactions": v["transactions"], "revenue": round(v["revenue"], 2), "expenses": round(v["expenses"], 2)}
            for k, v in sorted(agg.items())]


def expense_split(expenses: list) -> list:
    """Recorded expenses by category for the period, largest first."""
    totals = defaultdict(float)
    for e in expenses:
        totals[e.get("category") or "other"] += e["amount"]
    total = sum(totals.values())
    return [{"category": k, "amount": round(v, 2), "share": round(v / total, 4) if total else 0.0}
            for k, v in sorted(totals.items(), key=lambda kv: -kv[1])]


def period_length(start: date, end: date) -> dict:
    """Exact period length for averages: inclusive days, days / 7 weeks, and calendar months
    where a partial month counts by the share of its days covered (Oct 1-16 = 16/31)."""
    import calendar
    days = (end - start).days + 1
    months, cursor = 0.0, start
    while cursor <= end:
        last = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        months += ((min(last, end) - cursor).days + 1) / last.day
        cursor = last + timedelta(days=1)
    return {"days": days, "weeks": round(days / 7, 4), "months": round(months, 4)}


def capture_metrics(txns: list) -> dict:
    total = sum(t["amount"] for t in txns) or 1
    digital = sum(t["amount"] for t in txns if config.CHANNELS[t["channel"]]["digital"])
    eco = sum(t["amount"] for t in txns if config.CHANNELS[t["channel"]]["ecosystem"])
    return {"digital_share": round(digital / total, 4),
            "ecosystem_share": round(eco / total, 4),
            "cash_share": round(1 - digital / total, 4)}


def _month_window(as_of: date, months_back: int) -> tuple[date, date]:
    """Calendar month that is `months_back` before the month of as_of (0 = current)."""
    y, m = as_of.year, as_of.month - months_back
    while m <= 0:
        m += 12
        y -= 1
    start = date(y, m, 1)
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return start, nxt - timedelta(days=1)


def incentive_status(txns: list, as_of: date) -> dict:
    """ENTICE: MoM growth in sales routed through ecosystem digital channels."""
    cs, ce = _month_window(as_of, 0)
    ps, pe = _month_window(as_of, 1)
    eco = lambda s, e: sum(t["amount"] for t in txns
                           if s <= _d(t["date"]) <= e and config.CHANNELS[t["channel"]]["ecosystem"])
    tot = lambda s, e: sum(t["amount"] for t in txns if s <= _d(t["date"]) <= e)
    cur, prev = eco(cs, min(ce, as_of)), eco(ps, pe)
    prev_total = tot(ps, pe) or 1
    # normalise partial current month to a full-month run-rate
    days_elapsed = (min(ce, as_of) - cs).days + 1
    days_in_month = (ce - cs).days + 1
    cur_run_rate = cur / days_elapsed * days_in_month
    note = None
    if prev / prev_total < config.INCENTIVE_MIN_BASE_SALES_SHARE:
        growth = None
        note = ("Previous-month ecosystem base is below the minimum share; "
                "milestones start once a stable base is established (anti-gaming rule).")
    else:
        growth = (cur_run_rate - prev) / prev if prev else None
    tier = None
    if growth is not None:
        for t in config.INCENTIVE_TIERS:
            if growth >= t["min_mom_growth"]:
                tier = t
                break
    nxt = None
    if growth is not None:
        for t in sorted(config.INCENTIVE_TIERS, key=lambda x: x["min_mom_growth"]):
            if growth < t["min_mom_growth"]:
                needed = prev * (1 + t["min_mom_growth"]) - cur_run_rate
                nxt = {"tier": t["tier"], "name": t["name"],
                       "additional_monthly_ecosystem_sales_needed": round(max(needed, 0), 2)}
                break
    return {
        "current_month": cs.strftime("%Y-%m"), "previous_month": ps.strftime("%Y-%m"),
        "ecosystem_sales_current_run_rate": round(cur_run_rate, 2),
        "ecosystem_sales_previous": round(prev, 2),
        "mom_growth": None if growth is None else round(growth, 4),
        "tier": tier["tier"] if tier else 0,
        "tier_name": tier["name"] if tier else "No milestone yet",
        "reward": tier["reward"] if tier else None,
        "next_milestone": nxt, "note": note,
    }


def receivable_behaviour(merchant, as_of: date) -> dict:
    """Distinguish *customer* payment delays (timing gap) from *merchant* repayment risk."""
    overdue = [r for r in merchant.receivables if not r["paid"] and _d(r["due"]) < as_of]
    overdue_amt = sum(r["amount"] for r in overdue)
    timing_gap = bool(overdue) and merchant.repayment_on_time_ratio >= 0.95
    return {
        "open_receivables": round(sum(r["amount"] for r in merchant.receivables if not r["paid"]), 2),
        "overdue_receivables": round(overdue_amt, 2),
        "overdue_count": len(overdue),
        "merchant_repayment_on_time_ratio": merchant.repayment_on_time_ratio,
        "classification": ("timing_delay" if timing_gap else
                           "repayment_risk" if merchant.repayment_on_time_ratio < 0.85 else
                           "normal"),
        "explanation": ("Customers are paying late, but the merchant's own repayment record is strong: "
                        "treat as a working-capital timing gap, not a credit default signal."
                        if timing_gap else
                        "Merchant's own repayment record shows late payments; review before new credit."
                        if merchant.repayment_on_time_ratio < 0.85 else
                        "No material timing or repayment issues detected."),
    }


def build_dashboard(merchant, as_of: date, start: date | None = None,
                    end: date | None = None, granularity: str = "monthly") -> dict:
    end = end or as_of
    start = start or (end - timedelta(days=89))
    txns = filter_period(merchant.transactions, start, end)
    spent = filter_period(merchant.expenses, start, end)
    return {
        "merchant": {"id": merchant.merchant_id, "name": merchant.name,
                     "currency": merchant.currency, "country": merchant.country},
        "period": {"start": start.isoformat(), "end": end.isoformat(), "granularity": granularity},
        "mix": channel_mix(txns),
        "expenses": round(sum(e["amount"] for e in filter_period(merchant.expenses, start, end)), 2),
        "expense_transactions": len(filter_period(merchant.expenses, start, end)),
        "net_income": round(sum(t["amount"] for t in txns) - sum(e["amount"] for e in filter_period(merchant.expenses, start, end)), 2),
        "trend": trend(txns, granularity, spent),
        "expense_split": expense_split(spent),
        "period_length": period_length(start, end),
        "capture": capture_metrics(txns),
        "incentive": incentive_status(merchant.transactions, as_of),
        "receivables": receivable_behaviour(merchant, as_of),
    }
