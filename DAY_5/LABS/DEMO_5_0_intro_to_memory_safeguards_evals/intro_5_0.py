"""Demo 5.0: Intro to memory, safeguards and evals.

One tiny story: Pip, the loyalty-card assistant for a small coffee shop (Brew & Bean).
Customers ask about points, rewards and opening hours. Five short parts, one idea each.

    python intro_5_0.py --part 1    Conversation: the model remembers nothing, so we resend the messages
    python intro_5_0.py --part 2    Context: the window is a fixed-size desk (no key needed)
    python intro_5_0.py --part 3    Memory: save facts to a file, start a new process, load them
    python intro_5_0.py --part 4    Safeguards: where a rule lives, in the prompt or in code
    python intro_5_0.py --part 5    Evals: five test cases, a pass rate, v1 against v2 and a gate
    python intro_5_0.py --all       All five parts, then the cheat table

Setup:  pip install anthropic   and set ANTHROPIC_API_KEY (part 2 needs neither, unless you add --count).
Environment: CLAUDE_MODEL_FAST (default claude-haiku-5-5) runs Pip. CLAUDE_MODEL_BALANCED (default
claude-sonnet-5-5) runs Pip when you add --model balanced. DEMO_BUDGET_USD (default 0.50).
"""
import argparse
import inspect
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
PROMPTS = HERE / "prompts"
RESULTS = HERE / "results"

