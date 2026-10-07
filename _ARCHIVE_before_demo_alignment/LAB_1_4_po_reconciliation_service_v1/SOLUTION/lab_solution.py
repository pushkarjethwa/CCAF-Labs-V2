"""LAB 1.4 - PO reconciliation service: cached, batched and cost-aware.

Run:   python lab.py                (needs an API key; 2 normal calls + 1 batch of 40 invoices; roughly $0.10-0.50)
Check: python check.py              (Part A needs no key; Part B reads evidence/evidence.json)

Scenario: accounts-payable receives ~100,000 supplier invoices a month. Each one is matched against its purchase
order under a long (~6,000 token) procurement policy. The prototype below "works", but it pays full price for the policy
on every call, never reads the cache, joins batch results by position, and has no cost gate.

Your work is three TODOs:
  TODO 1  the cache never hits: find what makes the system prompt different on every call and remove it
  TODO 2  batch results arrive in ANY order: join them by custom_id, not by position
  TODO 3  count tokens for two models and write a budget gate that refuses an over-budget batch
"""
import json
import pathlib
import re
import time
from datetime import datetime

from jsonschema import validators

from claude_client import MODEL_BALANCED, MODEL_FAST, PRICE_PER_MTOK, get_client, text_of

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
EVIDENCE = HERE / "evidence"

SERVICE_MODEL_ALIAS = "fast"        # "fast" or "balanced": decide after reading the projection table, justify in the memo
MONTHLY_INVOICES = 100_000          # production volume to project
RUN_BUDGET_USD = 0.50               # the 40-invoice batch must be projected under this before it is submitted
GATE_AVG_OUTPUT_TOKENS = 150        # assumption used by the budget gate
CACHE_HIT_RATE_SYNC = 0.95          # ASSUMPTION: steady traffic keeps the 5-minute cache warm
CACHE_HIT_RATE_BATCH = 0.90         # ASSUMPTION: batch cache hits are best-effort; vary it
MAX_TOKENS = 600                    # on Sonnet 5.5 hidden thinking tokens also count here
COUNT_SAMPLE = 5                    # invoices sampled per model for count_tokens
POLL_SECONDS = 30
CACHE_FLOOR = {MODEL_FAST: 4096, MODEL_BALANCED: 512}  # a prefix shorter than this is never cached


def models():
    return {"fast": MODEL_FAST, "balanced": MODEL_BALANCED}


# ----------------------------------------------------------------------------------------------
# STEP 1: the system prompt. Everything BEFORE the cache breakpoint must be byte-identical on every call.
# ----------------------------------------------------------------------------------------------
INSTRUCTIONS = (
    "You are the first-line invoice reconciliation analyst for Hartwell Distribution. Apply the policy below exactly. "
    "Reply with ONE JSON object only (no prose, no code fence): "
    '{"invoice_id", "decision", "matched_po", "rule_codes", "rationale"}.'
)


def build_system(policy_text):
    """Returns the `system` parameter: one text block with a cache breakpoint at the end of the shared prefix.
    TODO 1: something in the text below changes on every call, so the cache can never be read. Find it and remove it."""
    text = f"{INSTRUCTIONS}\n\n=== PROCUREMENT POLICY ===\n{policy_text}"
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


# ----------------------------------------------------------------------------------------------
# STEP 2 (provided): load data and validate decisions. Every decision is checked before anyone trusts it.
# ----------------------------------------------------------------------------------------------
def load():
    policy = (DATA / "procurement_policy.md").read_text(encoding="utf-8")
    invoices = json.loads((DATA / "invoices.json").read_text(encoding="utf-8"))
    purchase_orders = {po["po_number"]: po for po in json.loads((DATA / "purchase_orders.json").read_text(encoding="utf-8"))}
    prior = json.loads((DATA / "prior_invoices.json").read_text(encoding="utf-8"))
    truth = json.loads((DATA / "ground_truth.json").read_text(encoding="utf-8"))
    return policy, invoices, purchase_orders, prior, truth


