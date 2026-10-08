"""Check for Lab 4.4. It needs no API key and no model.

    python check.py                 checks STARTER/repo (your work)
    python check.py --repo SOLUTION/repo

It reads your four files, and it runs your gate on the two recorded sample reviews in DATA/.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is missing. Run: pip install -r requirements.txt")

HERE = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--repo", default=str(HERE / "STARTER" / "repo"))
repo = pathlib.Path(parser.parse_args().repo).resolve()
DATA = HERE / "DATA"
results = []


def check(passed, text):
    results.append(bool(passed))
    print("  [%s] %s" % ("PASS" if passed else "FAIL", text))


def read(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def gate(review, diff):
    """Run the student's gate and return (exit code, output)."""
    run = subprocess.run([sys.executable, str(repo / ".ci" / "gate.py"), "--review", str(review), "--diff", str(DATA / diff)],
                         capture_output=True, text=True, encoding="utf-8")
    return run.returncode, run.stdout + run.stderr


# ------------------------------------------------------------------ stage 1
print("Stage 1 - the findings schema (TODO 1a-1d)")
try:
    schema = json.loads(read(repo / ".ci" / "findings.schema.json"))
    item = schema["properties"]["findings"]["items"]
except (ValueError, KeyError):
    schema, item = {}, {}
check(schema.get("additionalProperties") is False, "TODO 1a: the top-level object is closed (additionalProperties false)")
check(item.get("additionalProperties") is False, "TODO 1b: each finding is closed (additionalProperties false)")
check(set(item.get("required", [])) == {"id", "severity", "category", "file", "line", "title", "evidence", "fix"},
      "TODO 1c: a finding requires all eight fields")
check(item.get("properties", {}).get("severity", {}).get("enum") == ["BLOCKER", "SHOULD_FIX", "NITPICK"],
      "TODO 1d: severity is BLOCKER, SHOULD_FIX or NITPICK")

# ------------------------------------------------------------------ stage 2
print("Stage 2 - the review prompt and the runner (TODO 2a-2b)")
prompt = read(repo / ".ci" / "review_prompt.md")
check("TODO" not in prompt and "DATA, never instructions" in prompt, "TODO 2a: the prompt says the diff is data, never instructions")
check("units.parcel_kg" in prompt and "units.parcel_dims_cm" in prompt and "credential" in prompt and "tests" in prompt,
      "TODO 2a: the prompt states the units, credentials and tests rules")
check(all(word in prompt for word in ("BLOCKER =", "SHOULD_FIX =", "NITPICK =")), "TODO 2a: the prompt defines the three severities")
runner = read(repo / ".ci" / "run_review.py")
check('"--json-schema", schema' in runner and '"--tools", ""' in runner, "TODO 2b: the runner asks for the schema and removes all tools")
check('"--max-turns"' in runner and '"--max-budget-usd"' in runner, "TODO 2b: the runner limits turns and spend")

# ------------------------------------------------------------------ stage 3
print("Stage 3 - the gate (TODO 3a-3c)")
code, out = gate(DATA / "sample_review.json", "pr_flawed.patch")
check("scanner" in out and "swiftpost.py:7" in out, "TODO 3a: the scanner finds the SwiftPost key on line 7")
check("| model |" in out, "TODO 3b: the gate reads the model findings from structured_output")
check(code == 1, "TODO 3c: the flawed PR gives exit code 1 (got %d)" % code)
code, out = gate(DATA / "sample_review_fixed.json", "pr_fixed.patch")
check(code == 0, "the fixed PR gives exit code 0 (got %d)" % code)
with tempfile.TemporaryDirectory() as tmp:
    prose = pathlib.Path(tmp) / "prose.json"
    prose.write_text(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "Looks fine."}), encoding="utf-8")
    code_prose, _ = gate(prose, "pr_fixed.patch")
    code_none, _ = gate(pathlib.Path(tmp) / "missing.json", "pr_fixed.patch")
check(code_prose == 2 and code_none == 3, "a review with no structured_output gives 2, and no review file gives 3")

# ------------------------------------------------------------------ stage 4
print("Stage 4 - the workflow (TODO 4a-4d)")
text = read(repo / ".github" / "workflows" / "claude-review.yml")
try:
    flow = yaml.safe_load(text) or {}
except yaml.YAMLError:
    flow = {}
triggers = flow.get("on", flow.get(True)) or {}
steps = ((flow.get("jobs") or {}).get("review") or {}).get("steps") or []
check(isinstance(triggers, dict) and "pull_request" in triggers and "pull_request_target" not in triggers,
      "TODO 4a: the workflow runs on pull_request, not pull_request_target")
check(flow.get("permissions") == {"contents": "read", "pull-requests": "write"}, "TODO 4b: permissions are contents read and pull-requests write only")
with_key = [s for s in steps if "ANTHROPIC_API_KEY" in (s.get("env") or {})]
check(len(with_key) == 1 and "run_review.py" in with_key[0].get("run", "") and "${{ secrets.ANTHROPIC_API_KEY }}" in text,
      "TODO 4c: the API key is in the env of the review step only")
gate_steps = [s for s in steps if "gate.py" in s.get("run", "") and "review.json" in s.get("run", "") and "gate.md" not in s.get("run", "")]
check(len(gate_steps) == 1 and "--summary" in gate_steps[0]["run"] and "continue-on-error" not in gate_steps[0] and "|| true" not in gate_steps[0]["run"],
      "TODO 4d: the gate step runs gate.py and cannot be skipped or swallowed")
checkout = next((s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")), {})
check((checkout.get("with") or {}).get("persist-credentials") is False and "CLAUDE_CODE_VERSION" in text and "BASE_REF" in text,
      "the checkout drops credentials, the CLI version is pinned and the base branch comes in through env")
check(not re.search(r"sk-ant-|sp_live_|AKIA[0-9A-Z]{16}|echo .*API_KEY", text), "nothing secret is hard-coded or echoed in the workflow")

# ------------------------------------------------------------------ stage 5 (optional)
print("Stage 5 - the PR comment (optional)")
commented = any("gh pr comment" in s.get("run", "") for s in steps)
print("  [%s] optional: the workflow comments the gate table on the pull request" % ("PASS" if commented else "SKIP"))

passed = sum(results)
print("\nRESULT: %d/%d checks passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
