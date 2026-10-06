"""server.py - the procurement MCP server (MCP Python SDK 2.3.0: MCPServer, not FastMCP).

Run by hand:
    python server.py --transport stdio      (a client launches it; needs PROC_API_KEY and PROC_KEY_* in the environment)
    python server.py --transport http --port 8765

You implement TODO 4 (resource), 5 (tool), 7 (HTTP auth) and remove the print() calls (stdout is the protocol channel!).
The rules themselves (TODO 1, 2, 3, 6) live in security.py. `python check.py` tests everything and needs no API key.

Three MCP ideas in this file:
  resource  = read-only data a client can fetch by URI (supplier://S-100)      @mcp.resource
  tool      = an action Claude can ask to run (find_supplier, approve_po)      @mcp.tool
  transport = stdio (local process, key in the environment) or streamable HTTP (Bearer header)
"""
import argparse
import json
import os
import sys

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

import procurement_db as pdb
import security
from security import log_event

mcp = MCPServer("procurement", instructions="Procurement data and approvals. Authenticate with an API key; approvals are limited by role and spend limit.")
CON = pdb.connect()


# ---------------------------------------------------------------- result models (the schema the client sees)
class SupplierSummary(BaseModel):
    id: str
    name: str
    category: str
    status: str
    rating: float


class POView(BaseModel):
    id: str
    supplier_id: str
    amount_cents: int
    currency: str
    status: str
    requested_by: str
    description: str
    approvals: list[dict]


class ApprovalResult(BaseModel):
    po_id: str
    status: str
    approved_by: str
    role: str
    amount_cents: int


def fail(status, error, **detail):
    """Raise a tool error whose message is machine-readable JSON."""
    raise ToolError(json.dumps({"status": status, "error": error, **detail}, sort_keys=True))


def caller(ctx):
    """Who is calling? HTTP: re-check the Authorization header (defence in depth). stdio: the process owner."""
    request = getattr(ctx.request_context, "request", None)
    principal = STDIO_PRINCIPAL if request is None else security.principal_from_header(request.headers.get("authorization", ""))
    if principal is None:
        fail(401, "unauthenticated")
    return principal


STDIO_PRINCIPAL = None  # set in main() for the stdio transport


# ---------------------------------------------------------------- resources
@mcp.resource("supplier://{supplier_id}", mime_type="application/json")
def supplier_resource(supplier_id: str) -> str:
    """One supplier record (worked example). The bank account is masked: resources are context handed to a model."""
    supplier = pdb.supplier_row(CON, supplier_id)
    if supplier is None:
        raise ValueError(f"unknown supplier {supplier_id}")
    supplier["bank_account_masked"] = pdb.mask_account(supplier.pop("bank_account"))
    return json.dumps(supplier, sort_keys=True)


@mcp.resource("procurement://policy/spend-limits", mime_type="application/json")
def spend_limit_policy() -> str:
    """Fixed resource: the approval limits per role, in cents."""
    return json.dumps(pdb.spend_limits(), sort_keys=True)


# TODO 4: add the resource template  po://{po_id}  (application/json). Return the PO including its approvals
#   (pdb.po_row); raise ValueError for an unknown id. Copy the supplier example's shape, minus the print.
@mcp.resource("po://{po_id}", mime_type="application/json")
def po_resource(po_id: str) -> str:
    """One purchase order with its approval history."""
    po = pdb.po_row(CON, po_id)
    if po is None:
        raise ValueError(f"unknown purchase order {po_id}")
    return json.dumps(po, sort_keys=True)


# ---------------------------------------------------------------- tools
@mcp.tool()
def find_supplier(query: str, ctx: Context, category: str | None = None, status: str | None = None, limit: int = 10) -> list[SupplierSummary]:
    """Search suppliers by (partial) name, optionally filtered by category and status. Sorted by id."""
    p = caller(ctx)
    rows = pdb.search_suppliers(CON, query, category, status, limit)
    log_event("tool_call", tool="find_supplier", user=p.user, role=p.role, query=query, hits=len(rows))
    return [SupplierSummary(**{k: r[k] for k in SupplierSummary.model_fields}) for r in rows]


