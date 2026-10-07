"""Lab 3.3 - Build the warranty claims agent (continues Demo 3C: same tools, same cases, same agent loop).

The agent works a warranty request with five tools: look up the registration, check the warranty terms, create the claim,
schedule the pickup, and submit the decision. Demo 3C built it in stages: structured tool results, a fixed pipeline, and a
live agent loop with a turn limit. You write the four key pieces here:

  TODO 1  run_tool     run one tool and return its result in the structured envelope: tool, ok, data
  TODO 2  decide       turn the warranty terms into a decision: approved or denied, with the reason
  TODO 3  ask          your Claude API call (with tools): one turn of the agent
  TODO 4  run_agent    the agent loop: ask Claude, run the tools it picks, send the results back, stop at the decision or the turn limit

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key: it tests TODO 1, 2 and 4 on the four cases.
  python lab.py      runs the live agent on the four cases (needs ANTHROPIC_API_KEY); then python check.py again
The mock tools, the tool definitions and the decision check are in warranty_core.py. You do not need to read it.
"""
import hashlib
import json
import pathlib

import warranty_core as core
from claude_client import MODEL_BALANCED, get_client


# ======================================================================================
# TODO 1 of 4 - RUN A TOOL: return the result in the structured envelope
# `name` is the tool name and `args` is a dict of its arguments. core.TOOL_FUNCTIONS maps each tool name to its function.
# Return a dict with three keys: "tool" (the name), "ok" (True) and "data" (what the tool function returns).
# ======================================================================================
def run_tool(name, args):
    return {"tool": name, "ok": True, "data": core.TOOL_FUNCTIONS[name](**args)}


# ======================================================================================
# TODO 2 of 4 - DECIDE: turn the warranty terms into a decision
# `terms` is the "data" of check_warranty_terms: it has covered (True or False), rule_id and reason.
# Return a dict with "decision" ("approved" when covered, otherwise "denied"), "rule_id" and "reason" copied from the terms.
# ======================================================================================
def decide(terms):
    return {"decision": "approved" if terms["covered"] else "denied", "rule_id": terms["rule_id"], "reason": terms["reason"]}


# ======================================================================================
# TODO 3 of 4 - your Claude API call, with tools: one turn of the agent
# `messages` is the conversation so far. core.AGENT_SYSTEM is the standing instruction and core.TOOLS the five tool definitions.
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
# TODO 4 of 4 - THE AGENT LOOP: ask Claude, run the tools it picks, send the results back
# Each turn: call ask_fn(messages); add the reply to messages as the assistant; collect the tool_use blocks from its content.
# No tool calls means Claude is done. Otherwise run each call with run_tool, keep the record, and send the results back as one
# user message of tool_result blocks. Stop after the turn in which submit_decision was called. The loop is bounded by core.MAX_TURNS.
# ======================================================================================
def run_agent(case, ask_fn=None):
    ask_fn = ask_fn or ask
    form = case["form"]
    messages = [{"role": "user", "content": f"Customer request: {case['message']}\nIntake form: {json.dumps(form)}"}]
    records, turns = [], 0
    for turns in range(1, core.MAX_TURNS + 1):
        response = ask_fn(messages)
        messages.append({"role": "assistant", "content": response.content})
        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            break
        results = []
        for call in calls:
            record = run_tool(call.name, call.input)
            records.append(record)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(record)})
        messages.append({"role": "user", "content": results})
        if any(call.name == "submit_decision" for call in calls):
            break
    return core.summarize(case, records, turns)


# ======================================================================================
# RUNNING THE AGENT - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
HOOKS = {"run_tool": run_tool, "decide": decide, "ask": ask, "run_agent": run_agent}


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def run_all(ask_fn=None):
    rows = []
    for case in core.CASES["cases"]:
        row = run_agent(case, ask_fn)
        rows.append(row)
        decision = row["decision"]["decision"] if row["decision"] else "none"
        print(f"{row['case']}  decision={decision:<9} turns={row['turns']:<2} tools={len(row['tools'])}  verified={row['verified']}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": source_fingerprint(), "rows": rows}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    run_all()
