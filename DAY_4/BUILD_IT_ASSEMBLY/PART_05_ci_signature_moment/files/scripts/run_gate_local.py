"""Run the review gate on your machine with no GitHub. Safe to run with no API key.

    python scripts/run_gate_local.py ../../DATA/pr_flawed.patch
    python scripts/run_gate_local.py ../../DATA/pr_flawed.patch --recorded ../../DATA/recorded_review_flawed.json
    python scripts/run_gate_local.py ../../DATA/pr_good.patch --live            (needs ANTHROPIC_API_KEY)
    python scripts/run_gate_local.py ../../DATA/pr_good.patch --live --login    (uses your Claude Code sign-in)

Without --recorded or --live, a recorded review next to the patch is used when its name matches
(pr_flawed.patch -> recorded_review_flawed.json). Exit codes are the gate's: 0 PASS, 1 BLOCK, 2 INVALID, 3 INCONCLUSIVE.
"""
import argparse
import functools
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
print = functools.partial(print, flush=True)


def run(*cmd):
    return subprocess.run([sys.executable] + [str(c) for c in cmd], text=True).returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", help="a unified diff such as DATA/pr_flawed.patch")
    parser.add_argument("--recorded", help="recorded review JSON to use instead of a live call")
    parser.add_argument("--live", action="store_true", help="call headless Claude for the review")
    parser.add_argument("--login", action="store_true", help="with --live: use your Claude Code sign-in")
    args = parser.parse_args()
    patch = pathlib.Path(args.patch).resolve()
    if not patch.is_file():
        print("PATCH NOT FOUND: " + str(patch))
        return 4
    work = pathlib.Path(tempfile.mkdtemp(prefix="gate_local_"))
    diff = work / "pr.diff"
    diff.write_text(patch.read_text(encoding="utf-8"), encoding="utf-8")
    print("DIFF: %s (%d lines)" % (patch.name, len(diff.read_text(encoding="utf-8").splitlines())))

    print("\n--- Step 1: the rule scanner (no model) ---")
    run(ROOT / "scripts" / "check_rules.py", "--diff", diff)

    review = work / "review.json"
    if args.live:
        print("--- Step 2: live headless review ---")
        extra = ["--login"] if args.login else []
        run(ROOT / ".ci" / "run_review.py", "--diff", diff, "--out", review, *extra)
    else:
        recorded = pathlib.Path(args.recorded) if args.recorded else \
            patch.parent / patch.name.replace("pr_", "recorded_review_").replace(".patch", ".json")
        if recorded.is_file():
            print("--- Step 2: recorded review %s (a saved sample, not a live call) ---" % recorded.name)
            review.write_text(recorded.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            print("--- Step 2: no recorded review found, the gate will report INCONCLUSIVE unless the scanner blocks ---")

    print("\n--- Step 3: the gate ---")
    code = run(ROOT / ".ci" / "gate.py", "--review", review, "--diff", diff)
    print("Local gate exit code: %d" % code)
    for item in (diff, review):
        if item.exists():
            item.unlink()
    work.rmdir()
    return code


if __name__ == "__main__":
    sys.exit(main())
