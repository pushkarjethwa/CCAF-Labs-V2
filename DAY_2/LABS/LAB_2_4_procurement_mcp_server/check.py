"""Run while you work.   python check.py
Part A tests YOUR code directly with hand-made inputs: no API key, no model, and no server is started.
Part B reads evidence/stageN.json from the stages you have run (python lab.py --stage N).
Fails on the starter by design. Exit code 0 means every check passed."""
import contextlib
import hmac
import io
import json
import logging
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
EVIDENCE = HERE / "evidence"
os.environ["PROC_KEY_ANALYST"], os.environ["PROC_KEY_APPROVER"] = "prk_an_check_0123456789abcdef", "prk_ap_check_fedcba9876543210"
os.environ.pop("PROC_API_KEY", None)

import lab  # noqa: E402
import procurement_core as core  # noqa: E402
import procurement_db as pdb  # noqa: E402
from pydantic import TypeAdapter  # noqa: E402

results = []
KEYS = {"analyst": os.environ["PROC_KEY_ANALYST"], "approver": os.environ["PROC_KEY_APPROVER"]}


def check(description, test):
    """Run a test function that returns (ok, detail). A TODO that is still a stub counts as a failure, not a crash."""
    try:
        ok, detail = test()
    except NotImplementedError as stub:
        ok, detail = False, str(stub)
    except Exception as exc:  # noqa: BLE001 - show the student what broke
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail and not ok else ""))


def info(text):
    print(f"[info] {text}")


def plain(function):
    """The undecorated function, whatever the SDK's decorator returned."""
    return function if callable(function) else getattr(function, "fn", function)


core.STATE["sink"] = []  # collect the audit lines the tests cause instead of printing them


def gate(auth, role=None):
    core.STATE.update(auth=auth, principal=core.Principal("tester", role) if role else None)


print("== Part A: your code, tested directly (no API key, no server) ==")


def t_logging():
    root = logging.getLogger()
    saved = root.handlers[:]
    root.handlers.clear()
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            lab.setup_logging()
    finally:
        root.handlers[:] = saved
    return out.getvalue() == "" and "procurement" in err.getvalue(), f"stdout got {out.getvalue()[:40]!r}, stderr got {err.getvalue()[:40]!r}"


def t_no_print():
    code = "\n".join(line.split("#")[0] for line in pathlib.Path(lab.__file__).read_text(encoding="utf-8").splitlines())
    return re.search(r"\bprint\(", code) is None, "lab.py still calls print()"


check("TODO 1: setup_logging writes nothing to stdout and its log line goes to stderr", t_logging)
check("TODO 1: lab.py has no print() call (stdout is the protocol channel)", t_no_print)


def t_po_resource():
    data = json.loads(plain(lab.po_resource)("PO-2001"))
    return data["id"] == "PO-2001" and data["amount_cents"] == 1840000 and "approvals" in data, ""


def t_po_resource_unknown():
    try:
        plain(lab.po_resource)("PO-9999")
    except ValueError:
        return True, ""
    return False, "no ValueError for an unknown id"


check("TODO 2: the po resource returns the purchase order with its approvals", t_po_resource)
check("TODO 2: an unknown purchase order id raises ValueError", t_po_resource_unknown)


def t_pattern():
    adapter = TypeAdapter(lab.PoId)
    accepted = adapter.validate_python("PO-2001")
    rejected = 0
    for bad in ("po-2001", "PO-12", "PO-12345", "2001", "PO-2001; DROP"):
        try:
            adapter.validate_python(bad)
        except Exception:  # noqa: BLE001
            rejected += 1
    return accepted == "PO-2001" and rejected == 5, f"{rejected}/5 bad ids rejected"


def t_get_po_ok():
    gate(False)
    result = plain(lab.get_po)(None, "PO-2002")
    return not result.is_error and result.structured_content["status"] == "APPROVED" and result.structured_content["supplier_id"] == "S-102", ""


def t_get_po_unknown():
    gate(False)
    result = plain(lab.get_po)(None, "PO-9999")
    error = (result.structured_content or {}).get("error", {})
    return result.is_error and error.get("code") == "po_not_found", f"error: {error}"


check("TODO 3: PoId only accepts ids shaped like PO-2001", t_pattern)
check("TODO 3: get_po returns PO-2002 (status APPROVED)", t_get_po_ok)
check("TODO 3: an unknown id gives is_error with the code po_not_found", t_get_po_unknown)


def lint(config):
    return lab.lint_config(config)


