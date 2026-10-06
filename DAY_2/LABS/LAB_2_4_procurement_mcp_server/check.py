"""Run while you work.   python check.py      No API key and no model needed in either part.
Part A tests security.py directly (no MCP needed): safe logging, constant-time auth, non-leaky 401, authorization rules.
Part B starts your REAL server (stdio as three roles, then HTTP) and talks to it with a real MCP client (needs `pip install mcp`).
Fails on the starter by design. Exit code 0 means every check passed."""
import asyncio
import json
import logging
import os
import pathlib
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
KEYS = {"PROC_KEY_ANALYST": secrets.token_hex(12), "PROC_KEY_APPROVER": secrets.token_hex(12), "PROC_KEY_DIRECTOR": secrets.token_hex(12)}
os.environ.update(KEYS)  # throw-away keys for this run only
import security  # noqa: E402

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


print("== Part A: security.py (no MCP, no key) ==")
secret = KEYS["PROC_KEY_APPROVER"]
check(security.authenticate(secret) and security.authenticate(secret).role == "approver", "authenticate: a valid key maps to its role")
check(security.authenticate("") is None and security.authenticate(secret[:-1] + "x") is None, "authenticate: empty and wrong keys give None")
source = (HERE / "security.py").read_text(encoding="utf-8")
check("compare_digest" in source, "authenticate uses hmac.compare_digest (constant time)")

record = logging.LogRecord("t", logging.INFO, "", 0, f"auth header=Bearer {secret} and raw {secret}", (), None)
record.fields = {"nested": {"k": f"x {secret} y"}, "list": [f"Bearer abc.def"]}
security.RedactingFilter().filter(record)
rendered = record.getMessage() + json.dumps(record.fields)
check(secret not in rendered and "abc.def" not in rendered, "RedactingFilter masks keys and Bearer tokens in message and nested fields")
check(security.MASK in rendered, "the mask text is visible, so a reader knows something was removed")

responses = {r: security.unauthorized_response("tok-" + r, r) for r in ("no_header", "wrong_scheme", "wrong_key")}
check(len({(tuple(h), b) for h, b in responses.values()}) == 1, "401 is identical for no header, wrong scheme and wrong key")
check(all(b"tok-" not in b and secret[:4].encode() not in b for _, b in responses.values()), "401 body never echoes the token or a key prefix")

analyst, approver, director = (security.Principal(security.USERS[r], r) for r in ("analyst", "approver", "director"))
limits = {"analyst": 0, "approver": 2500000, "director": 25000000}
po = {"supplier_id": "S-100", "requested_by": "lee.buyer", "amount_cents": 1840000}
active, suspended = {"status": "active"}, {"status": "suspended"}
check(security.check_role(analyst) and security.check_role(analyst)[0] == 403 and security.check_role(approver) is None, "analyst may not approve (403 forbidden); approver may")
check(security.check_po_rules(approver, po, active, limits) is None, "approver within limit on an active supplier: allowed")
check((security.check_po_rules(director, po, suspended, limits) or (0,))[0] == 422, "suspended supplier: 422 supplier_not_active")
check((security.check_po_rules(approver, {**po, "requested_by": approver.user}, active, limits) or (0, ""))[1] == "self_approval", "approving your own request: 403 self_approval")
over = security.check_po_rules(approver, {**po, "amount_cents": 6400000}, active, limits)
check(over and over[1] == "spend_limit_exceeded" and over[2].get("limit_cents") == 2500000, "over the role's limit: 403 spend_limit_exceeded with limit_cents")
check(security.check_po_rules(director, {**po, "amount_cents": 6400000}, active, limits) is None, "director may approve what an approver may not")
server_text = (HERE / "server.py").read_text(encoding="utf-8")
check(not re.search(r"^\s*print\((?!.*file=sys\.stderr)", server_text, re.M), "server.py has no print() to stdout (it would corrupt the stdio protocol)")
check("BearerAuthMiddleware(" in server_text.split("def main")[1], "main() wraps the HTTP app in BearerAuthMiddleware")

