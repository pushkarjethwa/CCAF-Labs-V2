"""release_core.py - the payment-release engine behind Demo 3D, with the five pieces YOU write in lab.py plugged in. DO NOT EDIT.

No model calls anywhere in this file. You do not need to read it to finish the lab.

Four small pieces, in the order a payment meets them:

  1. POLICY GATE   a pure function: evidence + the model's proposal -> auto-release / escalate / reject.
                   Thresholds live in data/policy.json. The gate never reads the model's prose, and any error fails closed.
  2. WORKFLOW      a SQLite state machine. A paused case survives a restart; transitions are compare-and-set.
  3. PAYMENTS      a mock bank with idempotency keys: paying twice with the same key moves money once.
  4. AUDIT         a hash-chained log. Edit any row and verify() names the first broken link.

States:  AWAITING_HUMAN -> HUMAN_APPROVED | REJECTED_BY_HUMAN        (escalated cases)
         AUTO_APPROVED                                               (clean cases)
         REJECTED_BY_POLICY                                          (duplicate or blocked payee)
         HUMAN_APPROVED / AUTO_APPROVED -> EXECUTED                  (money moves only from these two)
"""
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

DATA = Path(__file__).parent / "data"
EVIDENCE_KEYS = ["payee", "payment", "invoice", "po", "goods_receipt", "bank_history", "approver"]  # never the answer key


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


CASES = {c["case_id"]: c for c in load("cases.json")["cases"]}
REVIEWS = load("human_reviews.json")
REVIEWERS, SCRIPTED_DECISIONS = REVIEWS["reviewers"], REVIEWS["decisions"]


def evidence(case: dict) -> dict:
    """What a reviewer (or the model) is allowed to see: the evidence, not the label."""
    return {key: case.get(key) for key in EVIDENCE_KEYS}


def digest(case: dict) -> str:
    return hashlib.sha256(json.dumps(evidence(case), sort_keys=True).encode()).hexdigest()[:16]


# ── 1. THE POLICY GATE ───────────────────────────────────────────────────────

class Policy:
    def __init__(self, raw: bytes | None = None):
        raw = raw if raw is not None else (DATA / "policy.json").read_bytes()
        self.cfg, self.sha = json.loads(raw), hashlib.sha256(raw).hexdigest()[:12]
        self.version = self.cfg["policy_version"]
        self.bypass = [re.compile(p, re.I) for p in self.cfg["bypass_patterns"]]
        self.urgency = [re.compile(p, re.I) for p in self.cfg["urgency_patterns"]]


def conflicts(case: dict, cfg: dict) -> list[str]:
    invoice, payment = case["invoice"], case["payment"]
    tolerance = max(cfg["conflict_abs_tolerance"], cfg["conflict_pct_tolerance"] * invoice["amount"])
    found = []
    if abs(payment["amount"] - invoice["amount"]) > 0.005:
        found.append(f"payment {payment['amount']:,.2f} != invoice {invoice['amount']:,.2f}")
    if case.get("po") and round(invoice["amount"] - case["po"]["open_amount"], 2) > tolerance:
        found.append(f"invoice exceeds PO open amount by {invoice['amount'] - case['po']['open_amount']:,.2f}")
    receipt = case.get("goods_receipt")
    if receipt and round(abs(invoice["amount"] - receipt["received_value"]), 2) > tolerance:
        found.append(f"invoice {invoice['amount']:,.2f} vs receipt {receipt['received_value']:,.2f}")
    return found


def evaluate(case: dict, proposal: dict | None, policy: Policy, hooks: dict) -> dict:
    """Pure function. Returns the decision plus every reason. Any surprise becomes an escalation, never an exception."""
    try:
        return _evaluate(case, proposal, policy, hooks)
    except Exception as exc:  # malformed evidence must never turn into an implicit 'allow'
        return {"decision": "escalate", "risk_score": 0, "points": {}, "hard_flags": [f"POLICY_ERROR:{type(exc).__name__}"],
                "reject_flags": [], "policy_version": policy.version, "policy_sha": policy.sha}


