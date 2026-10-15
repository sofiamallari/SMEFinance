"""
Central configuration for SME Finance Copilot.

Every number the framework paper does not specify is an explicit, documented
ASSUMPTION here so that implementers can recalibrate without touching logic.
Values marked [PAPER] come directly from the framework; [REF-APP] come from the
team's reference prototypes; [ASSUMPTION] are design choices to be validated.
"""

# ---------------------------------------------------------------------------
# Market settings (ASEAN, currency-agnostic)
# ---------------------------------------------------------------------------
from copilot.currency_policy import CODE,SYMBOL
# Legacy entries below remain for existing data/operations, not new-merchant selection.
CURRENCIES = {
    CODE: (SYMBOL, 0.0),  # Provisional sandbox/exempt cart tax, not Chinese VAT.
    # code: (symbol, typical VAT/sales-tax rate used by the POS simulator)  [ASSUMPTION]
    "IDR": ("Rp", 0.11),
    "PHP": ("₱", 0.12),
    "MYR": ("RM", 0.06),
    "THB": ("฿", 0.07),
    "VND": ("₫", 0.10),
    "SGD": ("S$", 0.09),
}
# Restrict only the explicitly selected replacement; original data remains operable until approved retirement.
from copilot.demo_environment import selected as cny_demo_selected
if cny_demo_selected():CURRENCIES = {CODE: CURRENCIES[CODE]}
DEFAULT_CURRENCY = CODE

# ---------------------------------------------------------------------------
# Payment channels (generic names; no provider brands)
# ---------------------------------------------------------------------------
# "in-ecosystem" channels are the copilot's own digital rails; they count toward
# digital capture and incentive milestones.  "external" channels are still
# digital but routed through other providers; cash is invisible to credit models.
CHANNELS = {
    "qr_pay":         {"label": "QR Pay (dynamic QR)",            "ecosystem": True,  "digital": True},
    "tap_pay":        {"label": "Tap Pay (tap-to-phone card)",    "ecosystem": True,  "digital": True},
    "pay_link":       {"label": "Pay Link (instant checkout)",    "ecosystem": True,  "digital": True},
    "external_wallet":{"label": "External e-wallet / other bank", "ecosystem": False, "digital": True},
    "external_card":  {"label": "External card acquirer",         "ecosystem": False, "digital": True},
    "cash":           {"label": "Cash",                           "ecosystem": False, "digital": False},
}

# Merchant Discount Rate tiers by graduation stage.  The paper warns a flat ~3%
# MDR erodes micro margins and recommends tiered / subsidised rates, lower for
# early stages. [PAPER: principle]  [ASSUMPTION: values]
MDR_BY_STAGE = {1: 0.000, 2: 0.003, 3: 0.006, 4: 0.008, 5: 0.010, 6: 0.010}
MDR_FLAT_BENCHMARK = 0.03  # [PAPER] flat-rate benchmark used for comparison only

QR_EXPIRY_SECONDS = 300          # [REF-APP] dynamic QR valid for 5 minutes
PAY_LINK_EXPIRY_HOURS = 72       # [ASSUMPTION]
MAX_SINGLE_PAYMENT_MULTIPLE = 50 # [ASSUMPTION] anti-fraud: > 50x median ticket is flagged

# ---------------------------------------------------------------------------
# ENTICE: tiered incentive milestones on MoM growth of ecosystem digital sales
# ---------------------------------------------------------------------------
INCENTIVE_TIERS = [  # [PAPER]
    {"tier": 3, "name": "Mastery Milestone", "min_mom_growth": 0.50,
     "reward": "Priority access to higher financing ceilings and less rigid collateral requirements"},
    {"tier": 2, "name": "Growth Milestone", "min_mom_growth": 0.30,
     "reward": "Tiered interest / fee discounts on current and future microloans"},
    {"tier": 1, "name": "Entry Milestone", "min_mom_growth": 0.15,
     "reward": "Subsidised merchant discount rate and instant daily cashback"},
]
INCENTIVE_MIN_BASE_SALES_SHARE = 0.10  # [ASSUMPTION] guards against growth-from-zero gaming

