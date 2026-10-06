"""LAB 2.3 - Payroll agent: typed tool errors, bounded retries, escalation.

Run:   python lab.py [--only S4]     (needs an API key; 6 short agent runs, a few cents)
Check: python check.py               (Part A needs NO key: it tests your code directly)

What you build (search for TODO):
  Section 2  TODO 1-5  error catalog, retry policy table, structured tool_result, approval request
  Section 3  TODO A-D  execute_with_policy: bounded retry, no repeats, escalate permission errors
Sections 1 and 4 are given: the tools and the agent loop (read them, they are short).
payroll_db.py is a mock back end (do not edit); its clock is simulated, so waiting costs nothing.
"""
import argparse
import json
import pathlib
from dataclasses import dataclass, field

from claude_client import MODEL_BALANCED, ask, text_of, tool_calls_of, print_usage
from payroll_db import PayrollDB, PayrollError, SimClock

HERE = pathlib.Path(__file__).parent
RUNAWAY_CAP = 12  # safety net so the starter ends; a correct policy never needs it


# ---------------------------------------------------------------- 1. TOOLS (given)
def _schema(props, required):
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


S = {"type": "string"}
TOOL_SCHEMAS = [
    {"name": "lookup_employee",
     "description": "Look up one employee by id (format E####). Returns name, department and status. Read-only and safe to repeat.",
     "input_schema": _schema({"employee_id": S}, ["employee_id"])},
    {"name": "check_pay_period",
     "description": "Return the status (open|closed) of a pay period (YYYY-MM) and the next open period that can still accept adjustments. Read-only.",
     "input_schema": _schema({"period": S}, ["period"])},
    {"name": "apply_adjustment",
     "description": ("Apply a one-off pay adjustment (positive = pay, negative = deduction) to an employee for an open pay period. "
                     "Writes to the payroll ledger. Safe to retry ONLY with the same idempotency_key. "
                     "Errors come back as JSON with error_code, category, retryable, hint."),
     "input_schema": _schema({"employee_id": S, "period": S, "amount_cents": {"type": "integer"}, "reason": S, "idempotency_key": S},
                             ["employee_id", "period", "amount_cents", "reason", "idempotency_key"])},
]


# ---------------------------------------------------------------- 2. ERROR TAXONOMY (you)
@dataclass(frozen=True)
class RetryPolicy:
    """max_attempts counts the first try. Wait before retry k (k = attempts so far, from 1)
    is min(base_delay_s * factor ** (k - 1), max_delay_s)."""
    max_attempts: int = 1
    base_delay_s: float = 0.0
    factor: float = 2.0
    max_delay_s: float = 0.0


def delay_before_retry(policy, attempts_made):
    return min(policy.base_delay_s * policy.factor ** (attempts_made - 1), policy.max_delay_s)


# TODO 1: one entry per error code: {"category": tool|input|permission|environment, "retryable": bool, "action": short verb phrase, "hint": template}
#   Codes: PAY_PERIOD_CLOSED, EMPLOYEE_NOT_FOUND, HR_APPROVAL_REQUIRED, PAYROLL_DB_LOCKED, and UNEXPECTED_ERROR (fail-closed fallback).
#   A hint may contain {placeholders} filled from exc.details, e.g. {next_open_period}. Write hints that tell the model WHAT TO DO.
ERROR_CATALOG = {
    "PAY_PERIOD_CLOSED": {"category": "tool", "retryable": False, "action": "offer the next open period",
                          "hint": "Period {period} is closed and will not reopen. Do not retry. Tell the requester and offer the next open period, {next_open_period}."},
    "EMPLOYEE_NOT_FOUND": {"category": "input", "retryable": False, "action": "ask the requester to correct the id",
                           "hint": "No such employee. Do not retry the same id. Ask the requester to confirm the employee id."},
    "HR_APPROVAL_REQUIRED": {"category": "permission", "retryable": False, "action": "escalate to an HR manager",
                             "hint": "This amount needs HR_MANAGER approval. Do not retry or split the amount. An approval request was filed; report its id and stop."},
    "PAYROLL_DB_LOCKED": {"category": "environment", "retryable": True, "action": "retry with backoff",
                          "hint": "The ledger is temporarily locked. Retrying the same call with the same idempotency_key is safe."},
    "UNEXPECTED_ERROR": {"category": "tool", "retryable": False, "action": "stop and report",
                         "hint": "Unexpected failure. Do not retry. Report the problem to the requester and stop."},
}

# TODO 2: retry table. Which codes are worth retrying, how many attempts in total, what backoff? Everything else gets DEFAULT_POLICY.
RETRY_POLICY = {"PAYROLL_DB_LOCKED": RetryPolicy(max_attempts=4, base_delay_s=1.0, factor=2.0, max_delay_s=8.0)}
DEFAULT_POLICY = RetryPolicy(max_attempts=1)


def policy_for(code):
    # TODO 3: look the code up in RETRY_POLICY. An unknown code must FAIL CLOSED (one attempt, no retry).
    return RETRY_POLICY.get(code, DEFAULT_POLICY)