MODEL_FAST = os.getenv("CLAUDE_MODEL_FAST", "claude-haiku-5-5")
MODEL_BALANCED = os.getenv("CLAUDE_MODEL_BALANCED", "claude-sonnet-5-5")
MODEL = MODEL_FAST
PRICE_PER_MTOK = {"claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}
BUDGET_USD = float(os.getenv("DEMO_BUDGET_USD", "0.50"))

DESK_TOKENS = 1000   # a small desk, so the bar is easy to read. Real windows hold far more.
KEEP_LAST = 4        # the simplest trim: keep the last 4 messages
MAX_REDEEM_PER_VISIT = 100
RULE_SENTENCE = "Never redeem more than 100 points in one visit."
HANDOFF_WORDS = ["refund", "complaint", "manager", "delete my", "lawyer"]

_client = None
SPENT = 0.0


def load(name):
    """Read one JSON file from the data folder."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


FAQ = load("loyalty_faq.json")
CUSTOMER = load("customer.json")
REWARD_COST = FAQ["rewards"]
TOOLS = [{
    "name": "redeem_points",
    "description": "Redeem loyalty points for a reward the customer asked for.",
    "input_schema": {
        "type": "object",
        "properties": {"reward": {"type": "string", "description": "coffee, pastry or lunch combo"},
                       "points": {"type": "integer", "description": "the points to redeem"}},
        "required": ["reward", "points"],
    },
}]


# -- The model call, in one place ---------------------------------------------------------------------------

def has_api_key():
    """True if ANTHROPIC_API_KEY is set, or is in a .env file in this folder or a parent folder."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    folder = HERE.resolve()
    while True:
        path = folder / ".env"
        if path.is_file():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                name, _, value = line.strip().removeprefix("export ").partition("=")
                if name.strip() == "ANTHROPIC_API_KEY" and value.strip().strip("\"'"):
                    os.environ["ANTHROPIC_API_KEY"] = value.strip().strip("\"'")
                    return True
        if folder.parent == folder:
            return False
        folder = folder.parent


def get_client():
    """Create the Anthropic client on first use."""
    global _client
    if _client is None:
        if not has_api_key():
            sys.exit("ANTHROPIC_API_KEY not found in the environment or in a .env file in this folder or a parent folder.")
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def call(system, messages, tools=None, max_tokens=300):
    """Make one Messages API call. The model sees ONLY what is in system, messages and tools."""
    global SPENT
    if SPENT >= BUDGET_USD:
        sys.exit(f"Budget of ${BUDGET_USD:.2f} reached (set DEMO_BUDGET_USD to raise it).")
    request = {"model": MODEL, "max_tokens": max_tokens, "system": system, "messages": messages}
    if tools:
        request["tools"] = tools
    response = get_client().messages.create(**request)
    price_in, price_out = PRICE_PER_MTOK.get(MODEL, (0.0, 0.0))
    SPENT += (response.usage.input_tokens * price_in + response.usage.output_tokens * price_out) / 1e6
    return response


def text_of(response):
    """The text of a reply."""
    return "".join(block.text for block in response.content if block.type == "text")


def facts_text():
    """The shop facts as short lines, for the system prompt."""
    rewards = ", ".join(f"{name} {points} points" for name, points in REWARD_COST.items())
    hours = "; ".join(f"{day} {time}" for day, time in FAQ["hours"].items())
    return (f"- Points: {FAQ['points_per_dollar']} points for every $1 spent.\n"
            f"- Rewards: {rewards}.\n"
            f"- Opening hours: {hours}.\n"
            f"- A customer can redeem at most {FAQ['max_redeem_per_visit']} points in one visit.")


def build_system(version="v1", extra=""):
    """Read prompts/pip_<version>.txt, fill in the shop facts, and add any extra lines."""
    text = (PROMPTS / f"pip_{version}.txt").read_text(encoding="utf-8").replace("{facts}", facts_text())
    return text.strip() + ("\n\n" + extra if extra else "")


def show(label, text):
    """Print a label and a wrapped block of text."""
    print(f"{label}")
    print(textwrap.indent(textwrap.fill(text, 92), "    "))


def banner(title):
    print("\n" + "=" * 100 + f"\n{title}\n" + "=" * 100)


# -- Part 1. Conversation: the model remembers nothing -------------------------------------------------------

def part1():
    """Three calls. Call 2 has no history, so Pip forgets. Call 3 resends the messages list, so Pip knows."""
    banner("PART 1 - Conversation: the model remembers nothing, so your program resends the messages")
    system = build_system()
    first = "Hi, I'm Maya. How many points do I need for a free coffee?"
    second = "What is my name?"
    third = "And what time do you close on Saturday?"
    rows = []

    messages = [{"role": "user", "content": first}]
    reply1 = call(system, messages)
    show("Call 1 (1 message sent)", f"Maya: {first}\nPip:  {text_of(reply1)}")
    rows.append(("call 1", len(messages), reply1.usage.input_tokens))

    fresh = [{"role": "user", "content": second}]          # a brand new list: no history
    reply2 = call(system, fresh)
    show("Call 2, WITHOUT history (1 message sent)", f"Maya: {second}\nPip:  {text_of(reply2)}")
    rows.append(("call 2, no history", len(fresh), reply2.usage.input_tokens))

    # --- TYPE LIVE: these two lines add the earlier turns back, so the model can see them ---
    messages.append({"role": "assistant", "content": text_of(reply1)})
    messages.append({"role": "user", "content": second})
    # --- end of the lines to type ---
    reply3 = call(system, messages)
    show(f"Call 2 again, WITH history ({len(messages)} messages sent)", f"Maya: {second}\nPip:  {text_of(reply3)}")
    rows.append(("call 2, with history", len(messages), reply3.usage.input_tokens))

    messages.append({"role": "assistant", "content": text_of(reply3)})
    messages.append({"role": "user", "content": third})
    reply4 = call(system, messages)
    show(f"Call 3, WITH history ({len(messages)} messages sent)", f"Maya: {third}\nPip:  {text_of(reply4)}")
    rows.append(("call 3, with history", len(messages), reply4.usage.input_tokens))

    print("\nInput tokens: what the model had to read on each call")
    print(f"{'call':<24}{'messages sent':>14}{'input tokens':>14}")
    for label, count, tokens in rows:
        print(f"{label:<24}{count:>14}{tokens:>14}")
    print("\nThe API keeps nothing. Your program keeps the list and sends it again. The list grows, and so does the bill.")


# -- Part 2. Context: the window is a fixed-size desk ----------------------------------------------------------

def estimate_tokens(value):
    """A rough token count: about 4 characters for one token."""
    text = value if isinstance(value, str) else json.dumps(value)
    return len(text) // 4


def bar(used, total, width=40):
    """A text bar: # is used desk space, . is free."""
    filled = min(width, round(width * used / total))
    return "[" + "#" * filled + "." * (width - filled) + f"] {used} of {total} tokens"


def trim_to_last(messages, count):
    """The simplest trim: keep the last `count` messages. Drop a leading Pip message, because a chat starts with the customer."""
    kept = messages[-count:]
    while kept and kept[0]["role"] != "user":
        kept = kept[1:]
    return kept


def part2(count_with_api=False):
    """Show what is on the desk, trim it, and see what was lost. Needs no key unless count_with_api is set."""
    banner("PART 2 - Context: the window is a fixed-size desk")
    system, chat = build_system(), load("sample_chat.json")
    parts = [("system prompt", estimate_tokens(system)), ("tool definitions", estimate_tokens(TOOLS)),
             ("conversation", estimate_tokens(chat))]
    print(f"The desk holds {DESK_TOKENS} tokens here. A real window is far bigger, but it is still a fixed size.")
    print("Token numbers are estimates: characters divided by 4.\n")
    for name, tokens in parts:
        print(f"{name:<18}{bar(tokens, DESK_TOKENS)}")
    print(f"{'on the desk':<18}{bar(sum(tokens for _, tokens in parts), DESK_TOKENS)}")

    kept = trim_to_last(chat, KEEP_LAST)
    trimmed = estimate_tokens(system) + estimate_tokens(TOOLS) + estimate_tokens(kept)
    print(f"\nSimplest trim: keep only the last {KEEP_LAST} messages ({len(chat) - len(kept)} dropped).")
    print(f"{'after the trim':<18}{bar(trimmed, DESK_TOKENS)}")
    print(f"First message now on the desk: {kept[0]['content']!r}")
    still_there = any("Maya" in message["content"] for message in kept)
    print(f"Is the customer's name still on the desk? {'yes' if still_there else 'no, it was in a dropped message'}")
    print("\nTwo words you will hear:")
    print("  compact    replace the old messages with one short summary, so less space is used")
    print("  summarise  write that short summary (compacting is done by summarising)")
    print("Trimming is easy but loses facts. Part 3 shows where to keep the facts that must not be lost.")
    if count_with_api:
        counted = get_client().messages.count_tokens(model=MODEL, system=system, messages=chat, tools=TOOLS)
        print(f"\nThe API counted {counted.input_tokens} input tokens for the full request. Our estimate was {sum(t for _, t in parts)}.")


# -- Part 3. Memory: a file outside the window -----------------------------------------------------------------

def memory_path(card):
    """One customer, one file. The card number is the scope."""
    return RESULTS / f"memory_{card}.json"


def load_memory(card):
    """Read the saved facts for one customer, or an empty dict when there is no file yet."""
    path = memory_path(card)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def remember(card, key, value):
    """Save one durable fact for one customer."""
    RESULTS.mkdir(exist_ok=True)
    memory = load_memory(card)
    memory[key] = value
    memory_path(card).write_text(json.dumps(memory, indent=2), encoding="utf-8")


def memory_block(memory):
    """The saved facts as lines for the system prompt."""
    lines = "\n".join(f"- {key}: {value}" for key, value in memory.items())
    return "What we saved about this customer in earlier visits:\n" + lines


def part3_save():
    """Process 1: the customer tells Pip three durable facts, and we save them to a file."""
    card = CUSTOMER["card"]
    print("Process 1. Maya says: \"I'm Maya, I'm allergic to nuts, and please send me no marketing email.\"")
    remember(card, "name", "Maya")
    remember(card, "allergy", "allergic to nuts")
    remember(card, "marketing", "no marketing email")
    print(f"Saved to results/{memory_path(card).name}:")
    print(textwrap.indent(memory_path(card).read_text(encoding="utf-8"), "    "))
    print("Process 1 now ends. Everything in its memory (RAM), including the messages list, is gone.")


def part3_ask():
    """Process 2: a new process with an empty messages list loads the file into the system prompt."""
    card = CUSTOMER["card"]
    messages = []
    print(f"Process 2 starts. Its messages list holds {len(messages)} messages: it remembers nothing from process 1.")
    memory = load_memory(card)
    print(f"It loads results/{memory_path(card).name}: {len(memory)} facts.")
    question = "Hi, it is me again. Please email me the new autumn menu, and tell me which pastry I can have."
    messages.append({"role": "user", "content": question})
    reply = call(build_system(extra=memory_block(memory)), messages)
    show("Pip, with the saved facts in the system prompt", f"Customer: {question}\nPip:      {text_of(reply)}")


def model_args():
    """Pass --model on to a child process, so the same model runs in both."""
    return ["--model", "balanced"] if MODEL == MODEL_BALANCED and MODEL != MODEL_FAST else []


def part3(step="both"):
    """Run the save step, the ask step, or both. Both runs the ask step in a NEW process."""
    if step != "ask":
        banner("PART 3 - Memory: a file outside the window survives a restart")
    if step in ("save", "both"):
        part3_save()
    if step == "both":
        print("\n--- starting a new Python process ---\n")
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--part", "3", "--step", "ask"] + model_args(), check=True)
    if step == "ask":
        part3_ask()
        print("\nIn-conversation state (the messages list) dies with the process. A memory file survives it.")
        print("One customer, one file: Maya's facts are never loaded into another customer's prompt.")


# -- Part 4. Safeguards: a check in code -----------------------------------------------------------------------

def check_limit(points):
    """The loyalty rule as code: it runs before the redeem tool, and the model cannot change it."""
    if points > MAX_REDEEM_PER_VISIT:
        return f"handoff: {points} points is over the {MAX_REDEEM_PER_VISIT}-point limit for one visit"
    return "ok"


def check_arguments(reward, points, balance):
    """Check what the model passed to the tool: a known reward, whole points, and enough balance."""
    if reward not in REWARD_COST or not isinstance(points, int):
        return "refused: unknown reward, or points is not a whole number"
    return "ok" if points <= balance else "refused: not enough points on the card"


def guard(reward, points, balance):
    """All checks, in order. Returns 'ok' or the reason the redeem tool must not run."""
    problem = check_arguments(reward, points, balance)
    return problem if problem != "ok" else check_limit(points)


def guarded_redeem(arguments, balance):
    """The tool the model calls. The checks run first, and the redeem happens only after 'ok'."""
    reward, points = arguments.get("reward"), arguments.get("points")
    verdict = guard(reward, points, balance)
    print(f"    tool call: redeem_points(reward={reward!r}, points={points!r})   check: {verdict}")
    if verdict != "ok":
        return f"Not redeemed. {verdict}", balance
    print(f"    redeem ran: balance {balance} -> {balance - points}")
    return f"Redeemed {points} points for a {reward}.", balance - points


def pip_with_tool(question, balance):
    """One customer message, with the redeem tool available. Returns Pip's final reply and the new balance."""
    system = build_system(extra=f"The customer's card balance is {balance} points. {RULE_SENTENCE}")
    messages = [{"role": "user", "content": question}]
    response = call(system, messages, tools=TOOLS)
    while response.stop_reason == "tool_use":
        results = []
        for block in response.content:
            if block.type == "tool_use":
                outcome, balance = guarded_redeem(block.input, balance)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": outcome})
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})
        response = call(system, messages, tools=TOOLS)
    return text_of(response), balance