def context_for(invoice, purchase_orders, prior):
    """What the model sees for one invoice. The PO lookup is done by code, not by the model."""
    return {"invoice": invoice, "purchase_order": purchase_orders.get(invoice["po_number"]),
            "prior_invoice_numbers_for_vendor": prior.get(invoice["vendor_id"], [])}


def user_message(context):
    return "Reconcile this invoice and reply with the JSON decision only.\n" + json.dumps(context, sort_keys=True)


DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_id": {"type": "string"},
        "decision": {"type": "string", "enum": ["approve", "hold", "reject"]},
        "matched_po": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "rule_codes": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["invoice_id", "decision", "matched_po", "rule_codes", "rationale"],
    "additionalProperties": False,
}


def policy_codes(policy_text):
    """Every rule code defined anywhere in the policy."""
    return set(re.findall(r"R-[A-Z]+-\d\d", policy_text))


def validate_decision(decision, invoice, codes):
    """Return a list of "RULE_NAME: detail" strings. Empty list means acceptable."""
    schema_problems = list(validators.validator_for(DECISION_SCHEMA)(DECISION_SCHEMA).iter_errors(decision))
    if schema_problems:
        return [f"SCHEMA: {schema_problems[0].message}"]
    issues = []
    if decision["invoice_id"] != invoice["invoice_id"]:
        issues.append(f"INVOICE_ID_MISMATCH: decision is for {decision['invoice_id']}, asked about {invoice['invoice_id']}")
    unknown = [c for c in decision["rule_codes"] if c not in codes]
    if unknown:
        issues.append(f"UNKNOWN_RULE_CODE: {unknown} not in the policy")
    verdict, rule_codes = decision["decision"], decision["rule_codes"]
    if (verdict == "approve" and rule_codes) or (verdict in ("hold", "reject") and not rule_codes) \
            or (verdict == "reject" and not {"R-DUP-01", "R-VEND-01"} & set(rule_codes)):
        issues.append(f"DECISION_CODES_INCONSISTENT: {verdict} with codes {rule_codes}")
    if decision["matched_po"] is not None and decision["matched_po"] != invoice["po_number"]:
        issues.append(f"MATCHED_PO_MISMATCH: {decision['matched_po']} vs {invoice['po_number']}")
    return issues


# ----------------------------------------------------------------------------------------------
# STEP 3 (provided): normal calls, the cache check, and the batch.
# ----------------------------------------------------------------------------------------------
def make_params(model, policy, context):
    return {"model": model, "max_tokens": MAX_TOKENS, "system": build_system(policy),
            "messages": [{"role": "user", "content": user_message(context)}]}


def usage_dict(usage):
    return {"input_tokens": usage.input_tokens or 0,
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
            "output_tokens": usage.output_tokens or 0}


