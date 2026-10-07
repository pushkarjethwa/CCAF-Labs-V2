"""check.py - Part A tests your four TODOs with hand-made inputs (no API key). Part B checks the real run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import json
import sys

import desk_core as core
import desk_tools as desk
import lab

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def errors_for(role, data):
    return core.validate(data, lab.CONTRACTS[role])


Q = desk.QUESTIONS["Q4"]
FOUND = {"findings": [{"doc_id": "DOC-010", "fact": "NorthGrid revenue FY2022", "value": "$412M"}], "rumours": [],
         "needs_calculation": True, "calc_request": "CAGR from 412 to 710 over 3 years"}
GOOD_ANALYST = {"results": [{"label": "CAGR", "value": "19.9%", "inputs": "412, 710, 3"}]}
SUPPORTED = {"checks": [{"doc_id": "DOC-010", "claim": "revenue was 412", "verdict": "SUPPORTED", "detail": "matches"}]}
CONFLICT = {"checks": [{"doc_id": "DOC-004", "claim": "Voltrix leads", "verdict": "CONFLICT", "detail": "DOC-005 says Kestrel leads by units"}]}

print("PART A - your TODOs, tested with hand-made inputs (no API key)\n")
print("TODO 1 - contracts")
check(not errors_for("analyst", GOOD_ANALYST), "analyst: a correct hand-off is accepted", "; ".join(errors_for("analyst", GOOD_ANALYST)))
check(not errors_for("fact_checker", SUPPORTED), "fact_checker: a SUPPORTED hand-off is accepted", "; ".join(errors_for("fact_checker", SUPPORTED)))
check(not errors_for("fact_checker", CONFLICT), "fact_checker: a CONFLICT hand-off is accepted", "; ".join(errors_for("fact_checker", CONFLICT)))

print("\nTODO 2 - briefs")
searcher, analyst, fact_checker = lab.searcher_brief(Q), lab.analyst_brief(FOUND), lab.fact_check_brief(FOUND["findings"][0])
check(Q["text"] in searcher, "searcher brief contains the question")
check(FOUND["calc_request"] in analyst and "$412M" in analyst, "analyst brief contains the calculation request and the findings")
check("DOC-010" in fact_checker and "NorthGrid revenue FY2022" in fact_checker, "fact_checker brief contains the document id and the claim")

print("\nTODO 3 - escalation in code")
check(lab.has_conflict(CONFLICT["checks"]) is True, "a CONFLICT verdict is detected")
check(lab.has_conflict(SUPPORTED["checks"]) is False, "a SUPPORTED verdict is not flagged as a conflict")
seen = {}
hooks = {**lab.HOOKS, "call_writer": lambda brief: seen.setdefault("brief", brief)}
scripted = {"searcher": json.dumps({"findings": FOUND["findings"], "rumours": [], "needs_calculation": False, "calc_request": ""}),
            "fact_checker": json.dumps(CONFLICT)}
core.orchestrate(Q, hooks, lambda role, brief: scripted[role])
check("escalate to a human" in seen["brief"], "when a fact-check finds a conflict, the writer's brief tells it to escalate")

print("\nPART B - the real run (needs `python lab.py` with a key; tolerant of normal model variation)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in saved["rows"]}
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    check(all(r["report"].strip() for r in rows.values()), "every question produced a report", "an empty report usually means TODO 4 still returns an empty string")
    check(rows["Q2"]["checks"].get("escalation") is True, "Q2: the conflict between two reliable reports was escalated, not silently resolved")
    check(rows["Q4"]["checks"].get("fact:cagr") is True, "Q4: the growth rate 19.9% is in the report")
    check(rows["Q5"]["checks"].get("fact:partner") is True and rows["Q5"]["checks"].get("qualified:Hartwell") is True,
          "Q5: the real partner is named and the rumour (if mentioned) is labelled as unconfirmed")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
