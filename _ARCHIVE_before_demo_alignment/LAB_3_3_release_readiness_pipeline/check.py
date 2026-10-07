"""check.py - Part A tests YOUR functions (no key needed). Part B checks the saved results of `python lab.py`.

Each line says what is expected in plain words. Exit code 0 = everything passed.
"""
import json
import sys

import lab
from lab import StageValidationError, ToolError

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"  ({detail})" if detail and not ok else ""))


def raises_stage(fn, stage):
    try:
        fn()
    except StageValidationError as err:
        return err.stage == stage
    except Exception:
        return False
    return False


def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as err:  # a crash in student code is a failed check, not a crashed checker
        return f"crashed: {err!r}"


# ---------------------------------------------------------------- PART A: your functions
print("PART A - your functions, tested with hand-made inputs (no API key)\n")
tickets = [{"ticket_id": "T-1"}, {"ticket_id": "T-2"}]
good = {"items": [{"ticket_id": "T-1", "category": "bugfix", "risk": "low"}, {"ticket_id": "T-2", "category": "feature", "risk": "high"}]}


def variant(**change):
    items = [dict(i) for i in good["items"]]
    items[0].update(change)
    return {"items": items}


print("TODO 1 - validate_extract")
check(safe(lab.validate_extract, good, tickets) is None, "a correct answer passes")
check(raises_stage(lambda: lab.validate_extract({"items": []}, tickets), "extract"), "an empty answer is rejected")
check(raises_stage(lambda: lab.validate_extract(variant(category="schema_change"), tickets), "extract"), "a category that is not allowed is rejected")
check(raises_stage(lambda: lab.validate_extract(variant(risk="severe"), tickets), "extract"), "a risk that is not allowed is rejected")
check(raises_stage(lambda: lab.validate_extract(variant(ticket_id="T-9"), tickets), "extract"), "an unknown ticket id is rejected")
check(raises_stage(lambda: lab.validate_extract({"items": good["items"][:1]}, tickets), "extract"), "a missing ticket is rejected")
check(raises_stage(lambda: lab.validate_extract({"items": good["items"] + good["items"][:1]}, tickets), "extract"), "a ticket listed twice is rejected")

print("\nTODO 2 - validate_enrich")
enrich_ok = {"ci": {"pipeline_status": "passed"}, "deps": {"critical": 0, "high": 1}, "oncall": {"primary": {"name": "A"}}}
check(safe(lab.validate_enrich, enrich_ok) is None, "complete evidence passes")
check(raises_stage(lambda: lab.validate_enrich({**enrich_ok, "ci": {}}), "enrich"), "an empty CI record is rejected")
check(raises_stage(lambda: lab.validate_enrich({**enrich_ok, "deps": {"critical": 0}}), "enrich"), "a dependency scan without a 'high' count is rejected")
check(raises_stage(lambda: lab.validate_enrich({**enrich_ok, "oncall": {}}), "enrich"), "no on-call engineer is rejected")

print("\nTODO 3 - classify")
check(safe(lab.classify, StageValidationError("extract", "x", "m")) == "reasoning", "a model answer that breaks a rule is a 'reasoning' error")
check(safe(lab.classify, StageValidationError("enrich", "x", "m")) == "tool", "an unusable tool answer is a 'tool' error")
check(safe(lab.classify, ToolError("E", 503, "m")) == "environment", "status 503 is an 'environment' error")
check(safe(lab.classify, ToolError("E", 429, "m")) == "environment", "status 429 is an 'environment' error")
check(safe(lab.classify, ToolError("E", 408, "m")) == "environment", "status 408 is an 'environment' error")
check(safe(lab.classify, ToolError("E", 404, "m")) == "tool", "status 404 is a 'tool' error")
check(safe(lab.classify, ToolError("E", 422, "m")) == "tool", "status 422 is a 'tool' error")
check(safe(lab.classify, ValueError("503 unavailable")) == "unknown", "an unrelated exception is 'unknown', whatever its text says")

print("\nTODO 4 - backoff_delay")
delays = [safe(lab.backoff_delay, n) for n in (1, 2, 3)]
check(delays == [0.5, 1.0, 2.0], "waits double: 0.5, 1.0, 2.0 seconds", f"got {delays}")