def interpret(raw_text, invoice, codes):
    """Parse and validate one model reply. Never raises: bad output becomes valid=False with issues."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError as error:
        return {"decision": None, "valid": False, "issues": [f"JSON_PARSE: {error.msg}"]}
    issues = validate_decision(decision, invoice, codes)
    return {"decision": decision, "valid": not issues, "issues": issues}


def reconcile_once(model, policy, context, codes):
    response = get_client().messages.create(**make_params(model, policy, context))  # a normal (synchronous) call
    result = interpret(text_of(response), context["invoice"], codes)
    result["usage"] = usage_dict(response.usage)
    return result


def run_cache_check(model, policy, contexts, codes):
    """Two sequential calls that share the policy prefix. The second must show cache_read_input_tokens > 0."""
    first = reconcile_once(model, policy, contexts[0], codes)
    second = reconcile_once(model, policy, contexts[1], codes)
    return {"model": model, "call1_usage": first["usage"], "call2_usage": second["usage"]}


def run_batch(model, policy, contexts, codes):
    client = get_client()
    requests = [{"custom_id": c["invoice"]["invoice_id"], "params": make_params(model, policy, c)} for c in contexts]
    batch = client.messages.batches.create(requests=requests)
    while batch.processing_status != "ended":
        time.sleep(POLL_SECONDS)
        batch = client.messages.batches.retrieve(batch.id)

    results = {}
    # TODO 2: this joins by POSITION. Message Batches return results in ANY order, so rebuild it keyed on
    # entry.custom_id. For each entry: if entry.result.type != "succeeded", record the type and move on (do not crash);
    # otherwise validate the decision against ITS invoice (look the invoice up by custom_id).
    invoices_by_id = {c["invoice"]["invoice_id"]: c["invoice"] for c in contexts}
    for entry in client.messages.batches.results(batch.id):
        invoice_id = entry.custom_id
        if entry.result.type != "succeeded":
            results[invoice_id] = {"decision": None, "valid": False, "issues": [f"BATCH_{entry.result.type.upper()}"],
                                   "usage": {}, "result_type": entry.result.type}
            continue
        message = entry.result.message
        result = interpret(text_of(message), invoices_by_id[invoice_id], codes)
        result["usage"] = usage_dict(message.usage)
        result["result_type"] = "succeeded"
        results[invoice_id] = result
    join_key = "custom_id"
    return {"batch_id": batch.id, "n_requests": len(requests), "n_results": len(results), "join_key": join_key, "map": results}


# ----------------------------------------------------------------------------------------------
# STEP 4: counting tokens and the budget gate.
# ----------------------------------------------------------------------------------------------
def count_for_models(policy, contexts):
    """TODO 3a: return {alias: {"model_id", "prefix_tokens", "avg_invoice_tokens", "avg_request_tokens",
                                "cache_floor", "cache_eligible"}} for "fast" and "balanced".
    prefix_tokens      = count_tokens(system=build_system(policy), messages=[one tiny user message])
    avg_request_tokens = mean count_tokens over the first COUNT_SAMPLE real requests (system + that invoice)
    avg_invoice_tokens = avg_request_tokens - prefix_tokens
    cache_eligible     = prefix_tokens >= cache_floor
    Counts differ per model (different tokenizers), so count each model separately.
    API: get_client().messages.count_tokens(model=..., system=..., messages=[...]).input_tokens"""
    client = get_client()
    system = build_system(policy)
    info = {}
    for alias, model_id in models().items():
        tiny = [{"role": "user", "content": "ok"}]
        prefix = client.messages.count_tokens(model=model_id, system=system, messages=tiny).input_tokens
        sample = [client.messages.count_tokens(model=model_id, system=system, messages=[{"role": "user", "content": user_message(c)}]).input_tokens
                  for c in contexts[:COUNT_SAMPLE]]
        average = sum(sample) / len(sample)
        info[alias] = {"model_id": model_id, "prefix_tokens": prefix, "avg_invoice_tokens": round(average - prefix),
                       "avg_request_tokens": round(average), "cache_floor": CACHE_FLOOR[model_id],
                       "cache_eligible": prefix >= CACHE_FLOOR[model_id]}
    return info


def budget_gate(prefix_tokens, per_invoice_tokens, n_requests, model, budget_usd, avg_output_tokens=GATE_AVG_OUTPUT_TOKENS):
    """TODO 3b: pre-flight check before a batch is submitted.
    Return {"ok", "projected_cost_usd", "budget_usd", "cache_eligible", "reasons"}.
    Be conservative: project the WORST case (batch price = 50% off, NO cache hits) and refuse if it exceeds the budget.
    Also report whether the prefix reaches this model's cache floor (CACHE_FLOOR[model])."""
    price_in, price_out = PRICE_PER_MTOK[model]
    per_request = (prefix_tokens + per_invoice_tokens) * price_in + avg_output_tokens * price_out
    projected = n_requests * per_request / 1_000_000 * 0.5
    eligible = prefix_tokens >= CACHE_FLOOR[model]
    reasons = []
    if projected > budget_usd:
        reasons.append(f"worst-case ${projected:.4f} exceeds budget ${budget_usd:.4f}")
    if not eligible:
        reasons.append(f"prefix {prefix_tokens} tokens is below the cache floor {CACHE_FLOOR[model]}")
    return {"ok": projected <= budget_usd, "projected_cost_usd": round(projected, 6), "budget_usd": budget_usd,
            "cache_eligible": eligible, "reasons": reasons}


