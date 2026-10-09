"""Demo 5H - The shared ledger and the approval queue, as plain Python. No SDK, no model, no network.

results/week_ledger.json is the orchestrator's memory. It survives a restart. Only code in this file writes it,
and only after a hand-off has been validated. Subagents have no tool that can touch it.

    orders             one entry per request: status, the validated hand-offs, the total and the slot
    decisions          one line per finished request: what was decided and why
    slots_reserved     request id -> the slot in the kitchen calendar
    pending_approvals  request ids that wait for a person (also listed in results/approval_queue.json)
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

DONE = ("planned", "waiting_approval", "cannot_fulfil")  # a request in one of these states is never redone on --resume


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -- Read and write ---------------------------------------------------------------------------------------------

def new_ledger(week_start, requests):
    """An empty ledger with one 'new' order per request."""
    orders = {r["request_id"]: {"customer": r["customer"], "status": "new", "handoffs": {}, "total_usd": None, "slot": None}
              for r in requests}
    return {"week_start": week_start, "orders": orders, "decisions": [], "slots_reserved": {}, "pending_approvals": []}


def load(path):
    """The ledger from its file, or None when there is none yet."""
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(path, data):
    """Write the ledger file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def unfinished(data):
    """Request ids that still need work, in order. This is what --resume continues with."""
    return [request_id for request_id, order in data["orders"].items() if order["status"] not in DONE]


# -- Writes that follow a validated hand-off ----------------------------------------------------------------------

def add_handoff(data, role, handoff):
    """Store a hand-off that already passed its schema. Return a problem text when the request id is unknown, else None."""
    order = data["orders"].get(handoff["request_id"])
    if order is None:
        return f"unknown request {handoff['request_id']}"
    order["handoffs"][role] = handoff
    if role == "pricer":
        order["total_usd"] = handoff["total_usd"]
    return None


def decide(order, approval_limit, slot):
    """Return (status, reason) from the validated facts only. The model's words are never used. 'incomplete' means ask again."""
    stock, price, schedule = (order["handoffs"].get(role) for role in ("stock_checker", "pricer", "scheduler"))
    if not stock or not price:
        return "incomplete", "the stock check or the price is missing"
    if stock["status"] == "short":
        return "cannot_fulfil", "stock is short"
    if price["total_usd"] > approval_limit and order["status"] != "approved":
        return "waiting_approval", f"total {price['total_usd']:.2f} is above the {approval_limit} limit, so a person must approve"
    if not schedule or not slot:
        return "incomplete", "no slot is reserved yet"
    return "planned", f"slot {slot} reserved, total {price['total_usd']:.2f}"


def record_decision(data, request_id, approval_limit, slot):
    """Decide one request and write the result into the ledger. Return (status, reason)."""
    order = data["orders"][request_id]
    status, reason = decide(order, approval_limit, slot)
    if status == "incomplete":
        return status, reason
    order["status"] = status
    if status == "planned":
        order["slot"] = data["slots_reserved"][request_id] = slot
    if status == "waiting_approval" and request_id not in data["pending_approvals"]:
        data["pending_approvals"].append(request_id)
    data["decisions"].append({"request_id": request_id, "status": status, "reason": reason, "time": now()})
    return status, reason


# -- The approval queue and the human's decision --------------------------------------------------------------------

def queue_for_approval(path, request_id, order):
    """Put an over-limit order into the approval queue file. The same request is queued once."""
    queue = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else []
    if not any(item["request_id"] == request_id for item in queue):
        proposed = (order["handoffs"].get("scheduler") or {}).get("slot", "")
        queue.append({"request_id": request_id, "customer": order["customer"], "total_usd": order["total_usd"],
                      "proposed_slot": proposed, "status": "pending approval"})
        Path(path).write_text(json.dumps(queue, indent=2), encoding="utf-8")


def approve(data, path, request_id, slot):
    """A person approved this request. Mark it planned with the slot that code has just reserved."""
    queue = json.loads(Path(path).read_text(encoding="utf-8"))
    for item in queue:
        if item["request_id"] == request_id:
            item["status"] = "approved"
    Path(path).write_text(json.dumps(queue, indent=2), encoding="utf-8")
    order = data["orders"][request_id]
    order["status"], order["slot"] = "planned", slot
    data["slots_reserved"][request_id] = slot
    data["pending_approvals"].remove(request_id)
    data["decisions"].append({"request_id": request_id, "status": "planned", "reason": f"approved by a person, slot {slot}", "time": now()})


# -- The transcript archive (used by the PreCompact hook) ---------------------------------------------------------------

def archive_transcript(source, folder):
    """Copy the orchestrator's transcript file into the archive folder before it is compacted. Return the new path, or None."""
    if not source or not Path(source).is_file():
        return None
    Path(folder).mkdir(parents=True, exist_ok=True)
    target = Path(folder) / f"{Path(source).stem}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.jsonl"
    shutil.copyfile(source, target)
    return target
