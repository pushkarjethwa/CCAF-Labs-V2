"""PreToolUse hook: block any edit that writes a key-shaped value into a file.

Claude Code sends one JSON object on stdin before it runs a tool, for example:
  {"tool_name": "Write", "tool_input": {"file_path": "src/rewards/config.py", "content": "..."}}
Exit 0 means carry on, with no output. Exit 2 stops the tool call and sends stderr to Claude.
"""
import json
import re
import sys

SECRET = re.compile(r"(bb_live_[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{8,})")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}


def new_text(tool_input):
    """Return every piece of text the tool is about to write."""
    pieces = [tool_input.get("content", ""), tool_input.get("new_string", "")]
    for edit in tool_input.get("edits", []) or []:
        pieces.append(edit.get("new_string", ""))
    return "\n".join(str(piece) for piece in pieces)


try:
    event = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
if event.get("tool_name") not in EDIT_TOOLS:
    sys.exit(0)
tool_input = event.get("tool_input", {})
if SECRET.search(new_text(tool_input)):
    path = tool_input.get("file_path", "a file")
    sys.stderr.write("Blocked: the change to %s contains a key-shaped value. "
                     "Team rule 3: keys come from environment variables, never from source.\n" % path)
    sys.exit(2)
sys.exit(0)
