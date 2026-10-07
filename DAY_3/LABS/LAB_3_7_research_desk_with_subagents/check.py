"""check.py - Part A tests your two TODOs with no API key and no model. Part B checks the real run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import asyncio
import json
import sys

import lab

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def words(text):
    return len(str(text).split())


def tools_of(name):
    return sorted(getattr(lab.SUBAGENTS.get(name), "tools", None) or [])


print("PART A - your two TODOs, tested with no API key and no model\n")
print("TODO 1 - the subagents (least privilege)")
analyst, checker = lab.SUBAGENTS.get("analyst"), lab.SUBAGENTS.get("fact_checker")
check(tools_of("analyst") == sorted([lab.mcp("cagr"), lab.mcp("divide")]), "analyst: only the two arithmetic tools, cagr and divide", f"tools: {tools_of('analyst')}")
check(tools_of("fact_checker") == [lab.mcp("fetch_document")], "fact_checker: only fetch_document, nothing else", f"tools: {tools_of('fact_checker')}")
check(tools_of("writer") == [] and all(len(tools_of(n)) <= 3 for n in lab.SUBAGENTS), "writer has no tools, and no specialist has more than three")
check(words(getattr(analyst, "description", "")) >= 6 and "tool" in str(getattr(analyst, "prompt", "")).lower() and "arithmetic" in str(getattr(analyst, "prompt", "")).lower(),
      "analyst: the description says when to use it, and the prompt says to use the tools and never do arithmetic in its head")
check(words(getattr(checker, "description", "")) >= 6 and "CONFLICT" in str(getattr(checker, "prompt", "")) and "never choose" in str(getattr(checker, "prompt", "")).lower(),
      "fact_checker: the description says when to use it, and the prompt says to report CONFLICT and never choose between sources")
check(all(getattr(lab.SUBAGENTS.get(n), "maxTurns", None) for n in ("analyst", "fact_checker")), "analyst and fact_checker each have a turn limit (maxTurns)")

print("\nTODO 2 - the coordinator")
run = lab.Run(lab.QUESTIONS["Q5"])
try:
    options, error = lab.build_options(run), ""
except Exception as exc:
    options, error = None, f"{type(exc).__name__}: {exc}"
get = lambda name: getattr(options, name, None)  # noqa: E731
check(options is not None and get("agents") is lab.SUBAGENTS and sorted(get("agents") or {}) == ["analyst", "fact_checker", "searcher", "writer"], "the coordinator knows the four specialists", error)
check(options is not None and get("tools") == ["Agent"], "the coordinator's only built-in tool is Agent (delegation), so it cannot search or calculate itself")
allowed = set(get("allowed_tools") or [])
check(options is not None and {"Agent", "Task"} <= allowed and {lab.mcp(s.name) for s in lab.TOOL_SPECS} <= allowed, "delegation and all five desk tools are allowed (the subagents use them)", f"allowed_tools={sorted(allowed)}")
check(options is not None and get("max_turns") and get("max_turns") <= 40 and get("max_budget_usd") and 0 < get("max_budget_usd") <= 5 and get("setting_sources") == [] and get("system_prompt") == lab.COORDINATOR_PROMPT,
      "the desk has a turn limit (at most 40), a spending limit (at most 5 dollars), ignores local settings, and uses the coordinator prompt")

print("\nPART B - the real run (needs `python lab.py` with a key and the Claude Code CLI; tolerant of normal model variation)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in saved["rows"]}
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    check(all(r["delegated_to"] for r in rows.values()) and all("writer" in r["delegated_to"] for r in rows.values()), "the coordinator delegated to specialists, and the writer produced each report", f"delegations: {[r['delegated_to'] for r in rows.values()]}")
    q2 = rows["Q2"]["checks"]
    check(q2["escalation"] and q2["fact:revenue_basis"] and q2["fact:unit_basis"], "Q2: both reliable figures are reported and the conflict is escalated to a human", f"Q2 checks: {q2}")
    q5 = rows["Q5"]["checks"]
    check(q5["fact:partner"] and q5["qualified:Hartwell"], "Q5: the real partner is named and the rumour (if mentioned) is labelled as unconfirmed", f"Q5 checks: {q5}")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
