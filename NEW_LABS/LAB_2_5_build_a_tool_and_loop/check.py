"""Run while you work.   python check.py
Part A tests YOUR code with hand-made model replies: no API key needed.
Part B reads evidence/evidence.json from a real run (`python lab.py`).
Fails on the starter by design. Exit code 0 means every check passed."""
import json
import pathlib
import sys
from types import SimpleNamespace

import lab

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def tool_use(call_id, name, tool_input):
    return SimpleNamespace(type="tool_use", id=call_id, name=name, input=tool_input)


def reply(blocks, stop):
    return SimpleNamespace(content=blocks, stop_reason=stop)


def scripted(*replies):
    """A fake send(): returns the replies in order and records the messages it was given."""
    seen = []
    queue = list(replies)

    def send(messages, **kwargs):
        seen.append(json.loads(json.dumps(messages, default=lambda o: {"block": o.type, "id": getattr(o, "id", None)})))
        return queue.pop(0) if queue else reply([SimpleNamespace(type="text", text="(script ended)")], "end_turn")
    return send, seen


print("== Part A: your code with hand-made model replies (no API key) ==")
schema = lab.CHECK_DUE_DATE_TOOL
props = schema.get("input_schema", {}).get("properties", {})
check(schema.get("name") == "check_due_date" and len(schema.get("description", "")) > 40 and "member_id" in props
      and "member_id" in schema.get("input_schema", {}).get("required", []), "TODO 1: check_due_date schema has name, a real description, and required member_id")
check(lab.run_tool("find_book", {"title": "Dune"}).get("shelf") == "SF-12", "TODO 2: dispatcher runs find_book")
check(lab.run_tool("check_due_date", {"member_id": "M-200"}).get("due") == "2026-10-08", "TODO 2: dispatcher runs check_due_date")
check(lab.run_tool("delete_everything", {}).get("error") == "unknown_tool", "TODO 2: unknown tool name returns an error dict, no crash")
content, is_error = lab.run_tool_safely("find_book", {"title": "Nope"})
check(is_error is True and "book_not_found" in content, "TODO 4: an error result is flagged is_error=True")
try:
    content, is_error = lab.run_tool_safely("find_book", {"wrong_argument": 1})
except Exception as exc:  # the starter lets the crash escape
    content, is_error = f"CRASHED: {exc}", None
check(is_error is True and "tool_crashed" in content, "TODO 4: a crashing tool is caught and reported")
content, is_error = lab.run_tool_safely("find_book", {"title": "Dune"})
check(is_error is False and json.loads(content)["shelf"] == "SF-12", "TODO 4: a good result is a JSON string with is_error False")

send, seen = scripted(reply([SimpleNamespace(type="text", text="Paris.")], "end_turn"))
out = lab.answer("capital?", send=send)
check(out["answer"] == "Paris." and out["turns"] == 1 and out["tools_used"] == [], "TODO 3: no tool needed, loop ends after 1 turn")

send, seen = scripted(reply([tool_use("tu_1", "find_book", {"title": "Dune"})], "tool_use"),
                      reply([SimpleNamespace(type="text", text="Shelf SF-12.")], "end_turn"))
out = lab.answer("where is Dune?", send=send)
check(out["answer"] == "Shelf SF-12." and out["turns"] == 2 and out["tools_used"] == ["find_book"], "TODO 3: one tool call, then the final answer in turn 2")
second = seen[1] if len(seen) > 1 else []
check(len(second) == 3 and second[1]["role"] == "assistant" and second[2]["role"] == "user", "TODO 3: turn 2 sends user, assistant (tool_use), user (tool_result)")
blocks = second[2]["content"] if len(second) == 3 and isinstance(second[2]["content"], list) else []
check(len(blocks) == 1 and blocks[0].get("type") == "tool_result" and blocks[0].get("tool_use_id") == "tu_1", "TODO 3: tool_result carries the SAME id as the tool_use")

send, seen = scripted(reply([tool_use("a", "find_book", {"title": "Dune"}), tool_use("b", "check_due_date", {"member_id": "M-100"})], "tool_use"),
                      reply([SimpleNamespace(type="text", text="done")], "end_turn"))
out = lab.answer("both", send=send)
last = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 and isinstance(seen[1][2]["content"], list) else []
check(len(last) == 2 and [b.get("tool_use_id") for b in last] == ["a", "b"], "TODO 3: two tool calls in one turn -> ONE user message with both tool_results")

send, seen = scripted(*[reply([tool_use(f"t{i}", "find_book", {"title": "Dune"})], "tool_use") for i in range(20)])
out = lab.answer("loop forever", send=send)
check(out.get("gave_up") is True and out["turns"] == lab.MAX_TURNS, "the loop has an exit: it stops after MAX_TURNS tool-requesting turns")

if not EVIDENCE_FILE.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your real run with Claude (evidence.json) ==")
runs = {r["label"]: r for r in json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))["runs"]}
check(runs["needs find_book"]["tools_used"] == ["find_book"] and "SF-12" in runs["needs find_book"]["answer"], "Dune question: find_book used, answer has shelf SF-12")
check(runs["needs check_due_date"]["tools_used"] == ["check_due_date"] and "10-08" in runs["needs check_due_date"]["answer"].replace("October 8", "10-08"), "due-date question: check_due_date used, answer has the date")
check(set(runs["needs both"]["tools_used"]) == {"find_book", "check_due_date"}, "combined question: both tools used", str(runs["needs both"]["tools_used"]))
check(runs["needs none"]["tools_used"] == [] and "paris" in runs["needs none"]["answer"].lower(), "France question: no tool, Claude answered directly")
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
