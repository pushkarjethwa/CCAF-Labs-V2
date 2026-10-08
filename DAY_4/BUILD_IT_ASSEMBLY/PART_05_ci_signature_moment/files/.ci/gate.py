"""The review gate: the rule scanner plus Claude's findings, decided by plain code.

    python .ci/gate.py --review review.json --diff pr.diff [--summary file.md]

Exit codes:
    0  PASS          no BLOCKER from the scanner or the model
    1  BLOCK         at least one BLOCKER (a scanner blocker counts even if the model review is missing)
    2  INVALID       the model answer is not valid structured findings
    3  INCONCLUSIVE  the review run failed or produced no file

The decision uses parsed fields only. The free text is never searched for words like BLOCKER.
The scanner is scripts/check_rules.py, ordinary code that reads the diff, so it does not need the model.
"""
import argparse
import json
import pathlib
import subprocess
import sys

PASS, BLOCK, INVALID, INCONCLUSIVE = 0, 1, 2, 3
SEVERITIES = ["BLOCKER", "SHOULD_FIX", "NITPICK"]
CATEGORIES = ["secrets", "privacy", "money", "tests", "correctness", "style"]
FIELDS = {"id": str, "severity": str, "category": str, "file": str, "line": int, "title": str, "evidence": str, "fix": str}
ROOT = pathlib.Path(__file__).resolve().parent.parent
# How each scanner rule is graded, and which review category it matches.
RULES = {"secret-literal": ("BLOCKER", "secrets"), "pii-in-log": ("BLOCKER", "privacy"),
         "float-points": ("BLOCKER", "money"), "missing-test": ("SHOULD_FIX", "tests")}


def scan(diff_path):
    """Run scripts/check_rules.py on the diff and return findings in the review shape."""
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_rules.py"), "--diff", str(diff_path)],
                          capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise SystemExit("scanner failed: " + done.stderr.strip())
    findings = []
    for item in json.loads(done.stdout)["findings"]:
        severity, category = RULES.get(item["rule"], ("SHOULD_FIX", "correctness"))
        findings.append({"id": "SCAN-" + item["rule"].upper(), "severity": severity, "category": category,
                         "file": item["file"], "line": item["line"], "title": item["message"], "source": "scanner"})
    return findings


def validate(payload):
    """Return an error message, or None when the payload matches .ci/findings.schema.json."""
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
        if finding["line"] < 0 or not finding["title"].strip():
            return "finding %s: line must be 0 or more and title must not be empty" % finding["id"]
    return None


def read_review(path):
    """Return (status, payload, detail, recorded). status is ok, invalid or inconclusive."""
    file = pathlib.Path(path) if path else None
    if file is None or not file.exists() or file.stat().st_size == 0:
        return "inconclusive", None, "no review output was produced", False
    try:
        envelope = json.loads(file.read_text(encoding="utf-8"))
    except ValueError:
        return "invalid", None, "output is not JSON (free text cannot gate a build)", False
    if not isinstance(envelope, dict):
        return "invalid", None, "output is not a JSON object", False
    recorded = bool(envelope.get("recorded_sample"))
    if envelope.get("is_error") or envelope.get("subtype", "success") != "success":
        return "inconclusive", None, "the review run failed (subtype %s)" % envelope.get("subtype"), recorded
    payload = envelope.get("structured_output")
    if payload is None:
        return "invalid", None, "the envelope has no structured_output", recorded
    problem = validate(payload)
    if problem:
        return "invalid", None, problem, recorded
    return "ok", payload, "", recorded


def decide(status, payload, detail, scanned):
    """Return (decision, exit_code, reason, findings)."""
    model = [dict(f, source="model") for f in payload["findings"]] if status == "ok" else []
    seen = {(f["file"], f["category"]) for f in scanned if f["severity"] == "BLOCKER"}
    findings = scanned + [f for f in model if not (f["severity"] == "BLOCKER" and (f["file"], f["category"]) in seen)]
    blockers = [f for f in findings if f["severity"] == "BLOCKER"]
    if blockers:
        return "BLOCK", BLOCK, "%d blocker(s)" % len(blockers), findings
    if status == "invalid":
        return "INVALID", INVALID, detail, findings
    if status == "inconclusive":
        return "INCONCLUSIVE", INCONCLUSIVE, detail, findings
    return "PASS", PASS, "no blockers", findings


def render(decision, reason, findings, recorded):
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
    lines = ["## Claude review gate: **%s**" % decision, "",
             "%s. BLOCKER %d, SHOULD_FIX %d, NITPICK %d." % (reason, counts["BLOCKER"], counts["SHOULD_FIX"], counts["NITPICK"])]
    if recorded:
        lines += ["", "_The model review used here is a RECORDED SAMPLE, not a live call._"]
    if findings:
        lines.append("")
        for f in sorted(findings, key=lambda f: SEVERITIES.index(f["severity"])):
            where = "%s:%d" % (f["file"], f["line"]) if f["line"] else f["file"]
            lines.append("- **%s** `%s` (found by %s): %s" % (f["severity"], where, f["source"], f["title"]))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", help="review JSON from run_review.py (missing file means INCONCLUSIVE)")
    parser.add_argument("--diff", required=True)
    parser.add_argument("--summary", help="append the markdown summary to this file")
    parser.add_argument("--markdown-out", help="also write the markdown summary to this file")
    args = parser.parse_args(argv)
    status, payload, detail, recorded = read_review(args.review)
    decision, code, reason, findings = decide(status, payload, detail, scan(args.diff))
    text = render(decision, reason, findings, recorded)
    print(text)
    for target, mode in ((args.summary, "a"), (args.markdown_out, "w")):
        if target:
            with open(target, mode, encoding="utf-8") as handle:
                handle.write(text)
    print("GATE %s (exit %d)" % (decision, code))
    return code


if __name__ == "__main__":
    sys.exit(main())
