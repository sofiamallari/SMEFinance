"""
Model Context Protocol (MCP) server for SME Finance Copilot. Zero dependencies.

Lets real AI agents (Microsoft Copilot Studio, GitHub Copilot agent mode in VS Code,
Claude Desktop, or any MCP client) discover and call the copilot's tools.

Transports
  stdio            python -m copilot.mcp_server
  Streamable HTTP  POST /mcp on the web server (python -m copilot.server),
                   or standalone: python -m copilot.mcp_server --http --port 8001

Protocol
  * Handshake-based revisions 2025-03-26 / 2025-06-18 / 2025-11-25: `initialize`,
    `notifications/initialized`, `ping`, `tools/list`, `tools/call`.
  * Stateless revision 2026-07-28: `server/discover`; protocol version accepted per request
    from params._meta["io.modelcontextprotocol/protocolVersion"]; serverInfo returned in result _meta.
  JSON responses only (no SSE needed: every tool returns a single result).

Security
  * Identity for MCP callers comes from configuration, never from tool arguments:
      COPILOT_MCP_ROLE       owner | coach | lender_analyst | demo_guest   (default: owner)
      COPILOT_MCP_MERCHANTS  comma list of merchant IDs                    (default: all)
      COPILOT_MCP_CONSENT    yes | no  (owner data-sharing consent)        (default: yes)
  * HTTP: Origin header validated (DNS-rebinding protection); optional API key via
      COPILOT_MCP_API_KEY  -> clients send  Authorization: Bearer <key>  or  X-API-Key: <key>
  * Every tools/call goes through Copilot.call(): tiers, consent, audit log.
  * T3 (application submission) and T4 (credit approval, funds) are not exposed over MCP.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import sys
from urllib.parse import urlparse

from copilot import tools_spec
from copilot.auth import demo_mode, AuthError
from copilot.security import AccessDenied, ApprovalRequired, Principal, sanitize_input

SERVER_INFO = {"name": "sme-finance-copilot", "title": "SME Finance Copilot", "version": "1.2.0"}
SUPPORTED_VERSIONS = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26"]
LATEST = SUPPORTED_VERSIONS[0]
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_SERVER = "io.modelcontextprotocol/serverInfo"
INSTRUCTIONS = (
    "Tools for an advisory finance copilot serving ASEAN micro and small businesses (synthetic sandbox data). "
    "Start with list_merchants to get merchant IDs. Use ask_copilot for open questions, or the specific tools "
    "for structured data. All financing figures are indicative; the copilot cannot approve credit or move money."
)

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603


def principal_from_env(merchants) -> Principal:
    if not demo_mode():
        return Principal("unauthenticated-mcp", "anonymous")
    role = os.environ.get("COPILOT_MCP_ROLE", "owner")
    if role not in ("owner", "coach", "lender_analyst", "demo_guest"):
        role = "demo_guest"
    ids = os.environ.get("COPILOT_MCP_MERCHANTS", "").strip()
    allowed = {m.strip() for m in ids.split(",") if m.strip()} if ids else set(merchants)
    consent = os.environ.get("COPILOT_MCP_CONSENT", "yes").lower() == "yes"
    return Principal(user_id=f"mcp-{role}", role=role, merchant_ids=allowed & set(merchants),
                     consents={"share_with_lender", "coach_access"} if consent else set())


class MCPHandler:
    """Transport-independent JSON-RPC dispatcher."""

    def __init__(self, copilot, principal: Principal | None = None):
        self.copilot = copilot
        self.principal = principal or principal_from_env(copilot.merchants)
        self.negotiated = None

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _err(id_, code, msg, data=None):
        e = {"code": code, "message": msg}
        if data is not None:
            e["data"] = data
        return {"jsonrpc": "2.0", "id": id_, "error": e}

    @staticmethod
    def _ok(id_, result):
        return {"jsonrpc": "2.0", "id": id_, "result": result}

    def _capabilities(self):
        return {"tools": {"listChanged": False}}

    def _tools_list(self):
        return [{"name": t["name"], "title": t["name"].replace("_", " ").title(), "description": t["description"],
                 "inputSchema": t["inputSchema"], "annotations": t["annotations"]} for t in tools_spec.TOOLS]

    # ------------------------------------------------------------ dispatch
    def handle(self, msg):
        """Returns a response dict, or None for notifications."""
        if isinstance(msg, list):  # batches (2025-03-26)
            out = [r for r in (self.handle(m) for m in msg) if r is not None]
            return out or None
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            return self._err(msg.get("id") if isinstance(msg, dict) else None, INVALID_REQUEST, "Invalid Request")
        method, id_ = msg["method"], msg.get("id")
        params = msg.get("params") or {}
        if not isinstance(params, dict):
            return self._err(id_, INVALID_PARAMS, "params must be an object")
        is_notification = "id" not in msg
        if is_notification:
            return None  # notifications/initialized, notifications/cancelled, etc.

        # per-request version (2026-07-28 stateless clients)
        req_version = (params.get("_meta") or {}).get(META_VERSION)
        if req_version and req_version not in SUPPORTED_VERSIONS:
            return self._err(id_, INVALID_PARAMS, "Unsupported protocol version",
                             {"supported": SUPPORTED_VERSIONS, "requested": req_version})
        try:
            result = self._route(method, params)
        except _MethodNotFound:
            return self._err(id_, METHOD_NOT_FOUND, f"Method not found: {method}")
        except _BadParams as e:
            return self._err(id_, INVALID_PARAMS, str(e))
        except Exception as e:  # never leak stack traces
            return self._err(id_, INTERNAL_ERROR, f"Internal error: {type(e).__name__}")
        if req_version or self.negotiated == "2026-07-28":
            result.setdefault("_meta", {})[META_SERVER] = SERVER_INFO
        return self._ok(id_, result)

    def _route(self, method, params):
        if method == "initialize":
            requested = params.get("protocolVersion")
            self.negotiated = requested if requested in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[1]
            return {"protocolVersion": self.negotiated, "capabilities": self._capabilities(),
                    "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS}
        if method == "server/discover":
            return {"supportedVersions": SUPPORTED_VERSIONS, "capabilities": self._capabilities(),
                    "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": self._tools_list()}
        if method == "tools/call":
            return self._call(params)
        if method in ("resources/list", "prompts/list"):
            return {method.split("/")[0]: []}
        raise _MethodNotFound()

    def _call(self, params):
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in tools_spec.BY_NAME:
            raise _BadParams(f"Unknown tool: {name}")
        if not isinstance(args, dict):
            raise _BadParams("arguments must be an object")
        if "question" in args:
            clean = sanitize_input(str(args["question"]))
            args = {**args, "question": clean["text"]}
        try:
            result = tools_spec.execute(self.copilot, self.principal, name, args)
            return {"content": [{"type": "text", "text": tools_spec.to_text(result)}],
                    "structuredContent": result, "isError": False}
        except (AccessDenied, ApprovalRequired) as e:
            return _tool_error(f"Access denied: {e}")
        except (ValueError, KeyError) as e:
            return _tool_error(f"Invalid input: {e}")


class _MethodNotFound(Exception):
    pass


class _BadParams(Exception):
    pass


def _tool_error(text):
    # Tool execution errors are reported in the result so the model can self-correct (MCP convention)
    return {"content": [{"type": "text", "text": text}], "isError": True}


# ------------------------------------------------------------------ HTTP helpers
def origin_allowed(origin: str | None) -> bool:
    """DNS-rebinding protection. No Origin (server-to-server, e.g. Copilot Studio) is allowed.
    Browser origins must be localhost or listed in COPILOT_MCP_ALLOWED_ORIGINS."""
    if not origin:
        return True
    extra = {o.strip() for o in os.environ.get("COPILOT_MCP_ALLOWED_ORIGINS", "").split(",") if o.strip()}
    if origin in extra:
        return True
    host = urlparse(origin).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")


def api_key_ok(headers) -> bool:
    key = os.environ.get("COPILOT_MCP_API_KEY", "")
    if not key:
        return True
    auth = headers.get("Authorization", "")
    given = auth[7:] if auth.lower().startswith("bearer ") else headers.get("X-API-Key", "")
    return hmac.compare_digest(given.encode(), key.encode())


def handle_http(mcp: MCPHandler, headers, raw: bytes):
    """Returns (status, body_dict_or_None). Used by copilot/server.py for POST /mcp."""
    if not origin_allowed(headers.get("Origin")):
        return 403, {"jsonrpc": "2.0", "error": {"code": INVALID_REQUEST, "message": "Origin not allowed"}}
    if not demo_mode() and not mcp.principal.authenticated:
        return 401, {"error":"Authenticated session required"}
    if demo_mode() and not api_key_ok(headers):
        return 401, {"jsonrpc": "2.0", "error": {"code": INVALID_REQUEST, "message": "Unauthorized"}}
    try:
        msg = json.loads(raw or b"null")
    except json.JSONDecodeError:
        return 400, {"jsonrpc": "2.0", "id": None, "error": {"code": PARSE_ERROR, "message": "Parse error"}}
    resp = mcp.handle(msg)
    if resp is None:
        return 202, None  # notification accepted
    return 200, resp


# ------------------------------------------------------------------ stdio
def run_stdio(copilot):
    if demo_mode():
        mcp = MCPHandler(copilot)
    else:
        from copilot.auth import AuthStore
        from copilot.modules.transactions import TransactionStore
        auth = AuthStore(os.environ.get('COPILOT_IDENTITY_DB','logs/identity.sqlite3'),copilot.merchants)
        token = os.environ.get('COPILOT_MCP_SESSION_TOKEN','')
        principal = auth.principal(token)
        copilot.identity_store=auth
        copilot.audit.sink=auth.financial_audit
        TransactionStore(copilot,os.environ.get('COPILOT_TRANSACTION_FILE','logs/manual_transactions.jsonl'))
        mcp = MCPHandler(copilot,principal)
    print(f"[sme-finance-copilot MCP] stdio ready; role={mcp.principal.role}", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": PARSE_ERROR, "message": "Parse error"}}
        else:
            resp = mcp.handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, default=str, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="SME Finance Copilot MCP server")
    ap.add_argument("--http", action="store_true", help="serve Streamable HTTP at /mcp instead of stdio")
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8001)))
    a = ap.parse_args()
    if a.http:
        os.environ["HOST"], os.environ["PORT"] = a.host, str(a.port)
        from copilot import server
        sys.argv = [sys.argv[0], "--host", a.host, "--port", str(a.port)]
        server.main()
        return
    from copilot.agent import Copilot
    log_dir = os.environ.get("COPILOT_LOG_DIR", "logs")
    run_stdio(Copilot(audit_path=os.path.join(log_dir, "mcp_audit.jsonl"),
                      exec_path=os.path.join(log_dir, "mcp_execution.jsonl")))


if __name__ == "__main__":
    main()
