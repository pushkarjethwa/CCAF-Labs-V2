"""Run while you work.   python check.py
Part A tests your functions with fake MCP objects: no key and no MCP install needed.
Part B reads evidence/evidence.json from a real run (`python lab.py`).
Fails on the starter by design. Exit code 0 means every check passed."""
import asyncio
import json
import pathlib
import sys
from types import SimpleNamespace as NS

import lab

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


text = lambda s: NS(type="text", text=s)  # noqa: E731
print("== Part A: your functions with fake MCP objects (no key, no MCP) ==")
fake_tool = NS(name="get_note", description="Read a note", input_schema={"type": "object", "properties": {"note_id": {"type": "string"}}}, inputSchema=None)
converted = lab.mcp_tool_to_claude(fake_tool)
check(converted.get("name") == "get_note" and converted.get("description") == "Read a note" and converted.get("input_schema", {}).get("type") == "object",
      "TODO 1: an MCP tool becomes {name, description, input_schema}", str(sorted(converted)))
check(set(converted) == {"name", "description", "input_schema"}, "TODO 1: no extra keys (the API rejects unknown tool fields)")
old_style = NS(name="x", description=None, inputSchema={"type": "object", "properties": {}})
check(lab.mcp_tool_to_claude(old_style).get("input_schema", {}).get("type") == "object", "TODO 1: also works with the older `inputSchema` attribute and a missing description")

check(lab.result_to_text(NS(content=[text("a"), text("b")], is_error=False)) == ("a\nb", False), "TODO 2: joins several text items, is_error False")
check(lab.result_to_text(NS(content=[text("no note")], is_error=True)) == ("no note", True), "TODO 2: keeps the error flag")
check(lab.result_to_text(NS(content=[], is_error=False)) == ("(empty result)", False), "TODO 2: empty result gets a placeholder")


class FakeSession:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return NS(content=[text(f"result of {name}")], is_error=False)


def reply(blocks, stop):
    return NS(content=blocks, stop_reason=stop)


def scripted(*replies):
    queue, seen = list(replies), []

    def send(messages, **kwargs):
        seen.append([{"role": m["role"], "content": m["content"]} for m in messages])
        return queue.pop(0) if queue else reply([text("(script ended)")], "end_turn")
    return send, seen


session = FakeSession()
send, seen = scripted(reply([NS(type="tool_use", id="tu_1", name="search_notes", input={"query": "pager"})], "tool_use"), reply([text("Priya, 555-0142")], "end_turn"))
out = asyncio.run(lab.answer(session, [converted], "who is on call?", send=send))
check(session.calls == [("search_notes", {"query": "pager"})], "TODO 3: Claude's tool request was forwarded to the MCP session", str(session.calls))
check(out["answer"] == "Priya, 555-0142" and out["tools_used"] == ["search_notes"] and out["turns"] == 2, "TODO 3: loop ends with Claude's final answer")
sent_back = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 else []
check(isinstance(sent_back, list) and sent_back and sent_back[0].get("type") == "tool_result" and sent_back[0].get("tool_use_id") == "tu_1"
      and sent_back[0].get("content") == "result of search_notes", "TODO 3: the server's text went back as a tool_result with the same id")

if not EVIDENCE_FILE.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your real run (evidence.json) ==")
evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
check(sorted(evidence["tool_names"]) == ["get_note", "search_notes"], "the client discovered both server tools", str(evidence["tool_names"]))
runs = evidence["runs"]
check("555-0142" in runs[0]["answer"] and runs[0]["tools_used"], "on-call question answered from the notes via the server", str(runs[0]["tools_used"]))
check("75" in runs[1]["answer"] and runs[1]["tools_used"], "expense question answered from the notes via the server")
check("get_note" in runs[2]["tools_used"] and "N-9" in runs[2]["answer"] + " N-9" and runs[2]["turns"] < lab.MAX_TURNS and not runs[2].get("gave_up"),
      "unknown note id: the server's error reached Claude and the loop ended cleanly")
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
