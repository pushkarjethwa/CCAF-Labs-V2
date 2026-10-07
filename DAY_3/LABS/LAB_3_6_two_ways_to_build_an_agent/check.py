"""check.py - Part A tests your two builds with a scripted stand-in for Claude (no API key). Part B checks the real run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import json
import sys
from types import SimpleNamespace as NS

import incident_kit as kit
import lab

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def guarded(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # a TODO that crashes is reported as a failure, not a traceback
        return f"{type(exc).__name__}: {exc}"


def use(i, name, **args):
    return NS(type="tool_use", id=f"id{i}", name=name, input=args)


def reply(blocks, stop):
    return NS(content=blocks, stop_reason=stop, usage=NS(input_tokens=10, output_tokens=5))


TEXT = NS(type="text", text="Verdict: confirmed compromise on bastion-02.")


class ScriptedClient:
    """Plays a fixed list of replies and remembers exactly what it was asked."""

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.messages = NS(create=self._create)
        self.beta = NS(messages=NS(tool_runner=self._runner))
        self.runner_kwargs = None

    def _create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot: the list grows after the call
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]

    def _runner(self, **kwargs):
        self.runner_kwargs = kwargs
        replies = self.replies

        class Runner:
            def __iter__(self):
                return iter(replies[:-1])

            def until_done(self):
                return replies[-1]
        return Runner()


print("PART A - your two builds, tested with a scripted stand-in for Claude (no API key)\n")
print("TODO 1 - the manual loop")
turn1 = reply([use(1, "list_alerts"), use(2, "get_log_lines", host="bastion-02")], "tool_use")
client = ScriptedClient([turn1, reply([TEXT], "end_turn")])
out = guarded(lab.manual_loop, client)
first = client.calls[0] if client.calls else {}
check(first.get("model") == kit.MODEL and first.get("max_tokens") and first.get("system") == kit.SYSTEM_PROMPT
      and [t["name"] for t in first.get("tools", [])] == [t['name'] for t in kit.TOOLS] and first.get("messages", [{}])[0].get("content") == kit.GOAL,
      "1a: the first call sends the model, max_tokens, the system prompt, all three tools and the goal as the first user message", f"first call: {sorted(first)}; result: {out!r}")
second = client.calls[1]["messages"] if len(client.calls) > 1 else []
check(len(second) == 3 and second[1].get("role") == "assistant" and second[1].get("content") is turn1.content,
      "1b: Claude's own turn, tool_use blocks included, is kept in the conversation before the results", f"messages on the second call: {[m.get('role') for m in second]}")
results_message = second[2] if len(second) > 2 else {}
blocks = results_message.get("content") if isinstance(results_message.get("content"), list) else []
check(results_message.get("role") == "user" and [b.get("tool_use_id") for b in blocks] == ["id1", "id2"] and all(b.get("type") == "tool_result" for b in blocks),
      "1c: both tool results of one turn go back together in ONE user message, each with the matching tool_use_id", f"third message: {results_message!r}")
client = ScriptedClient([turn1, reply([TEXT], "end_turn")])
out = guarded(lab.manual_loop, client)
check(isinstance(out, dict) and out.get("stop_reason") == "end_turn" and out.get("tools_called") == ["list_alerts", "get_log_lines"] and len(client.calls) == 2,
      "the loop stops when Claude says end_turn, and reports the tools it called in order", f"returned {out!r}")

print("\nTODO 2 - the tool runner")
recorded = []
original_beta_tool = lab.beta_tool
lab.beta_tool = lambda fn, **kw: recorded.append((fn, kw)) or NS(wrapped=fn, **kw)
try:
    wrapped = guarded(lab.as_runner_tool, kit.TOOLS[1])
finally:
    lab.beta_tool = original_beta_tool
tool = kit.TOOLS[1]
check(len(recorded) == 1 and recorded[0][1] == {"name": tool["name"], "description": tool["description"], "input_schema": tool["input_schema"]},
      "as_runner_tool hands beta_tool the function, the tool's name, its description and its input schema", f"wrapped: {wrapped!r}")
check(len(recorded) == 1 and recorded[0][0](host="bastion-02") == kit.RUN_TOOL[tool["name"]]({"host": "bastion-02"}),
      "the wrapped function receives keyword arguments and passes them to the tool as a dict")
client = ScriptedClient([reply([use(1, "list_alerts")], "tool_use"), reply([use(2, "get_log_lines", host="bastion-02")], "tool_use"), reply([TEXT], "end_turn")])
lab.beta_tool = lambda fn, **kw: NS(wrapped=fn, **kw)
try:
    out = guarded(lab.runner_loop, client)
finally:
    lab.beta_tool = original_beta_tool
kw = client.runner_kwargs or {}
check(kw.get("model") == kit.MODEL and kw.get("max_tokens") and kw.get("system") == kit.SYSTEM_PROMPT and len(kw.get("tools", [])) == 3
      and kw.get("messages") == [{"role": "user", "content": kit.GOAL}], "the runner is created with the model, max_tokens, the system prompt, three tools and the goal", f"runner arguments: {sorted(kw)}; result: {out!r}")
check(kw.get("max_iterations") == kit.MAX_TURNS, f"the runner has the same brake as the manual loop: max_iterations={kit.MAX_TURNS}", f"max_iterations={kw.get('max_iterations')}")
check(isinstance(out, dict) and out.get("tools_called") == ["list_alerts", "get_log_lines"] and out.get("stop_reason") == "end_turn" and out.get("turns") == 2,
      "the runner build reports the tools called, the turns, and the stop reason of the final message", f"returned {out!r}")

print("\nPART B - the real run (needs `python lab.py` with a key; tolerant of normal model variation)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    rows = {r["build"]: r for r in saved["rows"]}
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    check(all(r["stop_reason"] == "end_turn" for r in rows.values()), "both builds ended with end_turn: Claude finished its report", f"stop reasons: {[r['stop_reason'] for r in rows.values()]}")
    check(all({"get_log_lines", "lookup_indicator"} <= set(r["tools_called"]) for r in rows.values()), "both agents read the logs and looked up an indicator, choosing their own steps",
          f"tools: {[r['tools_called'] for r in rows.values()]}")
    check(all("bastion-02" in r["final_text"].lower() for r in rows.values()), "both reports name bastion-02: the same task gives the same answer whoever runs the loop")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
