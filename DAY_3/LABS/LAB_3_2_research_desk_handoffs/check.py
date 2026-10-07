"""check.py - Part A tests your five TODOs with hand-made inputs (no API key). Part B checks the real run saved by `python lab.py`.

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


def guarded(fn, *args):
    try:
        return fn(*args), None
    except Exception as exc:  # a TODO that crashes is reported as a failure, not a traceback
        return None, f"{type(exc).__name__}: {exc}"


def errors_for(role, data):
    return core.validate(data, lab.CONTRACTS[role])


Q = desk.QUESTIONS["Q4"]
FOUND = {"findings": [{"doc_id": "DOC-010", "fact": "NorthGrid revenue FY2022", "value": "$412M"}], "rumours": [],
         "needs_calculation": True, "calc_request": "CAGR from 412 to 710 over 3 years"}
GOOD_ANALYST = {"results": [{"label": "CAGR", "value": "19.9%", "inputs": "412, 710, 3"}]}
GOOD_CHECKS = {"checks": [{"doc_id": "DOC-010", "claim": "revenue was 412", "verdict": "SUPPORTED", "detail": "matches"}]}

print("PART A - your TODOs, tested with hand-made inputs (no API key)\n")
print("TODO 1 - contracts")
check(not errors_for("analyst", GOOD_ANALYST), "analyst: a correct hand-off is accepted", "; ".join(errors_for("analyst", GOOD_ANALYST)))
check(errors_for("analyst", {"results": [{"label": "CAGR", "value": "19.9%"}]}), "analyst: a hand-off missing 'inputs' is rejected")
check(errors_for("analyst", {**GOOD_ANALYST, "opinion": "looks fine"}), "analyst: an extra field is rejected")
check(not errors_for("fact_checker", GOOD_CHECKS), "fact_checker: a correct hand-off is accepted", "; ".join(errors_for("fact_checker", GOOD_CHECKS)))
check(errors_for("fact_checker", {"checks": [{**GOOD_CHECKS["checks"][0], "verdict": "MAYBE"}]}), "fact_checker: a verdict outside the three allowed values is rejected")
check(errors_for("fact_checker", {"checks": [{**GOOD_CHECKS["checks"][0], "doc_id": "DOC-999"}]}), "fact_checker: a document that does not exist is rejected")

print("\nTODO 2 - briefs")
briefs = {"searcher": guarded(lab.searcher_brief, Q), "analyst": guarded(lab.analyst_brief, FOUND), "fact_checker": guarded(lab.fact_check_brief, FOUND["findings"][0])}
for role, (text, err) in briefs.items():
    leaked = text is not None and any(m.lower() in text.lower() for m in desk.LEAK_MARKERS)
    check(text and not leaked, f"{role} brief does not carry the confidential note", err or "the brief still contains the client note")
check(briefs["searcher"][0] and Q["text"] in briefs["searcher"][0], "searcher brief contains the question")
check(briefs["analyst"][0] and FOUND["calc_request"] in briefs["analyst"][0] and "$412M" in briefs["analyst"][0], "analyst brief contains the calculation request and the findings")
check(briefs["fact_checker"][0] and "DOC-010" in briefs["fact_checker"][0] and "NorthGrid revenue FY2022" in briefs["fact_checker"][0], "fact_checker brief contains the document id and the claim")

print("\nTODO 3 - failure policy")
GOOD_SEARCH = json.dumps({"findings": [], "rumours": [], "needs_calculation": False, "calc_request": ""})


def scripted(replies):
    calls = []

    def caller(role, brief):
        calls.append(brief)
        reply = replies[min(len(calls) - 1, len(replies) - 1)]
        if isinstance(reply, Exception):
            raise reply
        return reply
    return caller, calls


def drill(replies, brief="Question: test"):
    caller, calls = scripted(replies)
    try:
        data, reworks = core.call_with_contract("analyst", brief, caller, lab.CONTRACTS, lab.POLICY)
        return ("ok", reworks, calls)
    except Exception as exc:
        return (type(exc).__name__, None, calls)


good = json.dumps(GOOD_ANALYST)
outcome, reworks, calls = drill(["not json at all", good])
check(outcome == "ok" and reworks == 1 and len(calls) == 2 and "rejected" in calls[1], "a malformed hand-off is re-asked once, and the re-ask quotes the problem",
      f"outcome={outcome}, calls={len(calls)}")
outcome, _, calls = drill(["not json at all"])
check(outcome == "HandoffError" and len(calls) == 2, "a hand-off that stays malformed stops after exactly one re-ask (2 calls in total)", f"outcome={outcome}, calls={len(calls)}")
outcome, _, calls = drill([core.SubagentError("down"), core.SubagentError("down"), good])
check(outcome == "ok" and len(calls) == 3, "a crashed specialist is retried and recovers (3 calls)", f"outcome={outcome}, calls={len(calls)}")
outcome, _, calls = drill([core.SubagentError("down")])
check(outcome == "SubagentError" and len(calls) == 3, "a specialist that keeps crashing stops after exactly two retries (3 calls in total)", f"outcome={outcome}, calls={len(calls)}")
outcome, _, calls = drill([good], brief=f"Question: x\n{desk.PRIVATE_NOTE}")
check(outcome == "LeakError" and not calls, "a brief that contains the client note is blocked before any call is made", f"outcome={outcome}, calls={len(calls)}")
caller, calls = scripted([GOOD_SEARCH])
report, _, notes = core.orchestrate(Q, lab.HOOKS, caller)
check(notes["status"] == "partial" and "ESCALATION" in report, "when the searcher finds nothing the desk returns an honest partial report", f"status={notes['status']}")

print("\nTODO 4 - escalation in code")
conflict_checks = [{"doc_id": "DOC-004", "claim": "a", "verdict": "CONFLICT", "detail": "b"}]
no_conflict = [{"doc_id": "DOC-004", "claim": "a", "verdict": "SUPPORTED", "detail": "b"}]
check(guarded(lab.has_conflict, conflict_checks)[0] is True and guarded(lab.has_conflict, no_conflict)[0] is False, "a CONFLICT verdict is detected, and a clean set is not flagged")
check(guarded(lab.must_re_ask_writer, "ANSWER: A\nESCALATION: none", True)[0] is True, "a conflict whose report says 'ESCALATION: none' makes the desk re-ask the writer")
check(guarded(lab.must_re_ask_writer, "ANSWER: A\nESCALATION: two reports disagree; the analyst lead decides", True)[0] is False, "a conflict whose report escalates is left alone")
check(guarded(lab.must_re_ask_writer, "ANSWER: A\nESCALATION: none", False)[0] is False, "no conflict means no re-ask")

print("\nPART B - the real run (needs `python lab.py` with a key; tolerant of normal model variation)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in saved["rows"]}
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    check(all(r["report"].strip() for r in rows.values()), "every question produced a report", "an empty report usually means TODO 5 still returns an empty string")
    check(sum(r["leaks"] for r in rows.values()) == 0, "the confidential note reached no specialist and no report")
    check(rows["Q2"]["checks"].get("escalation") is True, "Q2: the conflict between two reliable reports was escalated, not silently resolved")
    check(rows["Q4"]["checks"].get("fact:cagr") is True, "Q4: the growth rate 19.9% is in the report")
    check(rows["Q5"]["checks"].get("fact:partner") is True and rows["Q5"]["checks"].get("qualified:Hartwell") is True,
          "Q5: the real partner is named and the rumour (if mentioned) is labelled as unconfirmed")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