def _evaluate(case, proposal, policy, hooks):
    cfg = policy.cfg
    pts, payment, payee, bank = cfg["points"], case["payment"], case["payee"], case.get("bank_history") or {}
    points, hard, reject = {}, [], []

    if case["invoice"]["number"] in payee.get("prior_invoices", []):
        reject.append("DUPLICATE_INVOICE")
    if payee.get("status") == "blocked":
        reject.append("VENDOR_BLOCKED")

    missing = [key for key in cfg["required_evidence"] if not case.get(key)]
    if missing:
        hard.append("EVIDENCE_INCOMPLETE:" + ",".join(missing))
    else:
        hard += [f"EVIDENCE_CONFLICT:{c}" for c in conflicts(case, cfg)]
        hard += hooks["payment_flags"](case, policy)  # YOUR TODO: bank mismatch, over the approver's limit, dual control
    text = payment.get("request_text", "")
    if any(rule.search(text) for rule in policy.bypass):
        hard.append("BYPASS_LANGUAGE")
    hard += hooks["proposal_flags"](proposal)  # YOUR TODO: what to do with a missing or "reject" proposal

    if payment["amount"] >= cfg["amount_mid_tier"]:
        points["AMOUNT_TIER"] = pts["AMOUNT_TIER"]
    if bank.get("change_type") == "update" and bank.get("last_change_days_ago", 10 ** 6) < cfg["bank_change_window_days"]:
        points["BANK_CHANGE_RECENT"] = pts["BANK_CHANGE_RECENT"]
    if payee["vendor_age_days"] < 30:
        points["VENDOR_NEW"] = pts["VENDOR_NEW_LT30"]
    elif payee["vendor_age_days"] < 90:
        points["VENDOR_NEW"] = pts["VENDOR_NEW_LT90"]
    if any(rule.search(text) for rule in policy.urgency):
        points["URGENCY"] = pts["URGENCY"]
    # The model's confidence can only ADD doubt. It can never remove a flag or lower the score.
    if proposal is not None and (proposal.get("decision") == "hold" or proposal.get("confidence", 0) < cfg["model_doubt_below"]):
        points["MODEL_DOUBT"] = pts["MODEL_DOUBT"]

    score = sum(points.values())
    decision = hooks["decide"](reject, hard, score, cfg["escalate_at_points"])  # YOUR TODO: the decision rule
    return {"decision": decision, "risk_score": score, "points": points, "hard_flags": hard, "reject_flags": reject,
            "policy_version": policy.version, "policy_sha": policy.sha}


def reasons(gate: dict) -> str:
    parts = gate["reject_flags"] + gate["hard_flags"] + [f"{k}+{v}" for k, v in gate["points"].items()]
    return ", ".join(parts) if parts else "no signals"


# ── 2 + 3 + 4. WORKFLOW, PAYMENTS, AUDIT (one SQLite file) ───────────────────

class WorkflowError(Exception):
    pass


