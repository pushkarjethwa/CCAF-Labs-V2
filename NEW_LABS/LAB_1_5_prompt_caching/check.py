"""Run after lab.py. Prints [PASS]/[FAIL] lines. Standard library only. Exit code 0 means all passed."""
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
plain, cached, with_time = (evidence[k]["calls"] for k in ("uncached", "cached", "with_time"))

check(all(c["cache_write"] == 0 and c["cache_read"] == 0 for c in plain), "run 1: nothing cached when the system prompt is a plain string")
check(cached[0]["cache_write"] > 0, "run 2: the first call WROTE the cache (cache_write > 0)", f"cache_write={cached[0]['cache_write']}")
check(all(c["cache_read"] > 0 for c in cached[1:]), "run 2: every later call READ the cache (cache_read > 0)", str([c["cache_read"] for c in cached[1:]]))
saving = 1 - evidence["cached"]["total_cost_usd"] / evidence["uncached"]["total_cost_usd"]
check(saving >= 0.4, "run 2: caching cut the total cost by at least 40%", f"{saving:.0%}")
check(all(c["cache_read"] > 0 for c in with_time), "run 3: a changing time AFTER the cached block still hits the cache", str([c["cache_read"] for c in with_time]))
check(all(c["answer"].strip() for c in plain + cached + with_time), "every call returned an answer")

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
