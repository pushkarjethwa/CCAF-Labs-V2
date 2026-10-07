"""LAB 1.1 - HR roster classification: which Claude model is good enough, and what will it cost at scale?

Run:   python lab.py                 measure the models in PLAN on 40 rows
       python lab.py --probe         show which ways of sending `temperature` fail (a classic old-tutorial crash)
       python lab.py --rows-file data/break_rows.jsonl     try 3 hostile rows on the fast model (see BREAK_IT.md)
Check: python check.py               (after you also write evidence/decision.md)

You will run the same classifier on three model tiers, compare accuracy, speed and cost, project the cost for
100,000 rows from MEASURED tokens, and write a decision memo with one rejected alternative and a numeric reason.
Needs an API key. Your code changes here are TODO 1 and TODO 2 (STEP 2).
"""
import argparse
import json
import pathlib

import anthropic
from jsonschema import validators

HERE = pathlib.Path(__file__).parent
DATA_FILE = HERE / "data" / "roster.jsonl"
EVIDENCE = HERE / "evidence"

RECORDS_TO_PROJECT = 100_000
MAX_PREMIUM_CALLS = 8      # hard ceiling on the expensive model: it may only see the 8 rows flagged "hard"
MAX_TOKENS = 2048          # on Sonnet/Opus 5.5 hidden thinking tokens also count against max_tokens

# ----------------------------------------------------------------------------------------------
# STEP 0 (provided): what we ask Claude to produce and how we ask for it
# ----------------------------------------------------------------------------------------------
FAMILIES = ["ENGINEERING", "SALES_MARKETING", "FINANCE", "PEOPLE_OPS", "SUPPORT", "OPERATIONS", "LEGAL_COMPLIANCE"]
LEVELS = ["L1", "L2", "L3", "L4", "L5", "L6"]
EMP_TYPES = ["FULL_TIME", "PART_TIME", "CONTRACT", "CONTRACT_TO_HIRE", "INTERN"]
FIELDS = ["job_family", "level", "employment_type"]

