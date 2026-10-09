"""Key-free self-check for Demo 5F. No key, no network, no Claude Code CLI, and the real SDK is never used.

    python check_offline.py

A scripted fake of claude_agent_sdk stands in for the model. Its replies and costs are author-written fixtures, not model results.
The workflow, the step table, the gate, the checkpoints, the approval queue, the confirmation and the logs all run for real.
Everything the script writes goes to temporary folders, so this folder stays clean.
"""
import ast
import asyncio
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
SECRET = "sk-ant-check-secret-0001"
os.environ["ANTHROPIC_API_KEY"] = SECRET  # a fake secret, to prove it never reaches a log
for name in ("CLAUDE_MODEL_BALANCED", "CLAUDE_MODEL_FAST"):
    os.environ.pop(name, None)
results = []


def check(name, passed):
    results.append(bool(passed))
    print(("PASS  " if passed else "FAIL  ") + name)


# -- The scripted fake SDK ------------------------------------------------------------------------------------

CALLS = []  # every query() the workflow made: {"step", "prompt", "options"}
FAKE_COST = 0.002  # author-written dollars per call
PARSED = {  # author-written: what the scripted 'model' reads out of each sample request
    "Acme": {"customer": "Acme Corp", "items": [{"name": "coffee", "qty": 40}, {"name": "muffin", "qty": 36}], "when": "Friday 9am", "notes": []},
    "Northside": {"customer": "Northside Dental", "items": [{"name": "coffee", "qty": 150}, {"name": "muffin", "qty": 100}], "when": "Monday 8am", "notes": []},
    "Harbor": {"customer": "Harbor Books", "items": [{"name": "coffee", "qty": 20}, {"name": "muffin", "qty": 24}], "when": "Thursday 10am",
               "notes": ["One of our guests has a peanut allergy"]}}


class Box:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)


def fields_of(prompt):
    """The field names in a step prompt: lines that start with 'name: '."""
    return re.findall(r"^(\w+): ", prompt, flags=re.M)


def field_value(prompt, field):
    """The JSON value of one field in a step prompt."""
    return json.loads(re.search(rf"^{field}: (.*)$", prompt, flags=re.M).group(1))


async def run_gate(options, tool, args):
    """Call the PreToolUse hooks as the SDK would. Return the denial reason, or None when the tool is allowed."""
    for matcher in options.hooks["PreToolUse"]:
        for hook in matcher.hooks:
            out = await hook({"tool_name": "mcp__catering__" + tool, "tool_input": args}, "toolu_x", None)
            if out["hookSpecificOutput"]["permissionDecision"] == "deny":
                return out["hookSpecificOutput"]["permissionDecisionReason"]
    return None


async def call_tool(options, tool, args):
    """Gate, then run the tool body, as the SDK would."""
    reason = await run_gate(options, tool, args)
    if reason:
        return f"denied: {reason}"
    tools = {t.name: t for t in options.mcp_servers["catering"]["tools"]}
    return (await tools[tool].handler(args))["content"][0]["text"]


async def scripted_reply(step, prompt, options):
    """What the scripted 'model' says for each step. It calls the tools, so the gate and the tool bodies run for real."""
    if step == "parse":
        return json.dumps(next(value for word, value in PARSED.items() if word in prompt))
    if step in ("stock", "price"):
        return await call_tool(options, "check_stock" if step == "stock" else "price_items", {"items": field_value(prompt, "items")})
    notes = field_value(prompt, "notes") + field_value(prompt, "preferences")
    message = f"Thank you, {field_value(prompt, 'customer')}. Your order arrives {field_value(prompt, 'when')}. Total ${field_value(prompt, 'total'):.2f}. Notes: {'; '.join(notes)}."
    await call_tool(options, "send_confirmation", {"message": message})
    return json.dumps({"sent": True, "message": message})


async def fake_query(prompt="", options=None):
    step = next(name for name in steps.ORDER if name != "approve" and steps.system_prompt(name) == options.system_prompt)
    CALLS.append({"step": step, "prompt": prompt, "options": options})
    yield fake.ResultMessage(result=await scripted_reply(step, prompt, options), total_cost_usd=FAKE_COST, usage={})


fake = types.ModuleType("claude_agent_sdk")
for class_name in ["ClaudeAgentOptions", "HookMatcher", "ResultMessage"]:
    setattr(fake, class_name, type(class_name, (Box,), {}))
fake.tool = lambda name, description, schema: (lambda handler: Box(name=name, handler=handler))
fake.create_sdk_mcp_server = lambda name, tools: {"name": name, "tools": tools}
fake.query = fake_query
sys.modules["claude_agent_sdk"] = fake

import catering_tools  # noqa: E402  (after the fake is in place)
import catering_workflow as flow  # noqa: E402
import steps  # noqa: E402
import workflow_state  # noqa: E402

