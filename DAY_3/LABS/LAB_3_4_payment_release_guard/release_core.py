"""release_core.py - the payment-release engine behind Demo 3D and Lab 3.4. DO NOT EDIT. No model calls in this file.

A payment moves through these states:
  AUTO_APPROVED      the gate found nothing to check, so the payment can be released
  AWAITING_APPROVAL  the gate sent the payment to a reviewer
  APPROVED           the reviewer approved it
  RELEASED           the money has moved
The pieces you write in lab.py (the gate rules, the reviewer choice and the release hook) are plugged in through `hooks`.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


CASES = {c["case_id"]: c for c in load("cases.json")["cases"]}
POLICY = load("policy.json")
REVIEWERS = load("human_reviews.json")["reviewers"]
APPROVALS = load("human_reviews.json")["approvals"]  # scripted: who approves each payment, and why
NOTE_SYSTEM = ("You help an accounts-payable reviewer. Given the evidence for one supplier payment, "
               "write a note of two plain sentences: what is being paid, and anything the reviewer should know.")


def evidence(case):
    """What the model and the reviewer see: everything except the answer key."""
    return {key: value for key, value in case.items() if key != "expected"}


def template_note(case):
    """The note used when no model is called (replay mode and the offline checks)."""
    payee, payment = case["payee"], case["payment"]
    return (f"Pay {payment['amount']:,.2f} {payment['currency']} to {payee['name']} (vendor for {payee['vendor_age_days']} days) "
            f"against invoice {payment['invoice_number']}. Invoice, purchase order and goods receipt all match.")


class WorkflowError(Exception):
    pass


class ReleaseService:
    """The gate, the approval step, the payment and the audit trail behind one small API."""

    def __init__(self, hooks):
        self.hooks, self.rows, self.audit, self.paid = hooks, {}, [], {}

    def log(self, case_id, actor, action, why=""):
        self.audit.append({"case_id": case_id, "actor": actor, "action": action, "why": why})

    def process(self, case_id, note):
        """Run one payment through the gate. Returns AUTO_APPROVED or AWAITING_APPROVAL."""
        case = CASES[case_id]
        flags = self.hooks["payment_flags"](case, POLICY)
        outcome = self.hooks["decide"](flags)
        state = "AUTO_APPROVED" if outcome == "auto-release" else "AWAITING_APPROVAL"
        reviewer = self.hooks["choose_reviewer"](case, REVIEWERS) if state == "AWAITING_APPROVAL" else None
        self.rows[case_id] = {"state": state, "outcome": outcome, "flags": flags, "note": note, "reviewer": reviewer}
        self.log(case_id, "gate", "gate_decision", f"{outcome}: " + (", ".join(flags) if flags else "no rules triggered"))
        return state

    def review_packet(self, case_id):
        """What the reviewer sees for a payment that is waiting."""
        row, payment = self.rows[case_id], CASES[case_id]["payment"]
        return {"question": f"Release {payment['amount']:,.2f} {payment['currency']} to {CASES[case_id]['payee']['name']}?",
                "reviewer": row["reviewer"], "reasons": row["flags"], "note": row["note"]}

    def approve(self, case_id, reviewer, reason):
        """Record the reviewer's approval."""
        if self.rows[case_id]["state"] != "AWAITING_APPROVAL":
            raise WorkflowError(f"{case_id} is {self.rows[case_id]['state']}, not awaiting approval")
        self.rows[case_id].update(state="APPROVED", approved_by=reviewer)
        self.log(case_id, f"reviewer:{reviewer}", "approved", reason)

    def authorisation(self, case_id):
        """The release hook asks this: may the money move for this payment? Returns (allowed, why)."""
        row = self.rows.get(case_id)
        if row and row["state"] in ("AUTO_APPROVED", "APPROVED"):
            return True, f"state {row['state']}"
        return False, f"state {row['state'] if row else 'unknown payment'}"

    def release(self, case_id):
        """Pay one payment. Safe to call twice: the second call changes nothing."""
        allowed, why = self.authorisation(case_id)
        if self.rows.get(case_id, {}).get("state") == "RELEASED":
            return self.paid[case_id]
        if not allowed:
            raise WorkflowError(f"cannot release {case_id}: {why}")
        self.paid[case_id] = CASES[case_id]["payment"]["amount"]
        self.rows[case_id]["state"] = "RELEASED"
        self.log(case_id, "bank", "released", f"{self.paid[case_id]:,.2f}")
        return self.paid[case_id]

    def states(self):
        return {case_id: row["state"] for case_id, row in self.rows.items()}

    def total_paid(self):
        return sum(self.paid.values())

    def audit_problems(self):
        """Every released payment needs a gate decision in the trail, and a reviewer approval when the gate asked for one."""
        problems = []
        for case_id in self.paid:
            actions = [row["action"] for row in self.audit if row["case_id"] == case_id]
            if "gate_decision" not in actions:
                problems.append(f"{case_id}: no gate decision in the audit trail")
            if self.rows[case_id]["reviewer"] and "approved" not in actions:
                problems.append(f"{case_id}: no reviewer approval in the audit trail")
        return problems
