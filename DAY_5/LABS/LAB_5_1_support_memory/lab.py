"""Lab 5.1 - Build the memory layer for a hotel reservations agent (continues Demo 5A: the same five sessions, one hard rule, the same stages).

Dana books rooms with Harbor Lane Hotels over five sessions. In session 1 she says "never send me marketing email".
In session 5 she asks for autumn offers by email. The API remembers nothing between calls, so you build a memory layer.
You write four pieces here:

  TODO 1  save facts      turn what the fast model extracts into records with a source and a time, and save them
  TODO 2  load facts      pick only the facts a question needs (hard rules always come along)
  TODO 3  compact         shrink old history to a summary, with the hard rule pinned above it
  TODO 4  retention check code that proves the rule survived

HOW TO RUN
  python check.py          pass/fail in plain words. Part A needs no key and no model.
  python lab.py history    the start state: all history in the prompt (needs ANTHROPIC_API_KEY)
  python lab.py save       extract facts from sessions 1 to 4 and save them to results/memory.json
  python lab.py load       a NEW process: load only what the request needs, answer, save what is new
  python lab.py compact    summarise sessions 1 to 4, pin the rule, and check that it survived
Then python check.py again. The sessions, the helpers and the printing are in memory_core.py. You do not need to read it.
"""
import hashlib
import json
import pathlib
import sys

import memory_core as core
from claude_client import MODEL_BALANCED, MODEL_FAST, get_client, text_of


def ask_claude(model, system, prompt):
    """The one Claude API call in this lab. Returns the answer text and the input tokens the API reported."""
    response = get_client().messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return text_of(response), response.usage.input_tokens


# ======================================================================================
# TODO 1 of 4 - SAVE FACTS
# Two functions. `item` is one fact from the model: {"fact": ..., "tags": [...], "hard_rule": true or false}.
#   make_record(item, session)   wrap a fact with its source session, time, scope, version and time to live
#                                (a hard rule never expires: ttl_days is None)
#   extract_facts(session)       ask the FAST model for the durable facts of one session, and return the records
# ======================================================================================
def make_record(item, session):
    return {}  # replace these lines in TODO 1


def extract_facts(session):
    return []  # replace these lines in TODO 1


# ======================================================================================
# TODO 2 of 4 - LOAD FACTS
# Return the records from `memory` that this question needs. A record is chosen when ALL of these hold:
#   its scope is this guest (core.SCOPE), it is still current (core.is_current(record, today)),
#   and it is a hard rule OR one of its tags is a topic of the question (core.tags_for(question)).
# ======================================================================================
def select_facts(question, memory, today):
    return []  # replace these lines in TODO 2


# ======================================================================================
# TODO 3 of 4 - COMPACT
#   pinned_rules(memory)               the hard rules, as exact text
#   compact_context(summary, pinned)   the new context: the pinned rules as a list, ABOVE the summary
# ======================================================================================
def pinned_rules(memory):
    return []  # replace this line in TODO 3


def compact_context(summary, pinned):
    return summary  # replace these lines in TODO 3


# ======================================================================================
# TODO 4 of 4 - THE RETENTION CHECK
#   rules_survive(context, pinned)   True when every pinned rule appears word for word in the context
#   memory_has_rule(memory)          True when a hard rule in memory mentions "marketing"
# ======================================================================================
def rules_survive(context, pinned):
    return True  # replace this line in TODO 4


def memory_has_rule(memory):
    return False  # replace this line in TODO 4


# ======================================================================================
# RUNNING THE LAB - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent


def fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def save_run(section, data):
    """Keep the result of one command in results/run.json, stamped with the fingerprint of this file."""
    run = core.read_json("run.json", {})
    run[section] = {**data, "fingerprint": fingerprint()}
    core.write_json("run.json", run)


def load_memory():
    memory = core.read_json("memory.json")
    if memory is None:
        sys.exit("No results/memory.json yet. Run: python lab.py save")
    return memory


