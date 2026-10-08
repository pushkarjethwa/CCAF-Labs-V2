"""check.py - Part A tests your TODOs with no API key and no model. Part B checks the real run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import json
import sys
from datetime import date

import lab
import memory_core as core

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def info(text):
    print(f"[info] {text}")


def guarded(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # a TODO that crashes is reported as a failure, not a traceback
        return f"{type(exc).__name__}: {exc}"


def record(fact, tags, hard=False, saved="2026-08-01", scope=None):
    return {"fact": fact, "tags": tags, "hard_rule": hard, "source_session": 1, "saved_at": saved,
            "scope": scope or core.SCOPE, "version": 1, "ttl_days": None if hard else 90}


RULE = "Dana must never be sent marketing email."
print("PART A - your four TODOs, tested with no API key and no model\n")

print("TODO 1 - save facts")
session = {"id": 3, "date": "2026-07-15", "topic": "Room needs", "turns": [["Dana", "I need a quiet room."]]}
plain = guarded(lab.make_record, {"fact": "Dana likes a quiet room.", "tags": ["room"], "hard_rule": False}, session)
hard = guarded(lab.make_record, {"fact": RULE, "tags": ["contact"], "hard_rule": True}, session)
ok = isinstance(plain, dict) and plain.get("fact") == "Dana likes a quiet room." and plain.get("tags") == ["room"]
check(ok, "make_record keeps the fact and its tags", f"you returned {plain!r}")
check(isinstance(plain, dict) and plain.get("source_session") == 3 and plain.get("saved_at") == "2026-07-15",
      "make_record records the source session (3) and the time (2026-07-15)", f"you returned {plain!r}")
check(isinstance(plain, dict) and plain.get("scope") == core.SCOPE and plain.get("version") == 1,
      "make_record sets the scope of this guest and version 1", f"you returned {plain!r}")
check(isinstance(plain, dict) and isinstance(hard, dict) and plain.get("ttl_days") == 90 and hard.get("ttl_days") is None
      and plain.get("hard_rule") is False and hard.get("hard_rule") is True,
      "a normal fact lives 90 days, and a hard rule never expires (ttl_days is None)", f"you returned {plain!r} and {hard!r}")
real_ask = lab.ask_claude
lab.ask_claude = lambda model, system, prompt: ('Here you go:\n```json\n[{"fact": "' + RULE + '", "tags": ["contact"], "hard_rule": true}]\n```', 10)
extracted = guarded(lab.extract_facts, session)
lab.ask_claude = real_ask
check(isinstance(extracted, list) and len(extracted) == 1 and extracted[0].get("fact") == RULE and extracted[0].get("source_session") == 3,
      "extract_facts turns the model's JSON list into records", f"you returned {extracted!r}")

print("\nTODO 2 - load facts")
memory = [record(RULE, ["contact"], hard=True, saved="2026-06-03"),
          record("Dana books the flexible rate in Porto.", ["booking"]),
          record("Receipts go to accounts@northfield.example.", ["billing"]),
          record("Another guest wants a quiet room.", ["booking"], scope={"tenant": "other", "user": "u-x"}),
          record("An old stay in Lisbon.", ["booking"], saved="2026-01-01")]
chosen = guarded(lab.select_facts, "Please extend my stay and email me your offers", memory, date(2026, 9, 18))
facts = [r["fact"] for r in chosen] if isinstance(chosen, list) else []
check(RULE in facts, "the hard rule is loaded", f"you returned {chosen!r}")
check("Dana books the flexible rate in Porto." in facts, "a fact whose topic matches the question is loaded")
check("Receipts go to accounts@northfield.example." not in facts, "a fact about another topic (billing) is left out")
check("Another guest wants a quiet room." not in facts, "a fact of another guest is never loaded")
check("An old stay in Lisbon." not in facts, "a fact past its time to live is skipped")

print("\nTODO 3 - compact")
pinned = guarded(lab.pinned_rules, memory)
check(pinned == [RULE], "pinned_rules returns only the hard rule, as exact text", f"you returned {pinned!r}")
context = guarded(lab.compact_context, "Dana booked in Lisbon and Porto.", [RULE])
check(isinstance(context, str) and RULE in context and "Dana booked in Lisbon and Porto." in context,
      "compact_context holds both the pinned rule and the summary", f"you returned {context!r}")
check(isinstance(context, str) and RULE in context and context.find(RULE) < context.find("Dana booked in Lisbon"),
      "the pinned rule comes ABOVE the summary", f"you returned {context!r}")

print("\nTODO 4 - the retention check")
check(guarded(lab.rules_survive, f"- {RULE}\n\nSummary: a booking.", [RULE]) is True, "rules_survive is True when the rule is in the context")
check(guarded(lab.rules_survive, "Summary: a booking in Lisbon.", [RULE]) is False, "rules_survive is False when the summary dropped the rule")
check(guarded(lab.memory_has_rule, memory) is True and guarded(lab.memory_has_rule, memory[1:]) is False,
      "memory_has_rule finds the no-marketing hard rule, and is False without it")

print("\nPART B - the real run (needs python lab.py history, save, load and compact with a key)\n")
run = core.read_json("run.json", {})
missing = [name for name in ("history", "save", "load", "compact") if name not in run]
if missing:
    print(f"[SKIP] no saved result for: {', '.join(missing)} - finish the TODOs, run those commands, then this again.")
else:
    memory = core.read_json("memory.json", [])
    check(all(run[name].get("fingerprint") == lab.fingerprint() for name in run),
          "the saved runs are from your CURRENT lab.py", "you edited lab.py after a run - run the four commands again")
    tokens = run["history"]["tokens"]
    check(len(tokens) == 5 and all(a < b for a, b in zip(tokens, tokens[1:])), "history: the input tokens grow on every call", f"{tokens}")
    check(run["save"]["facts"] >= 5 and all(r.get("source_session") and r.get("saved_at") for r in memory),
          "save: at least 5 facts were saved, and each has a source session and a time", f"facts: {run['save']['facts']}")
    check(lab.memory_has_rule(memory), "save: the no-marketing rule is in memory as a hard rule")
    check(0 < len(run["load"]["loaded"]) < run["load"]["total"], "load: only some of the facts were loaded",
          f"loaded {len(run['load']['loaded'])} of {run['load']['total']}")
    check(any("marketing" in fact.lower() for fact in run["load"]["loaded"]), "load: the no-marketing rule was loaded")
    check(run["load"]["input_tokens"] < tokens[-1], "load: the prompt is smaller than the full-history prompt",
          f"{run['load']['input_tokens']} versus {tokens[-1]}")
    check(run["compact"]["survive"] and run["compact"]["pinned"],
          "compact: every pinned rule is in the compacted context, word for word")
    check(run["compact"]["after"] < run["compact"]["before"], "compact: the context is smaller than the history",
          f"{run['compact']['after']} versus {run['compact']['before']}")
    for name in ("history", "load", "compact"):
        verdict = "offers marketing email (read the reply)" if core.offers_marketing(run[name]["reply"]) else "no marketing email offered"
        info(f"{name} reply: {verdict}")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
