"""check.py template: standard library only. Prints [PASS]/[FAIL] lines and a RESULT line.

Each lab's check.py copies this pattern. Exit code 0 means every check passed.
"""
import json
import pathlib
import sys

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {description}" + (f" ({detail})" if detail else ""))


if not EVIDENCE_FILE.exists():
    sys.exit(f"[FAIL] {EVIDENCE_FILE} not found - run lab.py first")
evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))

check(len(evidence.get("rows", [])) == 40, "40 rows classified", f"got {len(evidence.get('rows', []))}")

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
