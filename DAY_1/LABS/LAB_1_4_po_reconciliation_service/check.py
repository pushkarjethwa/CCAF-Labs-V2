"""Run after (or while) you work on lab.py.   python check.py
Part A needs no API key. Part B reads evidence/evidence.json, which `python lab.py` writes. Exit code 0 means all passed."""
import json
import pathlib
import sys

import lab
from claude_client import MODEL_FAST

HERE = pathlib.Path(__file__).parent
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


policy = (lab.DATA / "procurement_policy.md").read_text(encoding="utf-8")
invoices = {i["invoice_id"]: i for i in json.loads((lab.DATA / "invoices.json").read_text(encoding="utf-8"))}
planted = json.loads((lab.DATA / "planted_bad_decisions.json").read_text(encoding="utf-8"))

print("== Part A: your code on saved data (no API key needed) ==")
check(len(policy) / 4 >= 5000, "policy prefix is >= 5,000 tokens by chars/4 (above the Haiku 4096 cache floor)", f"~{len(policy) // 4}")
check(json.dumps(lab.build_system(policy)) == json.dumps(lab.build_system(policy)),
      "TODO 1: system prompt is identical across two builds (nothing time-based in the cached prefix)")
codes = lab.policy_codes(policy)
for case in planted:
    issues = lab.validate_decision(case["decision"], invoices[case["invoice_id"]], codes)
    if case["expect_rule"] is None:
        check(not issues, f"validator accepts valid case '{case['case']}'", str(issues))
    else:
        check(any(i.startswith(case["expect_rule"]) for i in issues), f"validator reports {case['expect_rule']} for '{case['case']}'", str(issues)[:80])
try:
    small = lab.budget_gate(6000, 300, 40, MODEL_FAST, 0.0001)
    big = lab.budget_gate(6000, 300, 40, MODEL_FAST, 100.0)
    floor = lab.budget_gate(1000, 300, 40, MODEL_FAST, 100.0)
    gate_ok = small["ok"] is False and big["ok"] is True and big["cache_eligible"] is True and floor["cache_eligible"] is False
except Exception as error:
    gate_ok = False
    print("gate error:", repr(error))
check(gate_ok, "TODO 3b: budget_gate refuses an over-budget batch, accepts a small one, flags a prefix below the cache floor")

evidence_file = HERE / "evidence" / "evidence.json"
if not evidence_file.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: the live run (evidence.json) ==")
evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
call1, call2 = evidence["cache_check"]["call1_usage"], evidence["cache_check"]["call2_usage"]
check(call1["cache_creation_input_tokens"] > 0, "call 1 wrote the cache (cache_creation_input_tokens > 0)", str(call1["cache_creation_input_tokens"]))
check(call2["cache_read_input_tokens"] > 0, "call 2 read the cache (cache_read_input_tokens > 0)", str(call2["cache_read_input_tokens"]))

counts = evidence["token_counts"]
tokens_ok = set(counts) == {"fast", "balanced"} and all(c["prefix_tokens"] > 0 and c["avg_request_tokens"] > c["prefix_tokens"] for c in counts.values())
check(tokens_ok, "TODO 3a: count_tokens recorded for two models with prefix and per-request counts")
check(tokens_ok and all(c["cache_eligible"] == (c["prefix_tokens"] >= c["cache_floor"]) for c in counts.values()), "cache_eligible agrees with each model's cache floor")
gate = evidence["budget_gate"]
check(gate["projected_cost_usd"] is not None and gate["ok"] is True and gate["budget_usd"] == lab.RUN_BUDGET_USD, "budget gate ran before the batch and passed",
      str(gate["projected_cost_usd"]))

rows = evidence["projection"]["rows"]
shape = len(rows) == 8 and {(r["model_alias"], r["scenario"]) for r in rows} == {(a, s) for a in ("fast", "balanced") for s in ("normal", "cached", "batch", "batch_cached")}
check(shape, "projection: 100,000 invoices a month x 2 models x 4 scenarios", f"{len(rows)} rows")
ordered = shape
for alias in ("fast", "balanced") if shape else ():
    cost = {r["scenario"]: r["monthly_cost_usd"] for r in rows if r["model_alias"] == alias}
    ordered = ordered and cost["batch_cached"] < cost["batch"] < cost["normal"] and cost["cached"] < cost["normal"]
check(ordered, "projection ordering is sane: batch_cached < batch < normal and cached < normal")

batch = evidence["batch"]
by_id = batch["map"]
check(batch["join_key"] == "custom_id" and set(by_id) == set(invoices) and batch["n_results"] == batch["n_requests"] == len(invoices),
      "TODO 2: batch map is complete (40 of 40) and joined by custom_id", f"{len(by_id)} entries, key={batch['join_key']}")
wrong = [k for k, e in by_id.items() if e.get("decision") and e["decision"].get("invoice_id") != k]
check(bool(by_id) and not wrong, "every decision belongs to its key (joined by id, not position)", f"{len(wrong)} mismatched")
check(sum(e.get("usage", {}).get("cache_read_input_tokens", 0) for e in by_id.values()) > 0, "batch results show cache_read_input_tokens > 0 (best effort)")
check(evidence["validation"]["n_checked"] == len(invoices), "validation ran on all 40 decisions",
      f"invalid={evidence['validation']['n_invalid']} correct={evidence['validation']['valid_and_correct_vs_truth']}")
measured = evidence["measured_cost_40"]
check(measured["cached_usd"] < measured["normal_usd"] and measured["batch_cached_usd"] < measured["batch_usd"],
      "measured on the real 40 results: caching lowers cost", f"normal={measured['normal_usd']:.4f} cached={measured['cached_usd']:.4f}")

memo = HERE / "evidence" / "capstone_day1.md"
text = memo.read_text(encoding="utf-8") if memo.exists() else ""
low = text.lower()
family = "haiku" if evidence["service_model_alias"] == "fast" else "sonnet"
check(len(text.split()) >= 150 and "what the service does" in low and "model choice" in low and family in low and "cache" in low and "batch" in low and "$" in text,
      "capstone_day1.md: >= 150 words, 'What the service does' and 'Model choice' sections, names the model class, cites $ figures",
      f"{len(text.split())} words" if text else "file missing")

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
