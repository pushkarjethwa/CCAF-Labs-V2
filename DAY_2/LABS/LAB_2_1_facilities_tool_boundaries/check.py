"""check.py - Part A tests your five TODOs with scripted data (no API key needed).
Part B checks the evidence that your stage runs saved in the evidence/ folder.

Exit code 0 = everything passed.
"""
import json
import pathlib

import facilities_core as core
import lab
import toolset_original as legacy
from toolset_lint import WHEN, WHEN_NOT, lint

HERE = pathlib.Path(__file__).parent
EVIDENCE = HERE / "evidence"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


class FakeClient:
    """Stands in for Claude. Records every request and returns a fixed reply."""

    def __init__(self):
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return "scripted response"


def attempt(function, *args):
    """Call a TODO function. If it is not written yet, say so instead of showing a traceback."""
    try:
        return function(*args)
    except NotImplementedError as exc:
        print(f"         ({exc})")
        return None


def lint_by_name(stage):
    tools, cap_map, scopes = core.build_stage(stage)
    return {name: (ok, detail) for name, ok, detail in lint(tools, cap_map, scopes)}


legacy_names = [t["name"] for t in legacy.LEGACY_TOOLS]
print("PART A - your code, tested with scripted data (no API key)\n")

print("TODO 1 - ask_with_tools: the Claude call")
fake = FakeClient()
lab.get_client = lambda: fake
tools_in = [{"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
got = attempt(lab.ask_with_tools, "model-x", tools_in, "Is Harbor 3 free?")
call = fake.calls[0] if fake.calls else {}
check(got == "scripted response" and len(fake.calls) == 1, "makes exactly one Claude call and returns its response")
check(call.get("model") == "model-x" and (call.get("max_tokens") or 0) > 0, "passes the model and a max_tokens", f"model={call.get('model')!r}, max_tokens={call.get('max_tokens')!r}")
check(call.get("tools") == tools_in, "offers the tools it was given", f"tools={call.get('tools')!r}"[:100])
check(call.get("tool_choice") == {"type": "auto"}, 'tool_choice is {"type": "auto"} (never forced)', f"tool_choice={call.get('tool_choice')!r}")
check(call.get("system") == core.SYSTEM and call.get("messages") == [{"role": "user", "content": "Is Harbor 3 free?"}], "sends core.SYSTEM as the system prompt and the prompt as the user message", f"keys sent: {sorted(call)}")

print("\nTODO 2 - DESCRIPTIONS: stage 2")
d = lab.DESCRIPTIONS
check(set(d) == set(legacy_names), "there is one description for each of the 11 legacy tools", f"missing: {sorted(set(legacy_names) - set(d))}")
check(bool(d) and all(WHEN.search(v) for v in d.values()), "every description says when to use the tool ('Use when ...')")
check(bool(d) and all(WHEN_NOT.search(v) for v in d.values()), "every description says when NOT to use it ('Do NOT use ...')")
check(bool(d) and all(len(v) >= 100 for v in d.values()), "every description is at least 100 characters")
check(bool(d) and all(any(f"use {n}" in v for n in legacy_names if n != k) for k, v in d.items()), "every description names a sibling tool to use instead ('use room_lookup')")
stage2 = lint_by_name(2)
check(stage2["when_to_use"][0] and stage2["when_not_to_use"][0] and stage2["description_length"][0], "the stage 2 toolset passes the three description lint checks", str({k: v for k, v in stage2.items() if not v[0]})[:140])

print("\nTODO 3 - CONSOLIDATED and CONSOLIDATED_MAP: stage 3")
c = lab.CONSOLIDATED
check(len(c) == 2 and all(t["input_schema"]["properties"].get("action", {}).get("enum") for t in c), "two consolidated tools, each with an `action` enum", f"got {[t['name'] for t in c]}")
routes = {f"{t['name']}:{a}" for t in c for a in t["input_schema"]["properties"].get("action", {}).get("enum", [])}
check(bool(routes) and set(lab.CONSOLIDATED_MAP) == routes, "CONSOLIDATED_MAP has exactly one entry for every tool:action", f"routes {sorted(routes)}; map {sorted(lab.CONSOLIDATED_MAP)}")
check(set(lab.CONSOLIDATED_MAP.values()) == {"room.search", "room.get", "room.hold", "ticket.create", "ticket.list_open", "ticket.log"}, "the six actions reach the six room and ticket capabilities")
check(bool(c) and all(WHEN.search(t["description"]) and WHEN_NOT.search(t["description"]) and len(t["description"]) >= 100 for t in c), "each consolidated description says when to use and when NOT to use the tool")
stage3_tools = core.build_stage(3)[0]
check(len(stage3_tools) == 13, "stage 3 offers 13 tools: the 11 old ones plus your 2 (the old ones go in stage 4)", f"{len(stage3_tools)} tools")

print("\nTODO 4 - REMOVE: stage 4")
check(bool(lab.REMOVE) and set(lab.REMOVE) <= set(legacy_names), "REMOVE lists only legacy tool names", f"REMOVE={lab.REMOVE}")
stage4_tools, stage4_map, _ = core.build_stage(4)
check(len(stage4_tools) <= 8 and bool(c), "after the removal there are 8 tools or fewer", f"{len(stage4_tools)} tools")
stage4 = lint_by_name(4)
check(stage4["capability_coverage"][0] and stage4["no_duplicate_routes"][0] and stage4["capability_map_valid"][0], "every capability has exactly one route, and no map entry points at a removed tool", str({k: v for k, v in stage4.items() if not v[0]})[:160])

print("\nTODO 5 - SCOPES: stage 5")
s = lab.SCOPES
check(set(s) == set(legacy.CONTEXTS), "there is one scope for each of the three desks", f"got {sorted(s)}")
tools5, cap5, scopes5 = core.build_stage(5)
names5 = {t["name"] for t in tools5}
check(bool(s) and all(0 < len(v) <= 7 and set(v) <= names5 for v in s.values()), "each desk has 1 to 7 tools, and every name is a real tool", str({k: len(v) for k, v in s.items()}))
misses = [p["id"] for p in core.load_prompts() if not (set(p["correct"]) & core.reachable(cap5, scopes5[p["context"]]))]
check(bool(s) and not misses, "no prompt is impossible: every desk can reach the capability its prompts need", f"unreachable prompts: {misses}")
stage5 = lint_by_name(5)
check(all(ok for ok, _ in stage5.values()), "the final toolset passes every lint check", str({k: v for k, v in stage5.items() if not v[0]})[:200])

print("\nThe given plumbing (checks that the data and helpers are intact)")
check(len(core.load_prompts()) == 16 and len(legacy.LEGACY_TOOLS) == 11, "16 prompts and 11 legacy tools")
check(core.capability_reached({"space:get": "room.get", "book_room": "booking.create"}, "space", {"action": "get"}) == "room.get", "the grader maps tool:action to a capability")

print("\nPART B - the evidence your stage runs saved (needs `python lab.py --stage N` with a key)\n")


def load(name):
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


ev = {n: load(f"stage{n}.json") for n in range(1, 6)}
gate = load("gate.json")
if not any(ev.values()):
    print("[SKIP] no evidence yet - run `python lab.py --stage 1`, then 2, 3, 4, 5 and gate, then this again.")
elif not all(results):
    print("[SKIP] fix Part A first, then run the stages again.")
else:
    sizes = {n: len(ev[n]["tool_names"]) for n in ev if ev[n]}
    check(not ev[1] or sizes[1] == 11, "stage 1 offered the 11 legacy tools", str(sizes))
    check(not ev[3] or sizes[3] == 13, "stage 3 offered 13 tools", str(sizes))
    check(not ev[4] or sizes[4] <= 8, "stage 4 offered 8 tools or fewer", str(sizes))
    for n in (1, 2, 3, 4, 5):
        if ev[n]:
            m = ev[n]["models"]
            print(f"       info: stage {n}: " + ", ".join(f"{a} {r['score_pct']}% ({r['tools_offered']} tools, {r['def_tokens']} definition tokens)" for a, r in m.items())
                  + f"; lint {ev[n]['lint']['passed']}/{ev[n]['lint']['total']}")
    if ev[5]:
        final = ev[5]["models"]
        check(all(not r["scope_misses"] for r in final.values()), "stage 5: no prompt was sent to a desk that could not answer it")
        for alias, bar in core.BAR.items():
            if alias in final:
                check(final[alias]["score_pct"] >= bar, f"stage 5: the {alias} model scores at least {bar:.0f}%", f"{final[alias]['score_pct']}%")
        if ev[1]:
            for alias in final:
                if alias in ev[1]["models"]:
                    check(final[alias]["score_pct"] >= ev[1]["models"][alias]["score_pct"] - 6.5, f"stage 5: the {alias} model did not get worse than the baseline (one prompt of tolerance)",
                          f"{ev[1]['models'][alias]['score_pct']}% -> {final[alias]['score_pct']}%")
    if gate:
        check(gate["pass"], "gate: the final toolset passes the bar and the lint", "; ".join(gate["problems"])[:160])
        check(bool(gate["sprawl_failed"]), "gate: re-adding three legacy tools makes the lint fail", str(gate["sprawl_failed"]))

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
raise SystemExit(0 if all(results) else 1)
