"""LAB 2.1 - Facilities assistant: fix the TOOL BOUNDARIES, then prove the score moved.

Run:   python lab.py [--models fast,balanced]       (needs an API key; 64 small calls, well under $1)
Check: python check.py

You inherit 11 overlapping tools with two-word descriptions ("Look up a room.", "Open a ticket."). Staff say "the
assistant keeps doing the wrong thing". This is an engineering problem, not a prompting one: you change the
tools in toolset.py (descriptions, consolidation, pruning, per-desk scoping) and re-run the SAME 16-prompt eval.

You edit toolset.py only. This file is the eval harness: it shows Claude the tools with tool_choice "auto",
records which tool Claude picked, and grades the CAPABILITY it reached (data/capabilities.json).
"""
import argparse
import hashlib
import json
import pathlib
from collections import Counter

import toolset
import toolset_original as legacy
from toolset_lint import lint

HERE = pathlib.Path(__file__).parent
EVIDENCE_FILE = HERE / "evidence" / "evidence.json"

SYSTEM = ("You are the facilities assistant for a corporate campus. For each request pick the one tool that fits "
          "best and call it with sensible arguments. Do not answer from memory when a tool applies.")


def load_prompts():
    lines = (HERE / "data" / "eval_prompts.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def capability_reached(cap_map, tool_name, tool_input):
    """Which real capability did this tool call reach? Tools with an `action` enum map as "tool:action"."""
    action = (tool_input or {}).get("action")
    if action and f"{tool_name}:{action}" in cap_map:
        return cap_map[f"{tool_name}:{action}"]
    return cap_map.get(tool_name)


def reachable(cap_map, scope):
    """Capabilities that the tools offered in this scope can reach."""
    return {capability for route, capability in cap_map.items() if route.partition(":")[0] in scope}


def evaluate(model, prompts, tools, cap_map, scopes):
    """Ask Claude each prompt with only the SCOPED tools, tool_choice auto, and grade the capability it reached."""
    from claude_client import ask, tool_calls_of
    by_name = {t["name"]: t for t in tools}
    rows = []
    for prompt in prompts:
        scope = scopes[prompt["context"]]
        offered = [{k: by_name[name][k] for k in ("name", "description", "input_schema")} for name in scope]
        # tool_choice must stay "auto": forced choice is rejected by Sonnet/Opus 5.5 and would hide the very confusion we measure
        response = ask([{"role": "user", "content": prompt["prompt"]}], system=SYSTEM, tools=offered, model=model,
                       max_tokens=1024, tool_choice={"type": "auto"})
        calls = tool_calls_of(response)
        tool_name = calls[0].name if calls else None
        tool_input = dict(calls[0].input) if calls else {}
        capability = capability_reached(cap_map, tool_name, tool_input) if tool_name else None
        rows.append({"id": prompt["id"], "expected": prompt["correct"], "got_tool": tool_name, "got_action": tool_input.get("action"),
                     "got_capability": capability, "correct": capability in prompt["correct"],
                     "scope_miss": not (set(prompt["correct"]) & reachable(cap_map, scope))})
    correct = sum(r["correct"] for r in rows)
    confusions = Counter((r["expected"][0], r["got_tool"] + (f":{r['got_action']}" if r["got_action"] else ""))
                         for r in rows if not r["correct"])
    return {"correct": correct, "total": len(rows), "score_pct": round(100.0 * correct / len(rows), 1), "per_prompt": rows,
            "confusions": [[e, g, n] for (e, g), n in confusions.most_common()],
            "scope_misses": [r["id"] for r in rows if r["scope_miss"]]}


def main():
    from claude_client import MODEL_BALANCED, MODEL_FAST
    models = {"fast": MODEL_FAST, "balanced": MODEL_BALANCED}

    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="fast,balanced")
    args = parser.parse_args()

    prompts = load_prompts()
    legacy_scopes = {context: [t["name"] for t in legacy.LEGACY_TOOLS] for context in legacy.CONTEXTS}
    evidence = {"tool_choice_used": "auto", "n_prompts": len(prompts), "models": {}}
    for alias in [a.strip() for a in args.models.split(",") if a.strip()]:
        model = models[alias]
        print(f"\n[{alias}] {model}")
        before = evaluate(model, prompts, legacy.LEGACY_TOOLS, legacy.LEGACY_MAP, legacy_scopes)
        after = evaluate(model, prompts, toolset.TOOLS, toolset.CAPABILITY_MAP, toolset.SCOPES)
        evidence["models"][alias] = {"model": model, "before": before, "after": after, "improvement_points": round(after["score_pct"] - before["score_pct"], 1)}
        print(f"  before: {before['correct']}/{before['total']} = {before['score_pct']}%   after: {after['correct']}/{after['total']} = {after['score_pct']}%"
              f"   delta {after['score_pct'] - before['score_pct']:+.1f} points")
        print("  top confusions BEFORE (expected capability -> tool chosen):")
        for expected, got, count in before["confusions"][:5]:
            print(f"    {count}x  {expected:<17} -> {got}")
        for expected, got, count in after["confusions"][:5]:
            print(f"  remaining AFTER: {count}x  {expected:<17} -> {got}")
        if after["scope_misses"]:
            print(f"  SCOPE MISS (the right tool was not offered in that context): {after['scope_misses']}")

    print("\nScoping table (tools offered per task context):")
    for context, names in toolset.SCOPES.items():
        print(f"  {context:<18} {len(names):>2} tools: {', '.join(names)}")
    print("\nToolset lint:")
    lint_rows = lint(toolset.TOOLS, toolset.CAPABILITY_MAP, toolset.SCOPES)
    for name, ok, detail in lint_rows:
        print(f"  [{'ok' if ok else '!!'}] {name}: {detail}")

    evidence["toolset_sha256"] = hashlib.sha256((HERE / "toolset.py").read_bytes()).hexdigest()
    EVIDENCE_FILE.parent.mkdir(exist_ok=True)
    EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("\nsaved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
