"""
Digital Payments Simulator (EQUIP – flexible payment channels).  SANDBOX ONLY.

Mirrors the reference simulator's two pathways:
  Pathway 1 – Standalone app: merchant keys in an amount and settles by
              QR Pay (dynamic QR), Tap Pay (tap-to-phone) or Pay Link.
  Pathway 2 – POS-integrated terminal: build a cart, add sales tax, then pay.

Adds what a production design needs: a payment state machine
(PENDING -> PAID | EXPIRED | CANCELLED), idempotency keys, tiered MDR,
settlement into a business wallet, integrity checks against
"engagement-washing" (gamed volume), and a strict no-card-data rule.

No real money moves.  QR payloads are tagged SANDBOX and are not valid on any
payment scheme.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import time
import threading
from functools import wraps
from dataclasses import dataclass, field
from statistics import median

from copilot import config

PAN_PATTERN = re.compile(r"(?:\d[ -]?){13,19}")  # looks like a card number


class PaymentError(ValueError):
    pass


def _crc16(data: str) -> str:
    crc = 0xFFFF
    for ch in data.encode():
        crc ^= ch << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


@dataclass
class Payment:
    ref: str
    merchant_id: str
    method: str
    amount: float
    currency: str
    status: str = "PENDING"
    created_at: float = 0.0
    expires_at: float = 0.0
    paid_at: float | None = None
    paid_channel: str | None = None
    mdr_rate: float = 0.0
    mdr_fee: float = 0.0
    net_settled: float = 0.0
    qr_payload: str | None = None
    link_url: str | None = None
    items: list = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    flags: list = field(default_factory=list)

    refunded_amount: float = 0.0

    def public(self) -> dict:
        return self.__dict__.copy()


def synchronized(method):
    @wraps(method)
    def invoke(self,*args,**kwargs):
        with self.lock:return method(self,*args,**kwargs)
    return invoke

class PaymentSimulator:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.RLock()
        self.payments: dict[str, Payment] = {}
        self.idempotency: dict[str, str] = {}
        self.wallets: dict[str, float] = {}
        self.events: list[dict] = []
        self.on_event = None
        self.on_refund = None
        self.existing_refund = None
        self.refunds = {}

    # ------------------------------------------------------------------ POS
    @staticmethod
    def cart_totals(items: list[dict], currency: str) -> dict:
        if not items:
            raise PaymentError("cart is empty")
        subtotal = 0.0
        from decimal import Decimal, InvalidOperation
        if not isinstance(items,list) or len(items)>50:raise PaymentError("Use 1–50 POS cart items")
        for it in items:
            try:
                price=Decimal(str(it.get("price",0)));qty=Decimal(str(it.get("qty",0)))
                valid=price.is_finite() and qty.is_finite() and 0<price<=Decimal('1e9') and 0<qty<=Decimal('1e6') and price==price.quantize(Decimal('.01'))
            except (InvalidOperation,ValueError,TypeError,AttributeError):valid=False
            if not valid:
                raise PaymentError("each item needs a positive qty and price")
            subtotal += it["qty"] * it["price"]
        rate = config.CURRENCIES[currency][1]
        tax = round(subtotal * rate, 2)
        return {"subtotal": round(subtotal, 2), "tax_rate": rate, "tax": tax,
                "total": round(subtotal + tax, 2)}

    # ------------------------------------------------------------ creation
    @synchronized
    def create(self, merchant, method: str, amount: float | None = None, items: list | None = None,
               stage: int = 1, idempotency_key: str | None = None, **extra) -> Payment:
        if method not in ("qr_pay", "tap_pay", "pay_link"):
            raise PaymentError("method must be qr_pay, tap_pay or pay_link")
        for v in extra.values():
            if isinstance(v, str) and PAN_PATTERN.search(v):
                raise PaymentError("Card numbers must never be entered. The simulator does not accept card data.")
        if idempotency_key:
            idempotency_key=merchant.merchant_id+":"+idempotency_key
        if idempotency_key and idempotency_key in self.idempotency:
            return self.payments[self.idempotency[idempotency_key]]

        subtotal = tax = 0.0
        if items:
            tot = self.cart_totals(items, merchant.currency)
            amount, subtotal, tax = tot["total"], tot["subtotal"], tot["tax"]
        from decimal import Decimal, InvalidOperation
        try:
            valid_amount=Decimal(str(amount))
            valid=valid_amount.is_finite() and Decimal('0')<valid_amount<=Decimal('1e12') and valid_amount==valid_amount.quantize(Decimal('.01'))
        except (InvalidOperation,ValueError,TypeError):valid=False
        if not valid:
            raise PaymentError("amount must be positive")

        now = self.clock()
        ref = f"SBX-{method.split('_')[0].upper()}-{merchant.merchant_id}-{secrets.token_hex(4).upper()}"
        ttl = config.QR_EXPIRY_SECONDS if method == "qr_pay" else (
            config.PAY_LINK_EXPIRY_HOURS * 3600 if method == "pay_link" else 120)
        p = Payment(ref=ref, merchant_id=merchant.merchant_id, method=method, amount=round(amount, 2),
                    currency=merchant.currency, created_at=now, expires_at=now + ttl,
                    mdr_rate=config.MDR_BY_STAGE.get(stage, 0.01), items=items or [],
                    subtotal=subtotal, tax=tax)
        if method == "qr_pay":
            body = (_tlv("00", "01") + _tlv("01", "12") + _tlv("26", _tlv("00", "SANDBOX.SMECOPILOT") +
                    _tlv("01", merchant.merchant_id)) + _tlv("53", merchant.currency) +
                    _tlv("54", f"{amount:.2f}") + _tlv("58", merchant.country) +
                    _tlv("59", merchant.name[:25]) + _tlv("62", _tlv("05", ref)) + "6304")
            p.qr_payload = body + _crc16(body)
        elif method == "pay_link":
            p.link_url = f"https://sandbox.pay.local/l/{secrets.token_urlsafe(10)}"
        p.flags = self._integrity_flags(merchant, p)
        self.payments[ref] = p
        if idempotency_key:
            self.idempotency[idempotency_key] = ref
        self._event("created", p)
        return p

    # ------------------------------------------------------------- lifecycle
    @synchronized
    def status(self, ref: str) -> Payment:
        p = self._get(ref)
        if p.status == "PENDING" and self.clock() > p.expires_at:
            p.status = "EXPIRED"
            self._event("expired", p)
        return p

    @synchronized
    def simulate_customer_payment(self, ref: str, paid_channel: str | None = None) -> Payment:
        """Customer completes payment. For Pay Link the customer may choose any rail."""
        p = self.status(ref)
        if p.status != "PENDING":
            raise PaymentError(f"payment is {p.status}, cannot be paid")
        if "requires_review" in p.flags:
            raise PaymentError("payment held for integrity review; a human must release it")
        channel = paid_channel or p.method
        if channel not in config.CHANNELS or channel == "cash":
            raise PaymentError("invalid payment channel")
        if p.method != "pay_link" and channel != p.method:
            raise PaymentError("channel must match the payment method for QR Pay / Tap Pay")
        p.status, p.paid_at, p.paid_channel = "PAID", self.clock(), channel
        eco = config.CHANNELS[channel]["ecosystem"]
        p.mdr_fee = round(p.amount * (p.mdr_rate if eco else 0), 2)
        p.net_settled = round(p.amount - p.mdr_fee, 2) if eco else 0.0
        if eco:
            self.wallets[p.merchant_id] = round(self.wallets.get(p.merchant_id, 0) + p.net_settled, 2)
        self._event("paid", p)
        return p

    @synchronized
    def refund(self,ref,amount,idempotency_key):
        from decimal import Decimal
        p=self._get(ref)
        key=p.merchant_id+":"+str(idempotency_key)
        value=Decimal(str(amount))
        if not idempotency_key or not value.is_finite() or value<=0 or value!=value.quantize(Decimal('.01')):raise PaymentError("Exact positive refund and idempotency key required")
        if key in self.refunds:
            old=self.refunds[key]
            if old["ref"]!=ref or old["amount"]!=float(value):raise PaymentError("Refund key belongs to a different request")
            return old
        reference="SBX-REF-"+__import__('hashlib').sha256(key.encode()).hexdigest()[:20]
        if self.existing_refund:
            existing=self.existing_refund(p,float(value),reference)
            if existing:self.refunds[key]=existing;return existing
        if p.status!="PAID" or value>Decimal(str(p.amount))-Decimal(str(p.refunded_amount)):raise PaymentError("Refund exceeds the completed unrefunded amount")
        if self.on_refund:self.on_refund(p,float(value),reference)
        p.refunded_amount=round(p.refunded_amount+float(value),2)
        # This is sandbox accounting only; no real bank refund or external settlement.
        if p.net_settled:self.wallets[p.merchant_id]=round(self.wallets.get(p.merchant_id,0)-float(value)*(1-p.mdr_rate),2)
        result={"ref":ref,"refund_reference":reference,"amount":float(value),"currency":p.currency,"status":"SIMULATED_REFUND","provenance":"simulated_payment"}
        self.refunds[key]=result
        self._event("refunded",p)
        return result

    @synchronized
    def fail(self,ref):
        p=self.status(ref)
        if p.status!="PENDING":raise PaymentError("Only a pending simulated payment may fail")
        p.status="FAILED";self._event("failed",p);return p

    @synchronized
    def cancel(self, ref: str) -> Payment:
        p = self.status(ref)
        if p.status != "PENDING":
            raise PaymentError(f"payment is {p.status}, cannot be cancelled")
        p.status = "CANCELLED"
        self._event("cancelled", p)
        return p

    def record_cash(self, merchant, amount: float) -> dict:
        if amount <= 0:
            raise PaymentError("amount must be positive")
        ev = {"type": "cash_recorded", "merchant_id": merchant.merchant_id, "amount": amount,
              "note": "Cash is self-reported and not verifiable; it does not count toward milestones."}
        self.events.append(ev)
        return ev

    def mdr_comparison(self, amount: float, stage: int) -> dict:
        tiered = config.MDR_BY_STAGE.get(stage, 0.01)
        return {"tiered_rate": tiered, "tiered_fee": round(amount * tiered, 2),
                "flat_benchmark_rate": config.MDR_FLAT_BENCHMARK,
                "flat_fee": round(amount * config.MDR_FLAT_BENCHMARK, 2),
                "saving": round(amount * (config.MDR_FLAT_BENCHMARK - tiered), 2)}

    # -------------------------------------------------------------- helpers
    def _integrity_flags(self, merchant, p: Payment) -> list:
        flags = []
        tickets = [t["amount"] / max(t["count"], 1) for t in merchant.transactions[-300:]]
        med = median(tickets) if tickets else p.amount
        if p.amount > med * config.MAX_SINGLE_PAYMENT_MULTIPLE:
            flags.append("requires_review")
            flags.append(f"amount is {p.amount / med:.0f}x the median ticket")
        recent = [x for x in self.payments.values()
                  if x.merchant_id == merchant.merchant_id and self.clock() - x.created_at < 60]
        if len(recent) >= 10:
            flags.append("velocity: >=10 payment requests in 60s")
        same = [x for x in recent if abs(x.amount - p.amount) < 0.01]
        if len(same) >= 3:
            flags.append("repeated identical amounts (possible engagement-washing)")
        return flags

    def _get(self, ref: str) -> Payment:
        if ref not in self.payments:
            raise PaymentError("unknown payment reference")
        return self.payments[ref]

    def _event(self, kind: str, p: Payment):
        if self.on_event:self.on_event(p)
        self.events.append({"type": kind, "ref": p.ref, "merchant_id": p.merchant_id,
                            "method": p.method, "amount": p.amount, "status": p.status,
                            "paid_channel": p.paid_channel, "ts": self.clock()})


def qr_matrix(payload: str, size: int = 21) -> list[list[int]]:
    """Deterministic visual placeholder for UI rendering (NOT a scannable QR)."""
    bits = bin(int(hashlib.sha256(payload.encode()).hexdigest() * 4, 16))[2:]
    grid = [[int(bits[(r * size + c) % len(bits)]) for c in range(size)] for r in range(size)]
    for r0, c0 in ((0, 0), (0, size - 7), (size - 7, 0)):  # finder patterns
        for r in range(7):
            for c in range(7):
                edge = r in (0, 6) or c in (0, 6)
                core = 2 <= r <= 4 and 2 <= c <= 4
                grid[r0 + r][c0 + c] = 1 if edge or core else 0
    return grid
