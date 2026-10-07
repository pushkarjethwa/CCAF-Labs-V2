"""check.py - Part A tests your code on the four cases (no API key). Part B checks the live run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import inspect
import json
import sys

import lab
import warranty_core as core

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def guarded(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # a TODO that crashes is reported as a failure, not a traceback
        return f"{type(exc).__name__}: {exc}"


class Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def canned_model(case):
    """A tiny stand-in for Claude that follows the happy path, so TODO 4 can be tested with no key."""
    form, turn = case["form"], [0]

    def model(messages):
        turn[0] += 1
        last = json.loads(messages[-1]["content"][-1]["content"]) if len(messages) > 1 else {"tool": None}
        data, name = last.get("data", {}), last["tool"]
        if name is None:
            call = ("lookup_product_registration", {"serial": form["serial"]})
        elif name == "lookup_product_registration":
            call = ("check_warranty_terms", {"serial": form["serial"], "issue_type": form["issue_type"]})
        elif name == "check_warranty_terms" and data["covered"]:
            call = ("create_claim", {"serial": form["serial"], "issue_type": form["issue_type"], "customer_id": form["customer_id"]})
        elif name == "check_warranty_terms":
            call = ("submit_decision", {"decision": "denied", "reason": data["reason"]})
        elif name == "create_claim":
            call = ("schedule_pickup", {"claim_number": data["claim_number"], "preferred_date": form["preferred_date"], "zone": form["zone"]})
        else:
            call = ("submit_decision", {"decision": "approved", "reason": "covered", "claim_number": data["claim_number"], "pickup_id": data["pickup_id"]})
        return Block(content=[Block(type="tool_use", id=f"t{turn[0]}", name=call[0], input=call[1])])

    return model


CASES = core.CASES["cases"]
print("PART A - your code, tested with no model and no API key\n")

print("TODO 1 - run_tool (the structured envelope)")
got = guarded(lab.run_tool, "lookup_product_registration", {"serial": "HX20481977"})
check(isinstance(got, dict) and got.get("tool") == "lookup_product_registration" and got.get("ok") is True,
      "the result has tool = the tool name and ok = True", f"you returned {got!r}")
check(isinstance(got, dict) and isinstance(got.get("data"), dict) and got["data"].get("plan") == "BASIC",
      "the data key holds what the tool returned (the registration for HX20481977)", f"you returned {got!r}")

print("\nTODO 2 - decide")
covered = {"covered": True, "rule_id": "R-BASIC-DEFECT", "reason": "covered until 2027-02-10"}
excluded = {"covered": False, "rule_id": "R-EXPIRED", "reason": "the plan expired"}
got = guarded(lab.decide, covered)
check(isinstance(got, dict) and got.get("decision") == "approved", "covered terms give the decision approved", f"you returned {got!r}")
got = guarded(lab.decide, excluded)
check(isinstance(got, dict) and got.get("decision") == "denied", "terms that are not covered give the decision denied", f"you returned {got!r}")
check(isinstance(got, dict) and got.get("rule_id") == "R-EXPIRED" and got.get("reason") == "the plan expired",
      "the rule_id and the reason are copied from the terms", f"you returned {got!r}")

print("\nTODO 1 and 2 together - the fixed pipeline on the four cases")
for case in CASES:
    row = guarded(core.run_pipeline, lab.HOOKS, case)
    ok = isinstance(row, dict) and row["verified"] and row["decision"]["decision"] == case["expected"]
    check(ok, f"{case['id']}: the decision is {case['expected']} and matches the tool results", f"result: {row}")

print("\nTODO 3 - the Claude call")
check("NotImplementedError" not in inspect.getsource(lab.ask), "the ask function makes a Claude API call (the placeholder line is gone)", "replace the raise NotImplementedError line in TODO 3")

print("\nTODO 4 - the agent loop (driven here by a tiny stand-in for Claude)")
for case in CASES:
    row = guarded(lab.run_agent, case, canned_model(case))
    ok = isinstance(row, dict) and row["verified"] and row["decision"]["decision"] == case["expected"]
    check(ok, f"{case['id']}: the loop ran the tools, submitted the decision and stopped ({case['expected']})", f"result: {row}")
row = guarded(lab.run_agent, CASES[0], canned_model(CASES[0]))
check(isinstance(row, dict) and row["tools"] == ["lookup_product_registration", "check_warranty_terms", "create_claim", "schedule_pickup", "submit_decision"]
      and row["turns"] == 5, "C01 used the five tools in order, one per turn, and finished in 5 turns", f"result: {row}")

print("\nPART B - the live agent (needs `python lab.py` with a key; tolerant of normal model variation)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    rows = {r["case"]: r for r in saved["rows"]}
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    for case in CASES:
        row = rows.get(case["id"], {})
        decision = (row.get("decision") or {}).get("decision")
        check(decision == case["expected"] and row.get("verified"), f"{case['id']}: Claude decided {case['expected']}, and the decision matches the tool results", f"got {decision}, verified={row.get('verified')}")
    check(all(r["turns"] <= core.MAX_TURNS for r in rows.values()), f"every run finished within the turn limit ({core.MAX_TURNS})")
    check("create_claim" not in rows.get("C04", {}).get("tools", ["create_claim"]), "C04 was denied without filing a claim")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
