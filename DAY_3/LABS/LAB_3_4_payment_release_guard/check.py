"""check.py - Part A tests your five TODOs with no API key and no model. Part B checks the real run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import asyncio
import copy
import inspect
import json
import sys

import lab
import release_core as core

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def guarded(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # a TODO that crashes is reported as a failure, not a traceback
        return f"{type(exc).__name__}: {exc}"


policy, neutral = core.Policy(), core.NEUTRAL
CASES = core.CASES
base = CASES["PAY-1001"]


def gate(case, proposal=neutral):
    return core.evaluate(case, proposal, policy, lab.HOOKS)


print("PART A - your five TODOs, tested with no API key and no model\n")
print("TODO 1 - the policy gate")
wrong = [cid for cid, c in CASES.items() if gate(c)["decision"] != c["expected"]]
check(not wrong, "the gate reaches the expected outcome on all 12 labelled payments", f"wrong on: {', '.join(wrong)}")
flags = guarded(lab.payment_flags, CASES["PAY-1009"], policy)
check(isinstance(flags, list) and "BANK_MISMATCH" in flags and "HV_DUAL_CONTROL" in flags, "payment_flags finds the bank mismatch and the dual-control amount on PAY-1009", f"you returned {flags!r}")
check(gate(CASES["PAY-1009"], {"decision": "release", "confidence": 0.99, "rationale": ""})["decision"] == "escalate", "a confident 'release' (0.99) cannot remove the hard flags of PAY-1009")
check("NO_MODEL_PROPOSAL" in gate(base, None)["hard_flags"], "no proposal from the model means a human decides (silence is never yes)")
check(gate(base, {"decision": "reject", "confidence": 0.9, "rationale": ""})["decision"] == "escalate", "a model that says reject sends the case to a human instead of silently rejecting it")
check(guarded(lab.decide, ["DUPLICATE_INVOICE"], ["BANK_MISMATCH"], 5, 3) == "reject" and guarded(lab.decide, [], ["BANK_MISMATCH"], 0, 3) == "escalate"
      and guarded(lab.decide, [], [], 3, 3) == "escalate" and guarded(lab.decide, [], [], 2, 3) == "auto-release",
      "decide: a reject flag wins, then any hard flag or a score at the limit escalates, otherwise auto-release")

print("\nTODO 2 - the human review")
case = copy.deepcopy(CASES["PAY-1011"])
reviewer = core.REVIEWERS["alice.moreno"]
good = {"reviewer": "alice.moreno", "decision": "approve", "reason": "Verified with the supplier.", "evidence_digest": core.digest(case)}
check(guarded(lab.decision_problem, case, good, reviewer) is None, "a proper decision is accepted")
mine = copy.deepcopy(case)
mine["payment"]["requested_by"] = "alice.moreno"
check(guarded(lab.decision_problem, mine, good, reviewer), "four-eyes: a reviewer cannot approve a payment they requested")
small = {"limit": 1000.0}
check(guarded(lab.decision_problem, case, good, small), "a reviewer whose limit is below the amount is refused")
check(guarded(lab.decision_problem, case, {**good, "evidence_digest": "0" * 16}, reviewer), "a decision made on stale evidence is refused")
check(guarded(lab.decision_problem, case, {**good, "reason": "  "}, reviewer), "a decision with an empty reason is refused")
check(guarded(lab.decision_problem, case, {**good, "decision": "maybe"}, reviewer), "a decision other than approve or reject is refused")

print("\nTODO 3 - the payment key")


def service(execute=True):
    svc = core.ReleaseService(lab.HOOKS)
    for cid in CASES:
        svc.process(cid, neutral, execute=execute)
    return svc


def approve(svc, cid):
    try:
        svc.human_decision(cid, core.scripted_decision(svc, cid))
    except Exception:
        pass  # the starter's gate may not have paused this case; the checks below then fail on their own


svc = service()
approve(svc, "PAY-1006")
guarded(svc.resume, "PAY-1006")
guarded(svc.resume, "PAY-1006")
check(svc.payment_count() == sum(1 for s in svc.states().values() if s == "EXECUTED") and svc.states().get("PAY-1006") == "EXECUTED",
      "resuming an approved payment twice moves money once", f"payments {svc.payment_count()}, state {svc.states().get('PAY-1006')}")
svc = core.ReleaseService(lab.HOOKS)
svc.process("PAY-1006", neutral)
approve(svc, "PAY-1006")
try:
    svc.resume("PAY-1006", crash_after_payment=True)
except Exception:
    pass
guarded(svc.resume, "PAY-1006")
check(svc.payment_count() == 1, "a crash right after the bank paid, then a retry, still pays once", f"payments {svc.payment_count()}")

print("\nTODO 4 - the release hook")
svc = service(execute=False)
approve(svc, "PAY-1006")
approve(svc, "PAY-1004")
before = lab.make_before_release(svc)
for label, tool_input, allowed in [("a clean case the gate approved", {"case_id": "PAY-1001"}, True), ("a case a human approved", {"case_id": "PAY-1006"}, True),
                                   ("a case a human rejected", {"case_id": "PAY-1004"}, False), ("a case still waiting for a human", {"case_id": "PAY-1009"}, False),
                                   ("a case that never went through the gate", {"case_id": "PAY-9999"}, False), ("malformed tool input (fails closed)", {}, False)]:
    out = guarded(lambda ti: asyncio.run(before({"tool_input": ti}, "t1", None)), tool_input)
    denied = isinstance(out, dict) and out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    check(isinstance(out, dict) and denied != allowed, f"{label}: {'allowed' if allowed else 'denied'}", f"hook returned {out!r}")

print("\nTODO 5 - the Claude call")
check("NotImplementedError" not in inspect.getsource(lab.ask), "the ask function makes a Claude API call (the placeholder line is gone)", "replace the raise NotImplementedError line in TODO 5")

print("\nPART B - the real run (needs `python lab.py` with a key; tolerant of normal model variation)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    check(saved["usable_proposals"] >= 11, "Claude returned a usable proposal for at least 11 of the 12 payments", f"usable: {saved['usable_proposals']}")
    check(not saved["unsafe_auto_releases"], "no risky payment was auto-released, whatever the model said", f"unsafe: {saved['unsafe_auto_releases']}")
    check(saved["correct"] >= 11, "the gate reached the expected outcome on at least 11 of 12 payments", f"correct: {saved['correct']}")
    check(saved["payments"] == saved["executed"] and not saved["completeness_problems"] and saved["audit_ok"],
          "every payment has one executed case, a gate decision (and a human approval where needed), and the audit chain is intact",
          f"payments {saved['payments']}, executed {saved['executed']}, problems {saved['completeness_problems']}")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
