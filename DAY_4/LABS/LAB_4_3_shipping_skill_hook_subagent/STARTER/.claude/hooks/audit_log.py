"""PostToolUse hook: append one JSON line per edit or command to .claude/logs/tool_audit.jsonl.

It runs after every matching tool call, says nothing, and never blocks.
PostToolUse stdin carries the result under `tool_response`.
"""
import json
import os
import pathlib
import sys

payload = json.load(sys.stdin)
tool_input = payload.get("tool_input") or {}
entry = {
    "tool": payload.get("tool_name"),
    "target": tool_input.get("file_path") or tool_input.get("command"),
    "ok": "tool_response" in payload,
}
log_dir = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
with (log_dir / "tool_audit.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps(entry) + "\n")
sys.exit(0)