def t_lint_shipped():
    configs = [json.loads((HERE / "CONFIGS" / name).read_text(encoding="utf-8")) for name in ("mcp.stdio.json", "mcp.http.json")]
    return all(lint(c) == [] for c in configs), ""


def t_lint_leaky():
    problems = lint(json.loads((HERE / "CONFIGS" / "mcp.leaky.json").read_text(encoding="utf-8")))
    rules = sorted(p.split()[0] for p in problems)
    return rules == ["R2", "R4", "R4", "R5"], f"found {rules}"


def t_lint_small():
    clean = {"mcpServers": {"a": {"type": "http", "url": "http://localhost:9/mcp", "headers": {"Authorization": "Bearer ${K}", "Content-Type": "application/json"}}}}
    literal = {"mcpServers": {"b": {"type": "stdio", "command": "python", "env": {"MY_API_KEY": "abc123"}}}}
    https = {"mcpServers": {"c": {"type": "http", "url": "https://x.example.com/mcp", "headers": {"X-Token": "abc"}}}}
    return lint(clean) == [] and [p.split()[0] for p in lint(literal)] == ["R4"] and [p.split()[0] for p in lint(https)] == ["R4"] and lint({}) == [], ""


check("TODO 4: the shipped stdio and http configs pass", t_lint_shipped)
check("TODO 4: the leaky config fails R2 (sse), R4 (two literal secrets) and R5 (plain http)", t_lint_leaky)
check("TODO 4: ${VAR} references and localhost pass; literals are caught; https is not R5", t_lint_small)


def t_auth_basic():
    return all(lab.authenticate(KEYS[r]) == r for r in KEYS), ""


def t_auth_bad():
    return lab.authenticate("") is None and lab.authenticate(None) is None and lab.authenticate(KEYS["approver"][:-1] + "x") is None and lab.authenticate("nope") is None, ""


def t_auth_work():
    counts, real, calls = [], hmac.compare_digest, {"n": 0}

    def counting(a, b):
        calls["n"] += 1
        return real(a, b)

    hmac.compare_digest = counting
    try:
        for token in (KEYS["analyst"], KEYS["approver"], "x" * 30):
            calls["n"] = 0
            lab.authenticate(token)
            counts.append(calls["n"])
    finally:
        hmac.compare_digest = real
    return len(set(counts)) == 1 and counts[0] == 2, f"comparisons: {counts}"


def t_roles():
    ok = lab.is_allowed("analyst", "get_po") and lab.is_allowed("analyst", "find_supplier") and not lab.is_allowed("analyst", "approve_po")
    return ok and lab.is_allowed("approver", "approve_po") and not lab.is_allowed("approver", "delete_po") and not lab.is_allowed("ghost", "get_po"), ""


def t_gate_403():
    gate(True, "analyst")
    result = plain(lab.approve_po)(None, "PO-2001")
    error = (result.structured_content or {}).get("error", {})
    return result.is_error and error.get("code") == "forbidden" and error.get("status") == 403, f"error: {error}"


def t_gate_401_and_ok():
    gate(True)
    nobody = plain(lab.get_po)(None, "PO-2002")
    lab.CON = pdb.connect()
    gate(True, "approver")
    done = plain(lab.approve_po)(None, "PO-2001")
    gate(False)
    return nobody.is_error and nobody.structured_content["error"]["status"] == 401 and not done.is_error and done.structured_content["status"] == "APPROVED", ""


check("TODO 5: authenticate maps each valid key to its role", t_auth_basic)
check("TODO 5: an empty, missing, one-character-off or unknown key gives None", t_auth_bad)
check("TODO 5: every key is compared, whatever the answer (constant work)", t_auth_work)
check("TODO 5: ROLE_TOOLS and is_allowed: analyst reads, approver approves, unknown is denied", t_roles)
check("TODO 5: the gate answers an analyst's approve_po with 403 forbidden", t_gate_403)
check("TODO 5: no caller gives 401; an approver may approve", t_gate_401_and_ok)


def t_redact():
    a, b = KEYS["analyst"], KEYS["approver"]
    text = f'{{"authorization": "Bearer {a}x", "note": "raw {b} and bearer abc.def"}}'
    cleaned = lab.redact(text)
    return a not in cleaned and b not in cleaned and "abc.def" not in cleaned and core.MASK in cleaned, f"result: {cleaned[:90]}"