class ReleaseService:
    """Gate + durable workflow + payments + audit behind one small API. Open the same file again after a 'restart'."""

    def __init__(self, hooks: dict, path: str = ":memory:", policy: Policy | None = None):
        self.db, self.policy, self.hooks = sqlite3.connect(path), policy or Policy(), hooks
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS workflows(case_id TEXT PRIMARY KEY, state TEXT NOT NULL, digest TEXT NOT NULL,
                proposal TEXT, gate TEXT, review TEXT, human TEXT);
            CREATE TABLE IF NOT EXISTS payments(receipt_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, reference TEXT, amount REAL);
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, case_id TEXT, actor TEXT,
                action TEXT, why TEXT, data TEXT, prev_hash TEXT, hash TEXT);""")
        self.db.commit()

    # ---- audit -------------------------------------------------------------
    def log(self, case_id: str, actor: str, action: str, why: str = "", data: dict | None = None) -> None:
        last = self.db.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        prev = last[0] if last else "genesis"
        ts, blob = time.strftime("%Y-%m-%dT%H:%M:%S"), json.dumps(data or {}, sort_keys=True)
        link = hashlib.sha256("|".join([prev, ts, case_id, actor, action, why, blob]).encode()).hexdigest()
        self.db.execute("INSERT INTO audit(ts,case_id,actor,action,why,data,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?)",
                        (ts, case_id, actor, action, why, blob, prev, link))
        self.db.commit()

    def verify_audit(self) -> tuple[bool, int | None]:
        """Recompute every link. Returns (True, None) or (False, seq of the first broken row)."""
        prev = "genesis"
        for seq, ts, case_id, actor, action, why, blob, prev_hash, link in self.db.execute("SELECT * FROM audit ORDER BY seq"):
            expected = hashlib.sha256("|".join([prev, ts, case_id, actor, action, why, blob]).encode()).hexdigest()
            if prev_hash != prev or link != expected:
                return False, seq
            prev = link
        return True, None

    def actions(self, case_id: str) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT action FROM audit WHERE case_id=? ORDER BY seq", (case_id,))]

    # ---- workflow ----------------------------------------------------------
    def get(self, case_id: str) -> dict | None:
        row = self.db.execute("SELECT state,digest,proposal,gate,review,human FROM workflows WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            return None
        return {"state": row[0], "digest": row[1], "proposal": json.loads(row[2]) if row[2] else None, "gate": json.loads(row[3]),
                "review": json.loads(row[4]) if row[4] else None, "human": json.loads(row[5]) if row[5] else None}

    def _cas(self, case_id: str, expect: str, new: str, **columns) -> bool:
        """Compare-and-set: move the case only if it is still in the state we think it is in."""
        sets = ", ".join(["state=?"] + [f"{k}=?" for k in columns])
        cursor = self.db.execute(f"UPDATE workflows SET {sets} WHERE case_id=? AND state=?",
                                 [new, *(json.dumps(v) for v in columns.values()), case_id, expect])
        self.db.commit()
        return cursor.rowcount == 1

    def process(self, case_id: str, proposal: dict | None, execute: bool = True) -> str:
        """Gate one case. Idempotent: a case already in the workflow is returned untouched.
        execute=False leaves a clean case AUTO_APPROVED, waiting for a separate release step (used by the hooks stage)."""
        if (existing := self.get(case_id)):
            return existing["state"]
        case = CASES[case_id]
        self.log(case_id, "model", "proposal_recorded", (proposal or {}).get("rationale", "no valid proposal; failing closed"),
                 {"decision": (proposal or {}).get("decision"), "confidence": (proposal or {}).get("confidence")})
        gate = evaluate(case, proposal, self.policy, self.hooks)
        self.log(case_id, f"policy:{gate['policy_version']}", "gate_decision", reasons(gate),
                 {"decision": gate["decision"], "digest": digest(case), "risk_score": gate["risk_score"]})
        state = {"auto-release": "AUTO_APPROVED", "escalate": "AWAITING_HUMAN", "reject": "REJECTED_BY_POLICY"}[gate["decision"]]
        review = self._review_packet(case, proposal, gate) if state == "AWAITING_HUMAN" else None
        self.db.execute("INSERT INTO workflows(case_id,state,digest,proposal,gate,review) VALUES(?,?,?,?,?,?)",
                        (case_id, state, digest(case), json.dumps(proposal), json.dumps(gate), json.dumps(review)))
        self.db.commit()
        if state == "AWAITING_HUMAN":
            self.log(case_id, "system", "review_requested", review["question"])
        elif state == "AUTO_APPROVED" and execute:
            self.resume(case_id)
        return self.get(case_id)["state"]

    def _review_packet(self, case: dict, proposal: dict | None, gate: dict) -> dict:
        pay = case["payment"]
        return {"question": f"Release {pay['amount']:,.2f} {pay['currency']} to {case['payee']['name']}?",
                "amount": pay["amount"], "reasons": gate["reject_flags"] + gate["hard_flags"] + list(gate["points"]),
                "model_said": proposal and {"decision": proposal["decision"], "confidence": proposal["confidence"]},
                "evidence": evidence(case), "evidence_digest": digest(case)}

    def human_decision(self, case_id: str, decision: dict) -> str:
        """Record a reviewer's decision, after the checks a real approval process would make."""
        row, case = self.get(case_id), CASES.get(case_id)
        if row is None:
            raise WorkflowError("unknown case")
        if row["human"]:
            if (row["human"]["reviewer"], row["human"]["decision"]) == (decision.get("reviewer"), decision.get("decision")):
                return "already_applied"
            raise WorkflowError(f"case already decided as {row['human']['decision']} by {row['human']['reviewer']}")
        if row["state"] != "AWAITING_HUMAN":
            raise WorkflowError(f"case is {row['state']}, not awaiting a human")
        reviewer = REVIEWERS.get(decision.get("reviewer"))
        if reviewer is None:
            raise WorkflowError(f"unknown reviewer {decision.get('reviewer')!r}")
        problem = self.hooks["decision_problem"](case, decision, reviewer)  # YOUR TODO: four-eyes, limit, stale evidence, valid decision
        if problem:
            raise WorkflowError(problem)
        new_state = "HUMAN_APPROVED" if decision["decision"] == "approve" else "REJECTED_BY_HUMAN"
        if not self._cas(case_id, "AWAITING_HUMAN", new_state, human=decision):
            raise WorkflowError("lost a race: the state changed concurrently")
        self.log(case_id, f"human:{decision['reviewer']}", "human_decision", decision["reason"], {"decision": decision["decision"]})
        return new_state

    def pay(self, case_id: str, amount: float, *, keyed: bool = True) -> dict:
        """The mock bank. With a key, the same request twice moves money once."""
        key = self.hooks["payment_key"](case_id, self.get(case_id)["digest"]) if keyed else None  # YOUR TODO: the idempotency key
        if key and (found := self.db.execute("SELECT receipt_id, amount FROM payments WHERE idempotency_key=?", (key,)).fetchone()):
            return {"receipt_id": found[0], "amount": found[1], "replayed": True}
        receipt = f"RC-{self.db.execute('SELECT COUNT(*) FROM payments').fetchone()[0] + 1:04d}"
        self.db.execute("INSERT INTO payments VALUES(?,?,?,?)", (receipt, key, case_id, amount))
        self.db.commit()
        return {"receipt_id": receipt, "amount": amount, "replayed": False}

    def resume(self, case_id: str, *, keyed: bool = True, crash_after_payment: bool = False) -> dict:
        """Continue an approved case. Safe to call twice; safe to call again after a crash."""
        row = self.get(case_id)
        if row is None:
            raise WorkflowError("unknown case")
        if row["state"] == "EXECUTED":
            return {"status": "already_executed"}
        if row["state"] in ("REJECTED_BY_POLICY", "REJECTED_BY_HUMAN"):
            self.log(case_id, "system", "case_closed", "no payment")
            return {"status": "closed_without_payment"}
        if row["state"] not in ("AUTO_APPROVED", "HUMAN_APPROVED"):
            raise WorkflowError(f"cannot resume from {row['state']}")
        receipt = self.pay(case_id, CASES[case_id]["payment"]["amount"], keyed=keyed)
        if crash_after_payment:
            raise RuntimeError("process died after the money moved and before the state was saved")
        self._cas(case_id, row["state"], "EXECUTED")
        self.log(case_id, "system", "payment_executed", f"released from {row['state']}", {"receipt": receipt["receipt_id"], "replayed": receipt["replayed"]})
        return {"status": "executed", "receipt": receipt}

    def authorisation(self, case_id: str) -> tuple[bool, str]:
        """Tool-side guard: may money move for this case right now?"""
        row = self.get(case_id)
        if row is None:
            return False, "the case has not been through the policy gate"
        if row["digest"] != digest(CASES[case_id]):
            return False, "the evidence changed since the gate decision; re-run the gate"
        if row["state"] in ("AUTO_APPROVED", "HUMAN_APPROVED", "EXECUTED"):
            return True, row["state"]
        return False, f"workflow state is {row['state']}"

    def total_paid(self) -> float:
        return self.db.execute("SELECT COALESCE(SUM(amount),0) FROM payments").fetchone()[0]

    def payment_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM payments").fetchone()[0]

    def states(self) -> dict[str, str]:
        return dict(self.db.execute("SELECT case_id, state FROM workflows ORDER BY case_id"))

    def completeness_problems(self) -> list[str]:
        """Every executed payment needs a gate decision in the audit log. An escalated one also needs a recorded human APPROVE."""
        problems = []
        for case_id, state in self.states().items():
            if state != "EXECUTED":
                continue
            if "gate_decision" not in self.actions(case_id):
                problems.append(f"{case_id}: paid with no gate decision in the audit log")
            if self.get(case_id)["review"]:
                human = [json.loads(blob).get("decision") for (blob,) in self.db.execute(
                    "SELECT data FROM audit WHERE case_id=? AND action='human_decision' ORDER BY seq", (case_id,))]
                if not human:
                    problems.append(f"{case_id}: escalated case paid with no human decision in the audit log")
                elif human[-1] != "approve":
                    problems.append(f"{case_id}: paid although the recorded human decision was '{human[-1]}'")
        return problems


