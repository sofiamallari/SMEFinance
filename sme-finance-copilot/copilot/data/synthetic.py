"""
Deterministic synthetic data generator.

NO real or enterprise data is used anywhere in this project.  Six fictional
ASEAN merchant personas are generated to exercise every Graduation Pipeline
stage.  Seeds make every run reproducible so tests and execution logs match.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta

AS_OF = date(2026, 9, 30)   # fixed "today" for reproducible evidence
HISTORY_DAYS = 180

WEEKDAY_FACTOR = [0.85, 0.9, 0.95, 1.0, 1.15, 1.35, 1.1]  # Mon..Sun


@dataclass
class Merchant:
    merchant_id: str
    name: str
    sector: str
    country: str
    currency: str
    years_operating: float
    business_registered: bool
    tax_registered: bool
    bookkeeping: str                 # none | manual | digital
    separate_business_account: bool
    employees: int
    units: int
    pos_adopted: bool
    online_marketplaces: int
    capacity_utilization: float      # 0..1 (production / service capacity used)
    unmet_demand: bool
    confirmed_orders_value: float
    succession_planned: bool
    owner_transition_expected: bool
    has_smartphone: bool
    repayment_on_time_ratio: float   # historic loan repayments paid on time
    max_days_late: int
    prior_loans: int
    monthly_debt_service: float
    wallet_balance: float
    gross_margin: float
    transactions: list = field(default_factory=list)   # {date, channel, amount, count}
    expenses: list = field(default_factory=list)       # {date, category, amount}
    receivables: list = field(default_factory=list)    # {invoice_id, customer, amount, issued, due, paid}
    payables: list = field(default_factory=list)       # {bill_id, supplier, amount, due}

    def to_dict(self) -> dict:
        return asdict(self)


PERSONAS = [
    dict(merchant_id="M001", name="Lola Nena's Kakanin Stall", sector="Food stall", country="PH",
         currency="PHP", seed=11, base_daily=3_800, growth=0.000, years_operating=1.5,
         business_registered=False, tax_registered=False, bookkeeping="none",
         separate_business_account=False, employees=0, units=1, pos_adopted=False,
         online_marketplaces=0, capacity_utilization=0.45, unmet_demand=False,
         confirmed_orders_value=0, succession_planned=False, owner_transition_expected=False,
         has_smartphone=True, repayment_on_time_ratio=0.80, max_days_late=12, prior_loans=1,
         monthly_debt_service=4_000, wallet_balance=2_600, gross_margin=0.30,
         mix_start={"cash": 0.92, "external_wallet": 0.08},
         mix_end={"cash": 0.85, "external_wallet": 0.09, "qr_pay": 0.06},
         household_draw=0.32, n_receivables=0),
    dict(merchant_id="M006", name="Bayanihan Sari-Sari Store", sector="Neighbourhood retail", country="PH",
         currency="PHP", seed=66, base_daily=9_500, growth=0.0010, years_operating=3,
         business_registered=True, tax_registered=False, bookkeeping="manual",
         separate_business_account=False, employees=1, units=1, pos_adopted=False,
         online_marketplaces=0, capacity_utilization=0.65, unmet_demand=False,
         confirmed_orders_value=0, succession_planned=False, owner_transition_expected=False,
         has_smartphone=True, repayment_on_time_ratio=0.92, max_days_late=6, prior_loans=1,
         monthly_debt_service=6_000, wallet_balance=42_000, gross_margin=0.22,
         mix_start={"cash": 0.75, "external_wallet": 0.20, "qr_pay": 0.05},
         mix_end={"cash": 0.55, "external_wallet": 0.20, "qr_pay": 0.25},
         household_draw=0.15, n_receivables=0),
    dict(merchant_id="M002", name="Tani Coffee & Tofu House", sector="Food & beverage", country="ID",
         currency="IDR", seed=22, base_daily=1_900_000, growth=0.0025, years_operating=4,
         business_registered=True, tax_registered=False, bookkeeping="manual",
         separate_business_account=True, employees=3, units=1, pos_adopted=False,
         online_marketplaces=1, capacity_utilization=0.96, unmet_demand=True,
         confirmed_orders_value=0, succession_planned=False, owner_transition_expected=False,
         has_smartphone=True, repayment_on_time_ratio=0.97, max_days_late=3, prior_loans=2,
         monthly_debt_service=3_500_000, wallet_balance=21_000_000, gross_margin=0.42,
         mix_start={"cash": 0.55, "qr_pay": 0.15, "external_wallet": 0.20, "external_card": 0.10},
         mix_end={"cash": 0.30, "qr_pay": 0.32, "tap_pay": 0.10, "pay_link": 0.05,
                  "external_wallet": 0.15, "external_card": 0.08},
         household_draw=0.08, n_receivables=6, receivable_delay=True),
    dict(merchant_id="M003", name="Baan Rattan Crafts", sector="Handicraft manufacturing", country="TH",
         currency="THB", seed=33, base_daily=26_000, growth=0.0015, years_operating=7,
         business_registered=True, tax_registered=True, bookkeeping="digital",
         separate_business_account=True, employees=9, units=1, pos_adopted=True,
         online_marketplaces=2, capacity_utilization=0.82, unmet_demand=True,
         confirmed_orders_value=900_000, succession_planned=False, owner_transition_expected=False,
         has_smartphone=True, repayment_on_time_ratio=0.99, max_days_late=1, prior_loans=3,
         monthly_debt_service=45_000, wallet_balance=420_000, gross_margin=0.38,
         mix_start={"cash": 0.20, "qr_pay": 0.35, "pay_link": 0.15, "external_wallet": 0.20, "external_card": 0.10},
         mix_end={"cash": 0.12, "qr_pay": 0.40, "pay_link": 0.22, "tap_pay": 0.08,
                  "external_wallet": 0.12, "external_card": 0.06},
         household_draw=0.05, n_receivables=10),
    dict(merchant_id="M004", name="Sen Lotus Bakery Group", sector="Bakery chain", country="VN",
         currency="VND", seed=44, base_daily=95_000_000, growth=0.0012, years_operating=11,
         business_registered=True, tax_registered=True, bookkeeping="digital",
         separate_business_account=True, employees=34, units=4, pos_adopted=True,
         online_marketplaces=3, capacity_utilization=0.88, unmet_demand=True,
         confirmed_orders_value=0, succession_planned=False, owner_transition_expected=False,
         has_smartphone=True, repayment_on_time_ratio=1.0, max_days_late=0, prior_loans=5,
         monthly_debt_service=150_000_000, wallet_balance=2_400_000_000, gross_margin=0.45,
         mix_start={"cash": 0.10, "qr_pay": 0.45, "tap_pay": 0.15, "pay_link": 0.10, "external_wallet": 0.12, "external_card": 0.08},
         mix_end={"cash": 0.07, "qr_pay": 0.48, "tap_pay": 0.18, "pay_link": 0.12, "external_wallet": 0.10, "external_card": 0.05},
         household_draw=0.04, n_receivables=8),
    dict(merchant_id="M005", name="Warisan Batik House", sector="Textile retail", country="MY",
         currency="MYR", seed=55, base_daily=6_500, growth=0.0005, years_operating=28,
         business_registered=True, tax_registered=True, bookkeeping="digital",
         separate_business_account=True, employees=14, units=3, pos_adopted=True,
         online_marketplaces=2, capacity_utilization=0.75, unmet_demand=False,
         confirmed_orders_value=0, succession_planned=False, owner_transition_expected=True,
         has_smartphone=True, repayment_on_time_ratio=1.0, max_days_late=0, prior_loans=6,
         monthly_debt_service=9_000, wallet_balance=310_000, gross_margin=0.48,
         mix_start={"cash": 0.15, "qr_pay": 0.40, "tap_pay": 0.15, "pay_link": 0.10, "external_wallet": 0.12, "external_card": 0.08},
         mix_end={"cash": 0.12, "qr_pay": 0.42, "tap_pay": 0.17, "pay_link": 0.12, "external_wallet": 0.11, "external_card": 0.06},
         household_draw=0.06, n_receivables=5),
]


def _blend(a: dict, b: dict, t: float) -> dict:
    keys = sorted(set(a) | set(b))
    mix = {k: a.get(k, 0) * (1 - t) + b.get(k, 0) * t for k in keys}
    s = sum(mix.values())
    return {k: v / s for k, v in mix.items() if v > 0}


def build_merchant(p: dict, as_of: date = AS_OF, days: int = HISTORY_DAYS) -> Merchant:
    rng = random.Random(p["seed"])
    fields = {k: v for k, v in p.items() if k in Merchant.__dataclass_fields__}
    m = Merchant(**fields)
    start = as_of - timedelta(days=days - 1)
    avg_ticket = max(p["base_daily"] / 60, 1)

    for i in range(days):
        d = start + timedelta(days=i)
        t = i / (days - 1)
        # adoption accelerates in the last ~45 days for the growth personas (drives ENTICE demo)
        t_mix = min(1.0, t ** 2.2)
        mix = _blend(p["mix_start"], p["mix_end"], t_mix)
        level = p["base_daily"] * (1 + p["growth"]) ** i * WEEKDAY_FACTOR[d.weekday()]
        level *= rng.uniform(0.82, 1.18)
        if p["merchant_id"] == "M001" and rng.random() < 0.08:
            level = 0  # micro stall closes some days
        for ch, share in mix.items():
            amt = round(level * share * rng.uniform(0.9, 1.1), 2)
            if amt <= 0:
                continue
            m.transactions.append({"date": d.isoformat(), "channel": ch, "amount": amt,
                                   "count": max(1, int(amt / avg_ticket))})
        # expenses: cost of goods + opex + household draws (mixing funds)
        cogs = level * (1 - p["gross_margin"])
        opex = p["base_daily"] * 0.12
        m.expenses.append({"date": d.isoformat(), "category": "supplies", "amount": round(cogs, 2)})
        m.expenses.append({"date": d.isoformat(), "category": "operating", "amount": round(opex, 2)})
        if rng.random() < 0.5:
            m.expenses.append({"date": d.isoformat(), "category": "household_draw",
                               "amount": round(level * p["household_draw"] * 2, 2)})
        if d.day == 15 and p["monthly_debt_service"]:
            m.expenses.append({"date": d.isoformat(), "category": "loan_repayment",
                               "amount": p["monthly_debt_service"]})

    # receivables (B2B / institutional customers)
    for j in range(p.get("n_receivables", 0)):
        issued = as_of - timedelta(days=rng.randint(10, 75))
        due = issued + timedelta(days=30)
        amt = round(p["base_daily"] * rng.uniform(1.5, 4), 2)
        paid = None
        if due < as_of and rng.random() < 0.6:
            paid = (due + timedelta(days=rng.randint(-3, 6))).isoformat()
        if p.get("receivable_delay") and j < 3:
            paid = None  # timing gap: customers paying late (not a default by the merchant)
            issued = as_of - timedelta(days=50 + j * 5)
            due = issued + timedelta(days=30)
        m.receivables.append({"invoice_id": f"{p['merchant_id']}-INV{j+1:03d}",
                              "customer": f"Customer {chr(65 + j)}", "amount": amt,
                              "issued": issued.isoformat(), "due": due.isoformat(), "paid": paid})
    # upcoming payables
    for k in range(3):
        due = as_of + timedelta(days=rng.randint(2, 25))
        m.payables.append({"bill_id": f"{p['merchant_id']}-BILL{k+1:02d}",
                           "supplier": f"Supplier {k+1}",
                           "amount": round(p["base_daily"] * rng.uniform(1.0, 3.5), 2),
                           "due": due.isoformat()})
    return m


def load_all(as_of: date = AS_OF) -> dict[str, Merchant]:
    return {p["merchant_id"]: build_merchant(p, as_of) for p in PERSONAS}
