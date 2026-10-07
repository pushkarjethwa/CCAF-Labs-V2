"""Lab 3.4 - Build a supplier-payment release gate with human approval (continues Demo 3D: same payments, rules, reviewers and engine).

Small payments are released automatically. Larger ones wait for a person to approve them, and only then is the money released.
You write four pieces here:

  TODO 1  the release gate     which rules send a payment to a reviewer, and the decision
  TODO 2  the reviewer         who approves a payment that is waiting
  TODO 3  the release hook     the Agent SDK PreToolUse hook that lets the release tool run for approved payments
  TODO 4  your Claude call     the model's short note for the reviewer (the only model call in this lab)

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key and no model.
  python lab.py      asks Claude for 6 notes, runs the payments through your gate, approval and hook (needs ANTHROPIC_API_KEY); then python check.py again
The engine (workflow, payment, audit trail) is in release_core.py. You do not need to read it.
"""
import asyncio
import hashlib
import json
import pathlib

import release_core as core
from claude_client import MODEL_BALANCED, get_client, text_of


# ======================================================================================
# TODO 1 of 4 - THE RELEASE GATE
# Two small functions. The engine calls them for every payment.
#   payment_flags(case, policy)   the rules that send a payment to a reviewer
#       AMOUNT_NEEDS_APPROVAL  the payment is at or above policy["approval_threshold"]
#       OVER_APPROVER_LIMIT    the payment is larger than the approver's limit
#       NEW_VENDOR             the vendor is younger than policy["new_vendor_days"] days
#   decide(flags)                 "needs-approval" when any rule is triggered, otherwise "auto-release"
# ======================================================================================
def payment_flags(case, policy):
    flags = []
    if case["payment"]["amount"] >= policy["approval_threshold"]:
        flags.append("AMOUNT_NEEDS_APPROVAL")
    if case["payment"]["amount"] > case["approver"]["limit"]:
        flags.append("OVER_APPROVER_LIMIT")
    if case["payee"]["vendor_age_days"] < policy["new_vendor_days"]:
        flags.append("NEW_VENDOR")
    return flags


def decide(flags):
    if flags:
        return "needs-approval"
    return "auto-release"


# ======================================================================================
# TODO 2 of 4 - THE REVIEWER
# `reviewers` maps a name to a record such as {"role": "AP analyst", "limit": 25000.0}.
# Return the name of the reviewer with the LOWEST limit that still covers the payment amount.
# ======================================================================================
def choose_reviewer(case, reviewers):
    amount = case["payment"]["amount"]
    for name, person in sorted(reviewers.items(), key=lambda item: item[1]["limit"]):
        if person["limit"] >= amount:
            return name


# ======================================================================================
# TODO 3 of 4 - THE RELEASE HOOK: an Agent SDK PreToolUse guard
# The hook runs BEFORE the release_payment tool. `input_data["tool_input"]["case_id"]` names the payment.
# svc.authorisation(case_id) returns (allowed, why). Return a PreToolUse decision: "allow" with the reason when allowed, otherwise "deny".
# ======================================================================================
def make_before_release(svc):
    async def before_release(input_data, tool_use_id, context):
        allowed, why = svc.authorisation(input_data["tool_input"]["case_id"])
        decision = "allow" if allowed else "deny"
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                       "permissionDecisionReason": why}}
    return before_release


# ======================================================================================
# TODO 4 of 4 - your Claude API call: the model's note for one payment
# `text` is the evidence as JSON. core.NOTE_SYSTEM tells the model to write two plain sentences. Return the answer text.
# ======================================================================================
def ask(text):
    response = get_client().messages.create(
        model=MODEL_BALANCED,
        max_tokens=1024,
        system=core.NOTE_SYSTEM,
        messages=[{"role": "user", "content": text}],
    )
    return text_of(response)


# ======================================================================================
# RUNNING THE DESK - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
HOOKS = {"payment_flags": payment_flags, "decide": decide, "choose_reviewer": choose_reviewer}


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def run_all(ask_fn=None):
    ask_fn, svc = ask_fn or ask, core.ReleaseService(HOOKS)
    for case_id, case in core.CASES.items():
        note = ask_fn(json.dumps(core.evidence(case), indent=1)).strip()
        print(f"{case_id}: {svc.process(case_id, note):<18} {note[:70]}")
    for case_id, state in svc.states().items():  # the scripted reviewers approve every payment that is waiting
        if state == "AWAITING_APPROVAL":
            packet = svc.review_packet(case_id)
            svc.approve(case_id, packet["reviewer"], core.APPROVALS[case_id]["reason"])
            print(f"{case_id}: {packet['question']} approved by {packet['reviewer']}")
    before_release, hook_allowed = make_before_release(svc), []
    for case_id in core.CASES:  # money moves only when the hook says allow
        verdict = asyncio.run(before_release({"tool_input": {"case_id": case_id}}, "t1", None))["hookSpecificOutput"]
        if verdict["permissionDecision"] == "allow":
            hook_allowed.append(case_id)
            svc.release(case_id)
    gate = {case_id: row["outcome"] for case_id, row in svc.rows.items()}
    row = {"fingerprint": source_fingerprint(), "notes": sum(bool(r["note"]) for r in svc.rows.values()), "gate": gate,
           "correct": sum(gate[c] == core.CASES[c]["expected"] for c in core.CASES), "hook_allowed": len(hook_allowed),
           "released": len(svc.paid), "total_paid": svc.total_paid(), "audit_problems": svc.audit_problems()}
    print(f"\ngate correct {row['correct']}/{len(core.CASES)} | released {row['released']} payments, total {row['total_paid']:,.2f}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(row, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    run_all()
