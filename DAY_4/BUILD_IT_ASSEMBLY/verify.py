"""Run each part's verify_part.py against the working repo and print a summary.

    python verify.py [--upto N] [--repo PATH]
Exit 0 only when every part passes.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from assemble import DEFAULT_REPO, discover_parts  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upto", type=int, help="verify parts 0..N (default: all parts found)")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    args = parser.parse_args(argv)
    results = []
    for number, folder in discover_parts().items():
        if args.upto is not None and number > args.upto:
            continue
        script = os.path.join(folder, "verify_part.py")
        if not os.path.isfile(script):
            results.append((number, os.path.basename(folder), None))
            continue
        print("== %s" % os.path.basename(folder), flush=True)
        done = subprocess.run([sys.executable, script, "--repo", args.repo], env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        results.append((number, os.path.basename(folder), done.returncode == 0))
    print("\nSummary")
    for number, name, ok in results:
        print("  %-30s %s" % (name, "PASS" if ok else ("FAIL" if ok is False else "no verify_part.py")))
    good = all(ok for _, _, ok in results) and bool(results)
    print("ALL PARTS PASS" if good else "SOME PARTS NOT READY")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
