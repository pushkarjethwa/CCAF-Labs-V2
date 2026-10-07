"""Run while you work.   python check.py
Part A tests YOUR code with fake MCP objects and hand-made model replies: no API key and no MCP install needed.
Part B reads evidence/stageN.json from the stages you have run (python lab.py --stage N).
Fails on the starter by design. Exit code 0 means every check passed."""
import asyncio
import contextlib
import json
import pathlib
import sys
import types
from types import SimpleNamespace as NS

import lab
import notes_core as core

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
    return NS(type="text", text=s)


def reply(blocks, stop):
    return NS(content=blocks, stop_reason=stop)


class FakeSession:
    """Stands in for an MCP session: records every call_tool and answers with a text item."""

    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return NS(content=[text(f"result of {name}")], is_error=False)


def scripted(*replies):
    queue, seen = list(replies), []

    def send(messages, **kwargs):
        seen.append([{"role": m["role"], "content": m["content"]} for m in messages])
        return queue.pop(0) if queue else reply([text("(script ended)")], "end_turn")
    return send, seen


ORIGINAL_ALLOWED = set(lab.ALLOWED_TOOLS)  # what YOUR TODO 6 says, before any test changes it


def run_loop(blocks, final="ok"):
    """Run the loop with the two real tool names allowed, so the TODO 4 and TODO 5 tests do not depend on TODO 6."""
    session = FakeSession()
    send, seen = scripted(reply(blocks, "tool_use"), reply([text(final)], "end_turn"))
    lab.ALLOWED_TOOLS = {"search_notes", "get_note"}
    try:
        out = asyncio.run(lab.answer(session, [], "question", send=send))
    finally:
        lab.ALLOWED_TOOLS = ORIGINAL_ALLOWED
    return out, session, seen


def use(call_id, name, tool_input):
    return NS(type="tool_use", id=call_id, name=name, input=tool_input)


print("== Part A: your code with fake MCP objects (no key, no MCP) ==")


def t_connect():
    events = []

    class Params:
        def __init__(self, command=None, args=(), env=None):
            events.append(("params", [str(a) for a in args]))

    @contextlib.asynccontextmanager
    async def fake_stdio_client(params):
        events.append("stdio_client")
        yield "READ", "WRITE"

    class FakeClientSession:
        def __init__(self, read, write):
            events.append(("session", read, write))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def initialize(self):
            events.append("initialize")

    fake = types.ModuleType("mcp")
    fake.StdioServerParameters, fake.stdio_client, fake.ClientSession = Params, fake_stdio_client, FakeClientSession
    saved = sys.modules.get("mcp")
    sys.modules["mcp"] = fake

    async def go():
        async with lab.open_session("notes_server.py") as session:
            events.append("inside")
            return isinstance(session, FakeClientSession)

    try:
        got_session = asyncio.run(go())
    finally:
        if saved is None:
            sys.modules.pop("mcp", None)
        else:
            sys.modules["mcp"] = saved
    params = [e for e in events if isinstance(e, tuple) and e[0] == "params"]
    ok = (got_session and bool(params) and params[0][1][0].endswith("notes_server.py") and ("session", "READ", "WRITE") in events
          and "initialize" in events and events.index("initialize") < events.index("inside"))
    return ok, f"events: {[e if isinstance(e, str) else e[0] for e in events]}"


check("TODO 1: open_session starts the server file, opens a ClientSession on its streams and calls initialize() before yielding it", t_connect)
fake_tool = NS(name="get_note", description="Read a note", input_schema={"type": "object", "properties": {"note_id": {"type": "string"}}})
check("TODO 2: an MCP tool becomes {name, description, input_schema}",
      lambda: (lab.mcp_tool_to_claude(fake_tool) == {"name": "get_note", "description": "Read a note", "input_schema": fake_tool.input_schema}, str(sorted(lab.mcp_tool_to_claude(fake_tool)))))
check("TODO 2: a missing description becomes an empty string", lambda: (lab.mcp_tool_to_claude(NS(name="x", description=None, input_schema={})).get("description") == "", ""))
check("TODO 3: several text items are joined, is_error False", lambda: (lab.result_to_text(NS(content=[text("a"), text("b")], is_error=False)) == ("a\nb", False), ""))
check("TODO 3: the error flag is kept", lambda: (lab.result_to_text(NS(content=[text("no note")], is_error=True)) == ("no note", True), ""))
check("TODO 3: an empty result gets a placeholder", lambda: (lab.result_to_text(NS(content=[], is_error=False)) == ("(empty result)", False), ""))
check("TODO 3: items that are not text are ignored", lambda: (lab.result_to_text(NS(content=[NS(type="image"), text("a")], is_error=False)) == ("a", False), ""))


def t_forward():
    out, session, _ = run_loop([use("tu_1", "search_notes", {"query": "pager"})], "Priya, 555-0142")
    return session.calls == [("search_notes", {"query": "pager"})] and out["tools_used"] == ["search_notes"], str(session.calls)


def t_final():
    out, _, _ = run_loop([use("tu_1", "search_notes", {"query": "pager"})], "Priya, 555-0142")
    return out["answer"] == "Priya, 555-0142" and out["turns"] == 2, str(out)


def t_result_back():
    _, _, seen = run_loop([use("tu_1", "search_notes", {"query": "pager"})])
    sent = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 else []
    ok = len(sent) == 1 and sent[0].get("type") == "tool_result" and sent[0].get("tool_use_id") == "tu_1" and sent[0].get("content") == "result of search_notes"
    return ok, str(sent)[:100]


