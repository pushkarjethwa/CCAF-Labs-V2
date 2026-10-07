"""Lab 2.4 - Procurement MCP server: build it, break it, and lock it down, one stage at a time.

This lab continues Demo 2D (the same method and the same stages), on a procurement server: suppliers, purchase orders (PO-2001 ...) and
approvals. The starter works, but it pollutes the protocol channel, has no po:// resource and no get_po tool, accepts any key, and logs keys.

WHAT YOU EDIT (six places, each marked "TODO n of 6"; the guide in README.md gives the exact code for each)
  TODO 1  setup_logging     -> stage 1: logs go to stderr, never to stdout
  TODO 2  po_resource       -> stage 2: the po://{po_id} resource template
  TODO 3  PoId, get_po      -> stage 3: a validated tool with a structured error
  TODO 4  lint_config       -> stage 4: find secrets and legacy settings in an MCP client config
  TODO 5  ROLE_TOOLS, authenticate, is_allowed -> stage 5: who are you (401), what may you do (403)
  TODO 6  redact            -> stage 5: a log line never holds a key

HOW TO RUN (in order)
  python lab.py --stage 1      a stdio server, and the stdout trap
  python lab.py --stage 2      resources
  python lab.py --stage 3      validated tools and structured errors
  python lab.py --stage 4      your own client, the host view, the config linter
  python lab.py --stage 5      authentication, roles, safe logging
  python lab.py --stage 6      the same server over HTTP, and the denial demo (needs no new code)
  python check.py              pass/fail in plain words
(python lab.py --serve is how the stages start this file as a server. You never run it by hand.)
"""
import argparse
import hmac
import json
import logging
import re
import sys
from typing import Annotated
from urllib.parse import urlparse

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import CallToolResult
from pydantic import Field

import procurement_core as core
import procurement_db as pdb

mcp = MCPServer("procurement", instructions="Procurement data and approvals. approve_po WRITES and needs the 'approver' role.")
CON = pdb.connect()


# ======================================================================================
# TODO 1 of 6 - logging (stage 1).
# stdout is the JSON-RPC wire of a stdio server, so anything printed there corrupts it. The starter prints a banner without a
# newline, which glues itself to the first reply and makes initialize time out. Send log lines to STDERR with the logging module.
# ======================================================================================
def setup_logging():
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="procurement %(levelname)s %(message)s")
    logging.getLogger("procurement").info("procurement server starting")


# ======================================================================================
# Given: a fixed resource, a resource template and a tool. Read them first: the next TODOs copy their shape.
#   resource = read-only data the APPLICATION attaches, fetched by URI      @mcp.resource
#   tool     = an action the MODEL asks to run                              @mcp.tool
# ======================================================================================
@mcp.resource("procurement://suppliers/index", mime_type="application/json")
def supplier_index() -> str:
    """Index of all suppliers: id, name and status."""
    rows = pdb.search_suppliers(CON, "", None, None, 50)
    return json.dumps([{"id": r["id"], "name": r["name"], "status": r["status"]} for r in rows])


@mcp.resource("supplier://{supplier_id}", mime_type="application/json")
def supplier_resource(supplier_id: str) -> str:
    """One supplier. The bank account is masked: a resource is context handed to a model."""
    supplier = pdb.supplier_row(CON, supplier_id)
    if supplier is None:
        raise ValueError(f"unknown supplier {supplier_id}")
    supplier["bank_account_masked"] = pdb.mask_account(supplier.pop("bank_account"))
    return json.dumps(supplier, sort_keys=True)


@mcp.tool()
def find_supplier(ctx: Context, query: str, category: str | None = None) -> CallToolResult:
    """Search suppliers by (partial) name, optionally by category. Returns id, name, category, status and rating."""
    def work():
        rows = pdb.search_suppliers(CON, query, category, None, 10)
        return {"count": len(rows), "suppliers": [{k: r[k] for k in ("id", "name", "category", "status", "rating")} for r in rows]}
    return core.run(ctx, "find_supplier", work)


# ======================================================================================
# TODO 2 of 6 - the po://{po_id} resource template (stage 2).
# Return the purchase order, with its approvals, as JSON text (pdb.po_row gives it). An unknown id raises ValueError.
# ======================================================================================
@mcp.resource("po://{po_id}", mime_type="application/json")
def po_resource(po_id: str) -> str:
    po = pdb.po_row(CON, po_id)
    if po is None:
        raise ValueError(f"unknown purchase order {po_id}")
    return json.dumps(po, sort_keys=True)


# ======================================================================================
# TODO 3 of 6 - the get_po tool (stage 3).
# PoId is the schema layer: only ids shaped like PO-2001 get through, and the client sees the pattern. The tool is the business layer:
# an unknown id raises core.ProcError("po_not_found", ...), which the gate (core.run) turns into a structured error.
# ======================================================================================
PoId = Annotated[str, Field(pattern=r"^PO-\d{4}$", description="Purchase order id such as PO-2001")]


