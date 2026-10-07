"""Run while you work.   python check.py
Part A tests YOUR code with hand-made failures: no API key, the mock database and a simulated clock.
Part B reads evidence/stageN.json from the stages you have run with Claude (python lab.py --stage N).
Fails on the starter by design. Exit code 0 means every check passed."""
import json
import pathlib
import sys

import lab
import payroll_core as core
from payroll_db import PayrollDB, PayrollError, SimClock

HERE = pathlib.Path(__file__).parent
EVIDENCE = HERE / "evidence"
EXPECTED = {"PAY_PERIOD_CLOSED": ("tool", False), "EMPLOYEE_NOT_FOUND": ("input", False),
            "HR_APPROVAL_REQUIRED": ("permission", False), "PAYROLL_DB_LOCKED": ("environment", True)}
KEYS = {"error_code", "category", "retryable", "message", "hint"}
ESC_KEYS = {"type", "request_id", "status", "error_code", "required_role", "employee_id", "period", "amount_cents",
            "currency", "threshold_cents", "reason", "requested_by", "original_call"}
results = []


def check(description, test):
    """Run a test function that returns (ok, detail). A TODO that is still a stub counts as a failure, not a crash."""
    try:
        ok, detail = test()
    except NotImplementedError as stub:
        ok, detail = False, str(stub)
    except Exception as exc:  # noqa: BLE001 - show the student what broke
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def info(text):
    print(f"[info] {text}")


def parse(text):
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except (TypeError, ValueError):
        return None


def adjust(key="K1", employee="E1001", period="2026-09", cents=15000):
    return {"employee_id": employee, "period": period, "amount_cents": cents, "reason": "test", "idempotency_key": key}


def run_call(args, lock=0, ctx=None, stage=5, db=None, clock=None):
    clock = clock or SimClock()
    db = db or PayrollDB(clock)
    db.arm_lock(lock)
    ctx = ctx or core.RunContext("t")
    content, is_error = core.execute_with_policy(db, clock, "apply_adjustment", args, ctx, stage)
    return content, is_error, db, clock, ctx


def n_apply(db, employee="E1001"):
    return db.calls.count(("apply_adjustment", employee))


print("== Part A: your code, tested directly (no API key) ==")
check("TODO 1: the catalog has the 4 codes plus UNEXPECTED_ERROR", lambda: (all(c in lab.ERROR_CATALOG for c in list(EXPECTED) + ["UNEXPECTED_ERROR"]), ""))
check("TODO 1: category and retryable are classified as specified",
      lambda: (all(lab.ERROR_CATALOG.get(c, {}).get("category") == v[0] and lab.ERROR_CATALOG.get(c, {}).get("retryable") == v[1] for c, v in EXPECTED.items()), ""))


def t_closed_json():
    run = run_call(adjust(period="2026-08"), stage=2)
    payload = parse(run[0])
    return payload is not None and KEYS <= set(payload) and run[1], "" if payload else "the tool_result is not JSON"


def t_closed_hint():
    payload = parse(run_call(adjust(period="2026-08"), stage=2)[0]) or {}
    hint = str(payload.get("hint", ""))
    return len(hint) > 20 and "2026-09" in hint, f"hint: {hint[:70]}"


class Weird(PayrollError):
    code = "WEIRD_NEW_CODE"


def t_unknown_fails_closed():
    body = parse(lab.to_tool_result(Weird("something new broke"))) or {}
    return body.get("retryable") is False and lab.policy_for("WEIRD_NEW_CODE").max_attempts == 1, ""


def t_missing_placeholder():
    exc = PayrollError("closed", period="2026-08")  # no next_open_period given
    exc.code = "PAY_PERIOD_CLOSED"
    body = parse(lab.to_tool_result(exc))
    return body is not None and "hint" in body, ""


check("TODO 2: an error tool_result is JSON with error_code, category, retryable, message, hint", t_closed_json)
check("TODO 2: the closed-period hint is actionable and names the next open period (2026-09)", t_closed_hint)
check("TODO 2: a hint placeholder with no value does not crash", t_missing_placeholder)
check("TODOs 2-3: an unknown error code fails closed (not retryable, one attempt)", t_unknown_fails_closed)


def t_closed_once():
    run = run_call(adjust(period="2026-08"), stage=3)
    return n_apply(run[2]) == 1, f"{n_apply(run[2])} database calls"


def t_recover():
    run = run_call(adjust(key="K5"), lock=2, stage=3)
    return not run[1] and len(run[2].adjustments) == 1 and n_apply(run[2]) == 3, f"{n_apply(run[2])} database calls, {len(run[2].adjustments)} rows"


def t_backoff():
    sleeps = run_call(adjust(key="K5"), lock=2, stage=3)[3].sleeps
    return len(sleeps) == 2 and sleeps[1] > sleeps[0], str(sleeps)


