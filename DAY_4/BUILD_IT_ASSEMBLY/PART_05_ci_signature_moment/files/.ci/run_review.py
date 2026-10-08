"""Run the headless Claude Code review on a diff and save the JSON envelope.

    python .ci/run_review.py --diff pr.diff --out review.json [--model sonnet] [--login]

The same script runs on your laptop and in the GitHub Actions job, so the flags live in one place.
By default it needs the `claude` CLI on PATH and ANTHROPIC_API_KEY in the environment (--bare does not use a login).
Add --login on your own machine to use your Claude Code sign-in instead (it drops --bare).
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

CI = pathlib.Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--login", action="store_true", help="use your Claude Code sign-in (no --bare)")
    args = parser.parse_args()

    claude = shutil.which("claude")
    if claude is None:
        print("REVIEW SKIPPED: claude CLI not found on PATH")
        return 127
    prompt = (CI / "review_prompt.md").read_text(encoding="utf-8")
    schema = (CI / "findings.schema.json").read_text(encoding="utf-8")
    diff = pathlib.Path(args.diff).read_text(encoding="utf-8")

    # Verify these flags on your Claude Code version (claude --help).
    command = [claude]
    if not args.login:
        command.append("--bare")        # ignore hooks, MCP servers and CLAUDE.md found in the PR's checkout
    command += [
        "-p", prompt,                   # headless: print one answer and exit
        "--output-format", "json",      # one JSON envelope on stdout
        "--json-schema", schema,        # the validated answer comes back in "structured_output"
        "--tools", "",                  # no tools: the reviewer only sees the diff on stdin
        "--permission-mode", "dontAsk",
        "--model", args.model,
        "--max-turns", "5",
        "--max-budget-usd", "1.00",
        "--no-session-persistence",
    ]
    result = subprocess.run(command, input=diff, capture_output=True, text=True, encoding="utf-8")
    pathlib.Path(args.out).write_text(result.stdout, encoding="utf-8")
    print("REVIEW DONE: claude exit code %d, wrote %d bytes to %s" % (result.returncode, len(result.stdout), args.out))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
