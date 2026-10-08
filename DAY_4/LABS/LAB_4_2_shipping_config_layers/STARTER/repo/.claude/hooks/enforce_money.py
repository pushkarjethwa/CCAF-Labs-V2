"""PostToolUse hook: after Claude edits a Python file under src/shipcalc, re-scan it for float money.

settings.json runs it after Edit, Write and MultiEdit. Claude Code sends a JSON event on stdin
(tool_name, tool_input.file_path). Exit 0 = fine. Exit 2 = send stderr back to Claude to fix.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import invariants  # noqa: E402


def unix_path(raw: str) -> str:
    return raw.replace("\\", "/")  # on Windows the path arrives with backslashes


def in_scope(file_path: str, project_dir: str) -> bool:
    file_path, project_dir = unix_path(file_path), unix_path(project_dir).rstrip("/")
    return file_path.endswith(".py") and (project_dir + "/src/shipcalc/") in file_path


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # not our event
    file_path = (event.get("tool_input") or {}).get("file_path", "")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd", "")
    if not file_path or not in_scope(file_path, project_dir):
        return 0
    source = pathlib.Path(file_path).read_text(encoding="utf-8")
    violations = invariants.scan_source(source)
    if not violations:
        return 0
    sys.stderr.write("MONEY INVARIANT in %s:\n" % unix_path(file_path))
    for line, why in violations:
        sys.stderr.write("  line %d: %s\n" % (line, why))
    sys.stderr.write("Prices are integer cents; do not use float, round() or float literals.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
