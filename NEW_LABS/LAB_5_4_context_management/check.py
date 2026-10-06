"""Run while you work.   python check.py
Part A tests YOUR functions on hand-made messages (no API key). Part B reads evidence/evidence.json from `python lab.py`.
Fails on the starter by design. Exit code 0 means every check passed."""
import json
import pathlib
import sys

import lab

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


big = "FINDING X: the cause.\n" + "noise line\n" * 100
history = [{"role": "user", "content": big}, {"role": "assistant", "content": "ok " * 200}, {"role": "user", "content": big},
           {"role": "assistant", "content": "fine"}, {"role": "user", "content": big}, {"role": "assistant", "content": "done"}]
print("== Part A: your functions on hand-made messages (no key) ==")
check(lab.estimate_tokens([{"role": "user", "content": "x" * 400}]) == 100, "TODO 1: 400 characters estimate to 100 tokens", str(lab.estimate_tokens([{"role": "user", "content": "x" * 400}])))
check(lab.estimate_tokens([{"role": "user", "content": [{"type": "text", "text": "y" * 40}]}]) == 10, "TODO 1: handles a message whose content is a list of blocks")
snapshot = json.dumps(history)
shrunk = lab.compact(history, keep_last=2)
check(json.dumps(history) == snapshot, "TODO 2: the input list is not modified")
check(len(shrunk) == len(history), "TODO 2: same number of messages (roles keep alternating)")
check(shrunk[0]["content"].startswith("[compacted]") and "FINDING X: the cause." in shrunk[0]["content"] and len(shrunk[0]["content"]) < 100,
      "TODO 2: an old bulky user message shrinks to its first line, which keeps the finding")
check(shrunk[1]["content"] == history[1]["content"] and shrunk[3]["content"] == "fine", "TODO 2: assistant messages are never changed")
check(shrunk[-2:] == history[-2:], "TODO 2: the last 2 messages are untouched, even though the last user message is bulky")
check(lab.compact([{"role": "user", "content": "short"}, {"role": "assistant", "content": "a"}], keep_last=0)[0]["content"] == "short", "TODO 2: short messages stay as they are")
check(lab.estimate_tokens(shrunk) < lab.estimate_tokens(history) / 2, "compaction really reduces the estimated size", f"{lab.estimate_tokens(history)} -> {lab.estimate_tokens(shrunk)}")

if not EVIDENCE_FILE.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your real run (evidence.json) ==")
evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
plain, compacted = evidence["plain"], evidence["compacted"]
check(plain["input_tokens_per_call"] == sorted(plain["input_tokens_per_call"]), "without compaction the input grows on every call", str(plain["input_tokens_per_call"]))
check(compacted["total"] <= 0.7 * plain["total"], "with compaction total input tokens are at least 30% lower", f"{compacted['total']} vs {plain['total']}")
check(compacted["peak"] < plain["peak"], "with compaction the peak context is smaller", f"{compacted['peak']} vs {plain['peak']}")
answer = compacted["final_answer"].lower()
check("tls" in answer and "disk" in answer, "with compaction Claude still answers about reports 2 and 9 (TLS certificate, full disk)", compacted["final_answer"][:100])
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
