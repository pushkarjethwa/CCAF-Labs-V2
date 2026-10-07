"""Run after `python lab.py`.   python check.py     (standard library + jsonschema; no API key needed)

Thresholds (live model): final overall field accuracy >= 0.80 and BREAK_IT >= 3/5. A typical live range is 0.80-0.95;
measure your own and write it in your notes. Exit code 0 means every check passed.
"""
import json
import pathlib
import re
import sys

import lab
from schema_lint import lint

HERE = pathlib.Path(__file__).parent
EVIDENCE_FILE = HERE / "evidence" / "evidence.json"
MIN_ACCURACY, MIN_ADVERSARIAL = 0.80, 3
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


if not EVIDENCE_FILE.exists():
    sys.exit("[FAIL] evidence/evidence.json not found - run `python lab.py` first")
evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
tickets = {t["id"]: t for t in lab.load_jsonl(lab.DATA / "tickets.jsonl")}
versions = evidence["versions"]
measured = [v for v in versions if not v["rejected"]]

check(len(measured) >= 4, ">= 4 versions with measured accuracy", str([v["version"] for v in measured]))
check(len(versions) >= 2 and all(a["fingerprint"] != b["fingerprint"] for a, b in zip(versions, versions[1:])),
      "every version differs from the previous one (prompt or schema content changed)")

recomputed = bool(measured)
for version in measured:  # recompute the numbers from the stored model outputs
    outputs = version["outputs"]
    if sorted(outputs) != sorted(tickets):
        recomputed = False
        continue
    hits = sum(sum(lab.score_ticket(o["pred"], tickets[tid]["truth"]).values()) for tid, o in outputs.items())
    compliant = sum(1 for o in outputs.values() if o["pred"] is not None and not lab.schema_errors(o["pred"], lab.TARGET))
    recomputed &= abs(hits / (len(tickets) * len(lab.FIELDS)) - version["overall_field_accuracy"]) < 1e-9
    recomputed &= abs(compliant / len(tickets) - version["schema_compliance"]) < 1e-9
check(recomputed, "stored accuracy and compliance numbers match the stored outputs vs ground truth")

final = versions[-1]
accuracy = 0.0 if final["rejected"] else final["overall_field_accuracy"]
check(accuracy >= MIN_ACCURACY, f"final overall field accuracy >= {MIN_ACCURACY}", f"got {accuracy:.3f}")
steps = [v["overall_field_accuracy"] for v in versions]
check(len(steps) >= 4 and steps[-1] >= steps[0] + 0.15 and all(b >= a - 0.05 for a, b in zip(steps, steps[1:])),
      "accuracy never drops more than 0.05 between versions and the final is >= 0.15 above v0", " -> ".join(f"{s:.2f}" for s in steps))
check(final["schema_compliance"] >= 0.95, "final schema compliance >= 0.95 against data/target_schema.json", f"got {final['schema_compliance']:.3f}")

adversarial = evidence["adversarial"]
final_cases = adversarial.get(evidence["final_version"], {})
check(len(final_cases) == 5, "BREAK_IT results for all 5 cases on the final version")
passes = sum(r["pass"] for r in final_cases.values())
baseline_key = next((k for k in adversarial if k != evidence["final_version"]), None)
baseline = sum(r["pass"] for r in adversarial.get(baseline_key, {}).values()) if baseline_key else 0
check(passes >= MIN_ADVERSARIAL and passes >= baseline, f"final version passes >= {MIN_ADVERSARIAL}/5 BREAK_IT cases and no fewer than the baseline",
      f"final {passes}/5, baseline {baseline}/5")

schema_path = HERE / evidence["final_schema_file"]
issues = lint(json.loads(schema_path.read_text(encoding="utf-8"))) if schema_path.exists() else ["final schema file missing"]
check(not issues, "final schema lints clean (no unsupported keyword, additionalProperties false, required-but-nullable, enums match)", "; ".join(issues[:3]))

failed_file = HERE / "evidence" / "failed_cases.json"
ok = False
if failed_file.exists() and not final["rejected"]:
    listed = {(c["ticket_id"], c["field"]) for c in json.loads(failed_file.read_text(encoding="utf-8"))["failed_cases"] if c["version"] == final["version"]}
    expected = {(tid, field) for tid, o in final["outputs"].items() for field, good in lab.score_ticket(o["pred"], tickets[tid]["truth"]).items() if not good}
    ok = listed == expected
check(ok, "evidence/failed_cases.json lists exactly the failed (ticket, field) pairs of the final version")

prompt_path = HERE / evidence["final_prompt_file"]
prompt_words = " ".join(words(prompt_path.read_text(encoding="utf-8"))) if prompt_path.exists() else ""
leaked = [tid for tid, t in tickets.items() for w in [words(t["text"])]
          if any(" ".join(w[i:i + 8]) in prompt_words for i in range(max(len(w) - 7, 0)))]
check(bool(prompt_words) and not leaked, "final prompt does not copy ticket text from data/tickets.jsonl (no example leakage)", f"leaked: {leaked[:3]}")

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
