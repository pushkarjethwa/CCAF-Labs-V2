"""PostToolUse hook: run the tests after Claude edits a Python file.

Claude Code sends one JSON object on stdin, for example:
  {"tool_name": "Edit", "tool_input": {"file_path": "bookshop/reports.py"}, ...}
Passing tests print one short line. Failing tests are sent to Claude on stderr with exit code 2.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

event = json.load(sys.stdin)
path = str(event.get("tool_input", {}).get("file_path", ""))
if not path.endswith(".py"):
    sys.exit(0)

run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                     cwd=ROOT, capture_output=True, text=True)
if run.returncode == 0:
    print("[hook] tests passed after editing " + pathlib.Path(path).name)
    sys.exit(0)
print(run.stderr[-1500:], file=sys.stderr)
sys.exit(2)