def to_tool_result(exc, extra=None, retryable=None, hint=None):
    """Turn a PayrollError into the JSON string the model sees as tool_result content.
    extra is merged into "details"; retryable / hint override the catalog (used when retries run out)."""
    # TODO 4: return json.dumps of {"error_code", "category", "retryable", "message", "hint", "details"}, sort_keys=True.
    #   Unknown codes use the UNEXPECTED_ERROR entry. Fill the hint template from exc.details (missing keys must not crash).
    code = exc.code if exc.code in ERROR_CATALOG else "UNEXPECTED_ERROR"
    entry = ERROR_CATALOG[code]
    details = {**exc.details, **(extra or {})}

    class _Blank(dict):
        def __missing__(self, key):
            return "unknown"

    text = hint if hint is not None else entry["hint"].format_map(_Blank(details))
    payload = {"error_code": code, "category": entry["category"], "retryable": entry["retryable"] if retryable is None else retryable,
               "message": exc.message, "hint": text, "details": details}
    return json.dumps(payload, sort_keys=True)


def build_approval_request(tool_name, args, exc):
    """The structured request handed to a human approver when a permission error happens."""
    # TODO 5: return a COMPLETE dict. Keys: type "hr_approval_request", request_id "HRA-" + idempotency_key, status "PENDING",
    #   error_code, required_role, employee_id, period, amount_cents, currency "USD", threshold_cents, reason,
    #   requested_by "payroll-agent", original_call {tool, idempotency_key}.
    d = exc.details
    return {"type": "hr_approval_request", "request_id": "HRA-" + args["idempotency_key"], "status": "PENDING", "error_code": exc.code,
            "required_role": d.get("required_role"), "employee_id": d.get("employee_id"), "period": d.get("period"),
            "amount_cents": d.get("amount_cents"), "currency": "USD", "threshold_cents": d.get("threshold_cents"),
            "reason": d.get("reason"), "requested_by": "payroll-agent",
            "original_call": {"tool": tool_name, "idempotency_key": args["idempotency_key"]}}


# ---------------------------------------------------------------- 3. EXECUTION POLICY (you)
@dataclass
class RunContext:
    """Per-scenario recorder (given)."""
    scenario_id: str
    trace: list = field(default_factory=list)  # one entry per attempt that reached the DB
    results: list = field(default_factory=list)  # what the model saw
    escalations: list = field(default_factory=list)
    final_failures: dict = field(default_factory=dict)  # canonical call -> final error content
    runaway: bool = False


def run_tool(db, name, args):
    """Run one tool call on the mock DB. Never raises. Returns (content, is_error, exception or None)."""
    handlers = {"lookup_employee": db.lookup_employee, "check_pay_period": db.check_pay_period, "apply_adjustment": db.apply_adjustment}
    try:
        if name not in handlers:
            raise PayrollError(f"Unknown tool {name}")
        return json.dumps(handlers[name](**args), sort_keys=True), False, None
    except PayrollError as exc:
        return to_tool_result(exc), True, exc
    except TypeError as exc:  # the model sent bad arguments
        wrapped = PayrollError(f"Invalid arguments for {name}: {exc}")
        return to_tool_result(wrapped), True, wrapped


def execute_with_policy(db, clock, name, args, ctx):
    """Run one tool call under the retry policy. Returns (tool_result content, is_error)."""
    # TODO A: if this exact call already failed for good (ctx.final_failures), do NOT touch the DB: return the stored error with details.repeat_blocked = true.
    # TODO B: retry only codes whose policy allows it; wait clock.sleep(delay_before_retry(...)) between attempts; stop at policy.max_attempts.
    # TODO C: when the budget is spent, return the error with retryable=False, details {attempts, retries_exhausted: true} and a hint telling the model to stop.
    # TODO D: permission errors are NEVER retried: build_approval_request(...), append to ctx.escalations, put its request_id in details.approval_request_id.
    call_key = name + json.dumps(args, sort_keys=True)
    if call_key in ctx.final_failures:
        stored = json.loads(ctx.final_failures[call_key])
        stored["details"] = {**stored.get("details", {}), "repeat_blocked": True}
        ctx.trace.append({"tool": name, "attempt": 0, "kind": "blocked", "error_code": stored["error_code"]})
        return json.dumps(stored, sort_keys=True), True
    attempt = 0
    while True:
        attempt += 1
        content, is_error, exc = run_tool(db, name, args)
        ctx.trace.append({"tool": name, "attempt": attempt, "kind": "db", "error_code": exc.code if exc else None})
        if not is_error:
            return content, False
        policy = policy_for(exc.code)
        if exc.code == "HR_APPROVAL_REQUIRED":
            request = build_approval_request(name, args, exc)
            ctx.escalations.append(request)
            content = to_tool_result(exc, extra={"approval_request_id": request["request_id"]})
        elif policy.max_attempts > 1 and attempt < policy.max_attempts:
            clock.sleep(delay_before_retry(policy, attempt))
            continue
        elif attempt > 1:
            content = to_tool_result(exc, extra={"attempts": attempt, "retries_exhausted": True}, retryable=False,
                                     hint="Retries are used up. Do NOT call this tool again. Tell the requester it failed for a temporary reason and stop.")
        ctx.final_failures[call_key] = content
        return content, True


