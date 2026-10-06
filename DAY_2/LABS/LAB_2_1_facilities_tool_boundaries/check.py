"""Run while you work on toolset.py.   python check.py
Part A lints your toolset: no API key needed. Part B reads evidence/evidence.json from a real run (`python lab.py`).
Thresholds (real models): balanced final >= 85%, fast final >= 75%, and no regression versus the legacy toolset.
Real models usually start well above 50%, so the headroom is smaller than you may expect: measure, do not assume.
Exit code 0 means every check passed."""
import hashlib
import json
import pathlib
import sys

import toolset
from toolset_lint import lint

HERE = pathlib.Path(__file__).parent
EVIDENCE_FILE = HERE / "evidence" / "evidence.json"
FINAL_MIN = {"balanced": 85.0, "fast": 75.0}
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


print("== Part A: your toolset.py (no API key needed) ==")
for name, ok, detail in lint(toolset.TOOLS, toolset.CAPABILITY_MAP, toolset.SCOPES):
    check(ok, f"lint: {name}", detail)
check(len(toolset.TOOLS) < 11, "toolset is smaller than the 11-tool legacy set", f"{len(toolset.TOOLS)} tools")

if not EVIDENCE_FILE.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your real run (evidence.json) ==")
evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
fresh = evidence["toolset_sha256"] == hashlib.sha256((HERE / "toolset.py").read_bytes()).hexdigest()
check(fresh, "evidence is fresh (toolset.py unchanged since lab.py ran)", "re-run lab.py if this fails")
check(evidence["tool_choice_used"] == "auto", "the eval used tool_choice=auto only (never forced)")
check(set(evidence["models"]) >= {"fast", "balanced"}, "both model classes were evaluated (fast and balanced)")
for alias, entry in evidence["models"].items():
    before, after = entry["before"]["score_pct"], entry["after"]["score_pct"]
    tag = f"{alias}: before {before}% -> after {after}% ({after - before:+.1f} points)"
    check(after - before >= 0, "no regression versus the legacy toolset", tag)
    check(after >= FINAL_MIN.get(alias, 85.0), f"final score >= {FINAL_MIN.get(alias, 85.0):.0f}%", tag)
    check(not entry["after"]["scope_misses"], f"{alias}: no prompt lost its correct tool to scoping", str(entry["after"]["scope_misses"] or "none"))

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
