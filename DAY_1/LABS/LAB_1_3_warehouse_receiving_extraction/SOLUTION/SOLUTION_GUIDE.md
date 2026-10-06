# Solution guide: Lab 1.3 - Warehouse Receiving Emails: Validate and Retry

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Validate-and-retry: extract fields from warehouse emails, validate them against the source text (grounding) and business rules, and retry with a corrective message that names the failed rules, within a hard attempt cap.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def check_po()

Solution:

```python
po_number = extraction["po_number"]
if po_number is None:
    return []
digits = re.sub(r"\D", "", po_number)
digit_runs_in_email = set(re.findall(r"\d+", email_text))
if not digits or digits not in digit_runs_in_email:
    return [fail("PO_NOT_GROUNDED", "po_number", "a PO number that appears in the email text, or null", po_number,
                 f"'{po_number}' does not appear anywhere in the email. Do not invent PO numbers: use null when the email has none.")]
if po_number not in purchase_orders:
    return [fail("PO_UNKNOWN", "po_number", "a PO number present in purchase_orders.json", po_number,
                 f"'{po_number}' is in the email but is not a known purchase order. Check you did not copy an invoice or reference number.")]
return []
```

### Block 2: def check_lines()

Solution:

```python
failures = []
po_lines = {line["sku"]: line for line in po["lines"]} if po else {}
for index, line in enumerate(extraction["lines"]):
    path = f"lines[{index}]"
    condition = line["condition"]
    if condition != "ok" and not line["discrepancy_note"]:
        failures.append(fail("NOTE_REQUIRED", f"{path}.discrepancy_note", "a non-null note explaining the discrepancy",
                             line["discrepancy_note"], f"condition is '{condition}' so discrepancy_note must describe it."))
    if po is None:
        continue
    po_line = po_lines.get(line["sku"])
    if po_line is None:
        failures.append(fail("SKU_NOT_ON_PO", f"{path}.sku", f"one of {sorted(po_lines)}", line["sku"],
                             f"SKU '{line['sku']}' is not a line of {po['po_number']}. Copy the SKU exactly as written in the email."))
        continue
    uom = line["uom"]
    if uom != uom.upper():
        failures.append(fail("UOM_INVALID", f"{path}.uom", uom.upper(), uom, "uom must be UPPER CASE."))
        continue
    factor = 1 if uom == po_line["uom"] else po_line.get("pack", {}).get(uom)
    if factor is None:
        allowed = [po_line["uom"], *po_line.get("pack", {})]
        failures.append(fail("UOM_INVALID", f"{path}.uom", f"one of {allowed}", uom,
                             f"'{uom}' cannot be converted to the PO unit {po_line['uom']} for {po_line['sku']}."))
        continue
    qty_in_po_units = line["qty_received"] * factor
    ordered = po_line["ordered_qty"]
    expected = "over" if qty_in_po_units > ordered else "short" if qty_in_po_units < ordered else None
    if expected and condition != expected and not (expected == "short" and condition == "damaged"):
        failures.append(fail("QTY_CONDITION_MISMATCH", f"{path}.condition", expected, condition,
                             f"{line['qty_received']} {uom} = {qty_in_po_units} {po_line['uom']} vs {ordered} ordered, so condition must be "
                             f"'{expected}' (check the unit: is the email quantity really in {uom}?)."))
    if expected is None and condition in ("short", "over"):
        failures.append(fail("QTY_CONDITION_MISMATCH", f"{path}.condition", "ok or damaged", condition,
                             f"{qty_in_po_units} {po_line['uom']} equals the {ordered} ordered; '{condition}' is wrong."))
return failures
```

### Block 3: def check_dates()

Solution:

