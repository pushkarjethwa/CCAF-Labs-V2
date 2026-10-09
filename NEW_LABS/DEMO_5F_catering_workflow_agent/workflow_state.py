"""Demo 5F - The memory of the workflow: checkpoints, run history, the approval queue and the audit log.

Plain Python: no SDK, no model, no network. Every file lives under one results folder:
    runs/<order_id>.json     the checkpoint: the state and the list of finished steps, saved after every step
    run_history.jsonl        one line per run, stop, resume or approval
    approval_queue.json      orders that wait for a manager
    audit_log.jsonl          one line per tool decision (no message text, no secrets)
    outbox/<order_id>.txt    the confirmation that was "sent" (see catering_tools.send_confirmation)
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def now():
    """The time as text, to the second, in UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_record(order_id, request_text):
    """The checkpoint of a brand-new run. The state holds only the customer's text so far."""
    return {"order_id": order_id, "status": "running", "done": [], "state": {"request_text": request_text}, "trace": []}


def mark_done(record, step, tokens_given, tokens_output, cost):
    """Add a step to the finished list, with what it cost. The caller saves the checkpoint."""
    record["done"].append(step)
    record["trace"].append({"step": step, "given": tokens_given, "output": tokens_output, "cost_usd": cost})


def total_cost(record):
    """What all finished steps of this order cost, in dollars."""
    return round(sum(entry["cost_usd"] for entry in record["trace"]), 6)


class RunStore:
    """All the files of the workflow, under one folder."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.history_path = self.folder / "run_history.jsonl"
        self.queue_path = self.folder / "approval_queue.json"
        self.audit_path = self.folder / "audit_log.jsonl"
        self.outbox = self.folder / "outbox"

    # -- Checkpoints ---------------------------------------------------------------------------------------

    def checkpoint_path(self, order_id):
        """The one checkpoint file for one order."""
        return self.folder / "runs" / f"{Path(order_id).name}.json"

    def save(self, record):
        """Write the checkpoint. Called after every step."""
        path = self.checkpoint_path(record["order_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return path

    def load(self, order_id):
        """The saved checkpoint, or None when this order has never run."""
        path = self.checkpoint_path(order_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    # -- Run history and audit log -------------------------------------------------------------------------

    def append_line(self, path, row):
        """Add one JSON line to a .jsonl file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row) + "\n")

    def add_history(self, record, steps_run, steps_skipped):
        """One line for this run, stop, resume or approval."""
        self.append_line(self.history_path, {
            "time": now(), "order_id": record["order_id"], "status": record["status"], "total": record["state"].get("total"),
            "steps_run": steps_run, "steps_skipped": steps_skipped, "cost_usd": total_cost(record)})

    def history(self):
        """Every history line, oldest first."""
        if not self.history_path.exists():
            return []
        return [json.loads(line) for line in self.history_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def log_decision(self, order_id, step, tool, args, allowed, reason):
        """One tool decision. Only the argument names are logged, never their values."""
        self.append_line(self.audit_path, {"time": now(), "order": order_id, "step": step, "tool": tool,
                                           "arg_names": sorted(args), "decision": "allow" if allowed else "deny", "reason": reason})

    # -- The approval queue --------------------------------------------------------------------------------

    def queue(self):
        """The orders that wait for a manager."""
        if not self.queue_path.exists():
            return []
        return json.loads(self.queue_path.read_text(encoding="utf-8"))

    def write_queue(self, entries):
        """Replace the queue file."""
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.queue_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def add_to_queue(self, order_id, total, limit):
        """Put an order in the queue, once."""
        entries = [entry for entry in self.queue() if entry["order_id"] != order_id]
        entries.append({"order_id": order_id, "total": total, "reason": f"over the ${limit:.2f} limit", "queued_at": now()})
        self.write_queue(entries)

    def remove_from_queue(self, order_id):
        """Take an order out of the queue."""
        self.write_queue([entry for entry in self.queue() if entry["order_id"] != order_id])