def t_redact_plain():
    text = '{"event": "tool_call", "outcome": "ok", "role": "approver", "tool": "get_po"}'
    return lab.redact(text) == text, "harmless text must not change"


check("TODO 6: redact masks keys and Bearer tokens anywhere in a line", t_redact)
check("TODO 6: redact leaves a harmless line unchanged", t_redact_plain)

print("\n== Part B: your real runs (evidence/stageN.json) ==")
found = sorted(EVIDENCE.glob("stage*.json")) if EVIDENCE.exists() else []
if not found:
    print("(Part B skipped: run `python lab.py --stage 1` and the later stages first)")
for path in found:
    data = json.loads(path.read_text(encoding="utf-8"))
    n = data["stage"]
    print(f"\n-- stage {n} --")
    if n == 1:
        check("stage 1: the client connected to your stdio server", lambda d=data: (d["initialized"], "initialize failed or timed out"))
        check("stage 1: the client logged no JSON-RPC parse error", lambda d=data: (d["initialized"] and d["parse_errors"] == 0, f"{d['parse_errors']} parse errors"))
        check("stage 1: the server's log lines arrived on stderr", lambda d=data: (d["log_lines"] >= 1, ""))
    if n == 2:
        check("stage 2: the po://{po_id} template is listed and readable", lambda d=data: ("po://{po_id}" in d["templates"] and d["po_read"], f"templates: {d['templates']}"))
        check("stage 2: an unknown id is an error and the session survives", lambda d=data: (d["bad_id_error"] and d["session_alive"], ""))
        check("stage 2: the supplier resource masks the bank account", lambda d=data: (d["supplier_masked"], ""))
    if n == 3:
        c = data["calls"]
        check("stage 3: get_po works and unknown ids give po_not_found", lambda: (c["get_po PO-2002"]["is_error"] is False and c["get_po PO-9999 (unknown)"]["code"] == "po_not_found", ""))
        check("stage 3: the client sees the PO-#### pattern in the schema", lambda d=data: (bool(d["po_pattern"]), ""))
        check("stage 3: a badly formed id is rejected by the schema", lambda: (c["get_po 'po-1' (bad format)"]["is_error"] and not c["get_po 'po-1' (bad format)"]["structured"], ""))
        check("stage 3: business rules give supplier_not_active and po_not_pending", lambda: (c["approve_po PO-2004 (supplier suspended)"]["code"] == "supplier_not_active"
                                                                                           and c["approve_po PO-2002 (already approved)"]["code"] == "po_not_pending", ""))
    if n == 4:
        check("stage 4: the shipped configs pass and the leaky one fails", lambda d=data: (d["lint"]["mcp.stdio.json"] == [] and d["lint"]["mcp.http.json"] == [] and len(d["lint"]["mcp.leaky.json"]) == 4, ""))
    if n == 5:
        check("stage 5: five failures give 401, valid keys get through", lambda d=data: (d["statuses"] == [401] * 5 + [200, 200], str(d["statuses"])))
        check("stage 5: one identical 401 body", lambda d=data: (d["distinct_401_bodies"] == 1, ""))
        check("stage 5: constant work for first, last and unknown key", lambda d=data: (len(set(d["counts"])) == 1 and d["counts"][0] >= 2, str(d["counts"])))
        check("stage 5: analyst cannot approve, approver can", lambda d=data: (bool(d["matrix"]) and d["matrix"]["analyst"]["approve_po"] and not d["matrix"]["approver"]["approve_po"], ""))
        check("stage 5: the refusal is forbidden with status 403", lambda d=data: ((d["forbidden"] or {}).get("status") == 403, ""))
        check("stage 5: no key in the log", lambda d=data: (d["keys_in_log"] == [], f"leaked: {d['keys_in_log']}"))
        check("stage 5: startup without a key exits 2 and prints no key", lambda d=data: (d["refused"], ""))
    if n == 6:
        check("stage 6: stdio and HTTP give identical results", lambda d=data: (d["identical"], ""))
        check("stage 6: over HTTP the analyst gets 403 and the approver succeeds", lambda d=data: (d["analyst_denied"] and d["approver_ok"], ""))
        check("stage 6: the server log shows 401s and the audited denial", lambda d=data: (401 in d["log_statuses"] and d["denied_audited"], str(d["log_statuses"])))
        check("stage 6: no key appears in the server log", lambda d=data: (d["keys_in_log"] == [], f"leaked: {d['keys_in_log']}"))
        check("stage 6: the HTTP server was stopped", lambda d=data: (d["stopped"], ""))
print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