# ── HELPERS FOR THE LAB (not part of the demo's engine) ──────────────────────

NEUTRAL = {"decision": "release", "confidence": 0.95, "rationale": "(neutral stand-in proposal)"}
AS_OUTCOME = {"release": "auto-release", "hold": "escalate", "reject": "reject"}
PROPOSAL_SYSTEM = ('You assist accounts payable. Given the evidence for one supplier payment, propose what to do. '
                   'Reply with JSON only: {"decision": "release" | "hold" | "reject", "confidence": a number from 0 to 1, '
                   '"rationale": "one or two sentences"}.')


def parse_proposal(text):
    """Return a valid proposal or None. A reply we cannot trust is treated as no proposal, never as 'release'."""
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start:end + 1])
        confidence = float(data["confidence"])
    except (ValueError, KeyError, TypeError):
        return None
    if data.get("decision") not in AS_OUTCOME or not 0 <= confidence <= 1:
        return None
    return {"decision": data["decision"], "confidence": confidence, "rationale": str(data.get("rationale", ""))[:300]}


def propose(case, ask_fn):
    """Ask the model for a proposal, with one retry on an unusable reply. `ask_fn(text)` is your Claude call from lab.py."""
    for _ in range(2):
        if (proposal := parse_proposal(ask_fn(json.dumps(evidence(case), indent=1)))):
            return proposal
    return None


def scripted_decision(svc, case_id):
    return {**SCRIPTED_DECISIONS[case_id], "evidence_digest": svc.get(case_id)["review"]["evidence_digest"]}
