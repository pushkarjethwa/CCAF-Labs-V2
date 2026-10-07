"""Run while you work.   python check.py
Part A tests YOUR code with hand-made model replies: no API key needed.
Part B reads evidence/stageN.json from the stages you have run with Claude (python lab.py --stage N).
Fails on the starter by design. Exit code 0 means every check passed."""
import json
import pathlib
import sys
from types import SimpleNamespace

import lab
import library_core as core

EVIDENCE = pathlib.Path(__file__).parent / "evidence"
results = []


def check(description, test):
    """Run a test function that returns (ok, detail). A TODO that is still a stub counts as a failure, not a crash."""
    try:
        ok, detail = test()
    except NotImplementedError as stub:
        ok, detail = False, str(stub)
    except Exception as exc:  # noqa: BLE001 - show the student what broke
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def info(text):
    print(f"[info] {text}")


def text(s):
    return SimpleNamespace(type="text", text=s)


def tool_use(call_id, name, tool_input):
    return SimpleNamespace(type="tool_use", id=call_id, name=name, input=tool_input)


def reply(blocks, stop):
    return SimpleNamespace(content=blocks, stop_reason=stop)


def scripted(*replies):
    """A fake send(): returns the replies in order and records the messages it was given."""
    seen, queue = [], list(replies)

    def send(messages, **kwargs):
        seen.append(json.loads(json.dumps(messages, default=lambda o: {"block": o.type, "id": getattr(o, "id", None)})))
        return queue.pop(0) if queue else reply([text("(script ended)")], "end_turn")
    return send, seen


print("== Part A: your code with hand-made model replies (no API key) ==")


def t_schema():
    schema = lab.CHECK_DUE_DATE_TOOL
    inp = schema.get("input_schema", {})
    ok = (schema.get("name") == "check_due_date" and len(schema.get("description", "")) > 40 and inp.get("type") == "object"
          and "member_id" in inp.get("properties", {}) and inp.get("required") == ["member_id"])
    return ok, "" if ok else f"keys found: {sorted(schema)}"


check("TODO 1: the check_due_date schema has a name, a real description and a required member_id", t_schema)
check("TODO 2: the dispatcher runs find_book", lambda: (lab.run_tool("find_book", {"title": "Dune"}).get("shelf") == "SF-12", ""))
check("TODO 2: the dispatcher runs check_due_date", lambda: (lab.run_tool("check_due_date", {"member_id": "M-200"}).get("due") == "2026-10-08", ""))
check("TODO 2: an unknown tool name returns an error dict, no crash", lambda: (lab.run_tool("delete_everything", {}) == {"error": "unknown_tool", "name": "delete_everything"}, ""))


def t_loop_none():
    send, _ = scripted(reply([text("Paris.")], "end_turn"))
    out = lab.answer("capital?", send=send)
    return out["answer"] == "Paris." and out["turns"] == 1 and out["tools_used"] == [], str(out)


def t_loop_one():
    send, seen = scripted(reply([tool_use("tu_1", "find_book", {"title": "Dune"})], "tool_use"), reply([text("Shelf SF-12.")], "end_turn"))
    out = lab.answer("where is Dune?", send=send)
    return out["answer"] == "Shelf SF-12." and out["turns"] == 2 and out["tools_used"] == ["find_book"], str(out)


def t_loop_shape():
    send, seen = scripted(reply([tool_use("tu_1", "find_book", {"title": "Dune"})], "tool_use"), reply([text("ok")], "end_turn"))
    lab.answer("where is Dune?", send=send)
    second = seen[1] if len(seen) > 1 else []
    return len(second) == 3 and [m["role"] for m in second] == ["user", "assistant", "user"], f"{len(second)} messages sent in turn 2"


def t_loop_id():
    send, seen = scripted(reply([tool_use("tu_1", "find_book", {"title": "Dune"})], "tool_use"), reply([text("ok")], "end_turn"))
    lab.answer("where is Dune?", send=send)
    blocks = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 and isinstance(seen[1][2]["content"], list) else []
    return len(blocks) == 1 and blocks[0].get("type") == "tool_result" and blocks[0].get("tool_use_id") == "tu_1" and "SF-12" in str(blocks[0].get("content")), ""


def t_loop_parallel():
    send, seen = scripted(reply([tool_use("a", "find_book", {"title": "Dune"}), tool_use("b", "check_due_date", {"member_id": "M-100"})], "tool_use"),
                          reply([text("done")], "end_turn"))
    out = lab.answer("both", send=send)
    last = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 and isinstance(seen[1][2]["content"], list) else []
    return len(last) == 2 and [b.get("tool_use_id") for b in last] == ["a", "b"] and out["tools_used"] == ["find_book", "check_due_date"], "one user message must hold both results"