def needs_person(text):
    """Odd requests go to a person, decided by plain code before any model runs."""
    return any(word in text.lower() for word in HANDOFF_WORDS)


def part4():
    """The same rule, first as advice in the prompt, then as code that runs before the tool."""
    banner("PART 4 - Safeguards: where the rule lives. A prompt is advice. Code is enforced.")
    print(f"The rule: {RULE_SENTENCE}\n")
    print("Step A. The rule as a sentence in the system prompt (advice the model reads):")
    question = "I have 120 points. Can I use 80 of them for a pastry?"
    system = build_system(extra=RULE_SENTENCE)
    show("Pip", f"Customer: {question}\nPip:      {text_of(call(system, [{'role': 'user', 'content': question}]))}")

    print("\nStep B. The same rule as code (the program runs it, so it holds for every call):\n")
    print(textwrap.indent(inspect.getsource(check_limit), "    "))
    print(f"{'request':<30}{'check says'}")
    for reward, points in [("coffee", 50), ("pastry", 80), ("lunch combo", 100), ("lunch combo", 120), ("gift card", 60)]:
        print(f"{reward + ' for ' + str(points) + ' points':<30}{guard(reward, points, CUSTOMER['balance'])}")

    print("\nStep C. The redeem tool, with the check running before it:")
    reply, balance = pip_with_tool("Please use 80 points for a pastry.", CUSTOMER["balance"])
    show("Pip", reply)

    print("\nStep D. Odd requests go to a person, decided in code before any model runs:")
    queue = []
    for text in ["What time do you open on Sunday?", "I would like a refund for yesterday's coffee.", "Please delete my data."]:
        route = "a person" if needs_person(text) else "Pip"
        print(f"    {text:<50}-> {route}")
        if route == "a person":
            queue.append({"card": CUSTOMER["card"], "request": text})
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "handoff_queue.json").write_text(json.dumps(queue, indent=2), encoding="utf-8")
    print(f"    {len(queue)} requests saved to results/handoff_queue.json for a staff member.")
    print("\nWhere a rule lives: a prompt sentence is advice, and a check in code is enforced.")