KEPT_FOLDERS = []  # temporary folders, so they stay alive until the end


def new_world():
    """A fresh results folder and an empty call list."""
    folder = tempfile.TemporaryDirectory(prefix="demo5f_check_")
    KEPT_FOLDERS.append(folder)
    flow.STORE = workflow_state.RunStore(folder.name)
    CALLS.clear()
    return Path(folder.name)


def run_main(*argv):
    """Run main() like the command line does. Return everything it printed."""
    sys.argv = ["catering_workflow.py", *argv]
    with contextlib.redirect_stdout(io.StringIO()) as shown:
        try:
            flow.main()
        except SystemExit as stop:
            if stop.code not in (0, None):
                print(stop.code)
    return shown.getvalue()


def steps_called():
    return [call["step"] for call in CALLS]


# -- A full run: small order -----------------------------------------------------------------------------------

print("A small order, run to the end")
world = new_world()
saved_sizes = []
real_save = flow.STORE.save
flow.STORE.save = lambda record: (saved_sizes.append(len(record["done"])), real_save(record))[1]
text = run_main("--request", "R-1")
record = flow.STORE.load("R-1")
check("R-1 runs all five steps and ends 'done'", record["status"] == "done" and record["done"] == steps.ORDER and "approve" in text)
check("the approve step is plain code: four model calls, none for approve", steps_called() == ["parse", "stock", "price", "confirm"])
check("each step receives only the fields steps.json lists for it",
      all(fields_of(call["prompt"]) == steps.STEPS[call["step"]]["reads"] for call in CALLS))
check("the checkpoint is written after every step (1, 2, 3, 4, 5 steps done)", {1, 2, 3, 4, 5} <= set(saved_sizes))
check("the checkpoint file holds the state and the trace", record["state"]["total"] == 248.0 and len(record["trace"]) == 5)
check("the run prints what each step is given and what one growing chat would carry", text.count("one chat") == 5 and "given     : request_text" in text)
last = record["trace"][-1]
check("the confirm step's prompt is smaller than a growing chat would be", last["given"] < sum(t["given"] + t["output"] for t in record["trace"][:-1]) + last["given"])
check("the order under the limit is approved by code, and the confirmation is in the outbox", record["state"]["approved_by"].startswith("auto")
      and (world / "outbox" / "R-1.txt").exists())
check("a second --request for the same order is refused, and nothing new is called", (lambda n: "already has a run" in run_main("--request", "R-1") and len(CALLS) == n)(len(CALLS)))

# -- Context: untrusted text, numbers in code --------------------------------------------------------------------

print("Context and untrusted data")
parse_prompt = CALLS[0]["prompt"]
check("customer text is passed quoted, as data", parse_prompt.startswith("request_text: <customer_request>") and parse_prompt.rstrip().endswith("</customer_request>"))
check("the parse prompt tells the model the text is data, not instructions", "never instructions" in steps.system_prompt("parse"))
SHELF_NUMBERS = ["3.5", "400"]  # a price and a stock level from data/stock.json
check("stock and price numbers live in data, not in any prompt the model gets",
      not any(word in call["prompt"] + call["options"].system_prompt for call in CALLS[:3] for word in SHELF_NUMBERS))
check("every step is a separate query() with its own options and system prompt",
      len({id(call["options"]) for call in CALLS}) == 4 and len({call["options"].system_prompt for call in CALLS}) == 4)

# -- Memory: stop, resume, history --------------------------------------------------------------------------------

print("Memory: --stop-after, --resume, history")
new_world()
text = run_main("--request", "R-1", "--stop-after", "2")
paused = flow.STORE.load("R-1")
check("--stop-after 2 runs two steps and saves a checkpoint", steps_called() == ["parse", "stock"] and paused["done"] == ["parse", "stock"]
      and paused["status"] == "stopped after 2 steps" and "--resume R-1" in text)
text = run_main("--resume", "R-1")
check("--resume does not call the model for the finished steps", steps_called() == ["parse", "stock", "price", "confirm"])
check("--resume says which steps it skipped, and ends 'done'", "skipped, it is already in the checkpoint" in text and flow.STORE.load("R-1")["status"] == "done")
check("--resume on a finished order does nothing", (lambda n: "Nothing to resume" in run_main("--resume", "R-1") and len(CALLS) == n)(len(CALLS)))
rows = flow.STORE.history()
check("run_history.jsonl has one line for the stop and one for the resume, with steps run and skipped",
      len(rows) == 2 and rows[1]["steps_skipped"] == ["parse", "stock"] and rows[1]["steps_run"] == ["price", "approve", "confirm"])