def t_bounded():
    run = run_call(adjust(key="K6"), lock=-1, stage=3)
    return run[1] and 2 <= n_apply(run[2]) <= 5 and sum(run[3].sleeps) <= 10.0, f"{n_apply(run[2])} calls, waited {sum(run[3].sleeps)}s"


def t_exhausted():
    body = parse(run_call(adjust(key="K6"), lock=-1, stage=3)[0]) or {}
    return body.get("retryable") is False and (body.get("details") or {}).get("retries_exhausted") is True, ""


def t_repeat_blocked():
    clock, ctx = SimClock(), core.RunContext("again")
    db = PayrollDB(clock)
    args = adjust(period="2026-07", key="K7")
    run_call(args, ctx=ctx, db=db, clock=clock, stage=3)
    before = len(db.calls)
    second = run_call(args, ctx=ctx, db=db, clock=clock, stage=3)
    return len(db.calls) == before and (parse(second[0]) or {}).get("details", {}).get("repeat_blocked") is True, ""


check("TODO 3: a closed period is tried once and never retried", t_closed_once)
check("TODO 3: a transient lock is retried and recovers with exactly one row written", t_recover)
check("TODO 3: the wait grows between retries (backoff)", t_backoff)
check("TODO 3: a lock that never clears is bounded (2-5 attempts, at most 10 s of waiting)", t_bounded)
check("TODO 3: exhausted retries return retryable=false and details.retries_exhausted=true", t_exhausted)
check("TODO 3: repeating a failed call is blocked without touching the database", t_repeat_blocked)


def t_escalation():
    run = run_call(adjust(key="K4", employee="E1004", cents=1250000), stage=4)
    return len(run[4].escalations) == 1 and n_apply(run[2], "E1004") == 1, f"{len(run[4].escalations)} escalations, {n_apply(run[2], 'E1004')} database calls"


def t_request_complete():
    request = run_call(adjust(key="K4", employee="E1004", cents=1250000), stage=4)[4].escalations[0]
    return ESC_KEYS <= set(request) and request["request_id"] == "HRA-K4" and request["status"] == "PENDING", f"missing {sorted(ESC_KEYS - set(request))}"


def t_request_linked():
    run = run_call(adjust(key="K4", employee="E1004", cents=1250000), stage=4)
    return (parse(run[0]) or {}).get("details", {}).get("approval_request_id") == "HRA-K4", ""


check("TODO 4: an over-threshold adjustment makes one database call and one escalation, no retry", t_escalation)
check("TODO 4: the approval request is complete (request_id HRA-K4, status PENDING)", t_request_complete)
check("TODO 4: the tool_result carries details.approval_request_id", t_request_linked)

cases = json.loads((HERE / "data" / "broken_conversations.json").read_text(encoding="utf-8"))
for case in cases:
    check(f"TODO 5: preflight {'catches' if case['expect_caught'] else 'accepts'}: {case['title']}",
          lambda case=case: (bool(lab.preflight(case["messages"])) == case["expect_caught"], ""))

print("\n== Part B: your real runs with Claude (evidence/stageN.json) ==")
found = sorted(EVIDENCE.glob("stage*.json")) if EVIDENCE.exists() else []
if not found:
    print("(Part B skipped: run `python lab.py --stage 1` and the later stages first)")
for path in found:
    data = json.loads(path.read_text(encoding="utf-8"))
    stage, rows, totals = data["stage"], data["rows"], data["totals"]
    print(f"\n-- stage {stage}: {core.STAGE_TITLES[stage]} --")
    info(f"{totals['right']}/{totals['n']} tickets ended with the expected status; {totals['apply_calls']} database writes tried; waited {totals['wait_s']:.1f}s")
    if stage >= 3:
        check(f"stage {stage}: no runaway retries", lambda t=totals: (t["runaway"] == 0, ""))
        if "S6" in rows:
            check(f"stage {stage}: S6 (lock never clears) stays within the budget", lambda r=rows["S6"]: (r["apply_calls"] <= 8, f"{r['apply_calls']} apply attempts"))
        if "S5" in rows:
            check(f"stage {stage}: S5 (transient lock) is recovered", lambda r=rows["S5"]: (r["status"] == "applied", f"status {r['status']}"))
    if stage >= 4 and "S4" in rows:
        check(f"stage {stage}: S4 filed exactly one approval request", lambda r=rows["S4"]: (len(r["escalations"]) == 1, f"{len(r['escalations'])} requests"))
    if stage >= 5:
        check("stage 5: at least 5 of the 6 tickets ended as expected", lambda t=totals: (t["right"] >= 5 or t["n"] < 6, f"{t['right']}/{t['n']}"))
        check("stage 5: the preflight table is right for all five conversations",
              lambda d=data: (bool(d.get("preflight")) and all(v["caught"] == v["expect_caught"] for v in d["preflight"].values()), ""))
    if stage == 1:
        info("stage 1 is the baseline: runaway retries and unparsed statuses are expected here")
print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