def run_history():
    print(f"START STATE - everything in the prompt. Guest: {core.CUSTOMER['user']} ({core.CUSTOMER['company']}), {len(core.SESSIONS)} sessions.\n")
    print(f"{'session':<9}{'topic':<18}{'input tokens':>13}")
    tokens = []
    for number, session in enumerate(core.SESSIONS, start=1):
        earlier = core.transcript(core.SESSIONS[:number - 1])
        prompt = (f"Earlier sessions:\n{earlier}\n\n" if earlier else "") + f"Current session:\n{core.transcript([session])}"
        reply, input_tokens = ask_claude(MODEL_BALANCED, core.SUPPORT_SYSTEM, prompt)
        tokens.append(input_tokens)
        print(f"{number:<9}{session['topic']:<18}{input_tokens:>13}")
    print(f"\nEach call re-sends every earlier session: {tokens[0]} -> {tokens[-1]} tokens. The API remembers nothing.")
    print(f"\nWith the full history in the prompt, the agent answers session 5:\n  {reply}")
    question = "What do you know about which emails Dana wants to receive?"
    fresh, _ = ask_claude(MODEL_BALANCED, core.SUPPORT_SYSTEM, question)
    print(f"\nNow a brand-new process, with no history. Question: {question}\n  {fresh}")
    save_run("history", {"tokens": tokens, "reply": reply})


def run_save():
    print("SAVE - after each session, the fast model extracts durable facts. Your code turns them into records.\n")
    memory = []
    for session in core.SESSIONS[:-1]:
        added = core.add_new_facts(memory, extract_facts(session))
        print(f"session {session['id']} ({session['topic']}): saved {added} facts")
    core.write_json("memory.json", memory)
    print(f"\n{'#':<3}{'fact':<70}{'tags':<18}{'from':<6}{'ttl'}")
    for number, record in enumerate(memory, start=1):
        ttl = "none" if record["ttl_days"] is None else record["ttl_days"]
        print(f"{number:<3}{record['fact'][:68]:<70}{','.join(record['tags']):<18}S{record['source_session']:<5}{ttl}")
    print("\nWe store facts, not transcripts. The hard rule never expires.")
    save_run("save", {"facts": len(memory)})


def run_load():
    memory = load_memory()
    print(f"NEW PROCESS - it has read nothing but results/memory.json ({len(memory)} facts).\n\nRequest: {core.REQUEST}\n")
    chosen = select_facts(core.REQUEST, memory, core.TODAY)
    print(f"LOAD - topics found in the request: {', '.join(sorted(core.tags_for(core.REQUEST)))}. Loaded {len(chosen)} of {len(memory)} facts:")
    for record in chosen:
        print(f"  - {record['fact']}")
    facts = "\n".join(f"- {record['fact']}" for record in chosen)
    reply, input_tokens = ask_claude(MODEL_BALANCED, core.SUPPORT_SYSTEM, f"Facts we know about this guest:\n{facts}\n\nGuest message:\n{core.REQUEST}")
    print(f"\nWORK - the agent says ({input_tokens} input tokens):\n  {reply}")
    added = core.add_new_facts(memory, extract_facts({**core.SESSIONS[-1], "turns": core.SESSIONS[-1]["turns"] + [["Agent", reply]]}))
    core.write_json("memory.json", memory)
    print(f"\nSAVE - {added} new fact(s) written back. Load, work, save: that is the loop.")
    save_run("load", {"loaded": [r["fact"] for r in chosen], "total": len(memory) - added, "input_tokens": input_tokens, "reply": reply})


def run_compact():
    memory = load_memory()
    old = core.SESSIONS[:-1]
    summary, _ = ask_claude(MODEL_FAST, core.SUMMARY_SYSTEM, core.transcript(old))
    pinned = pinned_rules(memory)
    context = compact_context(summary, pinned)
    before, after = core.estimate_tokens(core.transcript(old)), core.estimate_tokens(context)
    survive = rules_survive(context, pinned)
    print("COMPACT - older history becomes a short summary. Hard rules are pinned above it.\n")
    print(f"History of sessions 1 to 4: about {before} tokens (characters / 4)")
    print(f"Compacted context:          about {after} tokens\n")
    print("Pinned rules:")
    for rule in pinned:
        print(f"  - {rule}")
    print(f"\nThe memory holds the no-marketing rule: {'yes' if memory_has_rule(memory) else 'NO'}")
    print(f"Every pinned rule is in the compacted context, word for word: {'yes' if survive else 'NO'}")
    reply, input_tokens = ask_claude(MODEL_BALANCED, core.SUPPORT_SYSTEM, f"{context}\n\nGuest message:\n{core.REQUEST}")
    print(f"\nThe agent says ({input_tokens} input tokens):\n  {reply}")
    save_run("compact", {"before": before, "after": after, "pinned": pinned, "survive": survive, "reply": reply})


COMMANDS = {"history": run_history, "save": run_save, "load": run_load, "compact": run_compact}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit("usage: python lab.py history | save | load | compact")
    COMMANDS[sys.argv[1]]()
