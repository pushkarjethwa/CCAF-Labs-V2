"""check.py - Part A applies the design rules to your tables (no key needed). Part B checks that Claude's critique ran on your current design.

Exit code 0 = everything passed.
"""
import json
import sys

import lab

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


problems = lab.check_tables(lab.ARCHITECTURE, lab.STEPS, lab.DATA_FLOW)


def about(where):
    return "; ".join(f"{rule}: {msg}" for w, rule, msg in problems if w == where)


print("PART A - your two tables against the rules (no API key)\n")
print("TABLE 1 - the four briefs")
for brief in lab.DATA["briefs"]:
    check(not about(brief["id"]), f"{brief['id']} {brief['title']}", about(brief["id"]))

print("\nTABLE 2 - the seven recall steps")
for step in lab.DATA["steps"]:
    check(not about(step["id"]), f"{step['id']} {step['name']}", about(step["id"]))

print("\nWHOLE DESIGN")
check(not any(w == "design" and r in ("L1", "L2") for w, r, _ in problems), "at most 2 agents, and the two tables agree about whether an agent exists",
      about("design"))
check(lab.DATA_FLOW == "explicit_handoffs", "components share data through explicit hand-offs, not one shared database", about("design"))
kinds = {k: sum(1 for v in lab.STEPS.values() if v[0] == k) for k in lab.KINDS}
check(kinds["tool"] + kinds["fixed_step"] > kinds["agent"], f"least power: tools and fixed steps outnumber agents {kinds}")

print("\nPART B - Claude's second opinion (needs `python lab.py` with a key)\n")
if problems:
    print("[SKIP] fix Part A first. Claude's critique is only requested once the rules pass.")
elif not lab.RESULTS_FILE.exists():
    print("[SKIP] results/design.json not found - run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    crit = saved.get("critique") or {}
    check(saved.get("fingerprint") == lab.table_fingerprint(lab.ARCHITECTURE, lab.STEPS, lab.DATA_FLOW),
          "the saved critique is about your CURRENT tables", "you edited a table after the last run - run `python lab.py` again")
    check(bool(crit) and "raw" not in crit and crit.get("weakest_pick"), "Claude's critique came back readable and names a weakest pick",
          "the reply could not be parsed - run `python lab.py` again")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
