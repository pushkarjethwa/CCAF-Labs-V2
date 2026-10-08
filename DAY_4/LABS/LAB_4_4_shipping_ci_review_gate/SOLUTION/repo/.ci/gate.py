"""The review gate: Claude's findings plus an independent scanner, decided by plain code.

    python .ci/gate.py --review review.json --diff pr.diff [--summary summary.md]

Exit codes:
    0  PASS     no BLOCKER from the model or the scanner
    1  BLOCK    at least one BLOCKER (a scanner blocker counts even if the model review is missing)
    2  INVALID  the model's answer is not valid structured findings
    3  NO REVIEW the review run failed or produced no file

The decision uses parsed fields only. The free text is never searched for words like BLOCKER.
The scanner is ordinary code that reads the diff, so it does not depend on the model.
"""
import argparse
import json
import pathlib
import re
import sys

PASS, BLOCK, INVALID, NO_REVIEW = 0, 1, 2, 3
SEVERITIES = ["BLOCKER", "SHOULD_FIX", "NITPICK"]
CATEGORIES = ["units", "secrets", "tests", "correctness", "style"]
FIELDS = {"id": str, "severity": str, "category": str, "file": str, "line": int, "title": str, "evidence": str, "fix": str}
SECRET_PATTERNS = [
    re.compile(r"sp_live_[A-Za-z0-9]{16,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


# ---------------------------------------------------------------- reading the diff
def parse_diff(text):
    """Return {file: {new_line_number: added_text}} for every added line in a unified diff."""
    files, current, line_no = {}, None, 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            current = None
        elif line.startswith("+++ "):
            name = line[4:].strip()
            if name != "/dev/null":
                current = name[2:] if name.startswith("b/") else name
                files[current] = {}
        elif line.startswith("@@"):
            start = re.search(r"\+(\d+)", line)
            line_no = int(start.group(1)) if start else 0
        elif current is not None and line.startswith("+") and not line.startswith("+++"):
            files[current][line_no] = line[1:]
            line_no += 1
        elif current is not None and line.startswith(" "):
            line_no += 1
    return files


# ---------------------------------------------------------------- the scanner (no model)
def scan(diff_text):
    """Find what a regular expression can find: secrets in source, and source changed without tests."""
    files = parse_diff(diff_text)
    findings = []
    for name, added in sorted(files.items()):
        if name.startswith("tests/"):
            continue
        for line_no, text in sorted(added.items()):
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                findings.append({"id": "SCAN-SECRET", "severity": "BLOCKER", "category": "secrets", "file": name, "line": line_no,
                                 "title": "Credential-shaped literal added to source", "evidence": "line matches a secret pattern",
                                 "fix": "Read it from the environment and rotate the exposed value.", "source": "scanner"})
    source_files = [n for n in files if n.startswith("src/")]
    if source_files and not any(n.startswith("tests/") for n in files):
        findings.append({"id": "SCAN-NO-TESTS", "severity": "SHOULD_FIX", "category": "tests", "file": source_files[0], "line": 1,
                         "title": "Source changed but no test file changed", "evidence": "the diff touches src/ and nothing under tests/",
                         "fix": "Add tests for the changed behaviour, including the failure path.", "source": "scanner"})
    return findings


def is_anchored(finding, files):
    """A model finding should point at a line the diff really added (give or take 3 lines)."""
    added = files.get(finding["file"])
    return bool(added) and any(abs(finding["line"] - line_no) <= 3 for line_no in added)


# ---------------------------------------------------------------- reading the model's answer
def validate(payload):
    """Return an error message, or None when the payload matches findings.schema.json."""
    if not isinstance(payload, dict) or not isinstance(payload.get("summary"), str):
        return "payload needs a string summary"
    if not isinstance(payload.get("findings"), list):
        return "payload needs a findings list"
    for finding in payload["findings"]:
        if not isinstance(finding, dict) or set(finding) != set(FIELDS):
            return "a finding does not have exactly the fields %s" % sorted(FIELDS)
        for name, kind in FIELDS.items():
            if not isinstance(finding[name], kind) or isinstance(finding[name], bool):
                return "finding %s: field %s must be %s" % (finding.get("id"), name, kind.__name__)
        if finding["severity"] not in SEVERITIES or finding["category"] not in CATEGORIES:
            return "finding %s: unknown severity or category" % finding["id"]
        if finding["line"] < 1 or not finding["title"].strip():
            return "finding %s: line must be 1 or more and title must not be empty" % finding["id"]
    return None


def read_review(path):
    """Return (status, payload, detail). status is ok, invalid or no_review."""
    file = pathlib.Path(path)
    if not file.exists() or file.stat().st_size == 0:
        return "no_review", None, "no review output was produced"
    try:
        envelope = json.loads(file.read_text(encoding="utf-8"))
    except ValueError:
        return "invalid", None, "output is not JSON (free text cannot gate a build)"
    if not isinstance(envelope, dict):
        return "invalid", None, "output is not a JSON object"
    if envelope.get("is_error") or envelope.get("subtype", "success") != "success":
        return "no_review", None, "the review run failed (subtype %s)" % envelope.get("subtype")
    payload = envelope.get("structured_output")
    if payload is None:
        return "invalid", None, "the envelope has no structured_output"
    problem = validate(payload)
    if problem:
        return "invalid", None, problem
    return "ok", payload, ""


# ---------------------------------------------------------------- the decision
def decide(status, payload, detail, diff_text):
    """Return (decision, exit_code, reason, findings)."""
    files = parse_diff(diff_text)
    scanner = scan(diff_text)
    model = []
    if status == "ok":
        model = [dict(f, source="model") for f in payload["findings"]]
        for finding in model:
            if not is_anchored(finding, files):
                finding["title"] += " (not anchored to the diff)"
    scanned_blockers = {(f["file"], f["category"]) for f in scanner if f["severity"] == "BLOCKER"}
    findings = scanner + [f for f in model if not (f["severity"] == "BLOCKER" and (f["file"], f["category"]) in scanned_blockers)]
    blockers = [f for f in findings if f["severity"] == "BLOCKER"]
    if blockers:
        return "BLOCK", BLOCK, "%d blocker(s)" % len(blockers), findings
    if status == "invalid":
        return "INVALID", INVALID, detail, findings
    if status == "no_review":
        return "NO REVIEW", NO_REVIEW, detail, findings
    return "PASS", PASS, "no blockers", findings


def render(decision, reason, findings):
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
    lines = ["## Claude review gate: **%s**" % decision, "",
             "%s | BLOCKER %d | SHOULD_FIX %d | NITPICK %d" % (reason, counts["BLOCKER"], counts["SHOULD_FIX"], counts["NITPICK"])]
    if findings:
        lines += ["", "| severity | where | found by | title |", "|---|---|---|---|"]
        for f in sorted(findings, key=lambda f: SEVERITIES.index(f["severity"])):
            lines.append("| %s | `%s:%d` | %s | %s |" % (f["severity"], f["file"], f["line"], f["source"], f["title"].replace("|", "/")))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--diff", required=True)
    parser.add_argument("--summary")
    args = parser.parse_args()
    diff_text = pathlib.Path(args.diff).read_text(encoding="utf-8")
    status, payload, detail = read_review(args.review)
    decision, code, reason, findings = decide(status, payload, detail, diff_text)
    text = render(decision, reason, findings)
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    print("GATE %s (exit %d)" % (decision, code))
    return code


if __name__ == "__main__":
    sys.exit(main())
