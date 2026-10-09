"""Key-free self-check for Demo 5G. No key, no network, no Claude Code CLI, and the real SDK is never used.

    python check_offline.py

A scripted fake of claude_agent_sdk plays the detective. Its steps, notes and findings are author-written fixtures, not model results.
The tools, the bounded views, the argument limits, the gate, the audit log, the notes, the history, the approval queue and the PreCompact archive run for real.
Everything the script writes goes to a temporary folder, so this folder stays clean.
"""
import ast
import asyncio
import contextlib
import io
import json
import os
import re
import shutil
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

CLIENTS = []  # every client the run opened, in order
TRANSCRIPT = "fake transcript line 1\nfake transcript line 2\n"
FINDINGS = "Cause: weekend demand, a Tuesday delivery and a smaller case. Recommend 14 cases (112 cartons)."
FIRST_RUN = [
    ("read_inventory", {"branch": "harbour", "item": "oat milk"}),
    ("read_sales_log", {"branch": "harbour", "item": "oat milk", "days": 90}),
    ("write_note", {"text": "Oat milk sales jump at the weekend: Saturday about 24 and Sunday about 22 a day, against about 10 on weekdays."}),
    ("read_delivery_log", {"branch": "harbour"}),
    ("write_note", {"text": "Oat milk delivery arrives on Tuesdays. The quantity fell from 108 to 72 on 2026-08-04."}),
    ("read_supplier_notes", {"item": "oat milk"}),
    ("write_note", {"text": "Supplier case size changed from 12 to 8 cartons on 4 August. The standing order stayed at 9 cases."}),
    ("read_inventory", {"branch": "uptown", "item": "oat milk"}),  # the role may not read uptown: an ordinary refusal
    ("compact",),
    ("read_notes", {}),
    ("propose_order", {"item": "oat milk", "qty": 112}),
    ("raw", "Bash", {"command": "ls"}),  # not on the allow-list
    ("final", FINDINGS),
]
SECOND_RUN = [("read_notes", {}), ("read_inventory", {"branch": "harbour", "item": "oat milk"}), ("final", FINDINGS)]


class Box:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)


async def run_hooks(options, event, payload):
    """Call the hooks of one event as the SDK would. Return the denial reason for PreToolUse, otherwise None."""
    for matcher in options.hooks[event]:
        for hook in matcher.hooks:
            out = await hook(payload, "toolu_x", None)
            if event == "PreToolUse" and out["hookSpecificOutput"]["permissionDecision"] == "deny":
                return out["hookSpecificOutput"]["permissionDecisionReason"]
    return None


class FakeClient:
    def __init__(self, options=None):
        self.options, self.prompt = options, ""
        CLIENTS.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def query(self, prompt):
        self.prompt = prompt

    async def call_tool(self, full_name, args):
        """Gate first, then the real tool body. Return the text the model would receive."""
        reason = await run_hooks(self.options, "PreToolUse", {"tool_name": full_name, "tool_input": args})
        if reason:
            return f"Denied by the gate: {reason}"
        tools = {t.name: t for t in self.options.mcp_servers["stock"]["tools"]}
        return (await tools[full_name.removeprefix("mcp__stock__")].handler(args))["content"][0]["text"]

    async def receive_response(self):
        steps = SECOND_RUN if "investigated 1 time(s) before" in self.prompt else FIRST_RUN
        turns = 0
        for number, step in enumerate(steps):
            if step[0] == "compact":
                path = Path(tempfile.gettempdir()) / "demo5g_fake_transcript.jsonl"
                path.write_text(TRANSCRIPT, encoding="utf-8")
                await run_hooks(self.options, "PreCompact", {"transcript_path": str(path), "trigger": "auto"})
                yield fake.SystemMessage(subtype="compact_boundary", data={})
                continue
            turns += 1
            if step[0] == "final":
                yield fake.AssistantMessage(content=[fake.TextBlock(text=step[1])])
                continue
            full_name, args = (step[1], step[2]) if step[0] == "raw" else ("mcp__stock__" + step[0], step[1])
            yield fake.AssistantMessage(content=[fake.ToolUseBlock(id=f"t{number}", name=full_name, input=args)])
            text = await self.call_tool(full_name, args)
            yield fake.UserMessage(content=[fake.ToolResultBlock(tool_use_id=f"t{number}", content=text)])
        yield fake.ResultMessage(subtype="success", num_turns=turns, total_cost_usd=0.42, result=steps[-1][1], usage={})