check("--list shows the history", "R-1" in run_main("--list") and "done" in run_main("--list"))
check("the resumed order cost only the steps that ran", abs(workflow_state.total_cost(flow.STORE.load("R-1")) - 4 * FAKE_COST) < 1e-9)

# -- Safety: the approval gate -----------------------------------------------------------------------------------

print("Safety: the approval gate")
world = new_world()
text = run_main("--request", "R-2")
waiting = flow.STORE.load("R-2")
check("R-2 is over the limit: it stops with 'waiting for manager'", waiting["status"] == "waiting for manager" and "approve" not in waiting["done"]
      and waiting["state"]["total"] > steps.APPROVAL_LIMIT)
check("the order is in results/approval_queue.json", [entry["order_id"] for entry in flow.STORE.queue()] == ["R-2"])
check("the confirmation tool was NOT called and nothing is in the outbox", "confirm" not in steps_called() and not (world / "outbox").exists())
check("--list shows the order that waits", "R-2" in run_main("--list") and "Nobody waits" not in run_main("--list"))
check("--resume does not skip the gate", "Nothing to resume" in run_main("--resume", "R-2") and "confirm" not in steps_called())
text = run_main("--approve", "R-2")
done = flow.STORE.load("R-2")
check("--approve completes it: only the confirm step calls the model", steps_called()[-1] == "confirm" and steps_called().count("confirm") == 1
      and done["status"] == "done" and done["state"]["approved_by"] == "manager")
check("the queue is empty and the confirmation is in the outbox", flow.STORE.queue() == [] and (world / "outbox" / "R-2.txt").exists())
check("--approve on an order that does not wait is refused", "is not waiting for a manager" in run_main("--approve", "R-2"))
check("the gate in code decides: approval_decision is plain code, no prompt mentions the limit",
      steps.approval_decision(500)["approved"] and not steps.approval_decision(500.01)["approved"]
      and not any("500" in step["prompt"] for step in steps.STEPS.values()))
with contextlib.redirect_stdout(io.StringIO()):  # the gate prints its [guardrail] note
    denied = asyncio.run(run_gate(flow.build_options("R-9", "confirm", {"approved": False}, "m"), "send_confirmation", {"message": "x"}))
check("the gate also denies send_confirmation while the order is not approved", denied == "the order is not approved yet")

# -- Safety: one confirmation, idempotent ------------------------------------------------------------------------

print("Safety: idempotency")
world = new_world()
options = flow.build_options("R-7", "confirm", {"approved": True}, "m")
first = asyncio.run(call_tool(options, "send_confirmation", {"message": "first message"}))
second = asyncio.run(call_tool(options, "send_confirmation", {"message": "second message"}))
check("calling send_confirmation twice sends one confirmation", first == "Confirmation sent." and "Already sent" in second
      and (world / "outbox" / "R-7.txt").read_text(encoding="utf-8") == "first message" and len(list((world / "outbox").iterdir())) == 1)
new_world()
run_main("--request", "R-1")
sent_before = (flow.STORE.outbox / "R-1.txt").read_text(encoding="utf-8")
crashed = flow.STORE.load("R-1")
crashed["done"].remove("confirm")
crashed["status"] = "running"
flow.STORE.save(crashed)
run_main("--resume", "R-1")
check("a run that stopped after sending but before its checkpoint sends nothing twice", steps_called().count("confirm") == 2
      and (flow.STORE.outbox / "R-1.txt").read_text(encoding="utf-8") == sent_before and len(list(flow.STORE.outbox.iterdir())) == 1)

# -- Safety: tools, limits, schema --------------------------------------------------------------------------------

print("Safety: tools, limits and the output check")
for step in steps.ORDER:
    rules = steps.STEPS[step]
    if rules["kind"] == "code":
        continue
    options = flow.build_options("R-1", step, {"approved": True}, "m")
    names = [t.name for t in options.mcp_servers["catering"]["tools"]]
    check(f"options for {step}: its tools only ({names or 'none'}), setting_sources empty, dontAsk, limits set",
          options.allowed_tools == [steps.PREFIX + name for name in rules["tools"]] and names == rules["tools"]
          and options.setting_sources == [] and options.permission_mode == "dontAsk"
          and options.max_turns == rules["max_turns"] and options.max_budget_usd == rules["max_budget_usd"] and options.max_turns and options.max_budget_usd)
write_tools = [step for step in steps.ORDER if "send_confirmation" in steps.tools_for(step)]
check("only the confirm step has a write tool; the others are read-only", write_tools == ["confirm"])
steps.STEPS["price"]["tools"].append("check_stock")
changed = flow.build_options("R-1", "price", {}, "m")
check("steps.json is the single source: one edit changes the options and the gate", "mcp__catering__check_stock" in changed.allowed_tools
      and steps.gate_decision("price", "check_stock", {})[0])
