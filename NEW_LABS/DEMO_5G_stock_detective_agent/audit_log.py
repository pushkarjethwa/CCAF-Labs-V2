"""Demo 5G - The audit log, as plain Python. No SDK, no model, no network.

One JSON line per gate decision. Tool arguments are shortened, and nothing secret is ever written.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_VALUE_CHARS = 80


def shorten(args):
    """The tool arguments with every long text cut to MAX_VALUE_CHARS."""
    return {key: (value[:MAX_VALUE_CHARS] if isinstance(value, str) else value) for key, value in args.items()}


def write(path, case, role, tool, args, allowed, reason):
    """Append one decision to the log file and return the row."""
    row = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "case": case, "role": role, "tool": tool,
           "args": shorten(args), "decision": "allow" if allowed else "deny", "reason": reason}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as log:
        log.write(json.dumps(row) + "\n")
    return row