# TODO 5: add the tool  get_po(po_id: str, ctx: Context) -> POView.  Unknown id: fail(404, "po_not_found", po_id=po_id).
#   The docstring becomes the tool description Claude reads: say what it returns. Call caller(ctx) first.
@mcp.tool()
def get_po(po_id: str, ctx: Context) -> POView:
    """Read one purchase order (amount, status, requester, approval history). Read-only; does not approve anything."""
    p = caller(ctx)
    po = pdb.po_row(CON, po_id)
    if po is None:
        fail(404, "po_not_found", po_id=po_id)
    log_event("tool_call", tool="get_po", user=p.user, role=p.role, po_id=po_id)
    return POView(**po)


@mcp.tool()
def approve_po(po_id: str, ctx: Context, comment: str = "") -> ApprovalResult:
    """Approve a PENDING purchase order. Subject to role and spend-limit rules."""
    p = caller(ctx)
    # TODO 6 (wire-up): call security.check_role(p) FIRST (before any PO lookup), then the 404 and 409 checks,
    #   then security.check_po_rules(p, po, supplier, limits). A denial is (status, code, detail): call
    #   log_event("tool_denied", ...) and fail(status, code, **detail). The rules are in security.py.
    denial = security.check_role(p)
    if denial:
        log_event("tool_denied", tool="approve_po", user=p.user, role=p.role, po_id=po_id, error=denial[1])
        fail(denial[0], denial[1], **denial[2])
    po = pdb.po_row(CON, po_id)
    if po is None:
        fail(404, "po_not_found", po_id=po_id)
    if po["status"] != "PENDING":
        fail(409, "po_not_pending", po_id=po_id, status=po["status"])
    denial = security.check_po_rules(p, po, pdb.supplier_row(CON, po["supplier_id"]), pdb.spend_limits())
    if denial:
        log_event("tool_denied", tool="approve_po", user=p.user, role=p.role, po_id=po_id, error=denial[1])
        fail(denial[0], denial[1], **denial[2])
    pdb.record_decision(CON, po_id, p.user, p.role, comment)
    log_event("tool_ok", tool="approve_po", user=p.user, role=p.role, po_id=po_id, amount_cents=po["amount_cents"])
    return ApprovalResult(po_id=po_id, status="APPROVED", approved_by=p.user, role=p.role, amount_cents=po["amount_cents"])


# ---------------------------------------------------------------- HTTP authentication wrapper
class BearerAuthMiddleware:
    """ASGI middleware: answer 401 unless the Bearer key is valid. Wrap the streamable-HTTP app in it (TODO 7)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # lifespan must pass through or the MCP session manager never starts
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        header = headers.get("authorization", "")
        token = security.extract_bearer(header)
        if security.authenticate(token) is not None:
            return await self.app(scope, receive, send)
        reason = "no_header" if not header else ("wrong_scheme" if not token else "wrong_key")
        response_headers, body = security.unauthorized_response(token, reason)
        await send({"type": "http.response.start", "status": 401, "headers": response_headers})
        await send({"type": "http.response.body", "body": body})


# ---------------------------------------------------------------- entry point
def main():
    global STDIO_PRINCIPAL
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    ring = security.load_keyring()  # fail closed when no keys are configured
    log_event(f"server starting transport={args.transport} roles={sorted(ring)}")

    if args.transport == "stdio":
        STDIO_PRINCIPAL = security.authenticate(os.environ.get("PROC_API_KEY", ""))
        if STDIO_PRINCIPAL is None:
            print("refusing to start: PROC_API_KEY missing or invalid", file=sys.stderr)
            raise SystemExit(2)
        mcp.run(transport="stdio")
    else:
        import uvicorn
        app = mcp.streamable_http_app()
        # TODO 7: wrap the app in BearerAuthMiddleware. The starter serves it WITHOUT authentication.
        app = BearerAuthMiddleware(app)
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
