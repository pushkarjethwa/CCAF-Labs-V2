"""Part 1 check: the birthday request is in docs/ and the feature is planned but NOT built yet."""
import argparse
import os
import re
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    repo = os.path.abspath(parser.parse_args().repo)
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))

    request = os.path.join(repo, "docs", "BIRTHDAY_BONUS_REQUEST.md")
    check("docs/BIRTHDAY_BONUS_REQUEST.md present", os.path.isfile(request))
    if os.path.isfile(request):
        check("request mentions 50 extra points", "50" in open(request, encoding="utf-8").read())
    built = False
    for folder, _, files in os.walk(os.path.join(repo, "src")):
        for name in files:
            if name.endswith(".py") and re.search("birthday", open(os.path.join(folder, name), encoding="utf-8").read(), re.I):
                built = True
    check("birthday bonus is not built yet (built later as the good PR)", not built)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
