"""Lab 3.4 - Guard supplier-payment release with code, not prompts (continues Demo 3D: same cases, policy, reviewers and engine).

An agent may propose "release", "hold" or "reject" for a supplier payment, but a model's confidence is not a control.
Demo 3D put the control in code: a policy gate, a human review that really pauses the payment, an idempotent bank call,
and an Agent SDK hook that blocks the release tool. You write the five pieces here:

  TODO 1  the policy gate     which flags force a human, and the decision rule
  TODO 2  the human review    which reviewer decisions must be refused
  TODO 3  the payment key     so resuming twice (or after a crash) pays once
  TODO 4  the release hook    the Agent SDK PreToolUse guard that denies a release that is not authorised
  TODO 5  your Claude call    the model's proposal (the only model call in this lab)

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key and no model.
  python lab.py      asks Claude for 12 proposals, runs the gate and the workflow (needs ANTHROPIC_API_KEY); then python check.py again
The engine (policy, workflow, payments, audit) is in release_core.py. You do not need to read it.
"""
import hashlib
import json
import pathlib

import release_core as core
from claude_client import MODEL_BALANCED, get_client, text_of


# ======================================================================================
# TODO 1 of 5 - THE POLICY GATE
# Three small functions. The engine calls them for every payment.
#   payment_flags(case, policy)   hard flags from the evidence. A hard flag always forces a human.
#       BANK_MISMATCH       the bank account on the invoice differs from the one on file
#       OVER_APPROVER_LIMIT the payment is larger than the approver's limit
#       HV_DUAL_CONTROL     the payment is at or above policy.cfg["amount_dual_control"]
#   proposal_flags(proposal)      what the model said. proposal is None when the model gave nothing usable.
#       NO_MODEL_PROPOSAL (silence never means yes) or MODEL_RECOMMENDS_REJECT (a human decides, not a silent reject)
#   decide(...)                   reject if any reject flag; escalate if any hard flag or score >= escalate_at; otherwise auto-release
# ======================================================================================
def payment_flags(case, policy):
    return []  # replace these lines in TODO 1


def proposal_flags(proposal):
    return []  # replace these lines in TODO 1


def decide(reject_flags, hard_flags, score, escalate_at):
    return "auto-release"  # replace these lines in TODO 1


# ======================================================================================
# TODO 2 of 5 - THE HUMAN REVIEW: which decisions must be refused?
# `decision` is what the reviewer sent: {"reviewer", "decision", "reason", "evidence_digest"}. `reviewer` is their record ({"limit": ...}).
# Return a message saying why the decision is refused, or None when it is fine. Check, in this order:
#   four-eyes   the reviewer is the person who requested the payment
#   limit       the reviewer's limit is below the payment amount
#   stale       decision["evidence_digest"] is not core.digest(case): the evidence changed after the reviewer looked
#   invalid     the decision is not "approve" or "reject", or the reason is empty
# ======================================================================================
def decision_problem(case, decision, reviewer):
    return None  # replace these lines in TODO 2


# ======================================================================================
# TODO 3 of 5 - THE PAYMENT KEY: pay once, however many times you resume
# The bank remembers a key. The same key twice moves money once. Build a key that is the same for the same case and the same evidence.
# Return None for "no key" (what the starter does, and what pays twice after a crash).
# ======================================================================================
def payment_key(case_id, digest):
    return None  # replace this line in TODO 3


# ======================================================================================
# TODO 4 of 5 - THE RELEASE HOOK: an Agent SDK PreToolUse guard
# The hook runs BEFORE the release_payment tool. `input_data["tool_input"]["case_id"]` names the case.
# svc.authorisation(case_id) returns (allowed, why). Return {} to allow, or a "deny" decision to block the tool call.
# It must fail closed: if the guard itself errors, or the input is malformed, refuse.
# ======================================================================================
def make_before_release(svc):
    async def before_release(input_data, tool_use_id, context):
        return {}  # replace these lines in TODO 4
    return before_release


# ======================================================================================
# TODO 5 of 5 - your Claude API call: the model's proposal for one payment
# `text` is the evidence as JSON. core.PROPOSAL_SYSTEM tells the model to reply with a JSON proposal. Return the answer text.
# ======================================================================================
def ask(text):
    raise NotImplementedError("TODO 5 is not done yet")  # replace this line in TODO 5


# ======================================================================================
# RUNNING THE DESK - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
HOOKS = {"payment_flags": payment_flags, "proposal_flags": proposal_flags, "decide": decide,
         "decision_problem": decision_problem, "payment_key": payment_key}


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def run_all(ask_fn=None):
    ask_fn, proposals = ask_fn or ask, {}
    for cid, case in core.CASES.items():
        proposals[cid] = core.propose(case, ask_fn)
        said = proposals[cid]
        print(f"{cid}: model says {said['decision'] if said else 'NO VALID PROPOSAL':<8} confidence {said['confidence'] if said else '-'}")
    svc = core.ReleaseService(HOOKS)
    for cid in core.CASES:
        svc.process(cid, proposals[cid])
    for cid, state in svc.states().items():  # scripted reviewers answer every escalated case they have a decision for
        if state == "AWAITING_HUMAN" and cid in core.SCRIPTED_DECISIONS:
            try:
                svc.human_decision(cid, core.scripted_decision(svc, cid))
            except core.WorkflowError as exc:
                print(f"{cid}: human decision refused - {exc}")
    for cid, state in svc.states().items():
        if state == "HUMAN_APPROVED":
            svc.resume(cid)
    gate = {cid: core.evaluate(case, proposals[cid], svc.policy, HOOKS)["decision"] for cid, case in core.CASES.items()}
    unsafe = [cid for cid, case in core.CASES.items() if gate[cid] == "auto-release" and case["expected"] != "auto-release"]
    states = svc.states()
    row = {"fingerprint": source_fingerprint(), "usable_proposals": sum(p is not None for p in proposals.values()),
           "gate": gate, "correct": sum(gate[c] == core.CASES[c]["expected"] for c in core.CASES), "unsafe_auto_releases": unsafe,
           "executed": sum(s == "EXECUTED" for s in states.values()), "payments": svc.payment_count(),
           "completeness_problems": svc.completeness_problems(), "audit_ok": svc.verify_audit()[0]}
    print(f"\ngate correct {row['correct']}/12 | unsafe auto-releases {len(unsafe)} | payments {row['payments']} for {row['executed']} executed cases "
          f"| audit chain intact: {row['audit_ok']}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(row, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    run_all()
