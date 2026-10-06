"""Run after (or while) you work on lab.py.   python check.py

Part A  checks YOUR validators on saved sample data. No API key needed.
Part B  checks the retry loop from evidence/evidence.json (written by `python lab.py`). Skipped until that file exists.
Standard library only. Exit code 0 means every check passed.
"""
import json
import pathlib
import re
import sys

import lab

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
EVIDENCE_FILE = HERE / "evidence" / "evidence.json"
REQUIRED_LOG_FIELDS = {"email_id", "attempt", "model", "valid", "failure_rules", "failures", "feedback", "input_tokens", "output_tokens"}
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


purchase_orders = {po["po_number"]: po for po in load("purchase_orders.json")["purchase_orders"]}
email_text = {email["email_id"]: email["text"] for email in load("receiving_emails.json")}
truth = load("ground_truth.json")
planted = load("planted_bad_outputs.json")


def run_validators(extraction, text):
    try:
        return lab.validate_extraction(extraction, text, purchase_orders, lab.TODAY)
    except Exception as error:  # a crashing validator counts as a failing validator
        return [{"rule": "CRASH", "message": repr(error)}]


print("== Part A: your validators (no API key needed) ==")
for case in planted:
    text = case.get("email_text") or email_text[case["email_id"]]
    rules = {failure["rule"] for failure in run_validators(case["extraction"], text)}
    check(case["expect_rule"] in rules, f"fires {case['expect_rule']} on planted case '{case['case']}'", f"got {sorted(rules) or 'nothing'}")

false_alarms = {eid: [f["rule"] for f in run_validators(extraction, email_text[eid])] for eid, extraction in truth.items()}
false_alarms = {eid: rules for eid, rules in false_alarms.items() if rules}
check(not false_alarms, "no false alarms: all 20 correct extractions pass", str(false_alarms) if false_alarms else "")
sample = run_validators(planted[0]["extraction"], email_text[planted[0]["email_id"]])
check(all({"rule", "path", "expected", "got", "message"} <= set(f) for f in sample), "failures carry rule/path/expected/got/message")

if not EVIDENCE_FILE.exists():
    print("\n(Part B skipped: run `python lab.py` first to create evidence/evidence.json)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your retry loop (from evidence.json) ==")
evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
cap = lab.MAX_ATTEMPTS
log = evidence["attempt_log"]
by_email = {}
for entry in log:
    by_email.setdefault(entry["email_id"], []).append(entry)

check(not evidence["runaway"], "no email hit the runaway safety net", str(evidence["runaway"]))
too_many = [e["email_id"] for e in evidence["emails"] if e["attempts"] > cap]
check(not too_many, f"no email used more than {cap} attempts", str(too_many))
check(bool(log), "attempt log is not empty")
missing = [(e.get("email_id"), e.get("attempt")) for e in log if not REQUIRED_LOG_FIELDS <= set(e)]
check(bool(log) and not missing, "every log entry has the required fields", str(missing[:3]))
check(bool(log) and all(len(by_email.get(e["email_id"], [])) == e["attempts"] for e in evidence["emails"]),
      "one log entry per attempt for every email")
feedback_ok = bool(log)
for entries in by_email.values():
    for previous, current in zip(entries, entries[1:]):
        if not all(rule in current["feedback"] for rule in previous["failure_rules"]):
            feedback_ok = False
check(feedback_ok and any(len(v) > 1 for v in by_email.values()),
      "each retry's feedback names the rules that failed on the previous attempt")
exhausted_ok = all(
    (e["status"] == "needs_review") == (e["attempts"] == cap and not by_email[e["email_id"]][-1]["valid"])
    and (e["status"] != "needs_review" or e["extraction"] is None)
    for e in evidence["emails"] if by_email.get(e["email_id"]))
check(bool(log) and exhausted_ok, "needs_review is set only when every attempt failed, and then extraction is None")
slipped = [e["email_id"] for e in evidence["emails"] if e["status"] == "accepted" and run_validators(e["extraction"], email_text[e["email_id"]])]
check(not slipped, "every accepted extraction passes your validators", str(slipped))
invented = [e["email_id"] for e in evidence["emails"] if e["status"] == "accepted" and e["extraction"]["po_number"]
            and re.sub(r"\D", "", e["extraction"]["po_number"]) not in re.findall(r"\d+", email_text[e["email_id"]])]
check(not invented, "no accepted extraction has an invented PO number", str(invented))
print("info: rules that fired during the run:", sorted(evidence["validator_hits"]) or "none (a very good model may need no retries)")

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
