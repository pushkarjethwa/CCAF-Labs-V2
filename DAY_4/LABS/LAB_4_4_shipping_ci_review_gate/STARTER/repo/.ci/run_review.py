"""Run the headless Claude Code review on a diff and save the JSON envelope.

    python .ci/run_review.py --diff pr.diff --out review.json [--model sonnet]

The same script runs on your laptop and in the GitHub Actions job, so the flags live in one place.
Needs the `claude` CLI on PATH and ANTHROPIC_API_KEY in the environment (--bare does not use a login).
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

CI = pathlib.Path(__file__).resolve().parent

parser = argparse.ArgumentParser()
parser.add_argument("--diff", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--model", default="sonnet")
args = parser.parse_args()

claude = shutil.which("claude")
if claude is None:
    sys.exit("claude CLI not found on PATH (npm install -g @anthropic-ai/claude-code)")

prompt = (CI / "review_prompt.md").read_text(encoding="utf-8")
schema = (CI / "findings.schema.json").read_text(encoding="utf-8")
diff = pathlib.Path(args.diff).read_text(encoding="utf-8")

# Verify these flags on your Claude Code version (claude --help).
command = [
    claude,
    "--bare",                           # ignore hooks, MCP servers, CLAUDE.md and memory found in the PR's checkout
    "-p", prompt,                       # headless: print one answer and exit
    "--output-format", "json",          # one JSON envelope on stdout
    # TODO 2b: replace this line with four flags
    "--permission-mode", "dontAsk",
    "--model", args.model,
    "--no-session-persistence",
]
result = subprocess.run(command, input=diff, capture_output=True, text=True, encoding="utf-8")
pathlib.Path(args.out).write_text(result.stdout, encoding="utf-8")
print("claude exit code %d, wrote %d bytes to %s" % (result.returncode, len(result.stdout), args.out))
sys.exit(result.returncode)
