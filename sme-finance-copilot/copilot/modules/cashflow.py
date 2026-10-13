"""
Cash-flow management with alerts (EQUIP – Business Wallet discipline).

Forecasting method (transparent, explainable – no black box):
  inflow_d  = average inflow on the same weekday over the last 8 weeks
  outflow_d = average variable outflow on the same weekday over the last 8 weeks
              + scheduled payables and loan instalments falling on day d
              + expected receivable collections on their due date
                (overdue receivables are excluded = conservative case)
  balance_d = balance_{d-1} + inflow_d - outflow_d
Alerts are rule-based and each maps to a framework intervention.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from copilot import config

C = config.CASHFLOW


def _weekday_profile(rows: list, as_of: date, days: int, cats: set | None = None) -> list[float]:
    start = as_of - timedelta(days=days - 1)
    per_day = defaultdict(float)
    for r in rows:
        d = date.fromisoformat(r["date"])
        if start <= d <= as_of and (cats is None or r.get("category") in cats):
            per_day[d] += r["amount"]
    sums, counts = [0.0] * 7, [0] * 7
    for i in range(days):
        d = start + timedelta(days=i)
        sums[d.weekday()] += per_day[d]
        counts[d.weekday()] += 1
    return [s / c if c else 0 for s, c in zip(sums, counts)]


def forecast(merchant, as_of: date, days: int | None = None, include_overdue: bool = False) -> dict:
    days = days or C["forecast_days"]
    inflow_prof = _weekday_profile(merchant.transactions, as_of, C["lookback_days"])
    out_prof = _weekday_profile(merchant.expenses, as_of, C["lookback_days"],
                                {"supplies", "operating", "household_draw"})
    sched_out, sched_in = defaultdict(float), defaultdict(float)
    for p in merchant.payables:
        sched_out[date.fromisoformat(p["due"])] += p["amount"]
    for r in merchant.receivables:
        if r["paid"]:
            continue
        due = date.fromisoformat(r["due"])
        if due < as_of and not include_overdue:
            continue
        sched_in[max(due, as_of + timedelta(days=1))] += r["amount"]

    bal, path, runway = merchant.wallet_balance, [], None
    for i in range(1, days + 1):
        d = as_of + timedelta(days=i)
        loan = merchant.monthly_debt_service if d.day == 15 else 0
        inflow = inflow_prof[d.weekday()] + sched_in[d]
        outflow = out_prof[d.weekday()] + sched_out[d] + loan
        bal += inflow - outflow
        path.append({"date": d.isoformat(), "inflow": round(inflow, 2),
                     "outflow": round(outflow, 2), "balance": round(bal, 2)})
        if runway is None and bal < 0:
            runway = i
    avg_out = sum(out_prof) / 7 + merchant.monthly_debt_service / 30
    return {"currency": merchant.currency, "opening_balance": merchant.wallet_balance,
            "days": days, "path": path,
            "min_balance": round(min(p["balance"] for p in path), 2),
            "closing_balance": path[-1]["balance"],
            "runway_days": runway,   # None => stays positive through the horizon
            "buffer_days": round(merchant.wallet_balance / avg_out, 1) if avg_out else None,
            "method": "weekday-seasonal moving average (8 weeks) + scheduled items"}


def _sum_window(rows, start, end, pred=lambda r: True):
    return sum(r["amount"] for r in rows if start <= date.fromisoformat(r["date"]) <= end and pred(r))


def alerts(merchant, as_of: date, fc: dict | None = None) -> list[dict]:
    fc = fc or forecast(merchant, as_of)
    out = []

    def add(sev, code, msg, action, intervention):
        out.append({"severity": sev, "code": code, "message": msg,
                    "recommended_action": action, "framework_intervention": intervention})

    cur = merchant.currency
    if fc["runway_days"] is not None and fc["runway_days"] <= C["runway_critical_days"]:
        add("critical", "RUNWAY_CRITICAL",
            f"Projected cash runs out in {fc['runway_days']} days.",
            "Delay non-essential purchases, collect overdue invoices, and consider short-term working capital.",
            "Business Wallet / Revenue-Based Financing")
    elif fc["runway_days"] is not None and fc["runway_days"] <= C["runway_warning_days"]:
        add("warning", "RUNWAY_LOW", f"Projected cash turns negative in {fc['runway_days']} days.",
            "Review upcoming supplier bills and plan a cash buffer.", "Business Wallet / Revenue-Based Financing")
    elif fc["runway_days"] is not None:
        add("info", "RUNWAY_WATCH",
            f"Balance dips below zero on day {fc['runway_days']} of the 30-day forecast.",
            "Plan ahead for this dip.", "Business Wallet")
    if fc["buffer_days"] is not None and fc["buffer_days"] < C["buffer_days_target"] and fc["runway_days"] is None:
        add("info", "BUFFER_THIN",
            f"Cash covers only {fc['buffer_days']} days of spending (target {C['buffer_days_target']}).",
            "Set aside a small share of daily digital sales into a buffer pocket.", "Business Wallet")

    # sales drop week-on-week
    last7 = _sum_window(merchant.transactions, as_of - timedelta(days=6), as_of)
    prev7 = _sum_window(merchant.transactions, as_of - timedelta(days=13), as_of - timedelta(days=7))
    if prev7 and (prev7 - last7) / prev7 >= C["sales_drop_warning"]:
        add("warning", "SALES_DROP", f"Sales fell {(prev7 - last7) / prev7:.0%} versus the prior week.",
            "Check stock-outs, opening days, or channel issues.", "Merchant Intelligence Dashboard")

    # receivables
    overdue = [r for r in merchant.receivables if not r["paid"] and date.fromisoformat(r["due"]) < as_of]
    if overdue:
        amt = sum(r["amount"] for r in overdue)
        aged = [r for r in overdue if (as_of - date.fromisoformat(r["due"])).days > C["receivable_aged_days"]]
        add("warning" if aged else "info", "RECEIVABLES_OVERDUE",
            f"{len(overdue)} customer invoice(s) overdue totalling {amt:,.0f} {cur}"
            + (f"; {len(aged)} more than {C['receivable_aged_days']} days." if aged else "."),
            "Send Pay Link reminders so customers can pay instantly; this is a timing gap, not a default.",
            "Pay Link / Revenue-Based Financing")

    # upcoming obligations within 7 days vs. balance
    due7 = sum(p["amount"] for p in merchant.payables
               if as_of < date.fromisoformat(p["due"]) <= as_of + timedelta(days=7))
    if due7 and due7 > merchant.wallet_balance * 0.5:
        add("warning", "OBLIGATIONS_DUE",
            f"{due7:,.0f} {cur} of supplier bills due within 7 days (over half of current balance).",
            "Schedule payments after expected inflows or negotiate terms.", "Business Wallet")

    # household / business mixing
    inflow30 = _sum_window(merchant.transactions, as_of - timedelta(days=29), as_of)
    draws30 = _sum_window(merchant.expenses, as_of - timedelta(days=29), as_of,
                          lambda r: r["category"] == "household_draw")
    if inflow30 and draws30 / inflow30 > C["household_withdrawal_warning"]:
        add("warning", "FUNDS_MIXING",
            f"Personal/household withdrawals equal {draws30 / inflow30:.0%} of sales this month.",
            "Separate business and household money and pay yourself a fixed allowance.",
            "Business Wallet + financial literacy module")

    # channel concentration / cash dependence
    rev = defaultdict(float)
    for t in merchant.transactions:
        if as_of - timedelta(days=29) <= date.fromisoformat(t["date"]) <= as_of:
            rev[t["channel"]] += t["amount"]
    total = sum(rev.values()) or 1
    if rev.get("cash", 0) / total > C["concentration_warning"]:
        add("info", "CASH_DEPENDENCE",
            f"{rev['cash'] / total:.0%} of sales are cash, which lenders cannot see.",
            "Start accepting QR Pay; digital sales build the record needed for collateral-free financing.",
            "QR Pay onboarding + digital literacy")
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(out, key=lambda a: order[a["severity"]])
