"""Part 2 check: memory files and path-scoped rules are present and well formed."""
import argparse
import os
import re
import sys

RULES = {"money.md": "src/rewards/points.py", "logging.md": "src/**/*.py", "tests.md": "tests/**"}


def read(repo, path):
    full = os.path.join(repo, path)
    return open(full, encoding="utf-8").read() if os.path.isfile(full) else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    repo = os.path.abspath(parser.parse_args().repo)
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))

    root = read(repo, "CLAUDE.md")
    check("CLAUDE.md has the four team rules", all(("%d. " % n) in root for n in (1, 2, 3, 4)))
    check("CLAUDE.md imports @docs/ARCHITECTURE.md", re.search(r"^@docs/ARCHITECTURE\.md\s*$", root, re.M) is not None)
    check("nested src/rewards/CLAUDE.md present", "points.py" in read(repo, "src/rewards/CLAUDE.md"))
    for name, glob_ in RULES.items():
        text = read(repo, ".claude/rules/" + name)
        front = re.match(r"---\n(.*?)\n---", text, re.S)
        check(".claude/rules/%s has paths: %s" % (name, glob_),
              bool(front) and "paths:" in front.group(1) and ('"%s"' % glob_) in front.group(1))
    check("CLAUDE.local.md.example present", bool(read(repo, "CLAUDE.local.md.example")))
    check(".gitignore keeps CLAUDE.local.md out of git", "CLAUDE.local.md" in read(repo, ".gitignore").splitlines())
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
