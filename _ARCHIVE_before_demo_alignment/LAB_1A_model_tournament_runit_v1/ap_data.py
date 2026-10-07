"""ap_data.py - the dataset, the scorer and the legacy rules engine for the model tournament. GIVEN: read it, do not edit.

Three parts, top to bottom:
  1. DATA      load the 24 labelled invoices and build the text "case view" a model sees (ground truth is never in it)
  2. SCORING   accuracy, Wilson 95% interval, hold recall, severity-weighted error, confusion matrix
  3. LEGACY    the rules engine the company runs today (12/24 correct, hold recall 1/5). No Claude involved
No Claude call happens in this file.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- 1. DATA
LABELS = ("low", "medium", "high", "hold")
RANK = {label: i for i, label in enumerate(LABELS)}


def data_dir() -> Path:
    return Path(__file__).resolve().parent / "data"


def _load(name: str, base: Path | None = None):
    return json.loads(((base or data_dir()) / name).read_text(encoding="utf-8"))


def load_policy(base: Path | None = None) -> dict:
    return _load("policy.json", base)


def load_vendors(base: Path | None = None) -> dict[str, dict]:
    return {v["vendor_id"]: v for v in _load("vendors.json", base)}


def load_history(base: Path | None = None) -> list[dict]:
    return _load("invoice_history.json", base)


def load_invoices(base: Path | None = None) -> list[dict]:
    return _load("invoices.json", base)


def load_truth(base: Path | None = None) -> dict[str, dict]:
    raw = _load("ground_truth.json", base)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


@dataclass(frozen=True)
class Case:
    case_id: str
    amount_usd: float
    view: str          # the ONLY text a model ever sees
    invoice: dict      # raw record (for rules / routing metadata)


def render_label_guide(policy: dict) -> str:
    return "\n".join(f"- {label}: {text}" for label, text in policy["labels"].items())


def _usd(amount: float) -> str:
    return f"{amount:,.2f}"


def build_case_view(inv: dict, vendors: dict[str, dict], history: list[dict], policy: dict) -> str:
    vendor_id = inv.get("vendor_id_matched")
    vendor = vendors.get(vendor_id) if vendor_id else None
    lines = [f"INVOICE_ID: {inv['invoice_id']}", f"DOCUMENT TYPE: {inv['doc_type']}"]
    if vendor:
        lines.append(f"VENDOR ON DOCUMENT: {inv['vendor_name_on_invoice']} -> master record {vendor_id} "
                     f"({vendor['name']}), status {vendor['status']}, customer for {vendor['customer_days']} days")
    else:
        fuzzy = inv.get("fuzzy_match")
        fuzzy_note = ""
        if fuzzy:
            fuzzy_note = (f"; closest fuzzy match {fuzzy['vendor_id']} '{vendors[fuzzy['vendor_id']]['name']}' "
                          f"similarity {fuzzy['similarity']:.2f}")
        lines.append(f"VENDOR ON DOCUMENT: {inv['vendor_name_on_invoice']} -> NO exact master record{fuzzy_note}")
    lines.append(f"DOCUMENT NUMBER: {inv['invoice_number']} | AGE: {inv['age_days']} days | SUBMITTED VIA: {inv['submitted_via']}")
    range_note = ""
    if vendor and vendor.get("typical_range_usd"):
        low, high = vendor["typical_range_usd"]
        range_note = f" (this vendor's typical range: USD {low:,.0f} to {high:,.0f})"
    elif vendor:
        range_note = " (no invoice history for this vendor)"
    lines.append(f"AMOUNT: USD {_usd(inv['amount_usd'])}{range_note}")
    po = inv.get("po")
    if po is None:
        lines.append("PURCHASE ORDER: none quoted")
    else:
        po_amount = f"PO amount USD {_usd(po['amount_usd'])}" if po.get("amount_usd") is not None else "PO amount unknown"
        lines.append(f"PURCHASE ORDER: {po['number']}, {po['status']}, {po_amount}")
    lines.append(f"GOODS RECEIPT: {inv['goods_receipt']}")
    if inv.get("remit_bank_last4") is None:
        lines.append("REMIT-TO BANK: none (no payment instruction on this document)")
    else:
        on_file = vendor["bank_last4_on_file"] if vendor else None
        change_note = ""
        if vendor:
            if vendor["bank_change_log"]:
                last_change = vendor["bank_change_log"][-1]
                change_note = f"; change log: changed {last_change['days_ago']} days ago, call-back verification {'recorded' if last_change['verified_by_callback'] else 'NOT recorded'}"
            else:
                change_note = "; change log: no changes in the last 365 days"
        lines.append(f"REMIT-TO BANK: ****{inv['remit_bank_last4']} | bank on file: "
                     f"{'****' + on_file if on_file else 'none (no master record)'}{change_note}")
    lines.append("APPROVALS RECORDED: " + ("; ".join(inv["approvals"]) if inv["approvals"] else "none"))
    same_number = [h for h in history if vendor_id and h["vendor_id"] == vendor_id and h["invoice_number"] == inv["invoice_number"]]
    if same_number:
        lines.append("PRIOR PAID DOCUMENTS WITH THE SAME NUMBER: " + "; ".join(
            f"{h['invoice_number']} USD {_usd(h['amount_usd'])} paid {h['paid_days_ago']} days ago" for h in same_number))
    else:
        lines.append("PRIOR PAID DOCUMENTS WITH THE SAME NUMBER: none")
    referenced = inv.get("references_invoice")
    if referenced:
        matches = [h for h in history if h["invoice_number"] == referenced]
        lines.append(f"REFERENCED INVOICE: {referenced} -> " + (
            f"found, USD {_usd(matches[0]['amount_usd'])}, paid {matches[0]['paid_days_ago']} days ago" if matches else "not found"))
    lines.append(f"MEMO: {inv['memo']}")
    if inv.get("email_note"):
        lines.append(f"NOTE FROM SENDER: {inv['email_note']}")
    lines.append(f"POLICY CONTEXT: second approver required at or above USD {policy['approval_threshold_usd']:,}; "
                 f"PO required at or above USD {policy['po_required_at_or_above_usd']:,}.")
    return "\n".join(lines)


def load_cases(base: Path | None = None) -> list[Case]:
    policy, vendors, history = load_policy(base), load_vendors(base), load_history(base)
    return [Case(i["invoice_id"], i["amount_usd"], build_case_view(i, vendors, history, policy), i)
            for i in load_invoices(base)]


# ---------------------------------------------------------------- 2. SCORING
def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 percent Wilson score interval for a proportion. With n=24 it is WIDE - that is the lesson."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass
class Score:
    n: int
    correct: int
    accuracy: float
    ci: tuple[float, float]
    hold_total: int
    hold_caught: int
    hold_recall: float | None
    weighted_error: int
    misses: list[dict] = field(default_factory=list)
    confusion: dict = field(default_factory=dict)


def case_penalty(truth: str, pred: str | None, weights: dict) -> int:
    if pred is None:
        return weights["unusable_output"]
    rank_gap = RANK[pred] - RANK[truth]
    if rank_gap < 0:
        return -rank_gap * weights["under_classify_per_rank"]
    return rank_gap * weights["over_classify_per_rank"]


def score(preds: dict[str, str | None], truth: dict[str, dict], weights: dict,
          confidences: dict[str, float] | None = None) -> Score:
    confidences = confidences or {}
    confusion = {t: {p: 0 for p in (*LABELS, "none")} for t in LABELS}
    correct = weighted_error = hold_total = hold_caught = 0
    misses: list[dict] = []
    for cid in sorted(truth):
        true_label = truth[cid]["label"]
        predicted = preds.get(cid)
        confusion[true_label][predicted if predicted in LABELS else "none"] += 1
        weighted_error += case_penalty(true_label, predicted, weights)
        if true_label == "hold":
            hold_total += 1
            hold_caught += int(predicted == "hold")
        if predicted == true_label:
            correct += 1
        else:
            misses.append({"case_id": cid, "truth": true_label, "pred": predicted or "none", "confidence": confidences.get(cid)})
    n = len(truth)
    return Score(n, correct, correct / n if n else 0.0, wilson_interval(correct, n), hold_total, hold_caught,
                 (hold_caught / hold_total) if hold_total else None, weighted_error, misses, confusion)


def format_confusion(score_result: Score) -> str:
    columns = (*LABELS, "none")
    rows = ["truth\\pred " + "".join(f"{column:>8}" for column in columns)]
    for true_label in LABELS:
        rows.append(f"{true_label:<11}" + "".join(f"{score_result.confusion[true_label][column]:>8}" for column in columns))
    return "\n".join(rows)


def pct(fraction: float | None) -> str:
    return "n/a" if fraction is None else f"{100 * fraction:.1f}%"


# ---------------------------------------------------------------- 3. LEGACY RULES
def legacy_label(inv: dict, vendors: dict[str, dict], policy: dict | None = None) -> str:
    policy = policy or load_policy()
    vendor = vendors.get(inv.get("vendor_id_matched") or "")
    if vendor is None:
        return "high"
    if not str(vendor["status"]).startswith("active"):
        return "hold"
    amount = inv["amount_usd"]
    if amount < 0:
        return "medium"
    if inv.get("po") is None and amount >= policy["po_required_at_or_above_usd"]:
        return "high"
    if amount >= policy["approval_threshold_usd"] and not inv["approvals"]:
        return "medium"
    return "low"