# ---------------------------------------------------------------------------
# EQUIP: Revenue-Based Financing (RBF)
# ---------------------------------------------------------------------------
# Reference app: fee 14% / 12% / 10% stepping down with size, remittance rate
# 6% + (amount/max)*12%.  Generalised here to be relative to the merchant's own
# verified monthly sales so it works in any ASEAN currency. [REF-APP -> generalised]
RBF = {
    "max_advance_multiple": 1.5,     # [ASSUMPTION] max advance = 1.5x avg monthly verified sales
    "min_advance_multiple": 0.05,
    "fee_tiers": [                   # (advance as multiple of monthly sales upper bound, flat fee)
        (0.50, 0.14),
        (1.00, 0.12),
        (float("inf"), 0.10),
    ],
    "remit_rate_floor": 0.06,        # [REF-APP] 6%
    "remit_rate_span": 0.12,         # [REF-APP] +12% at maximum size
    "remit_rate_cap": 0.18,          # [ASSUMPTION] never deduct more than 18% of a day's sales
    "max_term_days": 540,            # [ASSUMPTION] review trigger if payoff exceeds 18 months
    "target_term_days": 365,
    "incentive_fee_discount": {1: 0.00, 2: 0.01, 3: 0.02},  # ENTICE Tier 2/3 fee step-down [ASSUMPTION]
    "min_history_days": 60,          # [ASSUMPTION] need 60 days of verified data
    "verified_share_floor": 0.30,    # [ASSUMPTION] at least 30% of sales must be digitally verified
}

# ---------------------------------------------------------------------------
# Cash-flow management alerts
# ---------------------------------------------------------------------------
CASHFLOW = {
    "forecast_days": 30,
    "lookback_days": 56,              # 8 weeks for weekday seasonality
    "runway_critical_days": 7,
    "runway_warning_days": 14,
    "sales_drop_warning": 0.20,       # 20% drop WoW in 7-day sales
    "receivable_overdue_days": 0,
    "receivable_aged_days": 30,
    "concentration_warning": 0.60,    # one channel > 60% of revenue (incl. cash)
    "household_withdrawal_warning": 0.25,  # personal draws > 25% of inflows -> mixing funds
    "buffer_days_target": 14,
}

# ---------------------------------------------------------------------------
# Seven-dimension assessment & graduation pipeline
# ---------------------------------------------------------------------------
DIMENSIONS = [
    "financial_health", "formalization", "digital_maturity", "market_access",
    "operational_capacity", "credit_readiness", "sustainability",
]
# Composite weights [ASSUMPTION – equal-ish, financial & credit slightly higher]
DIMENSION_WEIGHTS = {
    "financial_health": 0.18, "formalization": 0.12, "digital_maturity": 0.15,
    "market_access": 0.13, "operational_capacity": 0.14, "credit_readiness": 0.18,
    "sustainability": 0.10,
}
STAGES = {
    1: "Survival Borrower",
    2: "Striving Amateur",
    3: "Steady Upgrader",
    4: "Opportunity Seizer",
    5: "Expanding Proprietor",
    6: "Heir Seeker",
}
# Composite score lower bounds for stages 1-5 [ASSUMPTION]; stage 6 is triggered
# by a succession flag on top of a stage-5-level score.
STAGE_THRESHOLDS = [(0, 1), (35, 2), (50, 3), (65, 4), (78, 5)]
# Graduation also needs every "gate" dimension above a floor [ASSUMPTION]
STAGE_GATES = {
    3: {"financial_health": 45, "credit_readiness": 40},
    4: {"financial_health": 60, "credit_readiness": 55, "operational_capacity": 50},
    5: {"financial_health": 70, "credit_readiness": 65, "market_access": 60, "operational_capacity": 65},
}

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECURITY = {
    "approval_token_ttl_seconds": 300,
    "rate_limit_per_minute": 60,
    "max_message_chars": 2000,
    "audit_log_path": "logs/audit.jsonl",
    "execution_log_path": "logs/execution.jsonl",
}
