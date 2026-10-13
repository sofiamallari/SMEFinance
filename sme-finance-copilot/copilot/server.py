"""
Zero-dependency HTTP server (Python standard library only) exposing the
copilot as a JSON API, the unified web UI, and an MCP endpoint.

    python -m copilot.server --port 8000
      Web UI        http://127.0.0.1:8000/
      JSON API      /api/...
      MCP endpoint  POST http://127.0.0.1:8000/mcp   (Streamable HTTP)

DEMO AUTH: the UI picks a role via the X-Demo-Role header.  Replace
`principal_from_request` with your identity provider (OIDC/OAuth2) in
production; every other security control stays the same.
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import threading
from datetime import date
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from statistics import median
from urllib.parse import parse_qs, urlparse

from copilot import ai_agent, mcp_server
from copilot.agent import Copilot
from copilot.modules import rbf
from copilot.modules.payments import PaymentError, qr_matrix
from copilot.security import AccessDenied, ApprovalRequired, Principal

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "..", "web", "index.html")
MAX_BODY = 4_000_000  # base64-free JSON rows, max 1000 per import
TRANSACTION_FILE = os.environ.get("COPILOT_TRANSACTION_FILE", "logs/manual_transactions.jsonl")
TRANSACTION_LOCK = threading.RLock()

COPILOT = Copilot(audit_path=os.environ.get("COPILOT_AUDIT_LOG", "logs/audit.jsonl") or None,
                  exec_path=os.environ.get("COPILOT_EXEC_LOG", "logs/execution.jsonl") or None)
MCP = mcp_server.MCPHandler(COPILOT)

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                               "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                               "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def principal_from_request(headers) -> Principal:
    role = headers.get("X-Demo-Role", "owner")
    if role not in ("owner", "staff", "coach", "lender_analyst", "demo_guest"):
        role = "demo_guest"
    consent = headers.get("X-Demo-Consent", "") == "yes"
    consents = {"coach_access", "share_with_lender"} if consent else set()
    return Principal(user_id=f"demo-{role}", role=role, merchant_ids=set(COPILOT.merchants), consents=consents)



from copilot.modules.transactions import TransactionStore, validate_entry
STORE = TransactionStore(COPILOT, TRANSACTION_FILE)

def import_entries(principal, merchant_id, rows):
    return STORE.save(principal, merchant_id, rows)


def pos_catalog(m):
    tickets = [t["amount"] / max(t["count"], 1) for t in m.transactions[-200:]]
    base = median(tickets) if tickets else 100
    rnd = lambda x: round(x, -2) if x >= 1000 else round(x)
    return [{"key": "a", "name": "Signature item", "price": rnd(base * 1.0)},
            {"key": "b", "name": "Best-seller bundle", "price": rnd(base * 1.6)},
            {"key": "c", "name": "Snack / add-on", "price": rnd(base * 0.5)},
            {"key": "d", "name": "Family pack", "price": rnd(base * 2.4)}]


class Handler(BaseHTTPRequestHandler):
    server_version = "SMEFinanceCopilot/1.1"

    def log_message(self, fmt, *args):  # quiet console; audit log is the record
        pass

    def _send(self, code: int, payload, ctype="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _read_raw(self) -> bytes:
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > MAX_BODY:
            raise ValueError("request too large")
        return self.rfile.read(n) if n else b""

    def _mcp(self, method):
        if method != "POST":
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            raw = self._read_raw()
        except ValueError:
            return self._send(413, {"error": "request too large"})
        status, body = mcp_server.handle_http(MCP, self.headers, raw)
        if body is None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        return self._send(status, body)

    def _dispatch(self, method):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        if path == "/mcp":
            return self._mcp(method)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        p = principal_from_request(self.headers)
        try:
            body = {}
            if method == "POST":
                body = json.loads(self._read_raw() or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("JSON object expected")
            if method == "GET" and path == "/":
                with open(WEB, "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if method == "GET" and path == "/api/health":
                return self._send(200, {"ok": True, "narrator": COPILOT.narrator.name,
                                        "as_of": COPILOT.as_of.isoformat(),
                                        "agent_mode": "ai_agent" if ai_agent.configured() else "rule_engine",
                                        "mcp_endpoint": "/mcp", "mcp_role": MCP.principal.role,
                                        "mcp_auth": "api_key" if os.environ.get("COPILOT_MCP_API_KEY") else "none"})
            if method == "GET" and path == "/api/merchants":
                return self._send(200, [{"id": m.merchant_id, "name": m.name, "country": m.country,
                                         "currency": m.currency, "sector": m.sector}
                                        for m in COPILOT.merchants.values() if m.merchant_id in p.merchant_ids])
            mid = q.get("merchant") or body.get("merchant")
            if mid not in COPILOT.merchants:
                return self._send(404, {"error": "unknown merchant"})
            if method == "GET":
                if path == "/api/transactions":
                    return self._send(200, STORE.list_entries(p, mid))
                if path == "/api/cycle":
                    return self._send(200, COPILOT.run_cycle(p, mid))
                if path == "/api/dashboard":
                    return self._send(200, COPILOT.call(p, "get_dashboard", mid, start=q.get("start"),
                                                        end=q.get("end"), granularity=q.get("granularity", "monthly")))
                if path == "/api/cashflow":
                    return self._send(200, {"forecast": COPILOT.call(p, "cashflow_forecast", mid),
                                            "alerts": COPILOT.call(p, "cashflow_alerts", mid)})
                if path == "/api/match":
                    return self._send(200, COPILOT.call(p, "match_financing", mid))
                if path == "/api/rbf/limits":
                    COPILOT.guard.check(p, "rbf_quote", COPILOT.tools["rbf_quote"].tier, mid)
                    m = COPILOT.merchants[mid]
                    return self._send(200, {**rbf.limits(m, COPILOT.as_of),
                                            "eligibility": rbf.eligibility(m, COPILOT.as_of),
                                            "recommended": rbf.recommend_advance(m, COPILOT.as_of)})
                if path == "/api/pos/catalog":
                    COPILOT.guard.check(p, "payment_status", COPILOT.tools["payment_status"].tier, mid)
                    return self._send(200, pos_catalog(COPILOT.merchants[mid]))
                if path == "/api/payments/status":
                    return self._send(200, COPILOT.call(p, "payment_status", mid, ref=q.get("ref", "")))
            if method == "POST":
                if path == "/api/transactions/preview":
                    return self._send(200, STORE.preview(p, mid, body))
                if path == "/api/transactions/import":
                    return self._send(200, STORE.confirm(p, mid, body.get("preview_token"), body.get("confirmed")))
                if path == "/api/transactions/entry":
                    return self._send(200, STORE.save(p, mid, [body.get("entry")]))
                if path == "/api/transactions/manage":
                    return self._send(200, STORE.manage(p, mid, body))
                if path == "/api/rbf/quote":
                    return self._send(200, COPILOT.call(p, "rbf_quote", mid,
                                                        advance=float(body.get("advance") or 0) or None))
                if path == "/api/payments":
                    r = COPILOT.call(p, "payment_create", mid, method=body.get("method"),
                                     amount=float(body["amount"]) if body.get("amount") else None,
                                     items=body.get("items"), idempotency_key=body.get("idempotency_key"))
                    if r.get("qr_payload"):
                        r["qr_matrix"] = qr_matrix(r["qr_payload"])
                    return self._send(200, r)
                if path == "/api/payments/pay":
                    return self._send(200, COPILOT.call(p, "payment_simulate_pay", mid, ref=body.get("ref", ""),
                                                        channel=body.get("channel")))
                if path == "/api/chat":
                    hist = body.get("history") if isinstance(body.get("history"), list) else None
                    return self._send(200, COPILOT.handle(p, mid, str(body.get("message", "")),
                                                          body.get("approval_token"), hist))
            return self._send(404, {"error": "not found"})
        except ApprovalRequired as e:
            return self._send(202, {"approval_required": True, "approval_token": e.token, "message": str(e)})
        except AccessDenied as e:
            return self._send(403, {"error": str(e)})
        except (PaymentError, ValueError, KeyError, json.JSONDecodeError) as e:
            return self._send(400, {"error": str(e)})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    a = ap.parse_args()
    mode = "AI agent" if ai_agent.configured() else "rule engine"
    print(f"SME Finance Copilot running on http://{a.host}:{a.port}  (chat: {mode}; "
          f"MCP: http://{a.host}:{a.port}/mcp as role '{MCP.principal.role}')", flush=True)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