print("\nTODO 5 - cache_is_usable")
release = {"version": "3.1.0"}
check(safe(lab.cache_is_usable, {"for_version": "3.1.0"}, release) is True, "a cache for the same version is usable")
check(safe(lab.cache_is_usable, {"for_version": "3.0.4"}, release) is False, "a cache for an older version is NOT usable")
check(safe(lab.cache_is_usable, None, release) is False, "no cache is not usable")

print("\nTODO 6 - decide_recovery")
H = {"expected_id": "REL-1"}
policy = [
    (("reasoning", 1, None, False), "corrective_reprompt"), (("reasoning", 2, None, False), "corrective_reprompt"),
    (("reasoning", 3, None, False), "escalate"),
    (("tool", 1, H, False), "retry_changed_args"), (("tool", 2, H, False), "escalate"), (("tool", 1, None, False), "escalate"),
    (("environment", 1, None, False), "backoff_retry"), (("environment", 3, None, True), "backoff_retry"),
    (("environment", 4, None, True), "fallback_cache"), (("environment", 4, None, False), "pause_alert"),
    (("unknown", 1, None, False), "escalate"),
]
for args, expected in policy:
    got = safe(lab.decide_recovery, *args)
    check(got == expected, f"{args[0]:<11} tries={args[1]} hint={'yes' if args[2] else 'no '} cache_ok={str(args[3]):<5} -> {expected}", f"got {got!r}")

part_a_ok = all(results)

# ---------------------------------------------------------------- PART B: the real run
print("\nPART B - the eight scenarios from `python lab.py`\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/scenarios.json not found - run `python lab.py` (needs ANTHROPIC_API_KEY), then run this again.")
elif not part_a_ok:
    print("[SKIP] fix Part A first; the scenarios call your functions, so they would only repeat the same mistakes.")
else:
    rows = {r["scenario_id"]: r for r in json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))}
    ALL = ["extract", "enrich", "assess", "report"]
    # id: (stage_failed, error_class, recovery, attempts, outcome, stages_run)
    expected_rows = {
        "F0": (None, None, None, 1, "completed", ALL),
        "F1": ("enrich", "tool", "retry_changed_args", 2, "completed", ALL),
        "F2": ("enrich", "tool", "escalate", 1, "escalated", ["extract"]),
        "F3": ("extract", "reasoning", "corrective_reprompt", 2, "completed", ALL),
        "F4": ("extract", "reasoning", "escalate", 3, "escalated", []),
        "F5": ("enrich", "environment", "backoff_retry", 3, "completed", ALL),
        "F6": ("enrich", "environment", "fallback_cache", 4, "completed_degraded", ALL),
        "F7": ("enrich", "environment", "pause_alert", 4, "paused", ["extract"]),
    }
    for sid, want in expected_rows.items():
        r = rows.get(sid)
        if r is None:
            check(False, f"{sid} was run", "missing - run all scenarios: python lab.py")
            continue
        got = (r["stage_failed"], r["error_class"], r["recovery"], r["attempts"], r["outcome"], r["stages_run"])
        names = ("stage", "class", "recovery", "attempts", "outcome", "stages_run")
        diff = [f"{n}: expected {w!r}, got {g!r}" for n, w, g in zip(names, want, got) if w != g]
        check(not diff, f"{sid} {r['label']}", "; ".join(diff))
        if diff and sid in ("F0", "F1", "F2", "F5", "F6", "F7") and r["stages_run"][:1] != ["extract"]:
            print("       note: the real model's EXTRACT answer failed validation here - this is not an injected fault. Re-run `python lab.py`.")
    if all(s in rows for s in expected_rows):
        sleeps = [rows[s]["backoff_sleeps"] for s in ("F5", "F6")]
        check(sleeps[0] == [0.5, 1.0] and sleeps[1] == [0.5, 1.0, 2.0], "backoff waits grow: F5 [0.5, 1.0], F6 [0.5, 1.0, 2.0]", f"got {sleeps}")
        check(len(rows["F7"]["alerts"]) == 1 and rows["F7"]["verdict"] is None, "F7 raises exactly one alert and gives no verdict")
        check("assess" not in rows["F2"]["stages_run"], "F2 never reaches ASSESS (no verdict from empty evidence)")
        check(rows["F6"]["verdict"] != "go", "F6 (degraded evidence) is never a clean 'go'", f"verdict {rows['F6']['verdict']!r}")
        check(all(r["attempts"] <= lab.MAX_ENV_ATTEMPTS for r in rows.values()), f"every scenario stops within {lab.MAX_ENV_ATTEMPTS} attempts")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
