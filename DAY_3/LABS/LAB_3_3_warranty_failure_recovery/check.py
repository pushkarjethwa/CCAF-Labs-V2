"""check.py - Part A tests your recovery layer against Demo 3C's ground truth (no API key). Part B checks the live run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import inspect
import json
import sys

import lab
import warranty_core as core

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def guarded(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # a TODO that crashes is reported as a failure, not a traceback
        return f"{type(exc).__name__}: {exc}"


E = core.ServiceError
print("PART A - your recovery layer, tested with no model and no API key\n")
print("TODO 1 - classify (by status and code, never by message text)")
for label, exc, want in [("503 unavailable", E(503, "E_UNAVAILABLE", "x"), "environment"), ("504 timeout", E(504, "E_TIMEOUT", "x"), "environment"),
                         ("403 forbidden", E(403, "E_FORBIDDEN", "x"), "permission"), ("renamed argument", E(422, "E_ARG_RENAMED", "x"), "tool"),
                         ("schema rejected", E(422, "E_SCHEMA_REJECTED", "x"), "tool"), ("wrong coverage rule", E(422, "E_COVERAGE_MISMATCH", "x"), "reasoning"),
                         ("404 not found", E(404, "E_NOT_FOUND", "x"), "reasoning"), ("corrupt adapter reply", RuntimeError("corrupt frame"), "unknown")]:
    got = guarded(lab.classify, exc)
    check(got == want, f"{label} is classified as {want}", f"you returned {got!r}")
got = guarded(lab.classify, E(503, "E_UNAVAILABLE", "403 forbidden: permission denied"))
check(got == "environment", "the message text is ignored: a 503 whose message says 'forbidden' is still environment", f"you returned {got!r}")

print("\nTODO 2 - RECOVERY, checked against the chaos ground truth (6 faults x 4 steps)")
for fault in [f for f in core.PLANS["faults"] if core.PLANS["faults"][f]["family"] != "reasoning"]:
    want = core.EXPECTED[fault]
    runs = [guarded(core.run_chain, lab.HOOKS, fault, step) for step in core.STEPS]
    ok = all(isinstance(r, tuple) and r[0] == want["outcome"][step] and r[1] == want["attempts"] for r, step in zip(runs, core.STEPS))
    got = [r[:2] if isinstance(r, tuple) else r for r in runs[:1]]
    check(ok, f"{fault}: outcome and attempts match the ground truth on all 4 steps (expected {want['attempts']} attempt(s) at the faulted step)", f"first run gave {got}")

executor = core.ResilientExecutor(core.Injector(None, None), lab.HOOKS)
bad = {"serial": "HX20481977", "issue_type": "battery_defect", "coverage_rule_id": "R-WRONG", "customer_id": "CUS-1042"}
stops = [guarded(executor.run, "create_claim", bad) for _ in range(3)]
check(all(isinstance(s, dict) for s in stops) and [s.get("stop") for s in stops] == [None, None, "escalated"],
      "a model that keeps sending a wrong rule is corrected twice, then a human is called", f"stops: {[s.get('stop') if isinstance(s, dict) else s for s in stops]}")
good = {**bad, "coverage_rule_id": "R-BASIC-DEFECT"}
outage = core.ResilientExecutor(core.Injector("env_outage", "create_claim"), lab.HOOKS)
guarded(outage.run, "create_claim", good)
guarded(outage.run, "create_claim", good)
check(len(outage.alerts) == 1, "two calls into the same outage raise exactly ONE alert", f"alerts: {outage.alerts}")

print("\nTODO 3 - the corrective message")
msg = guarded(lab.corrective_message, E(422, "E_COVERAGE_MISMATCH", "rule is wrong"))
check(isinstance(msg, str) and "check_warranty_terms" in msg and "rule_id" in msg, "for a wrong coverage rule it tells the model to call check_warranty_terms and use the rule_id it returns", f"you returned {msg!r}")
msg = guarded(lab.corrective_message, E(422, "E_BAD_SERIAL_FORMAT", "serial must be two capital letters then eight digits"))
check(isinstance(msg, str) and "serial must be two capital letters then eight digits" in msg, "for any other error it quotes the error's own message", f"you returned {msg!r}")

print("\nTODO 4 - the Claude call")
check("NotImplementedError" not in inspect.getsource(lab.ask), "the ask function makes a Claude API call (the placeholder line is gone)", "replace the raise NotImplementedError line in TODO 4")

print("\nPART B - TODO 4 and the live agent (needs `python lab.py` with a key; tolerant of normal model variation)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    rows = {r["fault"]: r for r in saved["rows"]}
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    check(rows["tool_drift"]["status"] == "completed" and rows["tool_drift"]["faulted_step_attempts"] == 2,
          "tool_drift: the agent finished after exactly one retry with the renamed argument", f"got {rows['tool_drift']['status']}, {rows['tool_drift']['faulted_step_attempts']} attempt(s)")
    check(rows["env_outage"]["status"] == "paused_alerted" and rows["env_outage"]["faulted_step_attempts"] == 3 and len(rows["env_outage"]["alerts"]) == 1,
          "env_outage: three attempts with backoff, then the run paused and ONE alert was raised", f"got {rows['env_outage']['status']}, {rows['env_outage']['faulted_step_attempts']} attempt(s)")
    check(rows["permission"]["status"] == "escalated" and rows["permission"]["faulted_step_attempts"] == 1,
          "permission: ONE attempt, then escalated to a human (a blanket retry would have made three)", f"got {rows['permission']['status']}, {rows['permission']['faulted_step_attempts']} attempt(s)")
    check(rows["reasoning"]["status"] in ("completed", "escalated"), "reasoning: the model was corrected and either finished or was handed to a human, never retried blindly",
          f"got {rows['reasoning']['status']}")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
