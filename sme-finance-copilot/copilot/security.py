"""
Security layer: permission tiers, role-based access, human-approval tokens,
consent scoping, tamper-evident audit log, PII masking, input guardrails and
rate limiting.  The agent can never act with more authority than the human
principal it is serving, and nothing it reads from user text can raise that.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import IntEnum

from copilot import config


class Tier(IntEnum):
    T0_READ = 0              # view own analytics, forecasts, assessment
    T1_ADVISE = 1            # compute quotes, rankings, explanations (no side effects)
    T2_SANDBOX_WRITE = 2     # create simulated payments / records in the sandbox ledger
    T3_APPROVAL_REQUIRED = 3 # prepare a financing application packet (needs owner approval + consent)
    T4_PROHIBITED = 4        # approve credit, move real funds, change limits, cross-merchant access


ROLE_MAX_TIER = {
    "owner": Tier.T3_APPROVAL_REQUIRED,
    "staff": Tier.T2_SANDBOX_WRITE,  # authorized transaction entry, no financing application
    "coach": Tier.T1_ADVISE,          # field officer / progression coach
    "lender_analyst": Tier.T1_ADVISE,   # read only, consent-scoped
    "demo_guest": Tier.T2_SANDBOX_WRITE,
}

PROHIBITED_ACTIONS = {
    "approve_credit": "Credit decisions are made only by the lender's authorised underwriters.",
    "disburse_funds": "The copilot never moves real money.",
    "change_credit_limit": "Limits are set by the lender, not the copilot.",
    "export_raw_data": "Raw transaction data is never exported to third parties by the copilot.",
}


@dataclass
class Principal:
    user_id: str
    role: str
    merchant_ids: set = field(default_factory=set)      # merchants this user may act for / view
    consents: set = field(default_factory=set)          # e.g. {"share_with_lender", "coach_access"}

    def max_tier(self) -> Tier:
        return ROLE_MAX_TIER.get(self.role, Tier.T0_READ)


class AccessDenied(PermissionError):
    pass


class ApprovalRequired(PermissionError):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.token = token


class PolicyGuard:
    def __init__(self, secret: bytes | None = None, clock=time.time):
        self.secret = secret or os.environ.get("COPILOT_APPROVAL_SECRET", "").encode() or secrets.token_bytes(32)
        self.clock = clock
        self.used_tokens: set[str] = set()

    def check(self, principal: Principal, tool_name: str, tier: Tier, merchant_id: str,
              approval_token: str | None = None, required_consent: str | None = None) -> str:
        if tier == Tier.T4_PROHIBITED:
            raise AccessDenied(PROHIBITED_ACTIONS.get(tool_name, "This action is prohibited for the copilot."))
        if merchant_id not in principal.merchant_ids:
            raise AccessDenied("You do not have access to this merchant's data.")
        if principal.role == "coach" and "coach_access" not in principal.consents:
            raise AccessDenied("The merchant has not granted coach access.")
        if principal.role == "lender_analyst" and "share_with_lender" not in principal.consents:
            raise AccessDenied("The merchant has not consented to share data with the lender.")
        if principal.role == "lender_analyst" and tool_name not in {"assess_business", "match_financing", "rbf_quote", "cashflow_forecast", "cashflow_alerts", "financial_report"}:
            raise AccessDenied("Financing agents may access authorized financing information only")
        if tier > principal.max_tier():
            raise AccessDenied(f"Role '{principal.role}' cannot perform tier {tier.name} actions.")
        if required_consent and required_consent not in principal.consents:
            raise AccessDenied(f"Missing owner consent: {required_consent}.")
        if tier == Tier.T3_APPROVAL_REQUIRED:
            if not approval_token:
                tok = self.issue_token(principal.user_id, tool_name, merchant_id)
                raise ApprovalRequired("Owner approval required before this action.", tok)
            self.verify_token(approval_token, principal.user_id, tool_name, merchant_id)
        return "allowed"

    # HMAC-signed, single-use, time-limited approval tokens
    def issue_token(self, user_id: str, action: str, merchant_id: str) -> str:
        exp = int(self.clock()) + config.SECURITY["approval_token_ttl_seconds"]
        nonce = secrets.token_hex(8)
        msg = f"{user_id}|{action}|{merchant_id}|{exp}|{nonce}"
        sig = hmac.new(self.secret, msg.encode(), hashlib.sha256).hexdigest()[:32]
        return f"{msg}|{sig}"

    def verify_token(self, token: str, user_id: str, action: str, merchant_id: str):
        try:
            u, a, m, exp, nonce, sig = token.split("|")
        except ValueError:
            raise AccessDenied("Malformed approval token.")
        msg = f"{u}|{a}|{m}|{exp}|{nonce}"
        good = hmac.new(self.secret, msg.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(good, sig):
            raise AccessDenied("Invalid approval token.")
        if (u, a, m) != (user_id, action, merchant_id):
            raise AccessDenied("Approval token does not match this user/action/merchant.")
        if self.clock() > int(exp):
            raise AccessDenied("Approval token expired.")
        if token in self.used_tokens:
            raise AccessDenied("Approval token already used.")
        self.used_tokens.add(token)


# ---------------------------------------------------------------- guardrails
INJECTION_PATTERNS = [
    r"ignore (all|any|previous|prior) (instructions|rules)", r"system prompt", r"you are now",
    r"act as (an? )?(admin|administrator|underwriter|developer)", r"bypass", r"disable (security|guard)",
    r"approve (my|the|this) (loan|credit|application)", r"increase (my )?(credit )?limit",
    r"transfer (the )?(money|funds)", r"show (me )?(other|all) merchants",
]
_inj = re.compile("|".join(INJECTION_PATTERNS), re.I)
_pan = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_phone = re.compile(r"(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)")


def sanitize_input(text: str) -> dict:
    if not isinstance(text, str):
        raise ValueError("message must be text")
    text = text.replace("\x00", "")[: config.SECURITY["max_message_chars"]]
    flags = []
    if _inj.search(text):
        flags.append("possible_prompt_injection_or_privilege_request")
    if _pan.search(text):
        flags.append("card_number_detected_and_removed")
        text = _pan.sub("[REMOVED-CARD-NUMBER]", text)
    return {"text": text, "flags": flags}


def mask_pii(obj):
    if isinstance(obj, str):
        s = _pan.sub("[CARD]", obj)
        s = _email.sub("[EMAIL]", s)
        return _phone.sub("[PHONE]", s)
    if isinstance(obj, dict):
        return {k: mask_pii(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_pii(v) for v in obj]
    return obj


class RateLimiter:
    def __init__(self, per_minute: int | None = None, clock=time.time):
        self.per_minute = per_minute or config.SECURITY["rate_limit_per_minute"]
        self.clock = clock
        self.hits = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now, q = self.clock(), self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


class AuditLog:
    """Append-only JSONL with a SHA-256 hash chain: any edit or deletion breaks verification."""

    def __init__(self, path: str | None = None, clock=time.time):
        self.path = path
        self.clock = clock
        self.records: list[dict] = []
        self.prev = "GENESIS"
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def write(self, **event) -> dict:
        rec = {"seq": len(self.records) + 1, "ts": round(self.clock(), 3), **mask_pii(event),
               "prev_hash": self.prev}
        rec["hash"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
        self.prev = rec["hash"]
        self.records.append(rec)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=str) + "\n")
        return rec

    @staticmethod
    def verify(records: list[dict]) -> bool:
        prev = "GENESIS"
        for r in records:
            body = {k: v for k, v in r.items() if k != "hash"}
            if body["prev_hash"] != prev:
                return False
            if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != r["hash"]:
                return False
            prev = r["hash"]
        return True
