"""Part 0 check: the working repo exists, is a git repo on main, has a commit, and its tests pass."""
import argparse
import os
import subprocess
import sys


def run(repo, *cmd):
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    repo = os.path.abspath(parser.parse_args().repo)
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))

    check("repo folder exists", os.path.isdir(repo))
    if os.path.isdir(repo):
        for path in ("src/rewards/points.py", "src/rewards/api.py", "scripts/check_rules.py",
                     "tests/test_points.py", "docs/ARCHITECTURE.md", ".gitignore"):
            check("file present: " + path, os.path.isfile(os.path.join(repo, path)))
        branch = run(repo, "git", "rev-parse", "--abbrev-ref", "HEAD")
        check("git repo on branch main", branch.returncode == 0 and branch.stdout.strip() == "main")
        check("at least one commit", run(repo, "git", "rev-list", "--count", "HEAD").stdout.strip() not in ("", "0"))
        tests = run(repo, sys.executable, "-m", "unittest", "discover", "-s", "tests")
        check("service tests pass", tests.returncode == 0)
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