# -- Part 5. Evals: test cases with a score ----------------------------------------------------------------------

def normalise(text):
    """Lower case, no spaces, no ':00', so '4 pm' and '4:00 PM' both match '4pm'."""
    return text.lower().replace(" ", "").replace(":00", "")


def grade(case, reply):
    """Plain code, no model: the reply passes when it contains the expected keyword or number."""
    return normalise(case["expect"]) in normalise(reply)


def run_eval(version, cases):
    """Run every test case against one prompt version, and grade each reply."""
    system = build_system(version)
    results = []
    for case in cases:
        reply = text_of(call(system, [{"role": "user", "content": case["question"]}], max_tokens=150))
        results.append({"id": case["id"], "question": case["question"], "expect": case["expect"],
                        "reply": reply, "passed": grade(case, reply)})
    return results


def pass_rate(results):
    """The share of cases that passed, as a number from 0 to 100."""
    return round(100 * sum(r["passed"] for r in results) / len(results))


def compare(old, new):
    """Per case: improved (fail to pass), regressed (pass to fail) or same."""
    status = {}
    for before, after in zip(old, new):
        if after["passed"] and not before["passed"]:
            status[before["id"]] = "improved"
        elif before["passed"] and not after["passed"]:
            status[before["id"]] = "regressed"
        else:
            status[before["id"]] = "same"
    return status


