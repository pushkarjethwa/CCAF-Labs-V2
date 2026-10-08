"""Part 3 check: command, skills, subagent and hooks are present, well formed, and the hooks behave."""
import argparse
import json
import os
import re
import subprocess
import sys

KEY = "bb_" + "live_" + "EXAMPLE0000000000000000"
AWS = "AK" + "IA" + "EXAMPLE0000000000"


def read(repo, path):
    full = os.path.join(repo, path)
    return open(full, encoding="utf-8").read() if os.path.isfile(full) else ""


def front(text):
    """Return the front matter as a dict of simple 'key: value' pairs, or None."""
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    pairs = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            pairs[key.strip()] = value.strip()
    return pairs


def run_hook(repo, script, payload, raw=None):
    return subprocess.run([sys.executable, "-B", os.path.join(repo, ".claude", "hooks", script)], cwd=repo,
                          input=raw if raw is not None else json.dumps(payload), capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))


def hook_commands(settings, event):
    return [h.get("command", "") for entry in settings.get("hooks", {}).get(event, []) for h in entry.get("hooks", [])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    repo = os.path.abspath(parser.parse_args().repo)
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))

    command = read(repo, ".claude/commands/review-points.md")
    meta = front(command) or {}
    check("command /review-points has a description and uses $ARGUMENTS", bool(meta.get("description")) and "$ARGUMENTS" in command)

    for name in ("rewards-style", "audit-readonly"):
        meta = front(read(repo, ".claude/skills/%s/SKILL.md" % name)) or {}
        check("skill %s: name matches folder and description is present" % name,
              meta.get("name") == name and len(meta.get("description", "")) > 20)
    meta = front(read(repo, ".claude/skills/audit-readonly/SKILL.md")) or {}
    check("skill audit-readonly runs in a fork (context: fork)", meta.get("context") == "fork")

    meta = front(read(repo, ".claude/agents/rule-reviewer.md")) or {}
    tools = [t.strip() for t in meta.get("tools", "").split(",") if t.strip()]
    check("subagent rule-reviewer is read-only (Read, Grep, Glob only)",
          meta.get("name") == "rule-reviewer" and bool(meta.get("description"))
          and sorted(tools) == ["Glob", "Grep", "Read"])

    try:
        settings = json.loads(read(repo, ".claude/settings.json"))
        check(".claude/settings.json is valid JSON", True)
    except ValueError:
        settings = {}
        check(".claude/settings.json is valid JSON", False)
    post = hook_commands(settings, "PostToolUse")
    check("PostToolUse runs run_tests.py", any("run_tests.py" in c for c in post))
    pre = settings.get("hooks", {}).get("PreToolUse", [])
    check("PreToolUse runs block_secrets.py on Edit, Write and MultiEdit",
          any(all(t in e.get("matcher", "") for t in ("Edit", "Write", "MultiEdit"))
              and any("block_secrets.py" in h.get("command", "") for h in e.get("hooks", [])) for e in pre))

    ok = (os.path.isfile(os.path.join(repo, ".claude/hooks/block_secrets.py")))
    check(".claude/hooks/block_secrets.py present", ok)
    if ok:
        def write(path, text, tool="Write"):
            key = "content" if tool == "Write" else "new_string"
            return {"tool_name": tool, "tool_input": {"file_path": path, key: text}}
        bad = run_hook(repo, "block_secrets.py", write("src/rewards/config.py", "API_KEY = '%s'\n" % KEY))
        check("block_secrets exits 2 with a plain message on a key-shaped Write", bad.returncode == 2 and "Blocked" in bad.stderr)
        check("block_secrets exits 2 on a key-shaped Edit",
              run_hook(repo, "block_secrets.py", write("a.py", "k = '%s'" % KEY, "Edit")).returncode == 2)
        multi = {"tool_name": "MultiEdit", "tool_input": {"file_path": "a.py", "edits": [
            {"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": "k = '%s'" % AWS}]}}
        check("block_secrets exits 2 on a key inside MultiEdit", run_hook(repo, "block_secrets.py", multi).returncode == 2)
        good = run_hook(repo, "block_secrets.py", write("src/rewards/config.py", "import os\nKEY = os.environ.get('REWARDS_API_KEY')\n"))
        check("block_secrets exits 0 and stays silent on a normal Write", good.returncode == 0 and not good.stderr and not good.stdout)
        check("block_secrets ignores other tools", run_hook(repo, "block_secrets.py", {"tool_name": "Bash", "tool_input": {"command": "echo " + KEY}}).returncode == 0)
        check("block_secrets exits 0 on input that is not JSON", run_hook(repo, "block_secrets.py", None, raw="not json").returncode == 0)

    if os.path.isfile(os.path.join(repo, ".claude/hooks/run_tests.py")):
        quiet = run_hook(repo, "run_tests.py", {"tool_name": "Edit", "tool_input": {"file_path": "src/rewards/points.py"}})
        check("run_tests exits 0 and prints nothing when the tests pass", quiet.returncode == 0 and not quiet.stdout and not quiet.stderr)
        skip = run_hook(repo, "run_tests.py", {"tool_name": "Edit", "tool_input": {"file_path": "README.md"}})
        check("run_tests skips files that are not Python", skip.returncode == 0 and not skip.stdout)
    else:
        check("run_tests.py present", False)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