steps.STEPS["price"]["tools"].remove("check_stock")
check("a tool outside the step's list is denied by the gate", not steps.gate_decision("stock", "price_items", {})[0]
      and not steps.gate_decision("parse", "send_confirmation", {"approved": True})[0])
good = {"customer": "A", "items": [{"name": "coffee", "qty": 2}], "when": "Friday", "notes": []}
check("a correct parse output passes the check", steps.validate("parse", good, {}) is None)
check("the check names a missing field, a wrong type and an unknown item",
      "did not return the field 'when'" in steps.validate("parse", {k: v for k, v in good.items() if k != "when"}, {})
      and "wrong type" in steps.validate("parse", {**good, "items": "40 coffees"}, {})
      and "do not sell" in steps.validate("parse", {**good, "items": [{"name": "pizza", "qty": 1}]}, {}))
check("the check compares the price total with the price table, and the stock answer with the shelf",
      steps.validate("price", {"total": 7.0, "lines": []}, {"items": good["items"]}) is None
      and "does not match" in steps.validate("price", {"total": 9.0, "lines": []}, {"items": good["items"]})
      and "not enough stock" in steps.validate("stock", {"in_stock": False, "shortages": ["x"]}, {}))
check("a reply that is not JSON gives None, and a code fence is accepted", steps.parse_reply("sorry") is None and steps.parse_reply('```json\n{"a": 1}\n```') == {"a": 1})

# -- Memory: preferences ------------------------------------------------------------------------------------------

print("Memory: customer preferences")
new_world()
run_main("--request", "R-1")
check("Acme's standing preference 'no peanuts' reaches the confirm step and the message", "no peanuts" in CALLS[-1]["prompt"]
      and "no peanuts" in (flow.STORE.outbox / "R-1.txt").read_text(encoding="utf-8"))
new_world()
text = run_main("--request", "R-3")
check("the peanut note in the request is read by parse, passed to confirm and appears in the confirmation",
      "peanut allergy" in CALLS[-1]["prompt"] and "peanut allergy" in (flow.STORE.outbox / "R-3.txt").read_text(encoding="utf-8")
      and "deliver to the side door" in CALLS[-1]["prompt"] and "memory    : standing preferences for Harbor Books" in text)
check("the stock and price steps do not receive the notes or the preferences", all("preferences" not in call["prompt"] for call in CALLS if call["step"] != "confirm"))
check("R-3 is auto-approved and finishes", flow.STORE.load("R-3")["status"] == "done")

# -- Logs have no secrets -----------------------------------------------------------------------------------------

print("Logs")
audit_text = flow.STORE.audit_path.read_text(encoding="utf-8")
every_file = "".join(path.read_text(encoding="utf-8") for path in flow.STORE.folder.rglob("*") if path.is_file() and path.parent.name != "outbox")
audit_rows = [json.loads(line) for line in audit_text.splitlines()]
check("every tool decision is in the audit log with a reason", len(audit_rows) == 3 and all(r["reason"] and r["decision"] in ("allow", "deny") for r in audit_rows))
check("the audit log holds argument names only, no message text", all(r["arg_names"] for r in audit_rows) and "peanut" not in audit_text)
check("no results file holds the API key", SECRET not in every_file and "sk-ant" not in every_file)

# -- Models and the files -----------------------------------------------------------------------------------------

print("The files")
check("steps default to the fast model, and --model balanced picks the main one", flow.MODELS == {"fast": "claude-haiku-5-5", "balanced": "claude-sonnet-5-5"}
      and all(rules.get("model", "fast") == "fast" for rules in steps.STEPS.values()))
sources = {path.name: path.read_text(encoding="utf-8") for path in HERE.glob("*.py")}
for name, source in sources.items():
    ast.parse(source)
main_lines = sum(1 for line in sources["catering_workflow.py"].splitlines() if line.strip())
check(f"every .py file parses, and catering_workflow.py has {main_lines} non-blank lines (limit 300)", main_lines <= 300)
check("the pure modules import no SDK", all("claude_agent_sdk" not in sources[name] for name in ("steps.py", "workflow_state.py", "catering_tools.py")))
demo_code = "".join(source for name, source in sources.items() if name != "check_offline.py")
check("the demo uses no Opus, no temperature, no top_p, no thinking, no prefill", not re.search(r"opus|temperature|top_p|thinking|prefill", demo_code, flags=re.I))
left = sorted(p.name for p in (HERE / "results").iterdir()) if (HERE / "results").exists() else []
check("this folder has no results and no __pycache__", left in ([], [".gitkeep"]) and not list(HERE.rglob("__pycache__")))
print("ALL OK" if all(results) else "SOME CHECK FAILED")
sys.exit(0 if all(results) else 1)