def t_loop_exit():
    send, _ = scripted(*[reply([tool_use(f"t{i}", "find_book", {"title": "Dune"})], "tool_use") for i in range(20)])
    out = lab.answer("loop forever", send=send)
    return out.get("gave_up") is True and out["turns"] == lab.MAX_TURNS, str(out.get("turns"))


check("TODO 3: no tool needed, the loop ends after 1 turn", t_loop_none)
check("TODO 3: one tool call, then the final answer in turn 2", t_loop_one)
check("TODO 3: turn 2 sends user, assistant (tool_use), user (tool_result)", t_loop_shape)
check("TODO 3: the tool_result carries the SAME id as the tool_use and the tool's output", t_loop_id)
check("TODO 3: two tool calls in one turn give ONE user message with both tool_results", t_loop_parallel)
check("the loop has an exit: it stops after MAX_TURNS tool-requesting turns", t_loop_exit)


def t_error_flag():
    content, is_error = lab.run_tool_safely("find_book", {"title": "Nope"})
    return is_error is True and "book_not_found" in content, f"is_error={is_error}"


def t_crash():
    content, is_error = lab.run_tool_safely("find_book", {"wrong_argument": 1})
    return is_error is True and "tool_crashed" in content, f"is_error={is_error}"


def t_good():
    content, is_error = lab.run_tool_safely("find_book", {"title": "Dune"})
    return is_error is False and json.loads(content)["shelf"] == "SF-12", f"is_error={is_error}"


def t_unknown_flag():
    content, is_error = lab.run_tool_safely("delete_everything", {})
    return is_error is True and "unknown_tool" in content, f"is_error={is_error}"


check("TODO 4: an error result such as book_not_found is flagged is_error=True", t_error_flag)
check("TODO 4: a crashing tool is caught and reported as tool_crashed", t_crash)
check("TODO 4: a good result is a JSON string with is_error False", t_good)
check("TODO 4: an unknown tool is flagged is_error=True", t_unknown_flag)

print("\n== Part B: your real runs with Claude (evidence/stageN.json) ==")
found = sorted(EVIDENCE.glob("stage*.json")) if EVIDENCE.exists() else []
if not found:
    print("(Part B skipped: run `python lab.py --stage 1` and the later stages first)")
for path in found:
    data = json.loads(path.read_text(encoding="utf-8"))
    stage = data["stage"]
    print(f"\n-- stage {stage}: {core.STAGE_TITLES[stage]} --")
    info(data["score"])
    rows = {r["label"]: r for r in data.get("rows", [])}
    if stage == 1:
        info("stage 1 is the baseline: without tools, only the France question can be grounded")
    if stage == 2:
        for label in ("needs find_book", "needs check_due_date"):
            check(f"stage 2: {label}: Claude asked for the right tool", lambda r=rows[label]: (r["right"], f"asked {r['asked']}"))
        check("stage 2: Claude asked for a tool on at least 3 of the 4 questions", lambda d=data: (sum(1 for r in d["rows"] if r["asked"]) >= 3, ""))
        info("the 'needs both' question may ask for one tool first or both at once; both are fine")
    if stage == 3:
        for label in ("needs find_book", "needs check_due_date"):
            check(f"stage 3: {label}: the tool ran and the answer is grounded", lambda r=rows[label]: (r["grounded"] and bool(r["tools_used"]), f"tools {r['tools_used']}"))
        check("stage 3: the loop ended with an answer on every question", lambda d=data: (not any(r["gave_up"] for r in d["rows"]), ""))
        check("stage 3: the state trace of 'needs both' ends in DONE and has an EXECUTING_TOOLS step",
              lambda r=rows["needs both"]: (r["states"][-1] == "DONE" and "EXECUTING_TOOLS" in r["states"], " -> ".join(r["states"])))
        info(f"'needs both' used {rows['needs both']['tools_used']}; 'needs none' used {rows['needs none']['tools_used']} (model choice, not a failure)")
    if stage == 4:
        check("stage 4: the crash was caught and reported (recorded, no model)", lambda d=data: (d["crash_caught"], d["crash_content"][:60]))
        check("stage 4: the endless loop stopped at MAX_TURNS with gave_up (recorded, no model)",
              lambda d=data: (d["runaway"]["gave_up"] and d["runaway"]["turns"] == lab.MAX_TURNS, str(d["runaway"])))
        check("stage 4: at least one live tool error reached Claude flagged is_error", lambda d=data: (d["flagged_total"] >= 1, f"{d['flagged_total']} flagged"))
        check("stage 4: no live question ended in gave_up", lambda d=data: (not any(r["gave_up"] for r in d["live"]), ""))
print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
