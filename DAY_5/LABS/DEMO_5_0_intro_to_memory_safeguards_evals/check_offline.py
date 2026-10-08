"""Key-free self-check for Demo 5.0. No API key, no network, no model.

Run from this folder:   python check_offline.py
It tests the plain code (the rule, the grader, the gate, the memory file) and runs every part against a
scripted fake model. The fake model replays AUTHOR-WRITTEN replies from data/author_fixtures.json. They test
the code. They are not measured model output.
"""
import ast
import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import intro_5_0 as demo  # noqa: E402

failures = []


def check(label, ok):
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        failures.append(label)


def run_quiet(function, *args):
    """Run a function and return everything it printed."""
    with contextlib.redirect_stdout(io.StringIO()) as buffer:
        function(*args)
    return buffer.getvalue()


FIXTURES = json.loads((HERE / "data" / "author_fixtures.json").read_text(encoding="utf-8"))
CASES = demo.load("eval_cases.json")
SEEN = []   # every request the fake model received


def block(kind, **fields):
    return SimpleNamespace(type=kind, **fields)


def response(blocks, request, stop="end_turn"):
    tokens = len(json.dumps([request["system"], request["messages"], request.get("tools", [])], default=str)) // 4
    return SimpleNamespace(content=blocks, stop_reason=stop, usage=SimpleNamespace(input_tokens=tokens, output_tokens=30))


class FakeMessages:
    """A scripted Pip. It answers from what is in the request, so it also proves what the request contained."""

    def create(self, **request):
        SEEN.append(request)
        messages, system = request["messages"], request["system"]
        last = messages[-1]["content"]
        if isinstance(last, list):
            return response([block("text", text="Done. Your 80 points are redeemed, and you have 40 left.")], request)
        if "tools" in request and "80 points for a pastry" in last:
            call = block("tool_use", id="t1", name="redeem_points", input={"reward": "pastry", "points": 80})
            return response([call], request, stop="tool_use")
        return response([block("text", text=self.reply(last, system, messages))], request)

    def reply(self, last, system, messages):
        for case in CASES:
            if last == case["question"]:
                version = "v2" if "Rules for every answer" in system else "v1"
                return FIXTURES[version][case["id"]]
        if "What is my name" in last:
            seen = json.dumps(messages[:-1]) + system
            return "Your name is Maya." if "Maya" in seen else "I do not know your name yet."
        if "autumn menu" in last:
            return "Hi Maya. You asked for no marketing email, so I will not send it. Please ask staff about nuts."
        if "close on Saturday" in last:
            return "We close at 4pm on Saturday."
        if "free coffee" in last:
            return "A free coffee costs 50 points."
        return "Yes, 80 points for a pastry is fine, and it is under the 100-point limit."

    def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=777)


demo._client = SimpleNamespace(messages=FakeMessages())

# 1. Files and data.
source = (HERE / "intro_5_0.py").read_text(encoding="utf-8")
ast.parse(source)
check("intro_5_0.py parses", True)
check("5 eval cases, each with a question and an expected keyword", len(CASES) == 5 and all(c["question"] and c["expect"] for c in CASES))
check("both prompts hold the {facts} slot and v2 adds rules", all("{facts}" in (HERE / "prompts" / f"pip_{v}.txt").read_text() for v in ("v1", "v2"))
      and "Rules for every answer" in (HERE / "prompts" / "pip_v2.txt").read_text())
