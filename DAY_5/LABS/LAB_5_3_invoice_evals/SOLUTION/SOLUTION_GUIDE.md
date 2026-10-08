# Solution guide: Lab 5.3 - Grade, trace and gate an invoice checker

> **Spoiler warning.** Try the lab first, using `README.md` and `check.py`. Open this guide when you are stuck, or after you finish to compare. If `check.py` passes and you can explain why, your code is correct.

## What this lab teaches

A prompt is not known to work until a fixed test set says so. Plain code grades each answer, a source check proves that cited ids exist, a gate compares two prompt versions case by case, and a queue sends the risky answers to a person.

## Solutions, one TODO at a time

### TODO 1: grade(output, case)

Five plain-code checks. A wrong shape fails all five.

```python
if not core.schema_ok(output):
    return {name: False for name in core.CHECKS}
return {
    "schema": True,
    "decision": output["decision"] == case["expected_decision"],
    "items": set(case["required_items"]) <= set(output["citations"]),
    "total": abs(output["total"] - case["expected_total"]) <= 0.01 * case["expected_total"],
    "escalate": output["escalate"] == case["expected_escalate"],
}
```

### TODO 2: coverage(output, invoice)

The share of cited ids that exist in the invoice.

```python
ids = {line["id"] for line in invoice["lines"]}
cited = output["citations"]
return sum(item in ids for item in cited) / len(cited)
```

### TODO 3: release_gate(old, new)

Block on a regression, on a missed must-escalate case, or on a lower pass count.

```python
regressed = [case for case in old if old[case] and not new[case]]
missed = [case["id"] for case in core.CASES if case["expected_escalate"] and not new[case["id"]]]
if regressed or missed or sum(new.values()) < sum(old.values()):
    return "GATE: BLOCKED"
return "GATE: PASS"
```

### TODO 4: write_queue(outputs, path)

Queue an answer when the total is at or above the limit or the escalate flag is set, then write the file.

```python
queue = []
for case_id, output in outputs.items():
    if output["total"] >= core.ESCALATION_VALUE or output["escalate"]:
        queue.append({"case": case_id, "total": output["total"], "evidence": output["citations"]})
path.write_text(json.dumps(queue, indent=2), encoding="utf-8")
return queue
```
