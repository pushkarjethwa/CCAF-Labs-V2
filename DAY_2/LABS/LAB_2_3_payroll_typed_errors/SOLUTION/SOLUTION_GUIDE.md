# Solution guide: Lab 2.3 - Payroll agent: typed errors, bounded retries, escalation

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Typed tool errors: a taxonomy with category and retryable, a retry table with bounded backoff, fail-closed defaults for unknown errors, escalation (never retry) for permission errors, and repeat blocking.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: ERROR_CATALOG

What the TODO asks:

> TODO 1: one entry per error code: {"category": tool|input|permission|environment, "retryable": bool, "action": short verb phrase, "hint": template}
> Codes: PAY_PERIOD_CLOSED, EMPLOYEE_NOT_FOUND, HR_APPROVAL_REQUIRED, PAYROLL_DB_LOCKED, and UNEXPECTED_ERROR (fail-closed fallback).
> A hint may contain {placeholders} filled from exc.details, e.g. {next_open_period}. Write hints that tell the model WHAT TO DO.

Solution:

```python
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
```

### Block 2: RETRY_POLICY

What the TODO asks:

> TODO 2: retry table. Which codes are worth retrying, how many attempts in total, what backoff? Everything else gets DEFAULT_POLICY.

Solution:

```python
RETRY_POLICY = {"PAYROLL_DB_LOCKED": RetryPolicy(max_attempts=4, base_delay_s=1.0, factor=2.0, max_delay_s=8.0)}
```

### Block 3: def policy_for()

What the TODO asks:

> TODO 3: look the code up in RETRY_POLICY. An unknown code must FAIL CLOSED (one attempt, no retry).

Solution:

```python
return RETRY_POLICY.get(code, DEFAULT_POLICY)
```

### Block 4: def to_tool_result()

What the TODO asks:

> TODO 4: return json.dumps of {"error_code", "category", "retryable", "message", "hint", "details"}, sort_keys=True.
> Unknown codes use the UNEXPECTED_ERROR entry. Fill the hint template from exc.details (missing keys must not crash).

Solution:

```python
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
```

### Block 5: def build_approval_request()

What the TODO asks:

> TODO 5: return a COMPLETE dict. Keys: type "hr_approval_request", request_id "HRA-" + idempotency_key, status "PENDING",
> error_code, required_role, employee_id, period, amount_cents, currency "USD", threshold_cents, reason,
> requested_by "payroll-agent", original_call {tool, idempotency_key}.

Solution:

```python
d = exc.details
return {"type": "hr_approval_request", "request_id": "HRA-" + args["idempotency_key"], "status": "PENDING", "error_code": exc.code,
        "required_role": d.get("required_role"), "employee_id": d.get("employee_id"), "period": d.get("period"),
        "amount_cents": d.get("amount_cents"), "currency": "USD", "threshold_cents": d.get("threshold_cents"),
        "reason": d.get("reason"), "requested_by": "payroll-agent",
        "original_call": {"tool": tool_name, "idempotency_key": args["idempotency_key"]}}
```

### Block 6: def execute_with_policy()

What the TODO asks:

> TODO A: if this exact call already failed for good (ctx.final_failures), do NOT touch the DB: return the stored error with details.repeat_blocked = true.
> TODO B: retry only codes whose policy allows it; wait clock.sleep(delay_before_retry(...)) between attempts; stop at policy.max_attempts.
> TODO C: when the budget is spent, return the error with retryable=False, details {attempts, retries_exhausted: true} and a hint telling the model to stop.
> TODO D: permission errors are NEVER retried: build_approval_request(...), append to ctx.escalations, put its request_id in details.approval_request_id.

Solution:

```python
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
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- catalog has all 4 codes plus UNEXPECTED_ERROR
- catalog classifies category and retryable as specified
- an error tool_result is JSON with error_code/category/retryable/message/hint
- hint is actionable and names the next open period (2026-09)
- closed period is tried once, never retried
- unknown error code fails closed (non-retryable, 1 attempt)
- transient lock: retried and recovered, exactly one row written
- backoff grows between retries
- permanent lock: bounded attempts (2-5) and total wait <= 10s
- exhausted retries: retryable=false and details.retries_exhausted=true
- over-threshold: one DB attempt, one escalation, no retry
- approval request is complete (request_id HRA-K4, status PENDING)
- tool_result carries details.approval_request_id
- repeating a failed call is blocked without touching the DB (details.repeat_blocked)
- all 6 scenarios were run
- {sid} ({row['title']}) ended {row['expected_status']}
- {sid} no runaway retries
- S4 filed exactly one approval request
- S5 recovered within the retry budget

## 4. Common mistakes

- Retrying everything, or retrying permission errors (`HR_APPROVAL_REQUIRED`).
- An unbounded or too-generous retry budget (check.py limits attempts to 2-5 and total wait to 10 s).
- Returning a bare string such as 'Error: ...': the model has nothing to branch on.
- Forgetting that unknown codes must fail closed (one attempt, not retryable).
- Changing the idempotency key between retries of the same write.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Without the repeat guard (TODO A), a stubborn model repeats a failed call: extra DB attempts and duplicate approval requests. The harness must hold even when the model ignores advice, so the rule cannot live only in the prompt.
2. Adding `HR_APPROVAL_REQUIRED` to the retry table makes the permission failure look transient: more DB attempts and multiple approval requests, while the user-facing status may still look fine. The primary tripwire is the escalation count.
3. Same idempotency key for two different tickets: the second request silently returns the first row (a duplicate) instead of a new adjustment. Keys should be generated by the harness or ticket system from the ticket id, not by the model.
4. Reflection: a unit test on `to_tool_result()` catches the bare-string defect; only the agent trace shows retry storms and repeated escalations.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
