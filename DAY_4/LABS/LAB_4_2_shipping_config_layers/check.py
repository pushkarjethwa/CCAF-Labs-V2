"""Lab 4.2 checker. Key-free: no Claude Code, no network, standard library only.

  python check.py                  checks STARTER (your work)
  python check.py --root SOLUTION  checks the finished lab

The simulated user file is <root>/home_claude/CLAUDE.md; the project is <root>/repo.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--root", default=str(HERE / "STARTER"))
ROOT = pathlib.Path(parser.parse_args().root).resolve()
REPO = ROOT / "repo"
USER = ROOT / "home_claude" / "CLAUDE.md"


def read(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    assert "TODO" not in text, "still has its TODO placeholder"
    assert text.strip(), "empty"
    return text


def glob_to_regex(pattern):
    """Simple glob matcher: ** crosses folders, * and ? stay inside one folder."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile("^" + out + "$")


def rule_globs(path):
    """Parse a rule file: front matter with exactly one key, paths, a list of quoted globs."""
    text = read(path).replace("\r\n", "\n")
    assert text.startswith("---\n") and "\n---" in text[4:], "front matter missing"
    front = text[4:text.index("\n---", 4)].splitlines()
    assert front and front[0].strip() == "paths:", "the only front matter key must be paths:"
    globs = []
    for line in front[1:]:
        match = re.fullmatch(r'\s+-\s+"([^"]+)"', line)
        assert match, "each path must look like:   - \"glob\"  (got %r)" % line
        globs.append(match.group(1))
    assert globs, "paths: is empty"
    return globs


def matches(globs, rel):
    return any(glob_to_regex(g).match(rel) for g in globs)


