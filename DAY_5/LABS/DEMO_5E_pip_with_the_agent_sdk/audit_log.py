"""Demo 5E - The audit log, as plain Python. No SDK, no model, no network.

One JSON line per tool decision. The card id is masked, and nothing secret is ever written.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def mask(card_id):
    """Hide the last two characters of a card id: C-1042 becomes C-10**."""
    return (card_id[:-2] + "**") if card_id else "none"


def write(path, tier, card_id, tool, args, allowed, reason):
    """Append one decision to the log file and return the row."""
    row = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tier": tier, "card": mask(card_id),
           "tool": tool, "args": args, "decision": "allow" if allowed else "deny", "reason": reason}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as log:
        log.write(json.dumps(row) + "\n")
    return row
