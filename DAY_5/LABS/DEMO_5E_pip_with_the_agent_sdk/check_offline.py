"""Key-free self-check for Demo 5E. No key, no network, no Claude Code CLI, and the real SDK is never used.

    python check_offline.py

A scripted fake of claude_agent_sdk stands in for the model. Its replies, summaries and token counts are author-written fixtures, not model results.
The chat loop, the tier rules, the gate, the audit log, the memory files and the compaction all run for real.
Everything the script writes goes to a temporary folder, so this folder stays clean.
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

CLIENTS = []  # every client the chat opened, in order
FAKE = {"summary": "Customer chatted about hours and points.", "found": {"pinned_rules": ["allergic to nuts"], "facts": ["name is Maya"]}}
TOKENS_PER_MESSAGE = 250  # author-written: each stored message adds this many "tokens"
TOOL_FOR_WORD = {"redeem": "redeem_points", "menu": "read_menu", "points": "get_points_balance"}  # redeem first: its text also says "points"


class Box:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)


async def run_gate(options, tool, args):
    """Call the PreToolUse hooks as the SDK would. Return the denial reason, or None when the tool is allowed."""
    for matcher in options.hooks["PreToolUse"]:
        for hook in matcher.hooks:
            out = await hook({"tool_name": "mcp__pip__" + tool, "tool_input": args}, "toolu_x", None)
            if out["hookSpecificOutput"]["permissionDecision"] == "deny":
                return out["hookSpecificOutput"]["permissionDecisionReason"]
    return None


class FakeClient:
    def __init__(self, options=None):
        self.options, self.history, self.queue, self.connected = options, [], [], False
        CLIENTS.append(self)

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    def base_tokens(self):
        return 500 + len(self.options.system_prompt) // 4

    async def get_context_usage(self):
        return {"totalTokens": self.base_tokens() + TOKENS_PER_MESSAGE * len(self.history)}

    async def scripted_reply(self, prompt):
        """What the scripted 'model' says. It tries the tool that matches the message, so the gate and the tool run for real."""
        if prompt.startswith("Summarize this conversation"):
            return FAKE["summary"]
        if prompt.startswith("List what we must remember"):
            return json.dumps(FAKE["found"])
        word = next((word for word in TOOL_FOR_WORD if word in prompt.lower()), None)
        if word is None:
            return "Scripted reply."
        tool, args = TOOL_FOR_WORD[word], {}
        if tool == "redeem_points":
            args = {"points": int(re.search(r"redeem (\d+)", prompt).group(1))}
        reason = await run_gate(self.options, tool, args)
        if reason:
            return f"Sorry, I cannot do that: {reason}"
        tools = {t.name: t for t in self.options.mcp_servers["pip"]["tools"]}
        return (await tools[tool].handler(args))["content"][0]["text"]

    async def query(self, prompt):
        reply = await self.scripted_reply(prompt)
        self.history += [prompt, reply]
        usage = {"input_tokens": self.base_tokens() + TOKENS_PER_MESSAGE * (len(self.history) - 1), "output_tokens": TOKENS_PER_MESSAGE}
        self.queue = [fake.ResultMessage(result=reply, session_id="sess", usage=usage)]

    async def receive_response(self):
        for message in self.queue:
            yield message


fake = types.ModuleType("claude_agent_sdk")
for class_name in ["ClaudeAgentOptions", "HookMatcher", "ResultMessage"]:
    setattr(fake, class_name, type(class_name, (Box,), {}))
fake.tool = lambda name, description, schema: (lambda handler: Box(name=name, handler=handler))
fake.create_sdk_mcp_server = lambda name, tools: {"name": name, "tools": tools}
fake.ClaudeSDKClient = FakeClient
sys.modules["claude_agent_sdk"] = fake

import audit_log  # noqa: E402  (after the fake is in place)
import context_limit  # noqa: E402
import memory_store  # noqa: E402
import pip_agent_sdk as pip  # noqa: E402
import pip_tools  # noqa: E402
import tiers  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="demo5e_check_"))
FIVE = ["Hi, I'm Maya. When do you open on Saturday?", "Please never send me marketing email. I am allergic to nuts.", "What is on the menu?",
       "How many points do I have?", "Please redeem 80 points for me."]


def new_world():
    """Fresh memory and audit folders for one scenario."""
    folder = Path(tempfile.mkdtemp(dir=TMP))
    pip.MEMORY_DIR, pip.AUDIT_LOG = folder / "memory", folder / "audit_log.jsonl"
    CLIENTS.clear()
    FAKE["summary"] = "Customer chatted about hours and points."
    FAKE["found"] = {"pinned_rules": ["allergic to nuts"], "facts": ["name is Maya"]}


def lines_reader(lines, ending):
    """A reader that gives the lines one by one, echoes them like a chat, and then raises `ending`."""
    queue = list(lines)

    def read(prompt):
        if not queue:
            raise ending
        print(prompt + queue[0])
        return queue.pop(0)
    read.queue = queue
    return read


def chat(lines, card="C-1042", tier="gold", ending=EOFError):
    """Run one whole chat against the fake. Return (printed text, reader)."""
    read = lines_reader(lines, ending)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        asyncio.run(pip.run_chat(card, tier, pip.DEMO_LIMIT, "fake-model", read))
    return out.getvalue(), read


def run_main(*argv):
    """Run pip.main() as if from the command line. Return the printed text."""
    sys.argv = ["pip_agent_sdk.py", *argv]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        pip.main()
    return out.getvalue()


def saved(card):
    """The memory file for a card, or None."""
    return memory_store.load(pip.MEMORY_DIR, card)


# -- The chat loop ------------------------------------------------------------------------------------------

print("The chat loop")
new_world()
text, read = chat(["/compact", "Hi, I'm Maya.", "/help", "/memory", "/bogus", "What is on the menu?", "/end", "NEVER READ THIS"])
check("the chat ends only on /end (commands and many turns do not end it)", read.queue == ["NEVER READ THIS"] and text.count("Pip: ") == 2)
check("the commands work: /help, /memory (nothing saved yet), unknown command, /compact with nothing new", "Commands:" in text and "Nothing saved yet" in text
      and "Unknown command" in text and "Nothing new to compact" in text)
check("each reply shows the context size", "[context] " in text and " of 3000 tokens" in text)
check("/end saves the memory file and prints the recap", saved("C-1042") and "Memory saved to results/memory/C-1042.json" in text and "You still own" in text)

new_world()
text, _ = chat(["Hi, I'm Maya."], ending=KeyboardInterrupt)
check("Ctrl+C ends the chat cleanly and the memory is saved", saved("C-1042") and "(input ended)" in text and "Traceback" not in text)
new_world()
chat(["Hi, I'm Maya."], ending=EOFError)
check("end of input ends the chat cleanly and the memory is saved", saved("C-1042") is not None)
new_world()
text, _ = chat(["/end"])
check("a chat with no message writes no file", saved("C-1042") is None and "Memory saved" not in text)

# -- Memory: first run, second run, scope -------------------------------------------------------------------

print("Memory files")
new_world()
text, _ = chat(["Hi, I'm Maya.", "Please never send me marketing email.", "/end"])
file_one = saved("C-1042")
check("first run: no file, so 'New customer' and an empty memory in the prompt", "New customer, starting a new session" in text
      and "What we saved" not in CLIENTS[0].options.system_prompt)
check("the file holds card_id, summary, pinned_rules, facts, last_session and turns_total",
      set(file_one) == {"card_id", "summary", "pinned_rules", "facts", "last_session", "turns_total"} and file_one["card_id"] == "C-1042" and file_one["turns_total"] == 2)

text, _ = chat(["Hello again.", "/end"])
prompt = CLIENTS[-1].options.system_prompt
check("second run: 'Welcome back' prints the saved summary, rules and facts", "Welcome back" in text and file_one["summary"] in text
      and "allergic to nuts" in text and "name is Maya" in text)
check("second run: summary, pinned rules and facts are in the system prompt of a brand-new session",
      len(CLIENTS) == 2 and file_one["summary"] in prompt and "allergic to nuts" in prompt and "name is Maya" in prompt)
check("the second chat adds its turns to the file", saved("C-1042")["turns_total"] == 3 and "allergic to nuts" in saved("C-1042")["pinned_rules"])

new_world()
memory_store.save(pip.MEMORY_DIR, {**memory_store.blank("C-1042"), "pinned_rules": ["card A secret rule"], "summary": "card A summary"})
opened = []
real_path_for = memory_store.path_for
memory_store.path_for = lambda folder, card: (opened.append(card), real_path_for(folder, card))[1]
text, _ = chat(["Hi, I'm Ben.", "/memory", "/end"], card="C-2001", tier="member")
memory_store.path_for = real_path_for
check("per-card scope: card B never loads card A's file", "New customer" in text and "card A" not in text and "card A" not in CLIENTS[0].options.system_prompt
      and set(opened) == {"C-2001"})

# -- The token limit and compaction -------------------------------------------------------------------------

print("Token limit and compaction")
new_world()
memory_store.save(pip.MEMORY_DIR, {**memory_store.blank("C-1042"), "pinned_rules": ["never send marketing email", "allergic to nuts"], "turns_total": 4})
FAKE["summary"] = "\n".join(f"Line {n}: Customer asked about hours." for n in range(1, 10))
FAKE["found"] = {"pinned_rules": [], "facts": ["name is Maya"]}  # the fake summary and facts forget the old rules on purpose
text, read = chat(FIVE + ["y", "Which pastry is safe for me?", "/end"])
asked_after = text.index("[y/n]")
before, after = map(int, re.search(r"(\d+) tokens before, (\d+) after", text).groups())
check("limit reached: the y/n question appears after the fifth reply and not before", text.count("[y/n]") == 1 and text[:asked_after].count("Pip: ") == 5
      and re.search(r"Context is full \(\d+ of 3000 tokens\)\. Compact it and save to memory\? \[y/n\]", text) and "WARNING" in text)
check("y compacts: the old client is closed and a NEW session starts", len(CLIENTS) == 2 and not CLIENTS[0].connected and CLIENTS[1].connected is False and CLIENTS[1] is not CLIENTS[0])
check("y compacts: the token count drops", after < before and after < pip.DEMO_LIMIT and "A new session has started" in text)
check("retention PASS: old pinned rules survive although the fake summary omitted them", "Retention check, every old pinned rule is still present: PASS" in text
      and {"never send marketing email", "allergic to nuts"} <= set(saved("C-1042")["pinned_rules"]))
check("the new session's system prompt holds the summary, the pinned rules and the facts", "Line 1: Customer asked" in CLIENTS[1].options.system_prompt
      and "never send marketing email" in CLIENTS[1].options.system_prompt and "name is Maya" in CLIENTS[1].options.system_prompt)
check("the summary is clipped to six lines and the file is written", saved("C-1042")["summary"].count("\n") == 5 and saved("C-1042")["last_session"])
check("/end after compaction saves again without another new session", len(CLIENTS) == 2 and text.count("Memory saved") == 2 and saved("C-1042")["turns_total"] == 4 + 6)
check("the retention check can STOP: a lost rule is reported", memory_store.missing_rules({"pinned_rules": ["a", "B"]}, {"pinned_rules": ["b"]}) == ["a"])

new_world()
text, read = chat(FIVE + ["n", "What is on the menu?", "n", "/end"])
check("n continues in the same session and asks again after the next reply", text.count("[y/n]") == 2 and len(CLIENTS) == 1
      and "I will ask again" in text and "Compacted" not in text)
new_world()
text, _ = chat(["Hi, I'm Maya.", "Please never email me.", "/compact", "/end"])
check("/compact works at any time", "Compacted." in text and len(CLIENTS) == 2 and saved("C-1042"))
check("context_limit: the usage fields are summed, and the limit check is >=", context_limit.context_tokens({"input_tokens": 10, "cache_read_input_tokens": 5, "output_tokens": 2}) == 17
      and context_limit.context_tokens(None) == 0 and context_limit.is_full(3000, 3000) and not context_limit.is_full(2999, 3000))
check("the limits: demo is small, real is a stated fraction of the window", pip.LIMITS == {"demo": 3000, "real": int(pip.MODEL_WINDOW * pip.REAL_LIMIT_FRACTION)})
check("model JSON is validated in code: junk, a wrong shape and a list of numbers give empty lists",
      memory_store.parse_found("not json") == {"pinned_rules": [], "facts": []} and memory_store.parse_found('{"facts": "x"}')["facts"] == []
      and memory_store.parse_found('Sure! {"facts": ["a", 5, " "], "pinned_rules": ["r"]}') == {"pinned_rules": ["r"], "facts": ["a"]})

# -- Tier guardrails ----------------------------------------------------------------------------------------

print("Tier guardrails")
new_world()
text, _ = chat(["How many points do I have?", "Please redeem 50 points.", "What is on the menu?"], card="C-3003", tier="guest")
check("guest cannot get a balance or redeem, and sees a [guardrail] line live", "[guardrail] guest cannot use get_points_balance" in text
      and "[guardrail] guest cannot use redeem_points" in text and "Menu:" in text)
new_world()
text, _ = chat(["How many points do I have?", "Please redeem 20 points."], card="C-2001", tier="member")
check("member can get a balance but cannot redeem", "Ben has 40 points" in text and "[guardrail] member cannot use redeem_points" in text)
new_world()
text, _ = chat(["Please redeem 80 points."])
check("gold can redeem 80 points", "Redeemed 80 points for Maya" in text and "[guardrail]" not in text)
new_world()
text, _ = chat(["Please redeem 150 points."])
check("gold redeem over 100 is denied", "[guardrail] gold cannot redeem: the limit is 100 points per visit" in text)
new_world()
text, _ = chat(["Please redeem 80 points."], card="C-2001", tier="gold")
check("gold redeem over the balance is denied", "[guardrail] gold cannot redeem: the balance is only 40 points" in text)
check("a tool outside every tier (Bash) is denied", not tiers.decide("gold", "Bash", {}, 120)[0])

tools_a = {t.name: t for t in pip.build_server("C-1042")["tools"]}
tried = asyncio.run(tools_a["get_points_balance"].handler({"card_id": "C-2001"}))["content"][0]["text"]  # the model tries to name another card
redeemed = asyncio.run(tools_a["redeem_points"].handler({"points": 10, "card_id": "C-2001"}))["content"][0]["text"]
check("the tool bound to card A never returns card B's data", "Maya" in tried and "Ben" not in tried and "Maya" in redeemed and "Ben" not in redeemed)
for tier in tiers.TIERS:
    options = pip.build_options(tier, pip_tools.card_for(tier), memory_store.blank("x"), "m")
    check(f"options for {tier}: tier tools only, dangerous tools denied, dontAsk, CLAUDE.md on, limits set",
          options.allowed_tools == ["mcp__pip__" + t for t in tiers.tools_for(tier)] and {"Bash", "Write", "Edit"} <= set(options.disallowed_tools)
          and options.permission_mode == "dontAsk" and options.setting_sources == ["project"] and options.cwd == str(HERE / "workspace")
          and options.max_turns and options.max_budget_usd)
check("workspace/CLAUDE.md holds the standing shop rules", "100 points" in (HERE / "workspace" / "CLAUDE.md").read_text(encoding="utf-8"))
tiers.TIERS["guest"]["tools"].append("get_points_balance")
changed = pip.build_options("guest", "C-3003", memory_store.blank("x"), "m")
check("tiers.json is the single source: one edit changes the options and the gate", "mcp__pip__get_points_balance" in changed.allowed_tools
      and tiers.decide("guest", "get_points_balance", {}, 0)[0])
tiers.TIERS["guest"]["tools"].remove("get_points_balance")

new_world()
chat(["How many points do I have?", "Please redeem 80 points."])
log_text = pip.AUDIT_LOG.read_text(encoding="utf-8")
rows = [json.loads(line) for line in log_text.splitlines()]
check("every decision is in the audit log with a reason", len(rows) == 2 and all(r["reason"] and r["decision"] in ("allow", "deny") for r in rows))
check("audit log lines hold no secret and no full card id", SECRET not in log_text and "sk-ant" not in log_text and "C-1042" not in log_text and "C-10**" in log_text)
check("audit_log.mask hides the last two characters", audit_log.mask("C-1042") == "C-10**" and audit_log.mask(None) == "none")

# -- --script and the start-up questions --------------------------------------------------------------------

print("Script mode and start-up")
for tier, card, file in [("guest", "C-3003", "sample_chat_guest.txt"), ("member", "C-2001", "sample_chat_member.txt"), ("gold", "C-1042", "sample_chat_gold.txt")]:
    new_world()
    text = run_main("--script", str(HERE / "data" / file), "--card", card, "--tier", tier)
    check(f"--script {file} runs to /end and saves the memory", saved(card) and "Chat ended." in text and text.count("You: ") >= 4)
check("the gold script reaches the limit, answers y, compacts and ends", "[y/n] y" in text and "Compacted." in text and len(CLIENTS) == 2)
new_world()
text = run_main("--script", str(HERE / "data" / "sample_chat_guest.txt"), "--card", "C-3003", "--tier", "guest")
check("the guest script shows the guardrail and /memory", "[guardrail] guest cannot use redeem_points" in text and "Nothing saved yet" in text)
read = lines_reader(["", ""], EOFError)
with contextlib.redirect_stdout(io.StringIO()) as shown:
    login = pip.choose_login(types.SimpleNamespace(card=None, tier=None, script=None), read)
check("the card and the tier are asked once; empty answers take the defaults; the customers are listed", login == ("C-1042", "gold") and "C-2001" in shown.getvalue())
read = lines_reader(["C-2001", "guest"], EOFError)
with contextlib.redirect_stdout(io.StringIO()):
    login = pip.choose_login(types.SimpleNamespace(card=None, tier=None, script=None), read)
    flagged = pip.choose_login(types.SimpleNamespace(card="C-1042", tier="member", script=None), lines_reader([], EOFError))
check("a typed card and tier are used, and --card/--tier skip the questions", login == ("C-2001", "guest") and flagged == ("C-1042", "member"))

# -- The files ----------------------------------------------------------------------------------------------

print("The files")
sources = {path.name: path.read_text(encoding="utf-8") for path in HERE.glob("*.py")}
for name, source in sources.items():
    ast.parse(source)
main_lines = sum(1 for line in sources["pip_agent_sdk.py"].splitlines() if line.strip())
check(f"every .py file parses, and pip_agent_sdk.py has {main_lines} non-blank lines (limit 300)", main_lines <= 300)
check("the old stage code and the --live flag are gone", "def stage" not in sources["pip_agent_sdk.py"]
      and "--live" not in sources["pip_agent_sdk.py"])
check("the pure modules import no SDK", all("claude_agent_sdk" not in sources[name] for name in ("tiers.py", "memory_store.py", "pip_tools.py", "audit_log.py", "context_limit.py")))
left = sorted(p.name for p in (HERE / "results").iterdir()) if (HERE / "results").exists() else []
check("this folder has no results and no __pycache__", left in ([], [".gitkeep"]) and not list(HERE.rglob("__pycache__")))
print("ALL OK" if all(results) else "SOME CHECK FAILED")
sys.exit(0 if all(results) else 1)
