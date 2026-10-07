"""check.py - Part A tests your four TODOs with no API key and no model. Part B checks the real run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import asyncio
import contextlib
import io
import json
import sys

import claude_agent_sdk as sdk
import lab

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def words(text):
    return len(str(text).split())


specs = {s.get("name"): s for s in lab.TOOL_SPECS}
print("PART A - your four TODOs, tested with no API key and no model\n")
print("TODO 1 - tool descriptions")
check(set(specs) == {"list_alerts", "get_log_lines", "lookup_indicator"} and len(lab.TOOL_SPECS) == 3, "there are exactly three tools: list_alerts, get_log_lines, lookup_indicator", f"found {sorted(specs)}")
for name, must, hint in [("list_alerts", ("alert",), "what it lists"), ("get_log_lines", ("log", "host"), "what it returns and for which host"),
                         ("lookup_indicator", ("ip",), "what it looks up")]:
    description = str(specs.get(name, {}).get("description", ""))
    check(words(description) >= 8 and all(m in description.lower() for m in must), f"{name}: the description says {hint} (at least 8 words)", f"you wrote {description!r}")
check("host" in json.dumps(str(specs.get("get_log_lines", {}).get("schema"))) and "ip" in json.dumps(str(specs.get("lookup_indicator", {}).get("schema"))),
      "the schemas take a host (get_log_lines) and an ip (lookup_indicator)")

print("\nTODO 2 - the system prompt")
prompt = lab.SYSTEM_PROMPT
check(all(w in prompt for w in ("Verdict", "Evidence", "Next action")), "the prompt asks for a Verdict, Evidence and a Next action", "the three headings are missing")
check("do not guess" in prompt.lower() and "human" in prompt.lower(), "the prompt says to investigate rather than guess, and that a human approves actions")

print("\nTODO 3 - the agent configuration")
options = lab.build_options()
error = ""
get = lambda name: getattr(options, name, None)  # noqa: E731
check(options is not None and get("model") == lab.MODEL and get("system_prompt") == lab.SYSTEM_PROMPT, "the agent uses your model and your system prompt", error)
check(options is not None and get("tools") == [], "Claude Code's built-in file and shell tools are switched off (tools=[])")
check(options is not None and sorted(get("allowed_tools") or []) == ["mcp__soc__get_log_lines", "mcp__soc__list_alerts", "mcp__soc__lookup_indicator"],
      "exactly the three read-only tools are allowed, and nothing else", f"allowed_tools={get('allowed_tools')}")
check(options is not None and get("max_turns") and 1 <= get("max_turns") <= 20, "the loop has a turn limit (max_turns, at most 20)", f"max_turns={get('max_turns')}")
check(options is not None and get("max_budget_usd") and 0 < get("max_budget_usd") <= 2, "the run has a spending limit (max_budget_usd, at most 2 dollars)", f"max_budget_usd={get('max_budget_usd')}")
check(options is not None and get("setting_sources") == [] and "soc" in (get("mcp_servers") or {}), "local settings files are ignored, and the tool server is named soc")

print("\nTODO 4 - the agent loop")


def make(cls, **attrs):
    obj = object.__new__(cls)
    obj.__dict__.update(attrs)
    return obj


async def scripted_query(prompt, options):
    yield make(sdk.AssistantMessage, content=[make(sdk.ToolUseBlock, id="t1", name="mcp__soc__list_alerts", input={})], model="x", parent_tool_use_id=None)
    yield make(sdk.AssistantMessage, content=[make(sdk.TextBlock, text="Verdict: confirmed compromise on bastion-02.")], model="x", parent_tool_use_id=None)
    yield make(sdk.ResultMessage, num_turns=2, total_cost_usd=0.01, stop_reason="end_turn", result="done")


original_query = lab.query
lab.query = scripted_query
with contextlib.redirect_stdout(io.StringIO()):
    events = asyncio.run(lab.run_live())
lab.query = original_query
check(isinstance(events, list) and [e["kind"] for e in events] == ["tool", "text", "result"], "run_live reads every message from query() and returns the three events (tool, text, result)", f"run_live returned {events!r}")

print("\nPART B - the real run (needs `python lab.py` with a key and the Claude Code CLI; the exact route the agent takes can vary)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    events = saved["events"]
    tools = [e["name"] for e in events if e["kind"] == "tool"]
    final = " ".join(e["text"] for e in events if e["kind"] == "text").lower()
    done = [e for e in events if e["kind"] == "result"]
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "run `python lab.py` again to refresh results/run.json")
    check("get_log_lines" in tools and "lookup_indicator" in tools, "the agent read the logs and looked up an indicator before deciding (it chose its own steps)", f"tools used: {tools}")
    check(done, "the run finished and reported its turns and cost", f"result: {done}")
    check("bastion-02" in final and any(w in final for w in ("confirmed", "suspected", "false alarm")), "the report names bastion-02 and gives a verdict")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