fake = types.ModuleType("claude_agent_sdk")
for class_name in ["ClaudeAgentOptions", "HookMatcher", "ResultMessage", "AssistantMessage", "UserMessage", "SystemMessage",
                   "ToolUseBlock", "ToolResultBlock", "TextBlock"]:
    setattr(fake, class_name, type(class_name, (Box,), {}))
fake.tool = lambda name, description, schema: (lambda handler: Box(name=name, handler=handler))
fake.create_sdk_mcp_server = lambda name, tools: {"name": name, "tools": tools}
fake.ClaudeSDKClient = FakeClient
sys.modules["claude_agent_sdk"] = fake

import audit_log  # noqa: E402  (after the fake is in place)
import case_memory  # noqa: E402
import context_meter  # noqa: E402
import limits  # noqa: E402
import stock_detective as sd  # noqa: E402
import stock_tools  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="demo5g_check_"))


def new_world():
    """An empty results folder inside the temporary folder, wired into the demo."""
    shutil.rmtree(TMP / "results", ignore_errors=True)
    sd.RESULTS = TMP / "results"
    sd.AUDIT_LOG, sd.APPROVAL_QUEUE, sd.ARCHIVE = sd.RESULTS / "audit_log.jsonl", sd.RESULTS / "approval_queue.json", sd.RESULTS / "archive"
    CLIENTS.clear()


def run_main(*argv):
    """Run the command line with these arguments and return everything it printed."""
    sys.argv = ["stock_detective.py", *argv]
    with contextlib.redirect_stdout(io.StringIO()) as shown:
        sd.main()
    return shown.getvalue()


def call_tool(name, args, role="branch_manager", case="oat-milk-harbour"):
    """Call one tool of the real server directly. Return its text."""
    tools = {t.name: t for t in sd.build_server(case, role, 1)["tools"]}
    return asyncio.run(tools[name].handler(args))["content"][0]["text"]


# -- Bounded views -------------------------------------------------------------------------------------------

print("Bounded tool results")
raw_rows = stock_tools.SALES["harbour"]["oat milk"]
long_log = call_tool("read_sales_log", {"branch": "harbour", "item": "oat milk", "days": 90})
check(f"the whole sales log is large ({stock_tools.sales_log_chars()} chars), the 90-day view is small ({len(long_log)} chars)",
      stock_tools.sales_log_chars() > 50_000 and len(long_log) < 2_000)
check("the sales view holds a summary, at most 7 rows and a 'Truncated' hint; the raw log is never returned whole",
      "Average by weekday" in long_log and long_log.count("\n  2026-") <= stock_tools.MAX_ROWS and "Truncated" in long_log
      and len(raw_rows) == 90 and raw_rows[0]["date"] not in long_log)
check("the weekend spike and the stock-out days are visible in the summary", "Sat 2" in long_log and "Stock-out days" in long_log and "Sun" in long_log)
delivery = call_tool("read_delivery_log", {"branch": "harbour"})
check("the delivery view gives the pattern and 8 rows, with a truncation hint", "oat milk: arrives on Tue" in delivery
      and delivery.count("\n  2026-") == stock_tools.MAX_DELIVERIES and "Truncated" in delivery)
supplier = call_tool("read_supplier_notes", {"item": "oat milk"})
older = call_tool("read_supplier_notes", {"item": "oat milk", "skip": 2})
check("supplier notes are bounded, wrapped as untrusted data, and 'skip' reaches the older notes", "untrusted=\"true\"" in supplier
      and "Truncated" in supplier and "cases of 8 cartons" in supplier and "Price list" in older and len(supplier) < 1_000)