```python
try:
    received = date.fromisoformat(extraction["received_date"])
except ValueError:
    return [fail("DATE_FORMAT", "received_date", "a real calendar date as YYYY-MM-DD", extraction["received_date"],
                 "received_date is not a valid YYYY-MM-DD date.")]
failures = []
if po is not None and received < date.fromisoformat(po["po_date"]):
    failures.append(fail("DATE_BEFORE_PO", "received_date", f">= {po['po_date']}", extraction["received_date"],
                         f"goods cannot be received before the PO was raised ({po['po_date']}). Re-read the date (and year) in the email."))
if received > today:
    failures.append(fail("DATE_FUTURE", "received_date", f"<= {today}", extraction["received_date"],
                         f"received_date is after today ({today}). Use the date the goods arrived, resolving words like 'yesterday' from the Sent header."))
return failures
```

### Block 4: def check_followup()

Solution:

```python
needs_followup = extraction["po_number"] is None or any(line["condition"] != "ok" for line in extraction["lines"])
if needs_followup and not extraction["needs_followup"]:
    return [fail("FOLLOWUP_INCONSISTENT", "needs_followup", "true", extraction["needs_followup"],
                 "needs_followup must be true when po_number is null or any line condition is not 'ok'.")]
return []
```

### Block 5: def build_corrective_messages()

Solution:

```python
feedback = ("Your previous JSON failed validation against our purchase-order records:\n" + format_failures(failures) +
            "\nReturn the corrected JSON object only. Fix every listed failure; do not change fields that were not flagged.")
return messages + [{"role": "assistant", "content": invalid_output}, {"role": "user", "content": feedback}], feedback
```

### Block 6: def extract_with_retry()

What the TODO asks:

> TODO 6: (a) loop at most MAX_ATTEMPTS times, (b) after a failed attempt call build_corrective_messages,
> (c) append a log entry for EVERY attempt, (d) if all attempts fail, return status "needs_review"
> with extraction None. Never trust the last invalid output.

Solution:

```python
for attempt in range(1, MAX_ATTEMPTS + 1):
    response = call_model(model, messages)
    raw = response_text(response)
    extraction, failures = parse_model_output(raw)
    if extraction is not None:
        failures = validate_extraction(extraction, email["text"], purchase_orders, TODAY)
    log.append({"email_id": email["email_id"], "attempt": attempt, "model": model, "valid": not failures,
                "failure_rules": sorted({f["rule"] for f in failures}), "failures": failures, "feedback": feedback,
                "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens})
    if not failures:
        return {"email_id": email["email_id"], "status": "accepted", "attempts": attempt, "extraction": extraction, "attempt_log": log}
    if attempt < MAX_ATTEMPTS:
        messages, feedback = build_corrective_messages(messages, raw, failures)
return {"email_id": email["email_id"], "status": "needs_review", "attempts": MAX_ATTEMPTS, "extraction": None, "attempt_log": log}
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- no false alarms: all 20 correct extractions pass
- failures carry rule/path/expected/got/message
- no email hit the runaway safety net
- no email used more than {cap} attempts
- attempt log is not empty
- every log entry has the required fields
- one log entry per attempt for every email
- each retry's feedback names the rules that failed on the previous attempt
- needs_review is set only when every attempt failed, and then extraction is None
- every accepted extraction passes your validators
- no accepted extraction has an invented PO number
- ires {case['expect_rule']} on planted case '{case['case']}

## 4. Common mistakes

- A retry message that only says 'try again'. It must list which rule failed and why.
- Validating format instead of truth (an invented PO number can be well-formed and even exist in the registry).
- Counting loop iterations instead of model calls when auditing the retry cap.
- Forgetting to append the assistant's wrong answer before the corrective user message.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Break 1: a vague retry gives the model nothing new, so it repeats the mistake and you pay twice; `attempts` goes up and repairs go down.
2. Break 2: a format-only PO check cannot catch an invented but well-formed PO that also exists in `purchase_orders.json`; the planted case `invented_po` stops firing. Ground the value in the email text.
3. Break 3: `range(1, MAX_ATTEMPTS + 2)` allows one extra call per failing row. The attempt-cap check in `check.py` catches it; audit the number of model calls because that is what costs money.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
