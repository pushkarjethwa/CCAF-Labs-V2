"""Lab 2.3 - Payroll agent: make tool failures typed, bounded and safe, one stage at a time.

This lab continues Demo 2B (the same method: run the loop, break it, harden it, and read the ledger), on the payroll adjustment agent.
The agent applies one-off pay adjustments. Its first version shows the model a bare error string and retries every failure blindly.

WHAT YOU EDIT (five places, each marked "TODO n of 5"; the guide in README.md gives the exact code for each)
  TODO 1  ERROR_CATALOG          -> stage 2: one typed entry per error code
  TODO 2  to_tool_result         -> stage 2: the JSON the model sees instead of a bare string
  TODO 3  RETRY_POLICY, policy_for -> stage 3: which errors are retried, how often, how long to wait
  TODO 4  build_approval_request -> stage 4: the request a human approver receives
  TODO 5  preflight              -> stage 5: check a conversation before it is sent

HOW TO RUN (in order)
  python lab.py --stage 1      the raw loop: the baseline (needs no code from you)
  python lab.py --stage 2      typed errors
  python lab.py --stage 3      bounded retry
  python lab.py --stage 4      escalation
  python lab.py --stage 5      preflight, and the final gate
  python check.py              pass/fail in plain words
Add --only S4 to run one ticket only.
"""
import argparse
import json
from collections import defaultdict

import payroll_core as core
from payroll_core import RetryPolicy


# ======================================================================================
# TODO 1 of 5 - the error catalog (stage 2).
# One entry per error code: category (tool | input | permission | environment), retryable (True or False),
# action (a short verb phrase) and hint. The hint tells the MODEL what to do, and may contain {placeholders}
# that are filled from the error's details, for example {next_open_period}.
# ======================================================================================
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


# ======================================================================================
# TODO 2 of 5 - the structured tool_result (stage 2).
# exc is a PayrollError with .code, .message and .details. Return json.dumps of a dict with the keys
# error_code, category, retryable, message, hint and details, with sort_keys=True.
# `extra` is merged into details. `retryable` and `hint`, when given, override the catalog (the harness uses them when retries run out).
# An unknown code uses the UNEXPECTED_ERROR entry, and a hint placeholder with no value must not crash.
# ======================================================================================
def to_tool_result(exc, extra=None, retryable=None, hint=None):
    entry = ERROR_CATALOG.get(exc.code, ERROR_CATALOG["UNEXPECTED_ERROR"])
    details = {**exc.details, **(extra or {})}
    return json.dumps({
        "error_code": exc.code,
        "category": entry["category"],
        "retryable": entry["retryable"] if retryable is None else retryable,
        "message": exc.message,
        "hint": hint if hint is not None else entry["hint"].format_map(defaultdict(str, details)),
        "details": details,
    }, sort_keys=True)


# ======================================================================================
# TODO 3 of 5 - the retry table (stage 3).
# RETRY_POLICY maps an error code to a RetryPolicy(max_attempts, base_delay_s, factor, max_delay_s). Only the transient code
# PAYROLL_DB_LOCKED is worth retrying: 4 attempts in total, waiting 1 second, then 2, then 4 (never more than 8).
# policy_for returns the policy of a code, and an unknown code must FAIL CLOSED: one attempt, no retry (DEFAULT_POLICY).
# ======================================================================================
DEFAULT_POLICY = RetryPolicy(max_attempts=1)
RETRY_POLICY = {"PAYROLL_DB_LOCKED": RetryPolicy(max_attempts=4, base_delay_s=1.0, factor=2.0, max_delay_s=8.0)}


def policy_for(code):
    return RETRY_POLICY.get(code, DEFAULT_POLICY)


# ======================================================================================
# TODO 4 of 5 - the approval request (stage 4).
# When an adjustment is above the approval threshold, the harness hands a human approver a COMPLETE request. Return a dict with
# type "hr_approval_request", request_id "HRA-" + the call's idempotency_key, status "PENDING", error_code, required_role,
# employee_id, period, amount_cents, currency "USD", threshold_cents, reason, requested_by "payroll-agent",
# and original_call {tool, idempotency_key}. The amounts and the role are in exc.details.
# ======================================================================================
def build_approval_request(tool_name, args, exc):
    return {
        "type": "hr_approval_request",
        "request_id": "HRA-" + args["idempotency_key"],
        "status": "PENDING",
        "error_code": exc.code,
        "required_role": exc.details.get("required_role"),
        "employee_id": args["employee_id"],
        "period": args["period"],
        "amount_cents": args["amount_cents"],
        "currency": "USD",
        "threshold_cents": exc.details.get("threshold_cents"),
        "reason": args["reason"],
        "requested_by": "payroll-agent",
        "original_call": {"tool": tool_name, "idempotency_key": args["idempotency_key"]},
    }


# ======================================================================================
# TODO 5 of 5 - the preflight (stage 5).
# Return a list of problems with a conversation BEFORE it is sent (an empty list means it is fine). The tool_result contract:
# after an assistant message, the next user message must answer exactly the tool_use ids that the assistant asked for, one
# tool_result each, and the tool_result blocks must come first in that message. Messages hold either a string or a list of blocks.
# ======================================================================================
def preflight(messages):
    problems = []
    for i, message in enumerate(messages):
        if message["role"] != "assistant":
            continue
        asked = [b["id"] for b in message["content"] if isinstance(b, dict) and b.get("type") == "tool_use"] if isinstance(message["content"], list) else []
        reply = messages[i + 1]["content"] if i + 1 < len(messages) and isinstance(messages[i + 1]["content"], list) else []
        answered = [b.get("tool_use_id") for b in reply if b.get("type") == "tool_result"]
        if sorted(asked) != sorted(answered):
            problems.append(f"message {i}: tool_use ids {asked} but tool_result ids {answered}")
        if answered and reply[0].get("type") != "tool_result":
            problems.append(f"message {i + 1}: tool_result blocks must come first")
    return problems


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(to_tool_result=to_tool_result, policy_for=policy_for, build_approval_request=build_approval_request, preflight=preflight)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4", "5"])
    parser.add_argument("--only", help="run one ticket only, for example S4")
    args = parser.parse_args()
    core.run_stage(int(args.stage), args.only)


if __name__ == "__main__":
    main()