# ----------------------------------------------------------------------------------------------
# STEP 5 (provided): the 100,000-invoices-a-month projection, with the four price schedules.
# Cache write costs 1.25x input, cache read 0.10x, batch is 50% off everything.
# ----------------------------------------------------------------------------------------------
def project_cost(model, records, avg_input_tokens, avg_output_tokens, batch=False, cached_prefix_tokens=0, cache_hit_rate=0.0):
    price_in, price_out = PRICE_PER_MTOK[model]
    uncached = avg_input_tokens - cached_prefix_tokens
    prefix_cost = cached_prefix_tokens * price_in * (cache_hit_rate * 0.10 + (1 - cache_hit_rate) * 1.25)
    per_request = uncached * price_in + prefix_cost + avg_output_tokens * price_out
    return records * per_request / 1_000_000 * (0.5 if batch else 1.0)


def build_projection(token_info, avg_output_tokens):
    rows = []
    for alias, info in token_info.items():
        for scenario, batch, cached in (("normal", False, False), ("cached", False, True), ("batch", True, False), ("batch_cached", True, True)):
            prefix = info["prefix_tokens"] if cached and info["cache_eligible"] else 0
            hit_rate = (CACHE_HIT_RATE_BATCH if batch else CACHE_HIT_RATE_SYNC) if prefix else 0.0
            rows.append({"model_alias": alias, "model_id": info["model_id"], "scenario": scenario, "records": MONTHLY_INVOICES,
                         "avg_input_tokens": info["avg_request_tokens"], "avg_output_tokens": avg_output_tokens,
                         "cached_prefix_tokens": prefix, "cache_hit_rate": hit_rate, "batch": batch,
                         "monthly_cost_usd": project_cost(info["model_id"], MONTHLY_INVOICES, info["avg_request_tokens"],
                                                          avg_output_tokens, batch, prefix, hit_rate)})
    return {"records": MONTHLY_INVOICES, "rows": rows}


