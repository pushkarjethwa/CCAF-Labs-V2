"""Run after lab.py. Prints [PASS]/[FAIL] lines. Standard library only."""
import json
import pathlib
import sys

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


if not EVIDENCE_FILE.exists():
    sys.exit(f"[FAIL] {EVIDENCE_FILE} not found - run lab.py first")
evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))

check(evidence["first_answer"].strip(), "STEP 1: Claude answered")
check(evidence["first_stop_reason"] == "end_turn", "STEP 1: stop_reason is end_turn", evidence["first_stop_reason"])
check(evidence["second_answer"].strip(), "STEP 2: follow-up answered")
check(evidence["was_cut_off"] and evidence["truncated_stop_reason"] == "max_tokens",
      "STEP 3: max_tokens=20 cut the answer and you detected it", evidence["truncated_stop_reason"])
check("first message" in evidence["error_text"].lower() or "user" in evidence["error_text"].lower(),
      "STEP 4: BadRequestError caught and message saved", evidence["error_text"][:60])
check(0 < evidence["total_cost_usd"] < 0.05, "STEP 5: total cost is a small positive number", f"${evidence['total_cost_usd']:.6f}")

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