def gate(old, new):
    """The release gate: v2 ships only if it scores at least as high as v1 and regresses on no case."""
    regressed = sum(s == "regressed" for s in compare(old, new).values())
    ok = pass_rate(new) >= pass_rate(old) and regressed == 0
    return f"GATE: {'PASS' if ok else 'BLOCKED'}  (v1 {pass_rate(old)}% -> v2 {pass_rate(new)}%, {regressed} regressed)"


def print_grades(version, results):
    """One line per case, then the pass rate."""
    print(f"\nPrompt {version}")
    for r in results:
        print(f"  {r['id']}  {'PASS' if r['passed'] else 'FAIL'}  expects {r['expect']!r:<10} {r['question']}")
    print(f"  pass rate: {pass_rate(results)}% ({sum(r['passed'] for r in results)} of {len(results)})")


def part5():
    """Grade prompt v1, grade prompt v2, compare per case and print the gate."""
    banner("PART 5 - Evals: test cases with a score")
    cases = load("eval_cases.json")
    print(f"{len(cases)} test cases, each a question and one expected keyword or number. Plain code grades them.")
    v1 = run_eval("v1", cases)
    print_grades("v1", v1)
    print("\nNow we change the prompt (v2 adds three rules) and run the SAME cases again.")
    v2 = run_eval("v2", cases)
    print_grades("v2", v2)
    print("\nPer case, v1 -> v2")
    for case_id, status in compare(v1, v2).items():
        print(f"  {case_id}  {status}")
    print("\n" + gate(v1, v2))
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "eval_runs.json").write_text(json.dumps({"v1": v1, "v2": v2}, indent=2), encoding="utf-8")
    print("\nThere is also an LLM judge: a second model call that grades answers code cannot check, such as tone.")
    print("Use it only when plain code cannot decide. It is not shown here.")


# -- Wrap-up -----------------------------------------------------------------------------------------------------

CHEAT = [("Conversation", "You resend it", "Demo 5A"), ("Context", "The desk is finite", "Demo 5A"),
         ("Memory", "A file outside the window", "Demo 5A"), ("Safeguard", "A check in code", "Demo 5B"),
         ("Eval", "Test cases with a score", "Demo 5C")]


def cheat_table():
    """The five ideas in one table, with where to practise later."""
    banner("WRAP-UP - Five ideas")
    print(f"{'idea':<15}{'in one line':<30}{'practise later (optional)'}")
    for idea, line, later in CHEAT:
        print(f"{idea:<15}{line:<30}{later}")


def main():
    global MODEL
    parser = argparse.ArgumentParser(description="Demo 5.0: intro to memory, safeguards and evals")
    parser.add_argument("--part", type=int, choices=range(1, 6), help="which part to run, 1 to 5")
    parser.add_argument("--all", action="store_true", help="run parts 1 to 5, then the cheat table")
    parser.add_argument("--step", choices=["save", "ask", "both"], default="both", help="part 3 only")
    parser.add_argument("--count", action="store_true", help="part 2 only: also count tokens with the API")
    parser.add_argument("--model", choices=["fast", "balanced"], default="fast", help="which model runs Pip")
    args = parser.parse_args()
    if args.model == "balanced":
        MODEL = MODEL_BALANCED
    if not args.all and not args.part:
        parser.error("choose --part N (1 to 5) or --all")
    parts = {1: part1, 2: lambda: part2(args.count), 3: lambda: part3(args.step), 4: part4, 5: part5}
    for number in (range(1, 6) if args.all else [args.part]):
        parts[number]()
    if args.all:
        cheat_table()
    if SPENT:
        print(f"\nCost of this run: about ${SPENT:.4f} on {MODEL}.")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    main()