print("\n== Part B: your running server, real MCP client ==")
try:
    import client
    import httpx2  # noqa: F401
except ImportError as exc:
    print(f"(Part B skipped: {exc}. Run `pip install -r requirements.txt`)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

LOG = tempfile.NamedTemporaryFile(suffix=".log", delete=False).name
os.environ["PROC_LOG_FILE"] = LOG


async def stdio_role(role):
    async with client.open_stdio(role, open(os.devnull, "w")) as session:
        info = await client.explore(session)
        return info, (await client.run_plan(session, role) if role in client.ROLE_PLAN else [])


def outcome(plan):
    return [(r["po_id"], r["status"]) for r in plan]


try:
    info, plan = asyncio.run(stdio_role("approver"))
    check(plan and outcome(plan) == [("PO-2001", 200), ("PO-2003", 403), ("PO-2005", 403)], "stdio approver: PO-2001 ok, PO-2003 self-approval 403, PO-2005 over limit 403", str(outcome(plan)))
    check("get_po" in info["tools"] and "po://{po_id}" in info["resource_templates"], "server lists the get_po tool and the po://{po_id} resource template", f"{info['tools']} {info['resource_templates']}")
    check("PO-2001" in info["reads"].get("po://PO-2001", ""), "reading po://PO-2001 returns the purchase order")
    supplier_text = info["reads"].get("supplier://S-100", "")
    check("bank_account" not in supplier_text.replace("bank_account_masked", "") and "****" in supplier_text, "supplier resource masks the bank account")
    check(info.get("get_po_status") == "APPROVED", "get_po tool returns PO-2002 with status APPROVED")
    _, plan = asyncio.run(stdio_role("director"))
    check(outcome(plan) == [("PO-2005", 200), ("PO-2004", 422)], "stdio director: PO-2005 ok, PO-2004 (suspended supplier) 422", str(outcome(plan)))
    _, plan = asyncio.run(stdio_role("analyst"))
    check(outcome(plan) == [("PO-2001", 403)], "stdio analyst: approve is forbidden (403)", str(outcome(plan)))
except BaseException as exc:  # noqa: BLE001 - a crash here is evidence, report it
    leaves = [f"{type(x).__name__}: {x}" for x in client.flatten(exc)]
    check(False, "stdio sessions ran (a print() to stdout or a crash breaks the handshake)", "; ".join(leaves)[:200])

port = 8791
server = subprocess.Popen([sys.executable, str(HERE / "server.py"), "--transport", "http", "--port", str(port)], cwd=str(HERE),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
url = f"http://127.0.0.1:{port}/mcp"
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1)
        except urllib.error.HTTPError:
            break
        except OSError:
            time.sleep(0.2)
    bodies = []
    for header in (None, "Basic abc", "Bearer wrong-key-123456789"):
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json", **({"Authorization": header} if header else {})})
        try:
            urllib.request.urlopen(req, timeout=5)
            bodies.append((200, b""))
        except urllib.error.HTTPError as err:
            bodies.append((err.code, err.read()))
    check(all(code == 401 for code, _ in bodies), "HTTP: no header, wrong scheme and wrong key all get 401", str([c for c, _ in bodies]))
    check(len({b for _, b in bodies}) == 1 and b"wrong-key" not in bodies[2][1], "HTTP: the three 401 bodies are identical and do not echo the key")

    async def http_ok():
        async with client.open_http(url, KEYS["PROC_KEY_APPROVER"]) as session:
            return await client.run_plan(session, "approver")

    plan = asyncio.run(http_ok())
    check(outcome(plan) == [("PO-2001", 200), ("PO-2003", 403), ("PO-2005", 403)], "HTTP with a valid approver key behaves like stdio", str(outcome(plan)))
finally:
    server.terminate()
    server.wait(timeout=10)

log_text = pathlib.Path(LOG).read_text(encoding="utf-8") if pathlib.Path(LOG).exists() else ""
check(log_text and not any(key in log_text for key in KEYS.values()), "no API key appears in the server log", f"{len(log_text)} bytes of log")
pathlib.Path(LOG).unlink(missing_ok=True)
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
