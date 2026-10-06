"""Run while you work.   python check.py
Part A tests YOUR code directly with hand-made failures (no API key needed, uses the mock DB and a simulated clock).
Part B reads evidence/evidence.json from a real run (`python lab.py`), where Claude is the agent.
Fails on the starter by design. Exit code 0 means every check passed."""
import json
import pathlib
import sys

import lab
from payroll_db import PayrollDB, PayrollError, SimClock

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"
EXPECTED = {"PAY_PERIOD_CLOSED": ("tool", False), "EMPLOYEE_NOT_FOUND": ("input", False),
            "HR_APPROVAL_REQUIRED": ("permission", False), "PAYROLL_DB_LOCKED": ("environment", True)}
KEYS = {"error_code", "category", "retryable", "message", "hint"}
ESC_KEYS = {"type", "request_id", "status", "error_code", "required_role", "employee_id", "period", "amount_cents",
            "currency", "threshold_cents", "reason", "requested_by", "original_call"}
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def parse(text):
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except (TypeError, ValueError):
        return None


def adjust(key="K1", employee="E1001", period="2026-09", cents=15000):
    return {"employee_id": employee, "period": period, "amount_cents": cents, "reason": "test", "idempotency_key": key}


def run_call(name, args, lock=0, ctx=None):
    clock = SimClock()
    db = PayrollDB(clock)
    db.arm_lock(lock)
    ctx = ctx or lab.RunContext("t")
    content, is_error = lab.execute_with_policy(db, clock, name, args, ctx)
    return content, is_error, db, clock, ctx


print("== Part A: your code, tested directly (no API key) ==")
check(all(c in lab.ERROR_CATALOG for c in list(EXPECTED) + ["UNEXPECTED_ERROR"]), "catalog has all 4 codes plus UNEXPECTED_ERROR")
check(all(lab.ERROR_CATALOG.get(c, {}).get("category") == v[0] and lab.ERROR_CATALOG.get(c, {}).get("retryable") == v[1] for c, v in EXPECTED.items()),
      "catalog classifies category and retryable as specified")

closed = run_call("apply_adjustment", adjust(period="2026-08"))
payload = parse(closed[0])
check(payload is not None and KEYS <= set(payload), "an error tool_result is JSON with error_code/category/retryable/message/hint")
check(payload is not None and len(str(payload.get("hint", ""))) > 20 and "2026-09" in str(payload.get("hint", "")),
      "hint is actionable and names the next open period (2026-09)")
check(closed[2].calls.count(("apply_adjustment", "E1001")) == 1, "closed period is tried once, never retried")

class Weird(PayrollError):
    code = "WEIRD_NEW_CODE"

unknown = parse(lab.to_tool_result(Weird("something new broke")))
check(unknown is not None and unknown.get("retryable") is False and lab.policy_for("WEIRD_NEW_CODE").max_attempts == 1,
      "unknown error code fails closed (non-retryable, 1 attempt)")

recover = run_call("apply_adjustment", adjust(key="K5"), lock=2)
check(not recover[1] and len(recover[2].adjustments) == 1 and recover[2].calls.count(("apply_adjustment", "E1001")) == 3,
      "transient lock: retried and recovered, exactly one row written", f"db calls {recover[2].calls.count(('apply_adjustment', 'E1001'))}")
check(recover[3].sleeps == sorted(recover[3].sleeps) and len(recover[3].sleeps) == 2 and recover[3].sleeps[1] > recover[3].sleeps[0],
      "backoff grows between retries", str(recover[3].sleeps))

forever = run_call("apply_adjustment", adjust(key="K6"), lock=-1)
body = parse(forever[0]) or {}
check(forever[1] and 2 <= forever[2].calls.count(("apply_adjustment", "E1001")) <= 5 and sum(forever[3].sleeps) <= 10.0,
      "permanent lock: bounded attempts (2-5) and total wait <= 10s", f"{forever[2].calls.count(('apply_adjustment', 'E1001'))} calls, waited {sum(forever[3].sleeps)}s")
check(body.get("retryable") is False and (body.get("details") or {}).get("retries_exhausted") is True,
      "exhausted retries: retryable=false and details.retries_exhausted=true")

big = run_call("apply_adjustment", adjust(key="K4", employee="E1004", cents=1250000))
request = big[4].escalations[0] if big[4].escalations else {}
check(len(big[4].escalations) == 1 and big[2].calls.count(("apply_adjustment", "E1004")) == 1, "over-threshold: one DB attempt, one escalation, no retry")
check(ESC_KEYS <= set(request) and request.get("request_id") == "HRA-K4" and request.get("status") == "PENDING",
      "approval request is complete (request_id HRA-K4, status PENDING)", f"missing {sorted(ESC_KEYS - set(request))}")
check((parse(big[0]) or {}).get("details", {}).get("approval_request_id") == "HRA-K4", "tool_result carries details.approval_request_id")

clock, ctx = SimClock(), lab.RunContext("again")
db = PayrollDB(clock)
args = adjust(period="2026-07", key="K7")
first = lab.execute_with_policy(db, clock, "apply_adjustment", args, ctx)
before = len(db.calls)
second = lab.execute_with_policy(db, clock, "apply_adjustment", args, ctx)
check(len(db.calls) == before and (parse(second[0]) or {}).get("details", {}).get("repeat_blocked") is True,
      "repeating a failed call is blocked without touching the DB (details.repeat_blocked)")

if not EVIDENCE_FILE.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your real run with Claude (evidence.json) ==")
sc = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))["scenarios"]
check(sorted(sc) == [f"S{i}" for i in range(1, 7)], "all 6 scenarios were run", str(sorted(sc)))
for sid, row in sorted(sc.items()):
    check(row["status"] == row["expected_status"], f"{sid} ({row['title']}) ended {row['expected_status']}", f"got {row['status']}")
    check(not row["runaway"], f"{sid} no runaway retries")
if "S4" in sc:
    check(len(sc["S4"]["escalations"]) == 1, "S4 filed exactly one approval request")
if "S1" in sc and "S5" in sc:
    check(sum(1 for o, _ in sc["S5"]["db_calls"] if o == "apply_adjustment") <= 5, "S5 recovered within the retry budget")
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
