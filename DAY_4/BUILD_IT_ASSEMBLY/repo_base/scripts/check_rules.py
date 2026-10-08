"""Key-free scanner for the Brew & Bean team rules. Prints JSON.

Usage:
    python scripts/check_rules.py --files a.py b.py
    python scripts/check_rules.py --diff change.patch      (use - to read stdin)

Add --strict to exit 1 when anything is found. Exit 2 means bad usage.
Rule ids: float-points, pii-in-log, secret-literal, missing-test.
"""
import argparse
import json
import re
import sys

SECRET = re.compile(r"(bb_live_[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{8,})")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
LOG_CALL = re.compile(r"\b(log_event|logger\.\w+|logging\.\w+|print)\s*\(")
PERSONAL = re.compile(r"\b(email|phone|address|full_name|dob)\b", re.I)
FLOAT_MATH = re.compile(r"float\s*\(|\d+\.\d+|(?<!/)/(?!/)|\bround\s*\(")


def norm(path):
    path = path.replace("\\", "/")
    return path[2:] if path.startswith("./") else path


def is_src(path):
    return norm(path).startswith("src/") and path.endswith(".py") and not path.endswith("__init__.py")


def is_test(path):
    return norm(path).startswith("tests/")


def scan_line(path, number, text):
    found = []

    def add(rule, message):
        found.append({"rule": rule, "file": norm(path), "line": number, "message": message})

    code = text.split("#", 1)[0]
    if SECRET.search(text):
        add("secret-literal", "Key-shaped literal in source. Read keys from environment variables.")
    if is_src(path) and LOG_CALL.search(code) and (PERSONAL.search(code) or EMAIL.search(code)):
        add("pii-in-log", "Personal data passed to a log call. Log the customer id only.")
    if is_src(path) and re.search(r"point", code, re.I) and FLOAT_MATH.search(code.replace('"', "")):
        add("float-points", "Points must be integers. Avoid float math, true division and round().")
    return found


def missing_tests(paths):
    changed_src = sorted(norm(p) for p in paths if is_src(p))
    if changed_src and not any(is_test(p) for p in paths):
        return [{"rule": "missing-test", "file": f, "line": 0,
                 "message": "src file changed with no test in the same change."} for f in changed_src]
    return []


def scan_files(paths):
    findings = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        except OSError as err:
            findings.append({"rule": "unreadable", "file": norm(path), "line": 0, "message": str(err)})
            continue
        for number, text in enumerate(lines, 1):
            findings += scan_line(path, number, text)
    return findings + missing_tests(paths)


def scan_diff_text(diff):
    findings, paths, current, number = [], [], None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            name = raw[4:].strip()
            current = None if name == "/dev/null" else re.sub(r"^b/", "", name)
            if current:
                paths.append(current)
        elif raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            number = int(match.group(1)) if match else 0
        elif current and raw.startswith("+") and not raw.startswith("+++"):
            findings += scan_line(current, number, raw[1:])
            number += 1
        elif current and raw.startswith(" "):
            number += 1
    return findings + missing_tests(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scan for Brew & Bean rule violations.")
    parser.add_argument("--files", nargs="+", help="files to scan (treated as the changed files)")
    parser.add_argument("--diff", help="path to a unified diff, or - for stdin")
    parser.add_argument("--strict", action="store_true", help="exit 1 when findings exist")
    args = parser.parse_args(argv)
    if bool(args.files) == bool(args.diff):
        parser.error("give exactly one of --files or --diff")
    if args.files:
        findings = scan_files(args.files)
    else:
        text = sys.stdin.read() if args.diff == "-" else open(args.diff, encoding="utf-8").read()
        findings = scan_diff_text(text)
    print(json.dumps({"findings": findings, "count": len(findings)}, indent=2))
    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    sys.exit(main())
