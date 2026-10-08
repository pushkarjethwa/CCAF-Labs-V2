"""PostToolUse hook: run the unit tests after Claude changes a Python file.

Claude Code sends one JSON object on stdin, for example:
  {"tool_name": "Edit", "tool_input": {"file_path": "src/rewards/points.py"}}
Quiet by design: when the tests pass it prints nothing and exits 0.
When they fail, the output goes to Claude on stderr with exit code 2, so Claude can fix it.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

try:
    event = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
path = str(event.get("tool_input", {}).get("file_path", "")).replace("\\", "/")
if not path.endswith(".py") or not ("src/" in path or "tests/" in path):
    sys.exit(0)

run = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
                     cwd=ROOT, capture_output=True, text=True)
if run.returncode == 0:
    sys.exit(0)
sys.stderr.write("Tests failed after editing " + path + "\n" + run.stderr[-1500:])
sys.exit(2)
