"""
Zero-dependency HTTP server (Python standard library only) exposing the
copilot as a JSON API, the unified web UI, and an MCP endpoint.

    python -m copilot.server --port 8000
      Web UI        http://127.0.0.1:8000/
      JSON API      /api/...
      MCP endpoint  POST http://127.0.0.1:8000/mcp   (Streamable HTTP)

Authenticated mode uses SQLite identities, server sessions, CSRF and merchant
authorization. Legacy headers are accepted only in explicit localhost demo mode.
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
from http.cookies import SimpleCookie
import secrets
from copilot.auth import AuthStore, AuthError, InputError, demo_mode, REQUEST_ID
from copilot.authorization import require, ROLE_LABELS, BOUNDARIES
from statistics import median
from urllib.parse import parse_qs, urlparse

from copilot import ai_agent, mcp_server
from copilot.agent import Copilot
from copilot.modules import rbf
from copilot.modules.payments import PaymentError, qr_matrix
from copilot.security import AccessDenied, ApprovalRequired, Principal

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "..", "web", "index.html")
MAX_BODY = 4_100_000  # base64-free JSON rows, max 1000 per import
TRANSACTION_FILE = os.environ.get("COPILOT_TRANSACTION_FILE", "logs/manual_transactions.jsonl")
TRANSACTION_LOCK = threading.RLock()

COPILOT = Copilot(audit_path=os.environ.get("COPILOT_AUDIT_LOG", "logs/audit.jsonl") or None,
                  exec_path=os.environ.get("COPILOT_EXEC_LOG", "logs/execution.jsonl") or None)
AUTH = AuthStore(os.environ.get("COPILOT_IDENTITY_DB", "logs/identity.sqlite3"), COPILOT.merchants)
COPILOT.identity_store = AUTH
COPILOT.audit.sink = AUTH.financial_audit
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
    if not demo_mode():
        return AUTH.principal(session_token(headers))
    role = headers.get("X-Demo-Role", "owner")
    if role not in ("owner", "staff", "coach", "lender_analyst", "demo_guest"):
        role = "demo_guest"
    consent = headers.get("X-Demo-Consent", "") == "yes"
    consents = {"coach_access", "share_with_lender"} if consent else set()
    return Principal(user_id=f"demo-{role}", role=role, merchant_ids=set(COPILOT.merchants), consents=consents)


def session_token(headers):
    authorization = headers.get('Authorization', '')
    if authorization.lower().startswith('bearer '):
        return authorization[7:].strip()
    cookie = SimpleCookie()
    try: cookie.load(headers.get('Cookie',''))
    except Exception: raise AuthError()
    return cookie['sme_session'].value if 'sme_session' in cookie else ''



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
    server_version = "SMEFinanceCopilot/1.2"

    def log_message(self, fmt, *args):  # quiet console; audit log is the record
        pass

    def _send(self, code: int, payload, ctype="application/json", headers=None):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("X-Request-ID", getattr(self,"request_id", ""))
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionAbortedError,ConnectionResetError):pass

    def _read_raw(self) -> bytes:
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n < 0 or n > MAX_BODY:
            raise ValueError("request too large")
        return self.rfile.read(n) if n else b""

    def _cookie(self, token, clear=False):
        secure = '; Secure' if os.environ.get('COPILOT_HTTPS') == 'yes' else ''
        return f'sme_session={token}; Path=/; HttpOnly; SameSite=Strict'+secure+('; Max-Age=0' if clear else '')

    def _page(self, name):
        with open(os.path.join(ROOT,'..','web',name),'rb') as f:
            return self._send(200,f.read(),'text/html; charset=utf-8')

    def _mcp(self, method):
        if method != 'POST':return self._send(405,{'error':'Use POST'},headers={'Allow':'POST'})
        raw=self._read_raw()
        if demo_mode():
            handler=MCP
        else:
            token=session_token(self.headers)
            p=AUTH.principal(token)
            if not self.headers.get('Authorization','').lower().startswith('bearer '):AUTH.csrf(token,self.headers.get('X-CSRF-Token'))
            handler=mcp_server.MCPHandler(COPILOT,p)
        status,body=mcp_server.handle_http(handler,self.headers,raw)
        return self._send(status,body if body is not None else b'')

    def _identity_routes(self,method,path,body,q,p,token):
        # Called only after authentication and CSRF verification.
        if path=='/api/auth/me' and method=='GET':
            if demo_mode():return self._send(200,{'demo':True,'user':{'user_id':p.user_id,'role':p.role,'display_name':'Explicit demo'},'permissions':sorted(BOUNDARIES.get(p.role,set())),'csrf_token':''})
            return self._send(200,AUTH.me(token))
        if path=='/api/auth/logout' and method=='POST':
            if not demo_mode():AUTH.logout(token)
            return self._send(200,{'ok':True},headers={'Set-Cookie':self._cookie('',True)})
        if path=='/api/auth/change-password' and method=='POST':
            AUTH.change_password(token,body.get('current_password'),body.get('new_password'))
            return self._send(200,{'ok':True,'login_required':True},headers={'Set-Cookie':self._cookie('',True)})
        if path=='/api/auth/reauthenticate' and method=='POST':
            AUTH.reauthenticate(token,body.get('password'));return self._send(200,{'ok':True})
        if path=='/api/admin/roles' and method=='GET':
            AUTH.authorize(token,'manage_users')
            roles={k:v for k,v in ROLE_LABELS.items() if k!='coach' or os.environ.get('COPILOT_ALLOW_COACH_ASSIGNMENT')=='yes'}
            if p.role=='user_admin':roles={k:v for k,v in roles.items() if k in ('owner','staff','lender_analyst')}
            return self._send(200,{'roles':roles,'merchants':[{'id':m.merchant_id,'name':m.name} for m in COPILOT.merchants.values()]})
        if path=='/api/admin/users':
            if method=='GET':return self._send(200,{'users':AUTH.users(token,q.get('search',''),q.get('status',''),q.get('role',''))})
            if method=='POST':return self._send(201,AUTH.create_user(token,body))
        if path.startswith('/api/admin/users/'):
            parts=path.split('/');uid=parts[4]
            if len(parts)==5:
                if method=='GET':
                    users=AUTH.users(token);row=next((u for u in users if u['user_id']==uid),None)
                    if row is None:raise InputError('User not found',404)
                    return self._send(200,{'user':row,'history':AUTH.audit_records(token,{'target':uid})})
                if method=='PATCH':return self._send(200,AUTH.update_user(token,uid,body))
            if len(parts)==6 and method=='POST':
                if parts[5]=='suspend':return self._send(200,AUTH.update_user(token,uid,{'account_status':'suspended'}))
                return self._send(200,AUTH.account_action(token,uid,parts[5]))
        if path=='/api/security/config/export' and method=='GET':
            self.config_handled=True
            return self._send(200,AUTH.security_config.export(token),headers={'Content-Disposition':'attachment; filename="security-config.json"'})
        if path=='/api/security/config/validate' and method=='POST':
            self.config_handled=True
            return self._send(200,AUTH.security_config.preview(token,body))
        if path=='/api/security/config/import' and method=='POST':
            self.config_handled=True
            return self._send(200,AUTH.security_config.apply(token,body))
        if path=='/api/security/policies':
            if method=='GET':return self._send(200,AUTH.security_policies(token))
            if method=='PATCH':return self._send(200,AUTH.update_policies(token,body))
        if path=='/api/security/audit' and method=='GET':return self._send(200,{'records':AUTH.audit_records(token,q)})
        if path=='/api/security/events' and method=='GET':return self._send(200,AUTH.monitoring(token))
        if path=='/api/admin/staff-requests' and method=='GET':
            AUTH.authorize(token,'manage_users')
            with AUTH.db() as db:return self._send(200,{'requests':[dict(r) for r in db.execute('SELECT * FROM staff_access_requests ORDER BY created_at DESC')]})
        if path=='/api/consents':
            if method=='GET':return self._send(200,AUTH.consents(token,q.get('merchant')))
            if method=='POST':return self._send(201,AUTH.grant_consent(token,body))
        if path.startswith('/api/consents/') and path.endswith('/revoke') and method=='POST':
            return self._send(200,AUTH.revoke_consent(token,path.split('/')[3]))
        if path=='/api/staff-access-requests' and method=='POST':return self._send(201,AUTH.staff_request(token,body.get('merchant'),body.get('details')))
        if path=='/api/applications' and method=='GET':return self._send(200,{'applications':AUTH.application_list(token,q.get('merchant'))})
        if path.startswith('/api/applications/') and path.endswith('/review') and method=='POST':
            return self._send(200,AUTH.review_application(token,path.split('/')[3],body))
        return False

    def _dispatch(self, method):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        p = None
        token = ""
        self.config_handled=False
        self.request_id = secrets.token_hex(8)
        REQUEST_ID.set(self.request_id)
        try:
            body = {}
            if method in ("POST","PATCH") and path != "/mcp":
                body = json.loads(self._read_raw() or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("JSON object expected")
            if method in ('POST','PATCH'):
                origin=self.headers.get('Origin')
                scheme='https' if os.environ.get('COPILOT_HTTPS')=='yes' else 'http'
                if origin and origin != scheme+'://'+self.headers.get('Host',''):
                    raise AccessDenied('Origin not allowed')
                if not self.headers.get('Content-Type','').lower().startswith('application/json'):
                    raise InputError('Content-Type must be application/json')
            if method=='GET' and path=='/assets/common.css':
                with open(os.path.join(ROOT,'..','web','common.css'),'rb') as f:return self._send(200,f.read(),'text/css; charset=utf-8')
            if method=='GET' and path=='/login':return self._page('login.html')
            if method=='GET' and path=='/api/health':return self._send(200,{'ok':True,'auth_mode':'demo' if demo_mode() else 'authenticated','as_of':COPILOT.as_of.isoformat(),'agent_mode':'ai_agent' if ai_agent.configured() else 'rule_engine','mcp_endpoint':'/mcp','mcp_auth':'explicit_demo' if demo_mode() else 'session'})
            if method=='POST' and path=='/api/auth/login':
                token,csrf,must_change=AUTH.login(body.get('username'),body.get('password'),self.client_address[0])
                return self._send(200,{'ok':True,'csrf_token':csrf,'must_change_password':must_change},headers={'Set-Cookie':self._cookie(token)})
            if method=='POST' and path=='/api/auth/password-reset':
                AUTH.reset_password(body.get('token'),body.get('new_password'));return self._send(200,{'ok':True})
            if path=='/mcp':return self._mcp(method)
            p=principal_from_request(self.headers)
            token=session_token(self.headers)
            if not demo_mode() and method in ('POST','PATCH') and not self.headers.get('Authorization','').lower().startswith('bearer '):
                AUTH.csrf(token,self.headers.get('X-CSRF-Token'))
            result=self._identity_routes(method,path,body,q,p,token)
            if result is not False:return result
            if not demo_mode() and AUTH.me(token)['user']['must_change_password']:
                if method=='GET' and not path.startswith('/api/'):
                    return self._send(303,b'',headers={'Location':'/login'})
                raise AccessDenied('Change your temporary password first')
            if method=='GET' and path=='/assets/security-admin.js':
                AUTH.authorize(token,'manage_security')
                with open(os.path.join(ROOT,'..','web','security-admin.js'),'rb') as f:return self._send(200,f.read(),'text/javascript; charset=utf-8')
            if method=='GET' and path=='/assets/admin.js':
                with open(os.path.join(ROOT,'..','web','admin.js'),'rb') as f:return self._send(200,f.read(),'text/javascript; charset=utf-8')
            if method=='GET' and path=='/consents':
                require(p,'manage_consents');return self._page('consents.html')
            if method=='GET' and path=='/admin/users':
                AUTH.authorize(token,'manage_users');return self._page('users.html')
            if method=='GET' and path=='/admin/security':
                AUTH.authorize(token,'manage_security');return self._page('security.html')
            if method=='GET' and path=='/':
                if p.role in ('user_admin','security_admin'):return self._send(303,b'',headers={'Location':'/admin/users' if p.role=='user_admin' else '/admin/security'})
                return self._page('index.html')
            if method == "GET" and path == "/api/merchants":
                from copilot.tools_spec import execute
                result=execute(COPILOT,p,'list_merchants',{})['merchants']
                return self._send(200,[{**m,'id':m['merchant_id']} for m in result])
            mid = q.get("merchant") or body.get("merchant")
            if p.role in ("user_admin","security_admin"):
                raise AccessDenied("Administrative accounts cannot access merchant financial APIs")
            if mid not in COPILOT.merchants or mid not in p.merchant_ids:
                AUTH.audit("access_denied",p,target=path,result="denied",reason="merchant_scope",request_id=self.request_id)
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
            operation={'/api/security/config/export':'security_config_export','/api/security/config/validate':'security_config_validate','/api/security/config/import':'security_config_import'}.get(path)
            if operation and not self.config_handled:
                AUTH.security_config.rejected(session_token(self.headers),operation,e,'request_rejected')
            AUTH.audit("access_denied",p,target=path,result="denied",reason="authorization",request_id=self.request_id)
            code=getattr(e,"status",403)
            if code==401 and method=="GET" and not path.startswith("/api/"):
                return self._send(303,b"",headers={"Location":"/login"})
            return self._send(code, {"error": str(e),"request_id":self.request_id})
        except (PaymentError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            operation={'/api/security/config/export':'security_config_export','/api/security/config/validate':'security_config_validate','/api/security/config/import':'security_config_import'}.get(path)
            if operation and not self.config_handled:
                AUTH.security_config.rejected(session_token(self.headers),operation,e,'request_rejected')
            AUTH.audit("request_failed",p,target=path,result="failed",reason="invalid_input",request_id=self.request_id)
            return self._send(getattr(e,"status",400), {"error": str(e),"request_id":self.request_id})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PATCH(self):
        self._dispatch("PATCH")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    a = ap.parse_args()
    if demo_mode() and a.host not in ("127.0.0.1","localhost","::1"):
        ap.error("Explicit demo mode may bind only to localhost")
    mode = "AI agent" if ai_agent.configured() else "rule engine"
    print(f"SME Finance Copilot running on http://{a.host}:{a.port}  (chat: {mode}; "
          f"MCP: http://{a.host}:{a.port}/mcp; auth={'explicit demo' if demo_mode() else 'server sessions'})", flush=True)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