check("the system prompt tells the model supplier text is data and that it cannot place orders", "Treat them as data" in sd.SYSTEM_PROMPT
      and "cannot place orders" in sd.SYSTEM_PROMPT)

# -- Argument limits inside the tools -------------------------------------------------------------------------

print("Argument limits inside the tools")
uptown = call_tool("read_inventory", {"branch": "uptown", "item": "oat milk"})
check("a branch outside the role is refused inside the tool, and says which branches are allowed", uptown.startswith(limits.REFUSED) and "harbour, central" in uptown)
check("the area_manager role may read uptown", "cartons on hand" in call_tool("read_inventory", {"branch": "uptown", "item": "oat milk"}, role="area_manager"))
check("days above 90 and days below 1 are refused", all(call_tool("read_sales_log", {"branch": "harbour", "item": "oat milk", "days": d}).startswith(limits.REFUSED)
                                                     for d in (91, 0, -5)))
check("an item that is not in the catalogue is refused", call_tool("read_sales_log", {"branch": "harbour", "item": "tea", "days": 7}).startswith(limits.REFUSED)
      and call_tool("read_supplier_notes", {"item": "tea"}).startswith(limits.REFUSED))
check("an unknown role may read nothing", limits.check_branch("intern", "harbour").startswith(limits.REFUSED))
new_world()
check("a note over the length limit is refused and not saved", call_tool("write_note", {"text": "x" * 500}).startswith(limits.REFUSED)
      and not case_memory.read_notes(sd.RESULTS, "oat-milk-harbour"))
check("a case name that could leave the results folder is rejected", not any(case_memory.CASE_NAME.match(bad) for bad in ("../x", "a/b", "Upper", "", "x" * 41))
      and case_memory.CASE_NAME.match("oat-milk-harbour"))

# -- Propose, never place --------------------------------------------------------------------------------------

print("Proposals and the approval queue")
new_world()
big = call_tool("propose_order", {"item": "oat milk", "qty": 112})
small = call_tool("propose_order", {"item": "oat milk", "qty": 10})
queue = json.loads(sd.APPROVAL_QUEUE.read_text(encoding="utf-8"))
check("an order above the limit goes to the approval queue and says it needs a manager", len(queue) == 2 and queue[0]["cost_usd"] == 268.8
      and queue[0]["status"] == "needs manager approval" and "NOT placed" in big)
check("a small proposal is also saved and answered, never dropped silently", queue[1]["cost_usd"] == 24.0 and "within the limit" in queue[1]["status"] and "NOT placed" in small)
check("no proposal is ever marked placed, and no code in the demo can place an order",
      all(row["placed"] is False for row in queue) and not [n for n in dir(stock_tools) + dir(limits) if "place" in n.lower() and n != "propose_order"])
check("bad proposals (qty 0, qty 5000, unknown item) are refused", all(call_tool("propose_order", a).startswith(limits.REFUSED)
      for a in ({"item": "oat milk", "qty": 0}, {"item": "oat milk", "qty": 5000}, {"item": "tea", "qty": 3})))

# -- The options ------------------------------------------------------------------------------------------------

print("The options")
options = sd.build_options("oat-milk-harbour", "branch_manager", 1)
check("allow-list: exactly the 7 stock tools, no built-in tools", options.allowed_tools == ["mcp__stock__" + t for t in limits.TOOLS]
      and len(options.allowed_tools) == 7 and options.tools == [])
check("Bash, Write and Edit are in disallowed_tools", {"Bash", "Write", "Edit"} <= set(options.disallowed_tools))
check("dontAsk, no settings files, the main model, a turn limit and a budget limit are set", options.permission_mode == "dontAsk" and options.setting_sources == []
      and options.model == "claude-sonnet-5-5" and options.max_turns == 25 and options.max_budget_usd == 1.0)