def load_set(rel):
    """Which instruction files are in context when Claude reads rel (broad to specific)."""
    loaded = ["user", "project"]
    folder = pathlib.PurePosixPath(rel).parent
    chain = [p for p in reversed(folder.parents)] + [folder]
    for directory in chain:
        if str(directory) != "." and (REPO / directory / "CLAUDE.md").exists():
            loaded.append(directory.name)
    for rule in sorted((REPO / ".claude" / "rules").glob("*.md")):
        if matches(rule_globs(rule), rel):
            loaded.append(rule.stem)
    return loaded


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hook(source_text):
    """Run the PostToolUse hook on a sample event; return (exit code, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        sample = pathlib.Path(tmp) / "src" / "shipcalc" / "sample.py"
        sample.parent.mkdir(parents=True)
        sample.write_text(source_text, encoding="utf-8")
        event = {"tool_name": "Edit", "cwd": tmp, "tool_input": {"file_path": str(sample)}}
        env = dict(os.environ, CLAUDE_PROJECT_DIR=tmp, PYTHONDONTWRITEBYTECODE="1")
        done = subprocess.run([sys.executable, "-B", str(REPO / ".claude" / "hooks" / "enforce_money.py")],
                              input=json.dumps(event), capture_output=True, text=True, env=env, timeout=30)
        return done.returncode, done.stderr


# ---------------------------------------------------------------- the checks
def c_user():
    text = read(USER)
    assert not re.search(r"float|decimal|cents|pytest|unittest|kilogram", text, re.I), \
        "the user file must hold personal style only, no team rules"


def c_project():
    text = read(REPO / "CLAUDE.md")
    for needed in ("python -m pytest", "integer cents", "kilograms", "logging"):
        assert needed in text, "CLAUDE.md should mention: " + needed


def c_carriers():
    text = read(REPO / "src/shipcalc/carriers/CLAUDE.md")
    assert "units.to_metric" in text, "mention units.to_metric"
    assert not re.search(r"float|pounds|cents|unittest", text, re.I), "keep money and style out of this file"


def c_lazy():
    assert "carriers" in load_set("src/shipcalc/carriers/acme.py"), "carriers/CLAUDE.md should load for an adapter"
    assert "carriers" not in load_set("src/shipcalc/rates.py"), "carriers/CLAUDE.md should not load for rates.py"


def c_rules_parse():
    for name in ("money", "tests"):
        rule_globs(REPO / ".claude" / "rules" / (name + ".md"))


def c_globs():
    money = rule_globs(REPO / ".claude/rules/money.md")
    tests = rule_globs(REPO / ".claude/rules/tests.md")
    for rel in ("src/shipcalc/rates.py", "src/shipcalc/carriers/acme.py", "src/shipcalc/carriers/zipfast.py"):
        assert matches(money, rel), "money.md should match " + rel
    for rel in ("tests/test_rates.py", "docs/ARCHITECTURE.md"):
        assert not matches(money, rel), "money.md should not match " + rel
    assert matches(tests, "tests/test_rates.py"), "tests.md should match tests/test_rates.py"
    assert not matches(tests, "src/shipcalc/rates.py"), "tests.md should not match source files"


def c_order():
    expected = {
        "src/shipcalc/rates.py": ["user", "project", "money"],
        "src/shipcalc/carriers/acme.py": ["user", "project", "carriers", "money"],
        "tests/test_rates.py": ["user", "project", "tests"],
        "docs/ARCHITECTURE.md": ["user", "project"],
    }
    for rel, want in expected.items():
        got = load_set(rel)
        assert got == want, "for %s expected %s, got %s" % (rel, want, got)


def c_import():
    assert "@docs/ARCHITECTURE.md" in read(REPO / "CLAUDE.md"), "add the @docs/ARCHITECTURE.md line"
    assert (REPO / "docs" / "ARCHITECTURE.md").exists()


def c_price():
    rates = load_module("lab_rates", REPO / "src" / "shipcalc" / "rates.py")
    for args, want in (((0.5, 1), 500), ((10.0, 3), 2860), ((1.0, 2), 575), ((3.0, 2), 863)):
        got = rates.price_cents(*args)
        assert got == want and isinstance(got, int), "price_cents%s should be %d, got %r" % (args, want, got)


def c_scanner():
    invariants = load_module("lab_invariants", REPO / ".claude" / "hooks" / "invariants.py")
    found = invariants.scan_tree(REPO / "src")
    assert not found, "float money in: " + ", ".join(found)


def c_tie_test():
    names = []
    for path in (REPO / "tests").glob("test_*.py"):
        names += re.findall(r"def (test_\w+)", path.read_text(encoding="utf-8"))
    assert any("tie" in name for name in names), "add a test whose name contains 'tie'"


def c_settings():
    path = REPO / ".claude" / "settings.json"
    assert path.exists(), "create .claude/settings.json"
    entries = json.loads(read(path)).get("hooks", {}).get("PostToolUse")
    assert entries, "settings.json needs hooks -> PostToolUse"
    assert any("Edit" in e["matcher"] and "Write" in e["matcher"] for e in entries), "matcher must cover Edit and Write"
    commands = [h["command"] for e in entries for h in e["hooks"] if h["type"] == "command"]
    assert any("enforce_money.py" in c for c in commands), "the command must run enforce_money.py"


def c_hook_sample():
    code, _ = run_hook("def price_cents(kg):\n    return 500 * 1150 // 1000\n")
    assert code == 0, "the hook should accept integer-cent code (exit %d)" % code
    code, err = run_hook("def price_cents(kg):\n    return int(500 * 1.15 + 0.5)\n")
    assert code == 2 and "MONEY INVARIANT" in err, "the hook should flag a float price with exit 2 (got %d)" % code


def c_scan_cli():
    done = subprocess.run([sys.executable, "-B", str(REPO / ".claude/hooks/invariants.py"), str(REPO / "src")],
                          capture_output=True, text=True, timeout=30)
    assert done.returncode == 0 and "MONEY INVARIANT: ok" in done.stdout, "scanner says: " + done.stdout.strip()[-80:]


def c_mcp():
    assert (REPO / ".mcp.json").exists(), "create .mcp.json"
    config = json.loads(read(REPO / ".mcp.json"))
    server = config["mcpServers"]["carrier-docs"]
    assert server["type"] == "http" and server["url"].startswith("https://"), "carrier-docs must be an https http server"


def c_secret():
    assert (REPO / ".mcp.json").exists(), "create .mcp.json"
    raw = read(REPO / ".mcp.json")
    server = json.loads(raw)["mcpServers"]["carrier-docs"]
    for value in server.get("headers", {}).values():
        assert "${" in value, "read the token from an environment variable, ${NAME}"
    assert not re.search(r"sk-|Bearer [A-Za-z0-9]{12,}", raw), "no literal credential in .mcp.json"


STAGES = [
    ("Stage 1: user and project layers", [
        ("user file holds personal style only", c_user),
        ("project CLAUDE.md has commands and conventions", c_project)]),
    ("Stage 2: subdirectory layer", [
        ("carriers/CLAUDE.md describes the folder only", c_carriers),
        ("carriers/CLAUDE.md loads for adapters, not for rates.py", c_lazy)]),
    ("Stage 3: path-scoped rules and import", [
        ("both rules use only the paths: key", c_rules_parse),
        ("globs match the intended shipcalc files", c_globs),
        ("load order is user, project, nested, rules", c_order),
        ("CLAUDE.md imports docs/ARCHITECTURE.md", c_import),
        ("rates.price_cents uses integer arithmetic", c_price),
        ("the scanner finds no float money in src", c_scanner),
        ("a half-cent tie regression test exists", c_tie_test)]),
    ("Stage 4: enforce the rule with a hook", [
        ("settings.json registers the PostToolUse hook", c_settings),
        ("the hook runs on a sample event", c_hook_sample),
        ("python invariants.py src reports ok", c_scan_cli)]),
    ("Stage 5: project MCP layer", [
        (".mcp.json declares carrier-docs", c_mcp),
        ("the token comes from an environment variable", c_secret)]),
]

passed = total = 0
for title, checks in STAGES:
    print(title)
    for label, fn in checks:
        total += 1
        try:
            fn()
            passed += 1
            print("  [PASS] " + label)
        except Exception as error:  # noqa: BLE001 - every problem is reported as "not yet"
            print("  [todo] %s (%s)" % (label, error))
print("\nRESULT: %d/%d checks passed" % (passed, total))
sys.exit(0 if passed == total else 1)
