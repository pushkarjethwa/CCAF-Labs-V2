# Solution guide: Lab 1.4 - PO Reconciliation: a validated, cached, batched service

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

A cost-engineered service: validated outputs, prompt caching (breakpoint at the end of the shared prefix), a budget gate that knows the cache floor, and batch results joined by `custom_id`, not by position.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def build_system()

Solution:

```python
text = f"{INSTRUCTIONS}\n\n=== PROCUREMENT POLICY ===\n{policy_text}"
```

### Block 2: def run_batch()

What the TODO asks:

> TODO 2: this joins by POSITION. Message Batches return results in ANY order, so rebuild it keyed on
> entry.custom_id. For each entry: if entry.result.type != "succeeded", record the type and move on (do not crash);
> otherwise validate the decision against ITS invoice (look the invoice up by custom_id).

Solution:

```python
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
```

### Block 3: def count_for_models()

Solution:

```python
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
```

### Block 4: def budget_gate()

Solution:

```python
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
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- policy prefix is >= 5,000 tokens by chars/4 (above the Haiku 4096 cache floor)
- TODO 1: system prompt is identical across two builds (nothing time-based in the cached prefix)
- TODO 3b: budget_gate refuses an over-budget batch, accepts a small one, flags a prefix below the cache floor
- call 1 wrote the cache (cache_creation_input_tokens > 0)
- call 2 read the cache (cache_read_input_tokens > 0)
- TODO 3a: count_tokens recorded for two models with prefix and per-request counts
- cache_eligible agrees with each model's cache floor
- budget gate ran before the batch and passed
- projection: 100,000 invoices a month x 2 models x 4 scenarios
- projection ordering is sane: batch_cached < batch < normal and cached < normal
- TODO 2: batch map is complete (40 of 40) and joined by custom_id
- every decision belongs to its key (joined by id, not position)
- batch results show cache_read_input_tokens > 0 (best effort)
- validation ran on all 40 decisions
- measured on the real 40 results: caching lowers cost
- capstone_day1.md: >= 150 words, 'What the service does' and 'Model choice' sections, names the model class, cites $ figures
- validator accepts valid case '{case['case']}
- validator reports {case['expect_rule']} for '{case['case']}

## 4. Common mistakes

- Putting anything that varies (timestamps, ids) before the cache breakpoint.
- Marking the varying user block with `cache_control` instead of the end of the shared prefix.
- Ignoring the cache floor (4096 tokens on Haiku, 512 on Sonnet): below it nothing is cached and no error is raised.
- Joining batch results by position. Batch results come back unordered; join by `custom_id`.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Break 1: a timestamp in the user message (after the breakpoint) keeps cache reads above 0; the same timestamp in `INSTRUCTIONS` (before it) drops reads to 0. Rule: nothing before the breakpoint may vary between requests.
2. Break 2: marking the user block writes the cache on every call (1.25x) and never reads it. The marker belongs at the end of the shared portion.
3. Break 3: on the fast alias reads and writes are both 0 with no error (below the 4096 floor); on the balanced alias (floor 512) caching works. `budget_gate()['cache_eligible']` tells you beforehand.
4. Break 4: positional joining is caught by the `check.py` join test; without it you would have to compare `custom_id` values by eye.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