# ---------------------------------------------------------------- 4. AGENT LOOP (given)
SYSTEM = """You are the payroll adjustment agent. Apply the requested adjustment with the tools.
Tool failures arrive as is_error tool_results containing JSON: error_code, category, retryable, message, hint, details.
Rules: follow the hint; never repeat a call whose error says retryable=false; never work around an approval requirement.
Use the ticket key as idempotency_key and convert dollars to cents. When done, reply with ONE JSON object and nothing else:
{"status": "applied|offer_next_period|needs_input|escalated|failed_transient|failed", "summary": "<one sentence>",
 "next_period": "<YYYY-MM or null>", "approval_request_id": "<id or null>"}"""


def request_text(sc):
    return (f"Payroll ticket {sc['key']}: apply a ${sc['amount']} adjustment ({sc['reason']}) "
            f"to employee {sc['employee_id']} for pay period {sc['period']}.")


def run_agent(db, clock, ctx, user_text, max_turns=8):
    """Standard manual tool loop: call Claude, run each tool_use through execute_with_policy, send ALL results back in ONE user message."""
    messages = [{"role": "user", "content": user_text}]
    for turn in range(1, max_turns + 1):
        response = ask(messages, system=SYSTEM, tools=TOOL_SCHEMAS, model=MODEL_BALANCED, max_tokens=2048)
        calls = tool_calls_of(response)
        if response.stop_reason != "tool_use" or not calls:
            return {"turns": turn, "stopped": "end_turn", "final_text": text_of(response)}
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in response.content]})
        results = []
        for call in calls:
            content, is_error = execute_with_policy(db, clock, call.name, dict(call.input), ctx)
            ctx.results.append({"tool": call.name, "is_error": is_error, "content": content})
            block = {"type": "tool_result", "tool_use_id": call.id, "content": content}
            if is_error:
                block["is_error"] = True
            results.append(block)
        messages.append({"role": "user", "content": results})
    return {"turns": max_turns, "stopped": "max_turns", "final_text": ""}


def parse_final(text):
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        obj = json.loads(text[start:end])
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {}


def export_catalog():
    return {"errors": {c: {k: v for k, v in e.items() if k != "hint"} for c, e in sorted(ERROR_CATALOG.items())},
            "retry_table": {c: {"max_attempts": p.max_attempts, "base_delay_s": p.base_delay_s, "factor": p.factor, "max_delay_s": p.max_delay_s}
                            for c, p in sorted(RETRY_POLICY.items())}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    args = parser.parse_args()
    scenarios = json.loads((HERE / "data" / "scenarios.json").read_text(encoding="utf-8"))
    clock = SimClock()
    db = PayrollDB(clock)
    out = {"scenarios": {}, "matrix": []}
    print(f"model: {MODEL_BALANCED}")
    for sc in scenarios:
        if args.only and sc["id"] != args.only:
            continue
        db.arm_lock(sc["lock"])
        calls0, sleeps0 = len(db.calls), len(clock.sleeps)
        ctx = RunContext(sc["id"])
        run = run_agent(db, clock, ctx, request_text(sc))
        final = parse_final(run["final_text"])
        status = final.get("status", "unparseable" if run["stopped"] == "end_turn" else "max_turns")
        db_calls = [list(c) for c in db.calls[calls0:]]
        sleeps = clock.sleeps[sleeps0:]
        out["scenarios"][sc["id"]] = {"title": sc["title"], "expected_status": sc["expected_status"], "status": status, "final": final,
                                      "turns": run["turns"], "trace": ctx.trace, "results": ctx.results, "db_calls": db_calls,
                                      "sleeps": sleeps, "escalations": ctx.escalations, "runaway": ctx.runaway}
        out["matrix"].append({"scenario": sc["id"], "db_calls": len(db_calls), "sleep_total_s": round(sum(sleeps), 2),
                              "status": status, "expected": sc["expected_status"], "escalations": len(ctx.escalations)})
        db.arm_lock(0)
    out["db_final"] = {"adjustment_keys": sorted(db.adjustments)}
    out["catalog"] = export_catalog()
    print(f"\n{'scn':<4}{'db_calls':>9}{'sleep_s':>9}  {'status':<18}{'expected':<18}esc")
    for r in out["matrix"]:
        print(f"{r['scenario']:<4}{r['db_calls']:>9}{r['sleep_total_s']:>9.2f}  {r['status']:<18}{r['expected']:<18}{r['escalations']}")
    print(f"\nadjustments written: {out['db_final']['adjustment_keys']}")
    evidence = HERE / "evidence" / "evidence.json"
    evidence.parent.mkdir(exist_ok=True)
    evidence.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("saved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