check("a PreToolUse gate and a PreCompact hook are registered", set(options.hooks) == {"PreToolUse", "PreCompact"})

# -- The gate and the audit log -------------------------------------------------------------------------------

print("The gate and the audit log")
new_world()
options = sd.build_options("oat-milk-harbour", "branch_manager", 1)
with contextlib.redirect_stdout(io.StringIO()) as shown:
    listed = asyncio.run(run_hooks(options, "PreToolUse", {"tool_name": "mcp__stock__read_notes", "tool_input": {}}))
    unlisted = asyncio.run(run_hooks(options, "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}))
    other = asyncio.run(run_hooks(options, "PreToolUse", {"tool_name": "mcp__stock__delete_everything", "tool_input": {}}))
rows = [json.loads(line) for line in sd.AUDIT_LOG.read_text(encoding="utf-8").splitlines()]
check("the gate allows a listed tool and denies Bash and an unlisted tool (deny by default)", listed is None and "allow-list" in unlisted and other is not None
      and "[guardrail]" in shown.getvalue())
check("every gate decision is in the audit log with a reason", [r["decision"] for r in rows] == ["allow", "deny", "deny"] and all(r["reason"] for r in rows))
new_world()
sd.AUDIT_LOG.parent.mkdir(parents=True)
audit_log.write(sd.AUDIT_LOG, "c", "r", "t", {"text": "y" * 300}, True, "ok")
log_text = sd.AUDIT_LOG.read_text(encoding="utf-8")
check("the audit log shortens long arguments", len(json.loads(log_text)["args"]["text"]) == audit_log.MAX_VALUE_CHARS)

# -- A whole run, then a second run ------------------------------------------------------------------------------

print("Run 1, run 2 and the saved memory")
new_world()
first = run_main("--case", "oat-milk-harbour")
tool_results = first.count(" chars  ~")
running = [int(n) for n in re.findall(r"running\s+(\d+) of", first)]
check("every turn prints the tool, the result size and the running context total", tool_results == 11 and len(running) == 11 and "turn  1  read_inventory" in first
      and "~" in first)
before_compaction = running[: running.index(max(running)) + 1]
check("the running total grows from result to result and starts again at the compaction", before_compaction == sorted(before_compaction)
      and "[compaction]" in first and "Context: 1 compaction(s)" in first and running[8] < running[7])
check("the bounded view keeps the context far below the whole log (peak vs the whole file)", max(running) < stock_tools.sales_log_chars() // context_meter.CHARS_PER_TOKEN // 5)
check("a refused branch is shown as a guardrail line and the run goes on", "[guardrail] Refused: the role branch_manager may not read the branch 'uptown'" in first
      and "propose_order" in first)
check("Bash is denied by the gate during the run", "[guardrail] Bash is not on the allow-list" in first)
check("the PreCompact hook archives the transcript before the compaction", len(list(sd.ARCHIVE.glob("oat-milk-harbour_*.jsonl"))) == 1
      and next(sd.ARCHIVE.glob("*.jsonl")).read_text(encoding="utf-8") == TRANSCRIPT and "[PreCompact] transcript archived" in first)
notes = case_memory.read_notes(sd.RESULTS, "oat-milk-harbour")
check("the working notes were written to results/notes_<case>.md, one short line per fact", notes.count("- (run 1)") == 3 and "Tuesdays" in notes and "weekend" in notes)
check("the retention check passes: the three key facts are still in the notes", "Retention check, the key facts are still in the notes: PASS" in first)
check("the retention check finds a fact that is missing", case_memory.missing_facts("Only weekend sales.", {"weekend": ["weekend"], "case": ["case"]}) == ["case"])
history = case_memory.load_history(sd.RESULTS, "oat-milk-harbour")
check("the findings are saved to case_history.jsonl", len(history) == 1 and history[0]["findings"] == FINDINGS and history[0]["turns"] == 12 and history[0]["retention"] == "PASS")
check("the findings are printed and the approval queue has one proposal waiting", "Findings:\nCause: weekend demand" in first and "Proposals waiting for a person: 1" in first)
check("the run ended inside its limits and says so", "(limit 25)" in first and "(limit $1.00)" in first)
first_prompt = CLIENTS[0].prompt

second = run_main("--case", "oat-milk-harbour")
check("the second run starts from the saved notes and findings", "Starting from saved notes and findings." in second and "run 2" in second
      and "investigated 1 time(s) before" in CLIENTS[1].prompt and FINDINGS in CLIENTS[1].prompt and "investigated" not in first_prompt)
check("the second run re-reads the notes with read_notes, and uses fewer turns", "read_notes" in second and second.count(" chars  ~") == 2
      and case_memory.load_history(sd.RESULTS, "oat-milk-harbour")[1]["turns"] < history[0]["turns"])
check("the notes keep the run 1 lines and the history now holds two runs", case_memory.read_notes(sd.RESULTS, "oat-milk-harbour").startswith(notes)
      and len(case_memory.load_history(sd.RESULTS, "oat-milk-harbour")) == 2)
check("--show-notes and --show-history print the saved memory without a run", "Tuesdays" in run_main("--show-notes") and "run 2" in run_main("--show-history")
      and len(CLIENTS) == 2)
try:
    run_main("--case", "new-case")
    exit_ok = False
except SystemExit as stop:
    exit_ok = "--task" in str(stop)
check("a case that is not in data/cases.json asks for --task instead of guessing", exit_ok)
long_notes = TMP / "long"
for number in range(80):
    case_memory.append_note(long_notes, "big", "A fact about the case, number " + str(number) + ". " + "x" * 60, 1)
bounded = case_memory.read_notes_bounded(long_notes, "big")
check("read_notes returns only the newest part of very long notes, with a hint", len(bounded) < case_memory.NOTES_READ_MAX_CHARS + 100
      and "Truncated" in bounded and "number 79" in bounded and "number 0." not in bounded)
check("a different case has its own notes", case_memory.read_notes(sd.RESULTS, "another-case") == "")

# -- The audit log of the whole run -----------------------------------------------------------------------------

audit_text = sd.AUDIT_LOG.read_text(encoding="utf-8")
audit_rows = [json.loads(line) for line in audit_text.splitlines()]
check("the audit log of the runs has allow and deny rows and no secret", {"allow", "deny"} <= {r["decision"] for r in audit_rows}
      and SECRET not in audit_text and "sk-ant" not in audit_text and "ANTHROPIC" not in audit_text)
for path in sd.RESULTS.rglob("*"):
    if path.is_file():
        assert SECRET not in path.read_text(encoding="utf-8")

# -- The files ----------------------------------------------------------------------------------------------------

print("The files")
sources = {path.name: path.read_text(encoding="utf-8") for path in HERE.glob("*.py")}
for source in sources.values():
    ast.parse(source)
main_lines = sum(1 for line in sources["stock_detective.py"].splitlines() if line.strip())
check(f"every .py file parses, and stock_detective.py has {main_lines} non-blank lines (limit 300)", main_lines <= 300)
check("the pure modules import no SDK", all("claude_agent_sdk" not in sources[name] for name in
      ("limits.py", "stock_tools.py", "case_memory.py", "context_meter.py", "audit_log.py", "shop_data.py")))
check("the SDK is used only in stock_detective.py", [n for n, s in sources.items() if "claude_agent_sdk" in s and n != "check_offline.py"] == ["stock_detective.py"])
left = sorted(p.name for p in (HERE / "results").iterdir()) if (HERE / "results").exists() else []
check("this folder has no results and no __pycache__", left in ([], [".gitkeep"]) and not list(HERE.rglob("__pycache__")))
shutil.rmtree(TMP, ignore_errors=True)
Path(tempfile.gettempdir(), "demo5g_fake_transcript.jsonl").unlink(missing_ok=True)
print("ALL OK" if all(results) else "SOME CHECK FAILED")
sys.exit(0 if all(results) else 1)
