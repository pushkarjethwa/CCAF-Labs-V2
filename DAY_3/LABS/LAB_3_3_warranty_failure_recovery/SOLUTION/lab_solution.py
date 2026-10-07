"""Lab 3.3 - Make the warranty intake agent survive failure (continues Demo 3C: same agent, tools, faults and ground truth).

The agent files a warranty claim with four tools: lookup registration -> check warranty terms -> create claim -> schedule pickup.
A fault injector breaks one tool. Demo 3C showed that a blanket "retry 3 times" is wrong for most failures, and that the
fix is: classify the error first, then use the recovery that fits. You write that fix here:

  TODO 1  classify               decide what kind of failure an error is, from its status and code (never its message text)
  TODO 2  RECOVERY               one recovery rule per kind of failure
  TODO 3  corrective_message     what to tell the model when IT caused the error
  TODO 4  ask                    your Claude API call (with tools): one turn of the agent

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key: it tests your recovery layer against Demo 3C's ground truth.
  python lab.py      runs the live agent on four faults (needs ANTHROPIC_API_KEY); then python check.py again
The machinery (mock services, fault injector, executor, agent loop) is in warranty_core.py. You do not need to read it.
"""
import hashlib
import json
import pathlib

import warranty_core as core
from claude_client import MODEL_BALANCED, get_client


# ======================================================================================
# TODO 1 of 4 - CLASSIFY: what kind of failure is this?
# `exc` is the error. A service error has .status_code (like 503) and .code (like "E_TIMEOUT"). Other errors have neither.
# Return one of: "permission", "environment", "tool", "reasoning", "unknown".
#   403 -> permission     503 or 504 -> environment     E_ARG_RENAMED or E_SCHEMA_REJECTED -> tool
#   404 or 422 (the caller sent bad arguments) -> reasoning     anything else -> unknown
# ======================================================================================
def classify(exc):
    status, code = getattr(exc, "status_code", None), getattr(exc, "code", "")
    if status == 403:
        return "permission"
    if status in (503, 504):
        return "environment"
    if code in ("E_ARG_RENAMED", "E_SCHEMA_REJECTED"):
        return "tool"
    if status in (404, 422):
        return "reasoning"
    return "unknown"


# ======================================================================================
# TODO 2 of 4 - RECOVERY: one rule per kind of failure
# Row format:   "kind": (action, limit),
# Actions the executor understands:
#   retry_same_call              the same call again; limit = total attempts            (the blanket retry)
#   retry_renamed_then_fallback  retry once with the renamed argument, else a fallback endpoint (degraded mode)
#   corrective_message           tell the model what it got wrong; limit = corrections allowed, then a human
#   backoff_then_breaker         wait and retry; limit = total attempts, then pause the run and alert once
#   escalate                     stop and hand over to a human; never retry, never route around
# ======================================================================================
RECOVERY = {
    "tool": ("retry_renamed_then_fallback", 1),
    "reasoning": ("corrective_message", 2),
    "environment": ("backoff_then_breaker", 3),
    "permission": ("escalate", 0),
    "unknown": ("escalate", 0),
}


# ======================================================================================
# TODO 3 of 4 - CORRECTIVE MESSAGE: what to say to the model when it caused the error
# `exc.code` is the error code and `exc.message` is its text. For the code "E_COVERAGE_MISMATCH" the model used a wrong rule:
# tell it to call check_warranty_terms again and use exactly the rule_id it returns. For any other error, quote exc.message.
# ======================================================================================
def corrective_message(exc):
    if exc.code == "E_COVERAGE_MISMATCH":
        return ("The coverage rule you used does not match the warranty terms for this serial and issue. "
                "Call check_warranty_terms again and use exactly the rule_id it returns.")
    return f"The call failed: {exc.message}. Fix the arguments (check the format) and call the tool again."


# ======================================================================================
# TODO 4 of 4 - your Claude API call, with tools: one turn of the agent
# `messages` is the conversation so far. core.AGENT_SYSTEM is the standing instruction and core.TOOLS the four tool definitions.
# Return the whole response: the agent loop reads its content blocks to find the tool calls.
# ======================================================================================
def ask(messages):
    return get_client().messages.create(
        model=MODEL_BALANCED,
        max_tokens=4096,
        system=core.AGENT_SYSTEM,
        tools=core.TOOLS,
        messages=messages,
    )


# ======================================================================================
# RUNNING THE AGENT - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
HOOKS = {"classify": classify, "recovery": RECOVERY, "corrective_message": corrective_message, "ask": ask}
FAULT_RUNS = [("tool_drift", "create_claim"), ("env_outage", "create_claim"), ("permission", "schedule_pickup"),
              ("reasoning", "check_warranty_terms")]  # one fault from each family


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def run_all(ask_fn=None):
    case, rows = core.CASES["cases"][0], []
    hooks = {**HOOKS, "ask": ask_fn or ask}
    for fault, step in FAULT_RUNS:
        outcome = core.run_agent(hooks, case, fault, step, log=lambda _text: None)
        rows.append({"fault": fault, "step": step, **outcome})
        print(f"{fault:<12} at {step:<20} status={outcome['status']:<20} faulted-step attempts={outcome['faulted_step_attempts']} alerts={outcome['alerts']}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": source_fingerprint(), "rows": rows}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    run_all()
