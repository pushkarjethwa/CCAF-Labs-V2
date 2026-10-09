"""Demo 5H - The audit log, as plain Python. No SDK, no model, no network.

One JSON line per tool decision: which agent, which tool, a short summary of the arguments, allow or deny, and why.
Briefs and raw data are never written, and nothing secret is ever written.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from team_policy import redact

SAFE_FIELDS = ("request_id", "date", "slot", "subagent_type")  # the only argument fields that are copied into the log


def summarize_args(args):
    """A short text for the log: the safe fields as they are, and the item list as a count."""
    parts = [f"{name}={args[name]}" for name in SAFE_FIELDS if name in args]
    if isinstance(args.get("items"), list):
        parts.append(f"items={len(args['items'])} lines")
    return " ".join(parts) or "no arguments"


def write(path, agent, tool, args, decision, reason):
    """Append one decision to the log file and return the row."""
    row = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "agent": agent, "tool": tool,
           "args": redact(summarize_args(args)), "decision": decision, "reason": redact(reason)}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as log:
        log.write(json.dumps(row) + "\n")
    return row