SCHEMA = {
    "type": "object",
    "properties": {
        "job_family": {"type": "string", "enum": FAMILIES},
        "level": {"type": "string", "enum": LEVELS},
        "employment_type": {"type": "string", "enum": EMP_TYPES},
    },
    "required": FIELDS,
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You classify one HR roster record into job_family, level and employment_type.
Return only the JSON object. Free-text titles are messy; apply these rules.

job_family: ENGINEERING (software, QA, data, IT/infra), SALES_MARKETING, FINANCE (accounting, payroll),
PEOPLE_OPS (HR, recruiting), SUPPORT (customer support / success), OPERATIONS (warehouse, logistics,
facilities), LEGAL_COMPLIANCE. The title decides; the department text is only a hint.

level (seniority band, from the title):
 L1 intern, trainee, assistant, clerk | L2 junior/Jr., associate, coordinator, title ending in "I"
 L3 plain title with no seniority marker, title ending in "II" | L4 senior/Sr., title ending in "III"
 L5 lead, principal, staff, manager, senior manager | L6 director, senior director, head of, VP, chief
Acting / interim titles: classify the person's SUBSTANTIVE (permanent) title, ignoring "acting"/"interim".
If the title is only "Acting X", the note gives the substantive title. "Sr. (acting) X" -> the Sr. substantive role.

employment_type: FULL_TIME, PART_TIME, CONTRACT, CONTRACT_TO_HIRE, INTERN.
 - "FTE" or "1.0 FTE" is a workload unit = FULL_TIME; a fraction below 1.0 (0.5, 0.6, 0.8 FTE) = PART_TIME.
 - contract-to-hire, c2h, temp-to-perm, conversion pending = CONTRACT_TO_HIRE, UNLESS the note says it was
   already converted = FULL_TIME.
 - agency temp, contractor, consultant, 1099, vendor SOW with no conversion = CONTRACT.
 - intern / co-op / summer student = INTERN even if part-time."""


def load_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def user_message(row):
    return f"Record id: {row['id']}\nTitle: {row['title']}\nDepartment: {row['department']}\nNote: {row['note']}"


# ----------------------------------------------------------------------------------------------
# STEP 1 (provided): classify ONE row. This is the Claude call - see claude_client.py.
# output_config.format asks for JSON that matches SCHEMA. There is NO temperature here on purpose (see --probe).
# ----------------------------------------------------------------------------------------------
def classify(model, row):
    from claude_client import ask  # imported here so check.py works without an API key
    response = ask([{"role": "user", "content": user_message(row)}], system=SYSTEM_PROMPT, model=model, max_tokens=MAX_TOKENS,
                   output_config={"format": {"type": "json_schema", "schema": SCHEMA}})
    return response


def parse_output(response):
    """Return (prediction_or_None, is_valid, reason)."""
    if response.stop_reason != "end_turn":
        return None, False, f"stop_reason={response.stop_reason}"
    text = "".join(block.text for block in response.content if block.type == "text")
    try:
        prediction = json.loads(text)
    except json.JSONDecodeError as error:
        return None, False, f"invalid JSON: {error.msg}"
    problems = list(validators.validator_for(SCHEMA)(SCHEMA).iter_errors(prediction))
    if problems:
        return None, False, problems[0].message
    return prediction, True, "ok"


def run_model(alias, model, rows):
    """Classify every row with one model. Returns the outputs plus token, latency and cost numbers."""
    import time
    from claude_client import cost_usd
    outputs, tokens_in, tokens_out, seconds, cost = {}, 0, 0, 0.0, 0.0
    for row in rows:
        if alias == "premium" and not row.get("hard"):
            raise RuntimeError(f"the premium model is restricted to hard rows; {row['id']} is not flagged hard")
        if alias == "premium" and len(outputs) >= MAX_PREMIUM_CALLS:
            raise RuntimeError(f"premium-model cap reached: {MAX_PREMIUM_CALLS} calls")
        started = time.perf_counter()
        response = classify(model, row)
        seconds += time.perf_counter() - started
        tokens_in += response.usage.input_tokens
        tokens_out += response.usage.output_tokens
        cost += cost_usd(response)
        prediction, is_valid, reason = parse_output(response)
        outputs[row["id"]] = {"valid": is_valid, "pred": prediction, "reason": reason}
    return {"outputs": outputs, "tokens_in": tokens_in, "tokens_out": tokens_out, "seconds": seconds, "cost": cost}


# ----------------------------------------------------------------------------------------------
# Scoring and projection (provided)
# ----------------------------------------------------------------------------------------------
def score(rows, outputs):
    exact = valid = hard_total = hard_hits = 0
    field_hits = {field: 0 for field in FIELDS}
    for row in rows:
        output = outputs[row["id"]]
        valid += output["valid"]
        all_fields_right = bool(output["valid"])
        for field in FIELDS:
            hit = bool(output["valid"] and output["pred"][field] == row["truth"][field])
            field_hits[field] += hit
            all_fields_right &= hit
        exact += all_fields_right
        if row.get("hard"):
            hard_total += 1
            hard_hits += all_fields_right
    count = len(rows)
    return {"exact_accuracy": exact / count, "field_accuracy": {f: field_hits[f] / count for f in FIELDS},
            "schema_compliance": valid / count, "hard_accuracy": hard_hits / hard_total if hard_total else None}


def model_entry(alias, model, rows, run):
    from claude_client import PRICE_PER_MTOK
    count = len(rows)
    price_in, price_out = PRICE_PER_MTOK[model]
    entry = {"alias": alias, "model_id": model, "rows_evaluated": count, "row_ids": [r["id"] for r in rows],
             "avg_latency_s": run["seconds"] / count, "avg_input_tokens": run["tokens_in"] / count,
             "avg_output_tokens": run["tokens_out"] / count, "total_cost_usd": run["cost"],
             "cost_per_1k_usd": run["cost"] / count * 1000, "price_in_per_mtok": price_in, "price_out_per_mtok": price_out}
    entry.update(score(rows, run["outputs"]))
    return entry


def project_100k(entry):
    """100,000-row cost from MEASURED average tokens. The Batch API is 50% cheaper but returns results unordered."""
    per_row = (entry["avg_input_tokens"] * entry["price_in_per_mtok"] + entry["avg_output_tokens"] * entry["price_out_per_mtok"]) / 1_000_000
    return {"records": RECORDS_TO_PROJECT, "sync_usd": round(per_row * RECORDS_TO_PROJECT, 4), "batch_usd": round(per_row * RECORDS_TO_PROJECT * 0.5, 4)}


def results_table(models, projection):
    lines = ["| model | rows | exact acc | hard acc | schema ok | avg s | avg in | avg out | $ / 1k rows | $ / 100k (sync) | $ / 100k (batch) |",
             "|" + "---|" * 11]
    for alias, e in models.items():
        hard = "n/a" if e["hard_accuracy"] is None else f"{e['hard_accuracy']:.3f}"
        lines.append(f"| {alias} | {e['rows_evaluated']} | {e['exact_accuracy']:.3f} | {hard} | {e['schema_compliance']:.3f} | "
                     f"{e['avg_latency_s']:.2f} | {e['avg_input_tokens']:.0f} | {e['avg_output_tokens']:.0f} | "
                     f"${e['cost_per_1k_usd']:.4f} | ${projection[alias]['sync_usd']:.2f} | ${projection[alias]['batch_usd']:.2f} |")
    lines.append("\nNote: 'premium' was measured on the 8 hard rows only; its 100k projection is the worst case (every row escalated).")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------------------------
# STEP 3 (provided): the parameter probe. Which way of sending `temperature` works on which model?
# ----------------------------------------------------------------------------------------------
def run_probe():
    from claude_client import MODEL_BALANCED, MODEL_FAST, ask
    trials = [("kwarg_temperature_haiku", MODEL_FAST, {"temperature": 0}),
              ("extra_body_temperature_haiku", MODEL_FAST, {"extra_body": {"temperature": 0}}),
              ("extra_body_temperature_sonnet", MODEL_BALANCED, {"extra_body": {"temperature": 0}})]
    results = {}
    for name, model, extra in trials:
        try:
            ask([{"role": "user", "content": "Record id: R001\nTitle: x\nDepartment: y\nNote: z"}], model=model, max_tokens=16, **extra)
            results[name] = "accepted"
        except TypeError:
            results[name] = "TypeError"
        except anthropic.BadRequestError:
            results[name] = "BadRequestError"
        print(f"  {name:<34} -> {results[name]}")
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "param_probe.json").write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    print("saved evidence/param_probe.json")


# ----------------------------------------------------------------------------------------------
# STEP 2 (YOUR WORK) is inside main(): the PLAN list.
# ----------------------------------------------------------------------------------------------
def main():
    from claude_client import MODEL_BALANCED, MODEL_FAST, MODEL_PREMIUM

    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true", help="run the temperature probe and exit")
    parser.add_argument("--rows-file", help="classify a different file with the fast model (BREAK_IT); no evidence written")
    args = parser.parse_args()
    if args.probe:
        run_probe()
        return

    if args.rows_file:
        rows = load_rows(pathlib.Path(args.rows_file))
        run = run_model("fast", MODEL_FAST, rows)
        for row in rows:
            output = run["outputs"][row["id"]]
            print(f"{row['id']}: truth={row['truth']} got={output['pred']} ({output['reason']})")
        return

    rows = load_rows(DATA_FILE)
    hard_rows = [row for row in rows if row["hard"]]
    print(f"models: fast={MODEL_FAST}  balanced={MODEL_BALANCED}  premium={MODEL_PREMIUM}")

    # TODO 1: add ("balanced", MODEL_BALANCED, rows) - the balanced model on all 40 rows.
    # TODO 2: add ("premium", MODEL_PREMIUM, hard_rows) - the premium model on the 8 hard rows ONLY.
    #         run_model() already refuses non-hard rows and stops after MAX_PREMIUM_CALLS. Think about what spending
    #         limit is sensible before you run it: premium costs roughly 2x balanced per token.
    plan = [("fast", MODEL_FAST, rows)]

    models, outputs = {}, {}
    for alias, model, subset in plan:
        print(f"\n== {alias} ({model}) on {len(subset)} rows ==")
        run = run_model(alias, model, subset)
        models[alias] = model_entry(alias, model, subset, run)
        outputs[alias] = run["outputs"]
        print(f"  exact={models[alias]['exact_accuracy']:.3f} schema_ok={models[alias]['schema_compliance']:.3f} cost=${models[alias]['total_cost_usd']:.4f}")

    projection = {alias: project_100k(entry) for alias, entry in models.items()}
    truth = {row["id"]: row["truth"] for row in rows}
    failures = {alias: [rid for rid, out in outs.items() if not out["valid"] or any(out["pred"][f] != truth[rid][f] for f in FIELDS)]
                for alias, outs in outputs.items()}
    table = results_table(models, projection)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "results_table.md").write_text(table, encoding="utf-8")
    (EVIDENCE / "evidence.json").write_text(json.dumps({
        "n_rows": len(rows), "n_hard": len(hard_rows), "models": models, "outputs": outputs, "failures": failures,
        "projection_100k": projection, "premium_calls": len(outputs.get("premium", {})), "max_premium_calls": MAX_PREMIUM_CALLS,
        "spent_usd": round(sum(e["total_cost_usd"] for e in models.values()), 6)}, indent=2), encoding="utf-8")
    print("\n" + table)
    print("saved evidence/evidence.json and evidence/results_table.md")
    print("NEXT: copy decision_template.md to evidence/decision.md and fill it in, then run: python check.py")


if __name__ == "__main__":
    main()
