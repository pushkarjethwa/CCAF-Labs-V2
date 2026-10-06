"""Run after the stages.   python check.py
Part A needs no API key. Part B checks whichever evidence files exist (written by `python demo.py --stage N`).
It checks that the demo RAN CORRECTLY and the plumbing is sound. It does not grade model quality: model results vary by run and version.
Exit code 0 means every check passed."""
import json
import pathlib
import sys

import ap_data as data
import demo

EVIDENCE = pathlib.Path(__file__).parent / "evidence"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def load(name):
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


print("== Part A: dataset, scorer and validator (no API key) ==")
cases, truth, policy, vendors = data.load_cases(), data.load_truth(), data.load_policy(), data.load_vendors()
check(len(cases) == 24 and set(truth) == {c.case_id for c in cases}, "24 invoices, each with a ground-truth label")
legacy = data.score({c.case_id: data.legacy_label(c.invoice, vendors, policy) for c in cases}, truth, policy["error_weights"])
check(legacy.correct == 12 and (legacy.hold_caught, legacy.hold_total) == (1, 5), "legacy rules engine: 12/24 correct, hold recall 1/5", f"{legacy.correct}/24, {legacy.hold_caught}/{legacy.hold_total}")
check(all(t["rationale"][:40] not in c.view for c, t in ((c, truth[c.case_id]) for c in cases)), "the case view never contains the ground-truth rationale")
check(data.wilson_interval(12, 24)[0] < 0.5 < data.wilson_interval(12, 24)[1] and data.wilson_interval(12, 24)[1] - data.wilson_interval(12, 24)[0] > 0.3, "with n=24 the 95% interval is wide (that is the lesson)")
rows = json.loads((pathlib.Path(__file__).parent / "data" / "bad_outputs.json").read_text(encoding="utf-8"))
check(all(demo.check_output(r["text"], r["stop_reason"]).usable == r["usable"] for r in rows), "validator agrees with all 10 bad-output cases (incl. confidence 95 and empty reasons)")
check(demo.check_output('{"label": "low", "reasons": ["a"], "confidence": 95}').structural_ok and not demo.check_output('{"label": "low", "reasons": ["a"], "confidence": 95}').usable,
      "a schema-valid answer can still be unusable (confidence 95)")

found = [name for name in ("stage1.json", "stage2.json", "tournament.json", "routing.json", "final_report.json") if (EVIDENCE / name).exists()]
if not found:
    print("\n(Part B skipped: run `python demo.py --stage 1` and later stages first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print(f"\n== Part B: your runs ({', '.join(found)}) ==")
s1 = load("stage1.json")
if s1:
    check(set(s1["answers"]) == {"fast", "balanced", "premium"} and all(a.strip() for a in s1["answers"].values()), "stage 1: all three tiers answered in plain text")
    print(f"       info: truth={s1['truth']}, naive script read {s1['naive_labels']}")
s2 = load("stage2.json")
if s2:
    check(all(r["structural_ok"] for r in s2["part_a"].values()), "stage 2: all three tiers returned schema-valid JSON")
    check(s2["part_b"]["temperature_kwarg"] == "TypeError", "stage 2: temperature kwarg raised TypeError in the SDK", s2["part_b"]["temperature_kwarg"])
    others = {k: v for k, v in s2["part_b"].items() if k != "temperature_kwarg"}
    print(f"       info: forced tool_choice / extra_body outcomes on your models: {others}")
s3 = load("tournament.json")
if s3:
    tiers = s3["tiers"]
    check(all(len(t["results"]) == s3["n"] for t in tiers.values()), "stage 3: every tier classified every case", str({k: len(v["results"]) for k, v in tiers.items()}))
    check(all(sum(r["structural_ok"] for r in t["results"]) >= 0.9 * s3["n"] for t in tiers.values()), "stage 3: at least 90% of answers were schema-valid on every tier")
    check(tiers["fast"]["per_100k_usd"] < tiers["balanced"]["per_100k_usd"] < tiers["premium"]["per_100k_usd"], "stage 3: cost per 100k rises fast < balanced < premium",
          str({k: v["per_100k_usd"] for k, v in tiers.items()}))
    correct = {k: f"{v['correct']}/{v['n']}" for k, v in tiers.items()}
    hold = {k: v["hold_recall"] for k, v in tiers.items()}
    print(f"       info: correct {correct}  hold recall {hold}")
s4 = load("routing.json")
if s4:
    names = [s["name"] for s in s4["strategies"]]
    check("ROUTED cascade" in names and "Haiku-only" in names, "stage 4: routed cascade and Haiku-only strategies were compared")
    check(s4["routed"]["to_premium"] <= s4["routed"]["to_balanced"] <= s4["n"], "stage 4: premium sees no more cases than balanced, which sees no more than all")
    print(f"       info: recommendation = {s4['choice']}")
s5 = (EVIDENCE / "decisions.jsonl")
if s5.exists():
    decisions = [json.loads(line) for line in s5.read_text(encoding="utf-8").splitlines() if line.strip()]
    check(len(decisions) > 0 and all(d["queue"] for d in decisions), "stage 5: every case was routed to a queue and logged")
    check(all(d["needs_human"] for d in decisions if d["final_label"] is None), "stage 5: a case with no usable answer always goes to a human")
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
