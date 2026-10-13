"""
Single source of truth for the tools that external AI agents may call.

Used by:
  * copilot/mcp_server.py  - exposes them over the Model Context Protocol (MCP)
  * copilot/ai_agent.py    - exposes them as function-calling tools to an LLM
                             powering the in-app Copilot tab

Every call is executed through Copilot.call(), so the PolicyGuard (tiers, roles,
consent, approval tokens) and the hash-chained audit log apply to AI agents
exactly as they apply to the web UI.  Prohibited (T4) tools are never exposed.
"""
from __future__ import annotations

import json

from copilot.modules import rbf
from copilot.security import Tier

_M = {"merchant_id": {"type": "string", "description": "Merchant ID, e.g. M002. Use list_merchants to find IDs."}}


def _schema(props: dict | None = None, required: list | None = None, merchant: bool = True) -> dict:
    p = dict(_M) if merchant else {}
    p.update(props or {})
    return {"type": "object", "properties": p,
            "required": (["merchant_id"] if merchant else []) + (required or []),
            "additionalProperties": False}


READ = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
WRITE_SANDBOX = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}

TOOLS = [
    {"name":"financial_report", "internal":"financial_report", "annotations":READ,
     "description":"Aggregate financial report, expenses, net income, risk alerts and 30-day revenue projection including saved uploads.",
     "inputSchema":_schema()},
    {"name": "list_merchants", "internal": None, "annotations": READ,
     "description": "List the (synthetic) small businesses this user may access, with country, currency and sector.",
     "inputSchema": _schema(merchant=False)},
    {"name": "ask_copilot", "internal": "__chat__", "annotations": READ,
     "description": ("Ask the SME Finance Copilot a free-text question about one business, e.g. 'how am I doing', "
                     "'what financing fits', 'any cash-flow alerts', 'how much can I borrow with RBF'. "
                     "Returns a plain-language answer computed by the copilot's rule engine."),
     "inputSchema": _schema({"question": {"type": "string", "maxLength": 2000}}, ["question"])},
    {"name": "assess_business", "internal": "assess_business", "annotations": READ,
     "description": ("Seven-dimension business assessment (financial health, formalization, digital maturity, market "
                     "access, operational capacity, credit readiness, sustainability), Graduation Pipeline stage 1-6, "
                     "binding constraints and recommended interventions."),
     "inputSchema": _schema()},
    {"name": "match_financing", "internal": "match_financing", "annotations": READ,
     "description": "Rank financing and support options for the business with reasons, plus options not yet eligible and why.",
     "inputSchema": _schema()},
    {"name": "rbf_quote", "internal": "rbf_quote", "annotations": READ,
     "description": ("Revenue-based financing simulation: advance, flat fee, % of daily digital sales remitted, "
                     "estimated payoff days. Omit 'advance' to get the recommended amount. Indicative only."),
     "inputSchema": _schema({"advance": {"type": "number", "exclusiveMinimum": 0,
                                         "description": "Requested advance in the merchant's currency"}})},
    {"name": "cashflow_forecast", "internal": "cashflow_forecast", "annotations": READ,
     "description": "30-day cash balance forecast, lowest point, runway (day cash goes negative) and buffer days.",
     "inputSchema": _schema({"days": {"type": "integer", "minimum": 7, "maximum": 90}})},
    {"name": "cashflow_alerts", "internal": "cashflow_alerts", "annotations": READ,
     "description": "Prioritised cash-flow alerts (critical/warning/info) each with a recommended action.",
     "inputSchema": _schema()},
    {"name": "get_dashboard", "internal": "get_dashboard", "annotations": READ,
     "description": ("Merchant intelligence dashboard: revenue and transaction mix by payment channel, trend, digital "
                     "capture share, incentive milestone, receivables timing-delay vs default classification."),
     "inputSchema": _schema({"start": {"type": "string", "format": "date"}, "end": {"type": "string", "format": "date"},
                             "granularity": {"type": "string",
                                             "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]}})},
    {"name": "incentive_status", "internal": "incentive_status", "annotations": READ,
     "description": "Tiered incentive milestone (15% / 30% / 50% month-on-month growth in own-rail digital sales).",
     "inputSchema": _schema()},
    {"name": "create_sandbox_payment", "internal": "payment_create", "annotations": WRITE_SANDBOX,
     "description": "Create a SANDBOX payment request (no real money): qr_pay, tap_pay or pay_link.",
     "inputSchema": _schema({"method": {"type": "string", "enum": ["qr_pay", "tap_pay", "pay_link"]},
                             "amount": {"type": "number", "exclusiveMinimum": 0}}, ["method", "amount"])},
    {"name": "payment_status", "internal": "payment_status", "annotations": READ,
     "description": "Check the status of a sandbox payment by reference.",
     "inputSchema": _schema({"ref": {"type": "string"}}, ["ref"])},
]
BY_NAME = {t["name"]: t for t in TOOLS}

# Fields stripped from tool output before it reaches any external model
_DROP = {"qr_matrix", "factors", "path", "first_14_days", "trend"}


def _trim(obj, depth=0):
    if isinstance(obj, dict):
        return {k: _trim(v, depth + 1) for k, v in obj.items() if k not in _DROP}
    if isinstance(obj, list):
        return [_trim(v, depth + 1) for v in obj[:12]]
    return obj


def execute(copilot, principal, name: str, args: dict, fixed_merchant: str | None = None):
    """Run a tool on behalf of `principal`.  If fixed_merchant is given (in-app agent), the
    model cannot choose a different merchant: any merchant_id it supplies is overridden."""
    if name not in BY_NAME:
        raise ValueError(f"Unknown tool: {name}")
    spec = BY_NAME[name]
    args = dict(args or {})
    allowed = set(spec["inputSchema"]["properties"])
    unknown = set(args) - allowed
    if unknown:
        raise ValueError(f"Unexpected argument(s): {', '.join(sorted(unknown))}")
    for req in spec["inputSchema"]["required"]:
        if req == "merchant_id" and fixed_merchant:
            continue
        if args.get(req) in (None, ""):
            raise ValueError(f"Missing required argument: {req}")

    if name == "list_merchants":
        from copilot.authorization import require
        from copilot.security import AccessDenied
        try:
            require(principal,"use_copilot")
            visible=[]
            for m in copilot.merchants.values():
                if m.merchant_id not in principal.merchant_ids:continue
                try:require(principal,"use_copilot",m.merchant_id)
                except AccessDenied:continue
                visible.append({"merchant_id":m.merchant_id,"name":m.name,"country":m.country,"currency":m.currency,"sector":m.sector})
        except AccessDenied:
            copilot.audit.write(actor=principal.user_id,role=principal.role,tool=name,decision="denied")
            raise
        copilot.audit.write(actor=principal.user_id,role=principal.role,tool=name,decision="allowed",outcome="ok")
        return {"merchants":visible}
    mid = fixed_merchant or str(args.pop("merchant_id", ""))
    args.pop("merchant_id", None)
    if mid not in copilot.merchants:
        raise ValueError("Unknown merchant_id")
    if name == "ask_copilot":
        r = copilot.handle(principal, mid, str(args["question"]))
        return {"answer": r["reply"], "intent": r["intent"]}
    out = copilot.call(principal, spec["internal"], mid, **args)
    if name == "rbf_quote" and isinstance(out, dict):
        out["eligibility"] = rbf.eligibility(copilot.merchants[mid], copilot.as_of)
    if isinstance(out, list):
        out = {"items": out}
    return _trim(out)


def to_text(result) -> str:
    return json.dumps(result, default=str, ensure_ascii=False)


def openai_tools(exclude_merchant: bool = True) -> list:
    """Function-calling schema for the in-app LLM agent (merchant is fixed by the session)."""
    out = []
    for t in TOOLS:
        if t["name"] in ("list_merchants", "ask_copilot"):
            continue
        params = json.loads(json.dumps(t["inputSchema"]))
        if exclude_merchant:
            params["properties"].pop("merchant_id", None)
            params["required"] = [r for r in params["required"] if r != "merchant_id"]
        out.append({"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                      "parameters": params}})
    return out


TIER_OF = {t["name"]: (Tier.T2_SANDBOX_WRITE if t["annotations"] is WRITE_SANDBOX else Tier.T0_READ) for t in TOOLS}
