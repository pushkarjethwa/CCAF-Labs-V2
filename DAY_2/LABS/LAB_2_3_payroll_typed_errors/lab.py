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
ERROR_CATALOG = {}  # replace these lines in TODO 1


# ======================================================================================
# TODO 2 of 5 - the structured tool_result (stage 2).
# exc is a PayrollError with .code, .message and .details. Return json.dumps of a dict with the keys
# error_code, category, retryable, message, hint and details, with sort_keys=True.
# `extra` is merged into details. `retryable` and `hint`, when given, override the catalog (the harness uses them when retries run out).
# An unknown code uses the UNEXPECTED_ERROR entry, and a hint placeholder with no value must not crash.
# ======================================================================================
def to_tool_result(exc, extra=None, retryable=None, hint=None):
    raise NotImplementedError("TODO 2: build the structured tool_result")  # replace these lines in TODO 2


# ======================================================================================
# TODO 3 of 5 - the retry table (stage 3).
# RETRY_POLICY maps an error code to a RetryPolicy(max_attempts, base_delay_s, factor, max_delay_s). Only the transient code
# PAYROLL_DB_LOCKED is worth retrying: 4 attempts in total, waiting 1 second, then 2, then 4 (never more than 8).
# policy_for returns the policy of a code, and an unknown code must FAIL CLOSED: one attempt, no retry (DEFAULT_POLICY).
# ======================================================================================
DEFAULT_POLICY = RetryPolicy(max_attempts=1)
RETRY_POLICY = {}  # replace this line in TODO 3


def policy_for(code):
    raise NotImplementedError("TODO 3: look the code up in RETRY_POLICY")  # replace this line in TODO 3


# ======================================================================================
# TODO 4 of 5 - the approval request (stage 4).
# When an adjustment is above the approval threshold, the harness hands a human approver a COMPLETE request. Return a dict with
# type "hr_approval_request", request_id "HRA-" + the call's idempotency_key, status "PENDING", error_code, required_role,
# employee_id, period, amount_cents, currency "USD", threshold_cents, reason, requested_by "payroll-agent",
# and original_call {tool, idempotency_key}. The amounts and the role are in exc.details.
# ======================================================================================
def build_approval_request(tool_name, args, exc):
    raise NotImplementedError("TODO 4: build the approval request")  # replace these lines in TODO 4


# ======================================================================================
# TODO 5 of 5 - the preflight (stage 5).
# Return a list of problems with a conversation BEFORE it is sent (an empty list means it is fine). The tool_result contract:
# after an assistant message, the next user message must answer exactly the tool_use ids that the assistant asked for, one
# tool_result each, and the tool_result blocks must come first in that message. Messages hold either a string or a list of blocks.
# ======================================================================================
def preflight(messages):
    raise NotImplementedError("TODO 5: check the tool_use and tool_result ids")  # replace these lines in TODO 5


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