def main():
    policy, invoices, purchase_orders, prior, truth = load()
    contexts = [context_for(i, purchase_orders, prior) for i in invoices]
    codes = policy_codes(policy)
    model = models()[SERVICE_MODEL_ALIAS]
    print(f"service model: {SERVICE_MODEL_ALIAS} ({model})   invoices: {len(contexts)}   policy ~{len(policy) // 4} tokens (chars/4)")
    evidence = {"service_model_alias": SERVICE_MODEL_ALIAS, "service_model": model, "n_invoices": len(contexts)}

    print("\n[1] cache check: two sequential calls sharing the policy prefix")
    cache_check = run_cache_check(model, policy, contexts, codes)
    evidence["cache_check"] = cache_check
    for key in ("call1_usage", "call2_usage"):
        u = cache_check[key]
        print(f"    {key}: write={u['cache_creation_input_tokens']} read={u['cache_read_input_tokens']} uncached={u['input_tokens']}")
    print("    cache_read_input_tokens > 0 on call 2:", cache_check["call2_usage"]["cache_read_input_tokens"] > 0)

    print("\n[2] token counts and budget gate")
    token_counts = count_for_models(policy, contexts)
    evidence["token_counts"] = token_counts
    for alias, c in token_counts.items():
        print(f"    {alias:<9} prefix={c['prefix_tokens']} per-invoice~{c['avg_invoice_tokens']} floor={c['cache_floor']} cache_eligible={c['cache_eligible']}")
    mine = token_counts.get(SERVICE_MODEL_ALIAS, {})
    gate = budget_gate(mine.get("prefix_tokens", 0), mine.get("avg_invoice_tokens", 0), len(contexts), model, RUN_BUDGET_USD)
    evidence["budget_gate"] = gate
    print(f"    gate: ok={gate['ok']} worst-case={gate['projected_cost_usd']} budget={gate['budget_usd']} reasons={gate['reasons']}")
    if not gate["ok"]:
        print("    GATE REFUSED the batch - not submitting.")
        EVIDENCE.mkdir(exist_ok=True)
        (EVIDENCE / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        return

    print(f"\n[3] batch of {len(contexts)} (polling every {POLL_SECONDS}s)")
    batch = run_batch(model, policy, contexts, codes)
    evidence["batch"] = batch
    print(f"    batch {batch['batch_id']}: requests={batch['n_requests']} results={batch['n_results']} join_key={batch['join_key']}")

    entries = batch["map"]
    invalid = sorted(i for i, e in entries.items() if not e.get("valid"))
    mismatched = sorted(i for i, e in entries.items() if (e.get("decision") or {}).get("invoice_id") != i)
    correct = sum(1 for i, e in entries.items() if e.get("valid") and (e["decision"]["decision"], e["decision"]["rule_codes"]) ==
                  (truth[i]["decision"], truth[i]["rule_codes"]))
    evidence["validation"] = {"n_checked": len(entries), "n_valid": len(entries) - len(invalid), "n_invalid": len(invalid),
                              "invalid_ids": invalid, "join_mismatches": mismatched, "valid_and_correct_vs_truth": correct}
    print(f"\n[4] validation: valid={len(entries) - len(invalid)} invalid={len(invalid)}  decision.invoice_id != key: {len(mismatched)}  "
          f"valid and correct vs ground truth: {correct}")

    usages = [e["usage"] for e in entries.values() if e.get("usage")]
    avg_out = max(1, round(sum(u["output_tokens"] for u in usages) / max(len(usages), 1)))
    projection = build_projection(token_counts, avg_out)
    evidence["projection"] = projection
    print(f"\n[5] projection for {MONTHLY_INVOICES:,} invoices/month (avg output tokens from this run: {avg_out})")
    for row in projection["rows"]:
        print(f"    {row['model_alias']:<9}{row['scenario']:<13}${row['monthly_cost_usd']:>10,.2f}")

    total = {k: sum(u[k] for u in usages) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")}
    price_in, price_out = PRICE_PER_MTOK[model]

    def cost(cached, batch):
        reads, writes = (total["cache_read_input_tokens"], total["cache_creation_input_tokens"]) if cached else (0, 0)
        plain_in = total["input_tokens"] + (0 if cached else total["cache_read_input_tokens"] + total["cache_creation_input_tokens"])
        value = (plain_in * price_in + writes * price_in * 1.25 + reads * price_in * 0.10 + total["output_tokens"] * price_out) / 1_000_000
        return value * (0.5 if batch else 1.0)

    evidence["measured_cost_40"] = {"usage_total": total, "normal_usd": cost(False, False), "cached_usd": cost(True, False),
                                    "batch_usd": cost(False, True), "batch_cached_usd": cost(True, True)}
    print("\n[6] measured on the 40 batch results (same tokens, four price schedules)")
    for key in ("normal_usd", "cached_usd", "batch_usd", "batch_cached_usd"):
        print(f"    {key:<18}${evidence['measured_cost_40'][key]:>8.4f}")
    memo = EVIDENCE / "capstone_day1.md"
    print("\n[7] memo:", "found" if memo.exists() else "MISSING - write evidence/capstone_day1.md")
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("saved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