@mcp.tool()
def get_po(ctx: Context, po_id: PoId) -> CallToolResult:
    """Look up one purchase order by id. Returns supplier, amount, status and approvals. Error po_not_found if unknown."""
    def work():
        po = pdb.po_row(CON, po_id)
        if po is None:
            raise core.ProcError("po_not_found", f"No purchase order {po_id}")
        return po
    return core.run(ctx, "get_po", work)


@mcp.tool()
def approve_po(ctx: Context, po_id: str, comment: str = "") -> CallToolResult:
    """WRITE (role 'approver' only): approve a PENDING purchase order whose supplier is active. Not idempotent."""
    def work():
        po = pdb.po_row(CON, po_id)
        if po is None:
            raise core.ProcError("po_not_found", f"No purchase order {po_id}", 404)
        if po["status"] != "PENDING":
            raise core.ProcError("po_not_pending", f"{po_id} is {po['status']}", 409)
        if pdb.supplier_row(CON, po["supplier_id"])["status"] != "active":
            raise core.ProcError("supplier_not_active", f"The supplier of {po_id} is not active", 422)
        user, role = core.who(ctx)
        pdb.record_decision(CON, po_id, user, role, comment)
        return {"po_id": po_id, "status": "APPROVED", "approved_by": user, "role": role}
    return core.run(ctx, "approve_po", work)


@mcp.prompt()
def review_po(po_id: str) -> str:
    """Template: review one purchase order with the procurement tools."""
    return (f"You are a procurement reviewer. Read the resource po://{po_id}, check its supplier with find_supplier, "
            "and summarise the risks. Do not call approve_po unless I ask.")


# ======================================================================================
# TODO 4 of 6 - the config linter (stage 4).
# config is the parsed .mcp.json of an MCP client: {"mcpServers": {name: {type, url, headers, env, ...}}}. Return a list of problems
# (an empty list means the file is fine). Three rules, each problem starting with its rule number:
#   R2  type "sse" is deprecated                          -> "R2 <name>: ..."
#   R4  a header or env entry whose name has key, token, secret or authorization must be a ${VAR} reference, not a literal
#   R5  plain http:// to any host except 127.0.0.1 or localhost sends the key in clear text
# ======================================================================================
def lint_config(config):
    problems = []
    for name, server in config.get("mcpServers", {}).items():
        if server.get("type") == "sse":
            problems.append(f"R2 {name}: type 'sse' is deprecated, use 'http'")
        url = server.get("url", "")
        if url.startswith("http://") and urlparse(url).hostname not in ("127.0.0.1", "localhost"):
            problems.append(f"R5 {name}: plain http to a non-local host")
        for key, value in {**server.get("headers", {}), **server.get("env", {})}.items():
            if re.search(r"(?i)key|token|secret|authorization", key) and "${" not in value:
                problems.append(f"R4 {name}: {key} holds a literal secret, use ${{VAR}}")
    return problems


# ======================================================================================
# TODO 5 of 6 - who are you, and what may you do (stage 5).
# ROLE_TOOLS says which tools a role may call. A role that is not listed, or a tool that is not listed for it, is forbidden (deny by default).
# authenticate(token) returns the role whose key equals token, or None. core.load_keyring() gives {role: key}. Compare EVERY key with
# hmac.compare_digest on bytes and never return early, so the time taken does not reveal which key matched. An empty token is never valid.
# ======================================================================================
ROLE_TOOLS = {"analyst": {"find_supplier", "get_po"}, "approver": {"find_supplier", "get_po", "approve_po"}}


def authenticate(token):
    found = None
    for role, key in core.load_keyring().items():
        if token and hmac.compare_digest(token.encode(), key.encode()):
            found = role
    return found


def is_allowed(role, tool):
    return tool in ROLE_TOOLS.get(role, set())


# ======================================================================================
# TODO 6 of 6 - a log line never holds a key (stage 5).
# Every audit line passes through redact(text) before it is written. Mask (1) anything shaped like "Bearer <token>" and (2) every value
# from core.known_secrets(), wherever it appears, with core.MASK. Return the cleaned text.
# ======================================================================================
def redact(text):
    text = re.sub(r"(?i)bearer\s+[\w.~+/=-]+", "Bearer " + core.MASK, text)
    for secret in core.known_secrets():
        text = text.replace(secret, core.MASK)
    return text


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(setup_logging=setup_logging, lint_config=lint_config, authenticate=authenticate, is_allowed=is_allowed, redact=redact)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4, 5, 6])
    parser.add_argument("--serve", action="store_true", help="run as the MCP server (the stages start this for you)")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--auth", choices=["on", "off"], default="off")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.serve:
        core.serve(mcp, args)
    elif args.stage:
        core.run_stage(args.stage)
    else:
        parser.error("give --stage N")


if __name__ == "__main__":
    main()
