"""check.py - key-free checks for Lab 4.3. No API key, no model, no Claude Code needed.

    python check.py              check all four stages
    python check.py --stage 2    check one stage
    python check.py --root SOLUTION

Exit code 0 = everything passed.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

HERE = pathlib.Path(__file__).resolve().parent
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def front_matter(path):
    """Return (front matter dict or None, body text)."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError:
        return None, ""
    match = re.match(r"---\r?\n(.*?)\r?\n---\r?\n?(.*)", text, re.S)
    if not match:
        return None, text
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, match.group(2)
    return (data if isinstance(data, dict) else None), match.group(2)


def run(args, stdin="", env=None):
    return subprocess.run([sys.executable] + args, input=stdin, capture_output=True, text=True, env=env, timeout=60)


def stage1(root):
    print("Stage 1 - the skill")
    skill = root / ".claude" / "skills" / "api-contract-review"
    meta, body = front_matter(skill / "SKILL.md")
    meta = meta or {}
    description = str(meta.get("description") or "")
    check(meta.get("name") == "api-contract-review" == skill.name, "SKILL.md has front matter with name api-contract-review, matching its folder")
    check(len(description) >= 60 and "use when" in description.lower(), "the description says what the skill does and when to use it ('Use when ...')", f"you wrote {description!r}")
    check(str(meta.get("argument-hint") or "").strip() != "" and "$ARGUMENTS" in body, "argument-hint is set and the body uses $ARGUMENTS")
    allowed = str(meta.get("allowed-tools") or "")
    check("diff_contract.py" in allowed and "Read" in allowed, "allowed-tools pre-approves Read and the contract script", f"allowed-tools={allowed!r}")
    links = re.findall(r"\]\((references/[\w.-]+\.md)\)", body)
    check(len(links) >= 3 and all((skill / link).exists() for link in links), "the body links to three reference files, and they all exist", f"links={links}")


def scan(root):
    script = root / ".claude" / "skills" / "api-contract-review" / "scripts" / "diff_contract.py"
    return run([str(script), "--root", str(root)]) if script.exists() else None


def stage2(root):
    print("\nStage 2 - the supporting script")
    done = scan(root)
    out = done.stdout if done else ""
    check(done is not None and done.returncode == 0, "diff_contract.py runs and exits 0")
    check(re.search(r"src/shipcalc/quote\.py:\d+ get_quote params .*'rush'", out) is not None, "the scanner finds the contract drift in quote.py (the new rush parameter)", f"output was {out.strip()!r}")
    check("contract scan: 1 candidate(s)" in out, "the scanner reports exactly one candidate")
    clean = pathlib.Path(tempfile.mkdtemp())
    try:
        shutil.copytree(root, clean / "repo", ignore=shutil.ignore_patterns("logs", "__pycache__", ".git"))
        contract = clean / "repo" / "docs" / "API_CONTRACT.json"
        data = json.loads(contract.read_text(encoding="utf-8"))
        data["public"][0]["params"].append("rush")
        contract.write_text(json.dumps(data), encoding="utf-8")
        done = scan(clean / "repo")
        check(done is not None and "contract scan: 0 candidate(s)" in done.stdout, "when the contract matches the code, the scanner reports 0 candidates")
    finally:
        shutil.rmtree(clean, ignore_errors=True)
    skill = (root / ".claude" / "skills" / "api-contract-review" / "SKILL.md")
    check("scripts/diff_contract.py" in (skill.read_text(encoding="utf-8") if skill.exists() else ""), "SKILL.md step 2 runs the scanner")


def stage3(root):
    print("\nStage 3 - the hooks")
    try:
        settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        settings = {}
    groups = (settings.get("hooks") or {}).get("PostToolUse") or []
    matcher = " ".join(str(g.get("matcher", "")) for g in groups)
    commands = [h for g in groups for h in g.get("hooks", [])]
    check(bool(groups), "settings.json is valid JSON with a PostToolUse hook")
    check(all(re.search(r"\b%s\b" % tool, matcher) for tool in ("Edit", "Write", "Bash")), "the matcher covers Edit, Write and Bash", f"matcher={matcher!r}")
    scripts = [re.search(r"\.claude/hooks/([\w.-]+\.py)", c.get("command", "")) for c in commands]
    check(bool(commands) and all(c.get("type") == "command" and "timeout" in c for c in commands), "each hook is a command hook with a timeout")
    check(bool(scripts) and all(m and (root / ".claude" / "hooks" / m.group(1)).exists() for m in scripts), "each command points at a script that exists")
    script = root / ".claude" / "hooks" / "audit_log.py"
    project = pathlib.Path(tempfile.mkdtemp())
    try:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
        samples = [{"tool_name": "Bash", "tool_input": {"command": "python scan.py"}, "tool_response": {"stdout": "ok"}},
                   {"tool_name": "Write", "tool_input": {"file_path": "reports/review.md"}, "tool_response": {"success": True}}]
        runs = [run([str(script)], json.dumps(s), env) for s in samples] if script.exists() else []
        check(len(runs) == 2 and all(r.returncode == 0 and r.stdout == "" and r.stderr == "" for r in runs), "audit_log.py exits 0 and prints nothing")
        log = project / ".claude" / "logs" / "tool_audit.jsonl"
        lines = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
        check([(l.get("tool"), l.get("target"), l.get("ok")) for l in lines] == [("Bash", "python scan.py", True), ("Write", "reports/review.md", True)],
              "audit_log.py writes one line per tool call: the tool, the target and ok", f"log lines: {lines}")
    finally:
        shutil.rmtree(project, ignore_errors=True)


def stage4(root):
    print("\nStage 4 - the read-only subagent")
    meta, body = front_matter(root / ".claude" / "agents" / "contract-reviewer.md")
    meta = meta or {}
    tools = meta.get("tools")
    tools = [t.strip() for t in tools.split(",")] if isinstance(tools, str) else tools
    check(meta.get("name") == "contract-reviewer" and len(str(meta.get("description") or "")) >= 40, "the agent has the name contract-reviewer and a description of at least 40 characters")
    check(isinstance(tools, list) and tools and set(tools) <= {"Read", "Grep", "Glob"}, "tools is an explicit read-only list (Read, Grep, Glob)", f"tools={tools}")
    check(isinstance(meta.get("maxTurns"), int) and meta["maxTurns"] <= 15, "maxTurns is set, at most 15", f"maxTurns={meta.get('maxTurns')}")
    check(len(body.strip()) >= 80, "the agent has a system prompt")
    skill = root / ".claude" / "skills" / "api-contract-review" / "SKILL.md"
    check("contract-reviewer" in (skill.read_text(encoding="utf-8") if skill.exists() else ""), "SKILL.md step 3 delegates to the contract-reviewer subagent")


STAGES = {1: stage1, 2: stage2, 3: stage3, 4: stage4}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=sorted(STAGES))
    parser.add_argument("--root", default=str(HERE / "STARTER"))
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    print(f"Lab 4.3 checks for {root.name}\n")
    for number in ([args.stage] if args.stage else sorted(STAGES)):
        STAGES[number](root)
    print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
