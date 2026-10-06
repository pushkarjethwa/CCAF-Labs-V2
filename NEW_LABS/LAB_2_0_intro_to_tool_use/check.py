"""Run after lab.py.   python check.py
Part A tests the tool code with no API key. Part B reads evidence/evidence.json. Exit code 0 means all passed."""
import json
import pathlib
import sys

import lab

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


print("== Part A: the tool code (no API key) ==")
check(lab.run_tool("get_order_status", {"order_id": "ORD-1001"}).get("carrier") == "Northwind Express", "dispatcher runs get_order_status")
check(lab.run_tool("get_return_policy", {}).get("window_days") == 30, "dispatcher runs get_return_policy")
check(lab.run_tool("get_order_status", {"order_id": "ORD-9"}).get("error") == "order_not_found", "unknown order returns an error dict")
check(lab.run_tool("nope", {}).get("error") == "unknown_tool", "unknown tool name returns an error dict")
check(all(t["name"] and "Use it when" in t["description"] and t["input_schema"]["type"] == "object" for t in lab.TOOLS), "each schema has a name, a 'when to use' description and an object input_schema")

if not EVIDENCE_FILE.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your real run (evidence.json) ==")
ev = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
if "step1" in ev:
    s1 = ev["step1"]
    check(s1["tool_calls"] == 0 and "northwind express" not in s1["answer"].lower(), "step 1: no tools, so Claude could not know the order's carrier", s1["answer"][:80])
if "step2" in ev:
    s2 = ev["step2"]
    check(s2["first_stop_reason"] == "tool_use" and s2["tool_name"] == "get_order_status" and s2["tool_input"].get("order_id") == "ORD-1001", "step 2: Claude REQUESTED get_order_status(ORD-1001) (stop_reason tool_use)")
    check(s2["final_stop_reason"] == "end_turn", "step 2: after the tool_result, Claude finished (end_turn)")
    answer = s2["answer"].lower()
    check("northwind express" in answer or "shipped" in answer, "step 2: the final answer uses the data our code returned", s2["answer"][:80])
if "step3" in ev:
    runs = {r["label"]: r["tools_used"] for r in ev["step3"]}
    check(runs["needs the ORDER tool"] == ["get_order_status"], "step 3: order question used only the order tool", str(runs["needs the ORDER tool"]))
    check(runs["needs the POLICY tool"] == ["get_return_policy"], "step 3: policy question used only the policy tool", str(runs["needs the POLICY tool"]))
    check(set(runs["needs BOTH tools"]) == {"get_order_status", "get_return_policy"}, "step 3: combined question used both tools", str(runs["needs BOTH tools"]))
    check(runs["needs NO tool"] == [], "step 3: a greeting used no tool")
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
