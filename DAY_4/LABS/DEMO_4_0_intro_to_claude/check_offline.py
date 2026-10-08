"""Key-free self-check for demo 4.0, Intro to Claude.  No Claude Code, no API key and no network are needed.
Run: python check_offline.py   (ends with ALL OK)
If the `mcp` package is not installed, the MCP server file is only parsed, and its plain functions are tested separately."""
import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import reset  # noqa: E402

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
problems = []


def expect(ok, message):
    print("  [%s] %s" % ("ok" if ok else "FAIL", message))
    if not ok:
        problems.append(message)


def front_matter(path):
    """Read the simple `key: value` front matter of a markdown file. Uses PyYAML when it is installed."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        return None
    block = text[4:].split("\n---", 1)[0]
    try:
        import yaml
        data = yaml.safe_load(block)
        return data if isinstance(data, dict) else None
    except ImportError:
        data = {}
        for line in block.splitlines():
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
        return data


def tests(repo):
    run = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"], cwd=str(repo),
                         capture_output=True, text=True, env=ENV)
    ran = [line for line in run.stderr.splitlines() if line.startswith("Ran ")]
    return run.returncode == 0, int(ran[0].split()[1]) if ran else 0


# 1. every file the story needs exists, and parses
print("1. files exist and parse")
needed = [
    "START_STATE/bookshop/reports.py", "START_STATE/data/books.json", "START_STATE/tests/test_reports.py",
    "PART_02_memory/add/CLAUDE.md",
    "PART_04_slash_command/add/.claude/commands/add-feature.md", "PART_04_slash_command/reference/bookshop/reports.py",
    "PART_05_skill/add/.claude/skills/report-style/SKILL.md", "PART_05_skill/reference/bookshop/reports.py",
    "PART_06_subagent/add/.claude/agents/reviewer.md",
    "PART_07_hook/add/.claude/settings.json", "PART_07_hook/add/.claude/hooks/run_tests.py",
    "PART_07_hook/reference/bookshop/cli.py",
    "PART_08_mcp/add/mcp_server/supplier.py", "PART_08_mcp/add/mcp_server/supplier_server.py", "PART_08_mcp/catch_up/.mcp.json",
    "FINAL/CLAUDE.md", "requirements.txt", "README.md", "RUN_SHEET.md", "reset.py",
]
for rel in needed:
    expect((HERE / rel).is_file(), rel)
for path in sorted(HERE.rglob("*")):
    if "workspace" in path.parts or not path.is_file():
        continue
    if path.suffix == ".py":
        ast.parse(path.read_text(encoding="utf-8"))
    elif path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
expect(True, "every .py parses (ast) and every .json is valid")

# 2. front matter
print("2. front matter")
fm = front_matter(HERE / "PART_04_slash_command/add/.claude/commands/add-feature.md")
expect(bool(fm and fm.get("description") and fm.get("argument-hint")), "slash command has description and argument-hint")
expect("$ARGUMENTS" in (HERE / "PART_04_slash_command/add/.claude/commands/add-feature.md").read_text(encoding="utf-8"), "slash command uses $ARGUMENTS")
fm = front_matter(HERE / "PART_05_skill/add/.claude/skills/report-style/SKILL.md")
expect(bool(fm and fm.get("name") == "report-style" and fm.get("description")), "skill has name (= folder name) and description")
fm = front_matter(HERE / "PART_06_subagent/add/.claude/agents/reviewer.md")
expect(bool(fm and fm.get("name") == "reviewer" and fm.get("description") and "Edit" not in str(fm.get("tools"))), "subagent has name, description and read-only tools")
for md in ["README.md", "RUN_SHEET.md"]:
    expect(front_matter(HERE / md) is not None, "%s has front matter" % md)
expect("## Run the demo" in (HERE / "RUN_SHEET.md").read_text(encoding="utf-8"), "RUN_SHEET has a Run the demo section")

# 3. the project at each point of the story
print("3. project state through the parts")
tmp = pathlib.Path(tempfile.mkdtemp(prefix="demo40_"))
seen = {}
for part, want_tests in [(1, 6), (5, 9), (6, 9), (8, 11), (10, 11)]:
    repo = reset.build(tmp / ("p%d" % part), part)
    ok, ran = tests(repo)
    seen[part] = ran
    expect(ok and ran == want_tests, "start of part %d: %d tests green (got %d)" % (part, want_tests, ran))
start = tmp / "p1"
expect(not (start / "CLAUDE.md").exists() and not (start / ".claude").exists(), "part 1 starts with no CLAUDE.md and no .claude folder")
out = subprocess.run([sys.executable, "-B", "-m", "bookshop", "summary"], cwd=str(start), capture_output=True, text=True, env=ENV)
expect(out.returncode == 0 and out.stdout.splitlines()[0] == "=== INVENTORY SUMMARY ===", "start: python -m bookshop summary works")
final_repo = tmp / "p10"
out = subprocess.run([sys.executable, "-B", "-m", "bookshop", "low-stock"], cwd=str(final_repo), capture_output=True, text=True, env=ENV)
lines = out.stdout.splitlines()
expect(out.returncode == 0 and lines[0] == "=== LOW STOCK (BELOW 5) ===" and lines[-1] == "Total: 4 titles", "final: low-stock report follows the shop style (title line, Total line)")

# 4. hook script runs on sample stdin JSON
print("4. hook")
settings = json.loads((HERE / "PART_07_hook/add/.claude/settings.json").read_text(encoding="utf-8"))
entry = settings["hooks"]["PostToolUse"][0]
expect(entry["matcher"] == "Edit|Write" and entry["hooks"][0]["type"] == "command", "hook is PostToolUse on Edit|Write")
expect("Bash(python -m unittest:*)" in settings["permissions"]["allow"], "settings allow the test command")
hook = final_repo / ".claude/hooks/run_tests.py"
for sample, expected in [({"tool_name": "Edit", "tool_input": {"file_path": "bookshop/reports.py"}}, "tests passed"),
                         ({"tool_name": "Write", "tool_input": {"file_path": "notes.txt"}}, "")]:
    run = subprocess.run([sys.executable, "-B", str(hook)], cwd=str(final_repo), input=json.dumps(sample),
                         capture_output=True, text=True, env=ENV)
    expect(run.returncode == 0 and expected in run.stdout, "hook on %s: exit 0, %r" % (sample["tool_input"]["file_path"], expected or "silent"))

# 5. MCP server
print("5. MCP server")
server_dir = HERE / "PART_08_mcp/add/mcp_server"
sys.path.insert(0, str(server_dir))
import supplier  # noqa: E402
expect(supplier.supplier_stock("9780000000028") == "9780000000028: supplier has 40 copies, ships in 2 days", "plain function supplier_stock")
expect(len(supplier.supplier_catalog().splitlines()) == 8, "plain function supplier_catalog lists 8 ISBNs")
books = json.loads((HERE / "START_STATE/data/books.json").read_text(encoding="utf-8"))
expect({b["isbn"] for b in books} == set(supplier.SUPPLIER_STOCK), "supplier lists every ISBN in the shop's data")
try:
    import mcp  # noqa: F401
    import supplier_server  # noqa: E402
    expect(callable(supplier_server.supplier_stock) and callable(supplier_server.supplier_catalog), "server module imports with the real mcp package")
except ImportError:
    print("  [note] `mcp` not installed here: server file parsed only. Run `pip install -r requirements.txt` and re-run for the import check.")
mcp_config = json.loads((HERE / "PART_08_mcp/catch_up/.mcp.json").read_text(encoding="utf-8"))["mcpServers"]["supplier"]
expect(mcp_config["args"] == ["mcp_server/supplier_server.py"] and (final_repo / mcp_config["args"][0]).is_file(), ".mcp.json points at a project-relative server file that exists")
sys.path.remove(str(server_dir))

# 6. FINAL is exactly the finished demo
print("6. FINAL matches the parts")
mine = {p.relative_to(HERE / "FINAL"): p.read_bytes() for p in (HERE / "FINAL").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
want = {p.relative_to(final_repo): p.read_bytes() for p in final_repo.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
expect(mine == want, "FINAL equals START_STATE plus all parts in order (%d files)" % len(want))

print("ALL OK" if not problems else "PROBLEMS: %d" % len(problems))
sys.exit(1 if problems else 0)
