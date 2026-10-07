"""Lab 2.2 - Travel disruption assistant: run the tool calls of one turn safely, one stage at a time.

This lab continues Demo 2C (the same method: run the loop, make it faster, break it, harden it, and read the ledger), on a
flight-disruption assistant. Flight XA482 was cancelled. For one traveler the assistant READS (flight status, alternatives, hotels,
loyalty tier) and then WRITES three dependent things: rebook, book a hotel with the new reference, and notify.

WHAT YOU EDIT (five places, each marked "TODO n of 5"; the guide in README.md gives the exact code for each)
  TODO 1  LOYALTY_TIER_TOOL  -> stage 2: the one tool definition that is missing
  TODO 2  run_concurrently   -> stage 2: run a turn's reads at the same time
  TODO 3  gate               -> stage 3: dependent writes only run in order, on references a tool really returned
  TODO 4  key_for, timeout_result -> stage 4: a retried write must be replayed, not repeated
  TODO 5  the loop guard     -> stage 5: a model that never stops is cut off

HOW TO RUN (in order)
  python lab.py --stage 1      one tool call after the other: the baseline (needs no code from you)
  python lab.py --stage 2      concurrent reads
  python lab.py --stage 3      the write gate (a recorded batch is replayed, then a live run)
  python lab.py --stage 4      idempotent writes (a recorded retry is replayed, then a live run)
  python lab.py --stage 5      the iteration guard and the final run
  python check.py              pass/fail in plain words
"""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import travel_core as core
from claude_client import ask

DEPENDS_ON = core.DEPENDS_ON


# ======================================================================================
# TODO 1 of 5 - the missing tool definition (stage 2).
# The assistant needs the traveler's tier to know the hotel rate cap, but the toolset has no tool for it. Write the definition of
# `loyalty_tier`: a dict with name, description and input_schema. The description must say that the tool is READ-ONLY, what it
# returns (the tier and its perks: fee waiver, hotel rate cap, priority) and when to use it. The input is one required string,
# `traveler_id`, and no other property is allowed.
# ======================================================================================
LOYALTY_TIER_TOOL = {
    "name": "loyalty_tier",
    "description": "Read-only. The loyalty tier of one traveler and its perks: change-fee waiver, hotel rate cap, lounge and priority rebooking. Use it before choosing a hotel, to learn the rate cap. Does not change anything.",
    "input_schema": {"type": "object", "properties": {"traveler_id": {"type": "string"}}, "required": ["traveler_id"], "additionalProperties": False},
}


# ======================================================================================
# TODO 2 of 5 - the concurrent executor (stage 2).
# `run_one(call)` runs ONE tool call and returns its tool_result block. Run all the calls at the same time on a thread pool with up to
# 8 workers, and return the results in the SAME ORDER as the calls (the API needs every result, matched by id, in one message).
# ======================================================================================
def run_concurrently(run_one, calls):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(run_one, calls))


# ======================================================================================
# TODO 3 of 5 - the write gate (stage 3).
# Called before every WRITE. `name` and `args` are the call, `state.succeeded` holds the tools that already returned OK, and
# `state.refs` holds the references that tools returned. DEPENDS_ON says which tools a write needs first.
# Return None when the call may run. Otherwise return a dict with error, retryable (False), message and hint:
#   error "PREREQUISITE_NOT_MET"  when a tool in DEPENDS_ON[name] has not succeeded yet;
#   error "UNKNOWN_REFERENCE"     when an argument whose name ends in _ref is not a reference that a tool returned.
# ======================================================================================
def gate(name, args, state):
    missing = [tool for tool in DEPENDS_ON.get(name, ()) if tool not in state.succeeded]
    if missing:
        return {"error": "PREREQUISITE_NOT_MET", "retryable": False, "message": f"{name} needs {', '.join(missing)} to succeed first",
                "hint": "Call the missing tool first and wait for its result. Do not guess references."}
    unknown = [key for key, value in args.items() if key.endswith("_ref") and value not in state.refs]
    if unknown:
        return {"error": "UNKNOWN_REFERENCE", "retryable": False, "message": f"{', '.join(unknown)} was not returned by any tool",
                "hint": "Use only references that a tool result returned."}
    return None


# ======================================================================================
# TODO 4 of 5 - the idempotency key and the timeout result (stage 4).
# key_for(name, args): the same tool with the same arguments must always give the same key, whatever the order of the arguments.
# Hash json.dumps({"tool": name, "args": args}, sort_keys=True) with SHA-256 and keep the first 16 hex characters.
# timeout_result(name, error): a dict with error "TIMEOUT", retryable True, outcome_unknown True, message (the error text) and a hint
# that says the write may or may not have been applied, and that a retry with IDENTICAL arguments is safe.
# ======================================================================================
def key_for(name, args):
    canonical = json.dumps({"tool": name, "args": args}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def timeout_result(name, error):
    return {"error": "TIMEOUT", "retryable": True, "outcome_unknown": True, "message": str(error),
            "hint": f"{name} may or may not have been applied. Retry with IDENTICAL arguments: the same idempotency key makes the retry safe."}


# ======================================================================================
# THE AGENT LOOP (given, except TODO 5)
# take_turn makes one model call and, when the model asked for tools, answers ALL of them in ONE user message.
# ======================================================================================
def run_agent(create, services, user_text, stage, max_turns=10):
    state, log = core.RunState(), core.new_log()
    messages = [{"role": "user", "content": user_text}]
    # ======================================================================================
    # TODO 5 of 5 - the iteration guard (stage 5).
    # The loop below can run forever if the model never stops asking for tools. Run at most max_turns turns, and when the
    # limit is reached return {"turns": max_turns, "stopped": "max_turns", "final_text": "", **log}.
    # ======================================================================================
    for turn in range(1, max_turns + 1):
        done = core.take_turn(create, services, state, messages, log, stage, turn)
        if done:
            return done
    return {"turns": max_turns, "stopped": "max_turns", "final_text": "", **log}


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(loyalty_tool=LOYALTY_TIER_TOOL, run_concurrently=run_concurrently, gate=gate, key_for=key_for,
               timeout_result=timeout_result, run_agent=run_agent)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4", "5"])
    args = parser.parse_args()
    core.run_stage(int(args.stage))


if __name__ == "__main__":
    main()