check("fixtures are labelled author-written", "AUTHOR-WRITTEN" in FIXTURES["_note"])
check("models and prices follow the course rules", demo.MODEL_FAST == "claude-haiku-5-5" and demo.MODEL_BALANCED == "claude-sonnet-5-5"
      and demo.PRICE_PER_MTOK == {"claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)})
check("no temperature, top_p, prefill, thinking or Opus in the script", not any(w in source.lower() for w in ("temperature", "top_p", "prefill", "thinking", "opus")))

# 2. Plain code: the rule, the guard, the router, the grader and the gate.
check("rule: 100 points is allowed, 101 is handed off", demo.check_limit(100) == "ok" and demo.check_limit(101).startswith("handoff"))
check("guard: pastry for 80 points is ok", demo.guard("pastry", 80, 120) == "ok")
check("guard: lunch combo for 120 points is handed off", demo.guard("lunch combo", 120, 120).startswith("handoff"))
check("guard: an unknown reward is refused", demo.guard("gift card", 60, 120).startswith("refused"))
check("guard: points that are not a whole number are refused", demo.guard("coffee", "50", 120).startswith("refused"))
check("guard: more points than the balance is refused", demo.guard("pastry", 80, 60).startswith("refused"))
with contextlib.redirect_stdout(io.StringIO()):
    refused_balance = demo.guarded_redeem({"reward": "lunch combo", "points": 120}, 120)[1]
check("redeem tool: the balance is unchanged when the check says no", refused_balance == 120)
check("router: refund and delete go to a person, hours go to Pip",
      demo.needs_person("I want a refund") and demo.needs_person("Please delete my data.") and not demo.needs_person("When do you open?"))
check("grader: '4 pm' and '4:00 PM' both match 4pm", all(demo.grade({"expect": "4pm"}, r) for r in ("We close at 4 pm", "Closing: 4:00 PM")))
check("grader: a missing keyword does not pass", not demo.grade({"expect": "100"}, "That depends on the shop."))
old = [{"id": "A", "passed": True}, {"id": "B", "passed": False}, {"id": "C", "passed": True}]
better = [{"id": "A", "passed": True}, {"id": "B", "passed": True}, {"id": "C", "passed": True}]
worse = [{"id": "A", "passed": False}, {"id": "B", "passed": True}, {"id": "C", "passed": True}]
check("compare: improved, regressed and same are found", demo.compare(old, worse) == {"A": "regressed", "B": "improved", "C": "same"})
check("gate: PASS when nothing regressed", demo.gate(old, better).startswith("GATE: PASS"))
check("gate: BLOCKED when a case regressed, even if the rate holds", demo.gate(old, worse).startswith("GATE: BLOCKED"))
chat = demo.load("sample_chat.json")
kept = demo.trim_to_last(chat, demo.KEEP_LAST)
check("trim: keeps the last 4 messages and starts with the customer", len(kept) == 4 and kept[0]["role"] == "user" and kept[-1] == chat[-1])
check("trim: drops a leading Pip message", demo.trim_to_last(chat, 3)[0]["role"] == "user")
check("bar: half full is half hashes", demo.bar(500, 1000, 10).startswith("[#####.....]"))

# 3. Part 1: no history means no name; history brings it back; input tokens grow.
SEEN.clear()
out = run_quiet(demo.part1)
check("part 1: Pip forgets the name without history", "I do not know your name yet." in out)
check("part 1: Pip knows the name with history", "Your name is Maya." in out)
tokens = [int(m) for m in re.findall(r"^call [^\n]*?(\d+)$", out, flags=re.M)]
check("part 1: input tokens grow once history is sent (call 1 < with history < call 3)", len(tokens) == 4 and tokens[0] < tokens[2] < tokens[3])
check("part 1: the TYPE LIVE lines are in the script", "# --- TYPE LIVE" in source and source.count('messages.append({"role": "assistant"') >= 2)

# 4. Part 2: no key needed, and the trim loses the name.
real_get_client = demo.get_client
demo.get_client = lambda: (_ for _ in ()).throw(RuntimeError("part 2 must not need the API"))
out = run_quiet(demo.part2)
check("part 2: runs with no client at all", "Simplest trim" in out)
check("part 2: the trim loses the customer's name", "no, it was in a dropped message" in out)
check("part 2: compact and summarise are explained", "compact" in out and "summarise" in out)
demo.get_client = real_get_client
check("part 2 --count: the API count is printed next to the estimate", "counted 777" in run_quiet(demo.part2, True))

# 5. Part 3: save, then a fresh start loads the file. Results go to a temp folder.
with tempfile.TemporaryDirectory() as tmp:
    demo.RESULTS = Path(tmp)
    run_quiet(demo.part3, "save")
    saved = demo.load_memory(demo.CUSTOMER["card"])
    check("part 3: three facts are saved to one file for one card", set(saved) == {"name", "allergy", "marketing"}
          and (Path(tmp) / f"memory_{demo.CUSTOMER['card']}.json").exists())
    SEEN.clear()
    out = run_quiet(demo.part3, "ask")
    system = SEEN[-1]["system"]
    check("part 3: the new process starts with an empty messages list", "holds 0 messages" in out and len(SEEN[-1]["messages"]) == 1)
    check("part 3: the saved facts are in the system prompt", "allergic to nuts" in system and "no marketing email" in system)
    check("part 3: Pip answers from memory", "Hi Maya" in out)
    launched = []
    original_run = demo.subprocess.run
    demo.subprocess.run = lambda cmd, **kw: launched.append(cmd)
    run_quiet(demo.part3, "both")
    demo.subprocess.run = original_run
    check("part 3: 'both' starts a NEW python process for the ask step", len(launched) == 1 and launched[0][0] == sys.executable and "ask" in launched[0])

    # 6. Part 4: the guard runs before the tool, and the prompt sentence is only advice.
    SEEN.clear()
    out = run_quiet(demo.part4)
    check("part 4: step A puts the rule sentence in the system prompt", demo.RULE_SENTENCE in SEEN[0]["system"])
    check("part 4: the check table shows ok and a handoff", "ok" in out and "handoff: 120 points is over the 100-point limit" in out)
    check("part 4: the tool call ran after the check said ok", "check: ok" in out and "balance 120 -> 40" in out)
    check("part 4: the source of the rule is printed", "def check_limit(points):" in out)
    queue = json.loads((Path(tmp) / "handoff_queue.json").read_text(encoding="utf-8"))
    check("part 4: two odd requests are queued for a person", len(queue) == 2)

    # 7. Part 5: v1, v2, per-case comparison and the gate.
    out = run_quiet(demo.part5)
    check("part 5: v1 scores 60% on the author fixtures", "pass rate: 60% (3 of 5)" in out)
    check("part 5: v2 scores 100% on the author fixtures", "pass rate: 100% (5 of 5)" in out)
    check("part 5: E2 and E3 are improved", "E2  improved" in out and "E3  improved" in out and "E1  same" in out)
    check("part 5: the GATE line is printed", "GATE: PASS  (v1 60% -> v2 100%, 0 regressed)" in out)
    check("part 5: the judge is mentioned, not run", "LLM judge" in out and not any("judge" in json.dumps(r["messages"]).lower() for r in SEEN[-10:]))

    # 8. The command line: --all runs everything, then the cheat table.
    demo.subprocess.run = lambda cmd, **kw: None
    sys.argv = ["intro_5_0.py", "--all"]
    out = run_quiet(demo.main)
    demo.subprocess.run = original_run
    check("--all: runs all five parts and ends with the cheat table", all(f"PART {n} -" in out for n in range(1, 6)) and "WRAP-UP" in out and "A check in code" in out)
    check("--all: prints the cost line", "Cost of this run" in out)

# 9. Hygiene: no fake results, no bytecode, no stray words.
check("results/ holds only .gitkeep", sorted(p.name for p in (HERE / "results").iterdir()) == [".gitkeep"])
check("no __pycache__ in the folder", not list(HERE.rglob("__pycache__")))
texts = [p.read_text(encoding="utf-8") for p in HERE.rglob("*") if p.suffix in (".py", ".md", ".json", ".txt")]
check("no banned words and no emojis", not any(re.search("|".join(["genu" + "inely", "hones" + "tly", "straight" + "forward"]), t, re.I) or re.search("[\\U0001F300-\\U0001FAFF\\u2600-\\u27BF]", t) for t in texts))

print("\nALL OK" if not failures else f"\n{len(failures)} CHECK(S) FAILED")
sys.exit(1 if failures else 0)
