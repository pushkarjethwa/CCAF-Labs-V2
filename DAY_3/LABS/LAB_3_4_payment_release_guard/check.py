"""check.py - Part A tests your four TODOs with no API key and no model. Part B checks the real run saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import asyncio
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


CASES, policy = core.CASES, core.POLICY

print("PART A - your four TODOs, tested with no API key and no model\n")
print("TODO 1 - the release gate")
flags = {cid: guarded(lab.payment_flags, case, policy) for cid, case in CASES.items()}
check(flags["PAY-1004"] == ["AMOUNT_NEEDS_APPROVAL"], "payment_flags: PAY-1004 (182,000) is flagged AMOUNT_NEEDS_APPROVAL", f"you returned {flags['PAY-1004']!r}")
check(flags["PAY-1005"] == ["AMOUNT_NEEDS_APPROVAL", "OVER_APPROVER_LIMIT"], "payment_flags: PAY-1005 (64,000, approver limit 50,000) gets two flags", f"you returned {flags['PAY-1005']!r}")
check(flags["PAY-1006"] == ["NEW_VENDOR"], "payment_flags: PAY-1006 (a 20-day-old vendor) is flagged NEW_VENDOR", f"you returned {flags['PAY-1006']!r}")
check(guarded(lab.decide, []) == "auto-release" and guarded(lab.decide, ["NEW_VENDOR"]) == "needs-approval",
      "decide: no flags means auto-release, any flag means needs-approval")

print("\nTODO 2 - the reviewer")
for cid, name in (("PAY-1006", "carol.diaz"), ("PAY-1005", "alice.moreno"), ("PAY-1004", "bob.chen")):
    amount = CASES[cid]["payment"]["amount"]
    check(guarded(lab.choose_reviewer, CASES[cid], core.REVIEWERS) == name, f"{cid} ({amount:,.0f}) goes to {name}, the lowest limit that covers it")

print("\nTODO 3 - the release hook")
svc = core.ReleaseService(lab.HOOKS)
for cid in CASES:
    svc.process(cid, core.template_note(CASES[cid]))
for cid, state in svc.states().items():
    if state == "AWAITING_APPROVAL":
        svc.approve(cid, core.APPROVALS[cid]["reviewer"], core.APPROVALS[cid]["reason"])
before = guarded(lab.make_before_release, svc)
for cid in ("PAY-1001", "PAY-1004"):
    out = guarded(lambda c: asyncio.run(before({"tool_input": {"case_id": c}}, "t1", None)), cid)
    verdict = out.get("hookSpecificOutput", {}) if isinstance(out, dict) else {}
    kind = "a payment the gate approved" if cid == "PAY-1001" else "a payment a reviewer approved"
    check(verdict.get("permissionDecision") == "allow" and verdict.get("permissionDecisionReason"), f"{kind} ({cid}): the hook allows the release tool and gives a reason", f"hook returned {out!r}")

print("\nTODO 4 - the Claude call")
check("NotImplementedError" not in inspect.getsource(lab.ask), "the ask function makes a Claude API call (the placeholder line is gone)", "replace the raise NotImplementedError line in TODO 4")

print("\nPART B - the real run (needs `python lab.py` with a key)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    total = sum(c["payment"]["amount"] for c in CASES.values())
    check(saved.get("fingerprint") == lab.source_fingerprint(), "the saved run is from your CURRENT lab.py", "you edited lab.py after the last run - run `python lab.py` again")
    check(saved["notes"] == len(CASES), "Claude wrote a note for every payment", f"notes: {saved['notes']}")
    check(saved["correct"] == len(CASES), "the gate reached the expected outcome on all 6 payments", f"correct: {saved['correct']}")
    check(saved["released"] == len(CASES) and abs(saved["total_paid"] - total) < 0.01 and saved["hook_allowed"] == len(CASES),
          "all 6 payments were allowed by the hook and released, for the full amount", f"released {saved['released']}, total {saved['total_paid']}")
    check(not saved["audit_problems"], "every released payment has a gate decision (and a reviewer approval where needed) in the audit trail", f"{saved['audit_problems']}")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
