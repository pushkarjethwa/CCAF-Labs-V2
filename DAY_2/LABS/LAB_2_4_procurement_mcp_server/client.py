"""Provided MCP client for the lab (GIVEN). Lists the server's capabilities and exercises it as one role.

    python client.py --transport stdio --role approver
    python client.py --transport http  --role analyst  --url http://127.0.0.1:8765/mcp
    python client.py --transport http  --role none     --url http://127.0.0.1:8765/mcp     # no credentials

Keys are read from the environment: PROC_KEY_ANALYST / PROC_KEY_APPROVER / PROC_KEY_DIRECTOR (the same variables the server reads).
Uses the mcp 2.3.0 client API: stdio_client, streamable_http_client(url, http_client=httpx2.AsyncClient(headers=...)).
Output is deterministic and never prints a key; the URL port is shown as <PORT>."""
import argparse
import asyncio
import contextlib
import json
import os
import pathlib
import re
import sys

import httpx2
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

HERE = pathlib.Path(__file__).resolve().parent
KEY_ENV = {"analyst": "PROC_KEY_ANALYST", "approver": "PROC_KEY_APPROVER", "director": "PROC_KEY_DIRECTOR"}
# what each role tries (PO ids from DATA/procurement_seed.json); order matters for the shared HTTP server
ROLE_PLAN = {"analyst": ["PO-2001"], "approver": ["PO-2001", "PO-2003", "PO-2005"], "director": ["PO-2005", "PO-2004"]}


def flatten(exc: BaseException):
    """Yield the leaf exceptions of (nested) ExceptionGroups. The 2.3.0 client reports an HTTP 401 as an
    ExceptionGroup whose leaf is MCPError(-32603 'Server returned an error response')."""
    if isinstance(exc, BaseExceptionGroup):
        for e in exc.exceptions:
            yield from flatten(e)
    else:
        yield exc


@contextlib.asynccontextmanager
async def open_stdio(role: str | None, errlog, instance_id: str = "", env: dict | None = None):
    """Launch server.py as a subprocess and talk MCP over its stdin/stdout. The key travels in PROC_API_KEY."""
    full = dict(os.environ if env is None else env)
    full.pop("PROC_API_KEY", None)
    if role in KEY_ENV and full.get(KEY_ENV[role]):
        full["PROC_API_KEY"] = full[KEY_ENV[role]]
    params = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py"), "--transport", "stdio",
                                                                 "--instance-id", instance_id],
                                   env=full, cwd=str(HERE))
    async with stdio_client(params, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@contextlib.asynccontextmanager
async def open_http(url: str, key: str | None):
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    async with httpx2.AsyncClient(headers=headers, timeout=30.0) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                yield session


def parse_tool_result(res) -> dict:
    """Normalise a CallToolResult: ok / error with the JSON detail the server put in the message."""
    text = res.content[0].text if res.content else ""
    out = {"is_error": bool(res.is_error)}
    if res.is_error:
        m = re.search(r"\{.*\}", text, re.S)
        try:
            out.update(json.loads(m.group(0)) if m else {"error": text[:80]})
        except ValueError:
            out["error"] = text[:80]
    else:
        out["structured"] = res.structured_content
    return out


async def explore(session) -> dict:
    """Capability listing + resource reads (no state changes)."""
    tools = await session.list_tools()
    res = await session.list_resources()
    tpl = await session.list_resource_templates()
    out = {"tools": sorted(t.name for t in tools.tools),
           "resources": sorted(r.uri for r in res.resources),
           "resource_templates": sorted(t.uri_template for t in tpl.resource_templates)}
    reads = {}
    for uri in ("supplier://S-100", "po://PO-2001", "procurement://policy/spend-limits"):
        try:
            r = await session.read_resource(uri)
            reads[uri] = r.contents[0].text
        except Exception as e:                      # a missing resource is evidence, not a crash
            reads[uri] = f"ERROR {type(e).__name__}"
    out["reads"] = reads
    found = parse_tool_result(await session.call_tool("find_supplier", {"query": "ind", "category": "maintenance"}))
    out["find_supplier_ids"] = sorted(s["id"] for s in (found.get("structured") or {}).get("result", []))
    if "get_po" in out["tools"]:
        po = parse_tool_result(await session.call_tool("get_po", {"po_id": "PO-2002"}))
        out["get_po_status"] = (po.get("structured") or {}).get("status")
    return out


async def run_plan(session, role: str) -> list[dict]:
    results = []
    for po_id in ROLE_PLAN[role]:
        r = parse_tool_result(await session.call_tool("approve_po", {"po_id": po_id, "comment": f"lab run by {role}"}))
        results.append({"po_id": po_id, "role": role, "is_error": r["is_error"],
                        "status": r.get("status", 200 if not r["is_error"] else None), "error": r.get("error")})
    return results


async def _cli(args) -> int:
    key = os.environ.get(KEY_ENV.get(args.role, ""), "") if args.role != "none" else ""
    shown = re.sub(r":\d+/", ":<PORT>/", args.url) if args.transport == "http" else "stdio"
    print(f"transport={args.transport} role={args.role} target={shown}")
    opener = open_stdio(args.role, sys.stderr) if args.transport == "stdio" else open_http(args.url, key or None)
    try:
        async with opener as session:
            info = await explore(session)
            for k in ("tools", "resources", "resource_templates", "find_supplier_ids"):
                print(f"{k}: {info[k]}")
            for uri, txt in sorted(info["reads"].items()):
                print(f"read {uri}: {txt[:70].replace(chr(10), ' ')}")
            if args.role in ROLE_PLAN:
                for r in await run_plan(session, args.role):
                    print(f"approve_po {r['po_id']} as {r['role']}: {'OK' if not r['is_error'] else 'DENIED'} "
                          f"status={r['status']} error={r['error']}")
    except BaseException as e:                       # noqa: BLE001 - report, do not crash
        leaves = [f"{type(x).__name__}({getattr(x, 'code', '')})" for x in flatten(e)]
        print(f"connection failed: {leaves}  (a 401 looks like MCPError(-32603) on the 2.3.0 client)")
        return 1
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    ap.add_argument("--role", choices=["analyst", "approver", "director", "none"], default="analyst")
    ap.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    sys.exit(asyncio.run(_cli(ap.parse_args())))