def t_two_calls():
    _, session, seen = run_loop([use("a", "search_notes", {"query": "x"}), use("b", "get_note", {"note_id": "N-1"})])
    sent = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 else []
    return [b.get("tool_use_id") for b in sent] == ["a", "b"] and len(session.calls) == 2, "both results go back in ONE user message"


check("TODO 4: Claude's tool request is forwarded to the MCP session", t_forward)
check("TODO 4: the loop ends with Claude's final answer in turn 2", t_final)
check("TODO 4: the server's text goes back as a tool_result with the same id", t_result_back)
check("TODO 4: two requests in one turn give one user message with both results", t_two_calls)

def t_server_error():
    class Broken(FakeSession):
        async def call_tool(self, name, arguments):
            raise RuntimeError("server went away")

    send, seen = scripted(reply([use("tu_1", "get_note", {"note_id": "N-1"})], "tool_use"), reply([text("ok")], "end_turn"))
    lab.ALLOWED_TOOLS = {"search_notes", "get_note"}
    try:
        out = asyncio.run(lab.answer(Broken(), [], "question", send=send))
    finally:
        lab.ALLOWED_TOOLS = ORIGINAL_ALLOWED
    sent = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 else []
    return out["answer"] == "ok" and len(sent) == 1 and sent[0].get("is_error") is True and "server went away" in sent[0].get("content", ""), str(sent)[:100]


check("TODO 4: a call to the server that raises becomes an error tool_result, not a crash", t_server_error)


def t_offer():
    tools = [{"name": "search_notes"}, {"name": "get_note"}, {"name": "delete_note"}]
    lab.ALLOWED_TOOLS = {"search_notes", "get_note"}
    try:
        names = [t["name"] for t in lab.offer(tools)]
    finally:
        lab.ALLOWED_TOOLS = ORIGINAL_ALLOWED
    return names == ["search_notes", "get_note"], str(names)


def t_guard_not_forwarded():
    out, session, _ = run_loop([use("tu_1", "delete_note", {"note_id": "N-3"})])
    return session.calls == [] and out["tools_used"] == [], f"{len(session.calls)} calls reached the server"


def t_guard_flagged():
    _, _, seen = run_loop([use("tu_1", "delete_note", {"note_id": "N-3"})])
    sent = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 else []
    ok = len(sent) == 1 and sent[0].get("tool_use_id") == "tu_1" and sent[0].get("is_error") is True and "not allowed" in sent[0].get("content", "")
    return ok, str(sent)[:100]


def t_guard_mixed():
    _, session, seen = run_loop([use("a", "delete_note", {"note_id": "N-3"}), use("b", "get_note", {"note_id": "N-1"})])
    sent = seen[1][2]["content"] if len(seen) > 1 and len(seen[1]) == 3 else []
    return session.calls == [("get_note", {"note_id": "N-1"})] and [b.get("tool_use_id") for b in sent] == ["a", "b"], "every tool_use still gets exactly one tool_result"


check("TODO 6: ALLOWED_TOOLS is exactly search_notes and get_note", lambda: (ORIGINAL_ALLOWED == {"search_notes", "get_note"}, str(ORIGINAL_ALLOWED)))
check("TODO 6: offer hides every tool that is not allowed", t_offer)
check("TODO 5: a request for delete_note is never forwarded to the server", t_guard_not_forwarded)
check("TODO 5: the refusal goes back as an error tool_result with the same id", t_guard_flagged)
check("TODO 5: with one allowed and one refused request, each gets one result and only the allowed one is forwarded", t_guard_mixed)

print("\n== Part B: your real runs (evidence/stageN.json) ==")
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
        check("stage 1: the server offers get_note and search_notes", lambda d=data: (d["tool_names"] == ["get_note", "search_notes"], str(d["tool_names"])))
        check("stage 1: the search found the pager note", lambda d=data: ("N-1" in d["search_text"], ""))
        check("stage 1: a missing note comes back as an error, not a crash", lambda d=data: (d["missing_is_error"] is True, ""))
    if stage == 2:
        check("stage 2: the on-call question made Claude ask for search_notes", lambda r=rows["on-call"]: (any(a.startswith("search_notes") for a in r["asked"]), str(r["asked"])))
        check("stage 2: Claude asked for a server tool on at least 2 of the 3 questions", lambda d=data: (sum(r["right"] for r in d["rows"]) >= 2, ""))
        info("which tool Claude picks first for the other questions is the model's choice")
    if stage == 3:
        check("stage 3: the on-call answer holds the pager number, fetched through the server", lambda r=rows["on-call"]: (r["ok"], f"tools {r['tools_used']}"))
        check("stage 3: the expense answer holds the limit, fetched through the server", lambda r=rows["expense limit"]: (r["ok"], f"tools {r['tools_used']}"))
        check("stage 3: the unknown note reached Claude as an error and the loop ended cleanly", lambda r=rows["unknown note"]: (r["flagged"] >= 1 and not r["gave_up"], f"flagged {r['flagged']}"))
        info(f"the model's wording of the N-9 answer: {rows['unknown note']['answer'][:90]}")
    if stage == 4:
        check("stage 4: the newer server offers delete_note", lambda d=data: ("delete_note" in d["server_tools"], str(d["server_tools"])))
        check("stage 4: Claude is handed only search_notes and get_note", lambda d=data: (d["offered_tools"] == ["get_note", "search_notes"], str(d["offered_tools"])))
        check("stage 4: the recorded delete request was refused and no note was deleted", lambda d=data: (d["notes_after"] == d["notes_before"] and d["tools_used"] == [], f"notes {d['notes_before']} -> {d['notes_after']}"))
        check("stage 4: the refusal reached Claude as an error tool_result", lambda d=data: (d["flagged"] == 1, ""))
print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
