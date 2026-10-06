"""Run after `python lab.py` and after you write evidence/decision.md.   python check.py   (no API key needed)
Exit code 0 means every check passed."""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
EVIDENCE_DIR = HERE / "evidence"
FIELDS = ["job_family", "level", "employment_type"]
ENTRY_KEYS = ["alias", "model_id", "rows_evaluated", "exact_accuracy", "field_accuracy", "schema_compliance", "avg_latency_s",
              "avg_input_tokens", "avg_output_tokens", "total_cost_usd", "cost_per_1k_usd", "hard_accuracy"]
ALIAS_WORDS = {"haiku": "fast", "fast": "fast", "sonnet": "balanced", "balanced": "balanced", "opus": "premium", "premium": "premium"}
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def close(a, b, rel=1e-6):
    return abs(a - b) <= max(1e-9, rel * max(abs(a), abs(b)))


def first_alias(text):
    """The model name that appears first in a line of the memo."""
    found = [(m.start(), alias) for word, alias in ALIAS_WORDS.items() if (m := re.search(r"\b" + word + r"\b", text, re.I))]
    return min(found)[1] if found else None


evidence_file = EVIDENCE_DIR / "evidence.json"
if not evidence_file.exists():
    sys.exit("[FAIL] evidence/evidence.json not found - run `python lab.py` first")
evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
rows = {}
for line in (HERE / "data" / "roster.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        row = json.loads(line)
        rows[row["id"]] = row
hard_ids = sorted(rid for rid, row in rows.items() if row["hard"])
models, outputs = evidence["models"], evidence["outputs"]

full = [alias for alias, e in models.items() if e["rows_evaluated"] == len(rows)]
check(len(full) >= 2, ">= 2 models measured on all 40 rows (TODO 1)", f"got {sorted(full)}")
premium = models.get("premium")
check(bool(premium) and sorted(premium["row_ids"]) == hard_ids, "premium model measured on exactly the 8 hard rows (TODO 2)")
check(bool(premium) and evidence["premium_calls"] <= 8 and evidence["premium_calls"] == premium["rows_evaluated"], "premium calls <= 8",
      f"calls={evidence['premium_calls']}")
keys_ok = bool(models) and all(all(k in e for k in ENTRY_KEYS) for e in models.values())
check(keys_ok, "results table has accuracy / compliance / latency / tokens / cost for every model")

recomputed = keys_ok
for alias, entry in (models.items() if keys_ok else []):
    ids, outs = entry["row_ids"], outputs.get(alias, {})
    if sorted(outs) != sorted(ids) or not ids:
        recomputed = False
        continue
    exact = sum(1 for rid in ids if outs[rid]["valid"] and all(outs[rid]["pred"][f] == rows[rid]["truth"][f] for f in FIELDS))
    valid = sum(1 for rid in ids if outs[rid]["valid"])
    recomputed &= close(exact / len(ids), entry["exact_accuracy"], 1e-9) and close(valid / len(ids), entry["schema_compliance"], 1e-9)
check(recomputed, "accuracy and schema-compliance numbers match the stored predictions vs ground truth")
check(keys_ok and all(close(e["cost_per_1k_usd"], e["total_cost_usd"] / e["rows_evaluated"] * 1000) and e["total_cost_usd"] > 0 for e in models.values()),
      "cost per 1k rows = total cost / rows * 1000, and cost > 0")

projection = evidence["projection_100k"]
proj_ok = keys_ok and set(projection) == set(models)
for alias, entry in (models.items() if proj_ok else []):
    per_row = (entry["avg_input_tokens"] * entry["price_in_per_mtok"] + entry["avg_output_tokens"] * entry["price_out_per_mtok"]) / 1_000_000
    proj_ok &= abs(per_row * 100_000 - projection[alias]["sync_usd"]) <= 0.01
    proj_ok &= abs(per_row * 100_000 * 0.5 - projection[alias]["batch_usd"]) <= 0.01
check(proj_ok, "100,000-row projection (sync and batch) matches the measured average tokens")

code = "\n".join(line.split("#")[0] for line in (HERE / "lab.py").read_text(encoding="utf-8").splitlines())
check(not re.search(r"\btemperature\s*=", code.split("def run_probe")[0]), "no temperature= argument in the classifier code (gotcha avoided)")
probe_file = EVIDENCE_DIR / "param_probe.json"
probe = json.loads(probe_file.read_text(encoding="utf-8"))["results"] if probe_file.exists() else {}
check(probe.get("kwarg_temperature_haiku") == "TypeError" and probe.get("extra_body_temperature_sonnet") == "BadRequestError",
      "param probe recorded: temperature kwarg -> TypeError, temperature on Sonnet -> BadRequestError (python lab.py --probe)", str(probe or "missing"))

memo_file = EVIDENCE_DIR / "decision.md"
memo = memo_file.read_text(encoding="utf-8") if memo_file.exists() else ""
check(len(memo.split()) >= 60 and "[[" not in memo, "decision memo exists, >= 60 words, no unfilled [[placeholders]]")
decision = re.search(r"^\W*decision\W*:\s*(.+)$", memo, re.I | re.M)
chosen = first_alias(decision.group(1)) if decision else None
check(chosen in models, "memo has a 'Decision:' line naming a model you measured", str(chosen))
rejected = [first_alias(line) for line in memo.splitlines() if re.match(r"^\W*rejected\W*:", line, re.I) and re.search(r"\d", line)]
check(any(a and a != chosen for a in rejected), "memo has a 'Rejected:' line for a different model with a numeric reason")
dollars = [float(x.replace(",", "").rstrip(".")) for x in re.findall(r"\$\s*([0-9][0-9,]*\.?[0-9]*)", memo)]
chosen_projection = projection.get(chosen, {}) if chosen else {}
check(bool(chosen_projection) and any(abs(d - v) <= 0.02 * v + 0.01 for d in dollars for v in (chosen_projection["sync_usd"], chosen_projection["batch_usd"])),
      "memo quotes the chosen model's 100,000-row projection (sync or batch) within 2% of the evidence")

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
