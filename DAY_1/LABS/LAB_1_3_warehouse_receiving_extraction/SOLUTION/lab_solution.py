"""LAB 1.3 - Warehouse receiving emails -> validated JSON, with a bounded corrective retry.

Run:   python lab.py [--model balanced|fast] [--only GR-005,GR-017]     (needs an API key)
Check: python check.py       (the validator checks run WITHOUT a key; the run checks need evidence/evidence.json)

Why this lab exists: schema-valid JSON can still be WRONG (400 anchors received vs 360 ordered but "ok",
a PO number the email never mentioned). A schema cannot express those rules, so YOU write validators,
and a retry loop that shows the model exactly what it got wrong.

Read top to bottom. Your work is the six TODOs: four validators (STEP 2) and the retry loop (STEP 3).
"""
import argparse
import json
import pathlib
import re
from datetime import date

from jsonschema import validators

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
EVIDENCE_FILE = HERE / "evidence" / "evidence.json"

TODAY = date(2026, 9, 14)  # fixed "today" so results are reproducible
MAX_ATTEMPTS = 3           # model calls allowed per email: first try + corrective retries
HARNESS_CALL_LIMIT = 12    # safety net only: stops a runaway loop from spending money. It is NOT the fix
MAX_TOKENS = 700


# ----------------------------------------------------------------------------------------------
# STEP 0 (provided): the output schema and the prompt. Business rules do NOT belong in the schema.
# ----------------------------------------------------------------------------------------------
NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "po_number": NULLABLE_STRING,
        "carrier": {"type": "string"},
        "received_date": {"type": "string"},
        "lines": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "sku": {"type": "string"},
                "qty_received": {"type": "integer"},
                "uom": {"type": "string"},
                "condition": {"type": "string", "enum": ["ok", "damaged", "short", "over"]},
                "discrepancy_note": NULLABLE_STRING,
            },
            "required": ["sku", "qty_received", "uom", "condition", "discrepancy_note"],
            "additionalProperties": False}},
        "needs_followup": {"type": "boolean"},
    },
    "required": ["po_number", "carrier", "received_date", "lines", "needs_followup"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You extract goods-receipt data from warehouse receiving emails.\n"
    "Return ONE JSON object with keys: po_number (string like PO-12345, or null if the email contains no purchase-order number), "
    "carrier, received_date (YYYY-MM-DD), lines[] (sku, qty_received as an integer in the unit the email states, uom in UPPER CASE "
    "such as EACH/CASE/BOX/ROLL/PAIR/BUNDLE, condition one of ok|damaged|short|over, discrepancy_note or null), needs_followup (boolean).\n"
    "Never guess a PO number. Reference numbers that are not purchase orders (invoices, pickup refs) are not PO numbers."
)


def build_request_text(email):
    return f"EMAIL_ID: {email['email_id']}\n--- EMAIL START ---\n{email['text']}--- EMAIL END ---\nExtract the receipt as JSON."


def parse_model_output(text):
    """Return (extraction_or_None, failures). Text that is not JSON is a failure with rule JSON_PARSE."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned), []
    except json.JSONDecodeError as error:
        return None, [fail("JSON_PARSE", "$", "a JSON object", text[:80], f"invalid JSON: {error.msg}")]


def fail(rule, path, expected, got, message):
    """Every failure has this shape. The retry loop sends it back to the model, so write messages a model can act on:
    say what is wrong AND what would be right."""
    return {"rule": rule, "path": path, "expected": expected, "got": str(got), "message": message}


def schema_failures(extraction):
    return [
        fail("SCHEMA", ".".join(str(part) for part in error.absolute_path) or "$", str(error.validator_value)[:60],
             str(error.instance)[:60], error.message)
        for error in validators.validator_for(EXTRACTION_SCHEMA)(EXTRACTION_SCHEMA).iter_errors(extraction)
    ]


# ----------------------------------------------------------------------------------------------
# STEP 2 (YOUR WORK): semantic validators - the checks a JSON schema cannot express.
#
# RULE NAMES (use exactly these; check.py looks for them):
#   PO_NOT_GROUNDED        po_number is not null but its digits do not appear in the email text
#   PO_UNKNOWN             po_number is in the email but is not a PO in purchase_orders.json
#   SKU_NOT_ON_PO          a line SKU is not a line of that PO
#   UOM_INVALID            uom is not UPPER CASE, or is neither the PO line's uom nor a key of its `pack` table
#   QTY_CONDITION_MISMATCH quantity (converted to the PO unit) vs ordered says short/over/equal; condition disagrees
#   NOTE_REQUIRED          condition is not "ok" but discrepancy_note is null
#   DATE_FORMAT            received_date is not a real YYYY-MM-DD date
#   DATE_BEFORE_PO         received_date is earlier than the PO's po_date
#   DATE_FUTURE            received_date is later than TODAY
#   FOLLOWUP_INCONSISTENT  needs_followup is false although po_number is null or any line condition is not "ok"
#
# Unit conversion: a PO line looks like {"sku", "ordered_qty", "uom": "EACH", "pack": {"CASE": 50}}.
# "12 CASE" of that line = 12 * 50 = 600 EACH. If the email's uom equals the line's uom, the factor is 1.
# ----------------------------------------------------------------------------------------------
def check_po(extraction, email_text, purchase_orders):
    """TODO 1: PO_NOT_GROUNDED (digits of po_number must appear in email_text) and PO_UNKNOWN."""
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


def check_lines(extraction, po):
    """TODO 2: for every line -> NOTE_REQUIRED, SKU_NOT_ON_PO, UOM_INVALID, QTY_CONDITION_MISMATCH.
    `po` is None when po_number is null or unknown: skip the checks that need the PO."""
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


def check_dates(extraction, po, today):
    """TODO 3: DATE_FORMAT, DATE_BEFORE_PO (only if po is known), DATE_FUTURE. `today` is a datetime.date."""
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


def check_followup(extraction):
    """TODO 4: FOLLOWUP_INCONSISTENT."""
    needs_followup = extraction["po_number"] is None or any(line["condition"] != "ok" for line in extraction["lines"])
    if needs_followup and not extraction["needs_followup"]:
        return [fail("FOLLOWUP_INCONSISTENT", "needs_followup", "true", extraction["needs_followup"],
                     "needs_followup must be true when po_number is null or any line condition is not 'ok'.")]
    return []


def validate_extraction(extraction, email_text, purchase_orders, today):
    """purchase_orders: {po_number: po_dict}. Returns [] when the extraction is acceptable. (Provided.)"""
    failures = schema_failures(extraction)
    if failures:  # structure first: the semantic checks assume the shape is right
        return failures
    failures += check_po(extraction, email_text, purchase_orders)
    po = purchase_orders.get(extraction["po_number"]) if extraction["po_number"] else None
    failures += check_lines(extraction, po)
    failures += check_dates(extraction, po, today)
    failures += check_followup(extraction)
    return failures


# ----------------------------------------------------------------------------------------------
# STEP 3 (YOUR WORK): the retry loop.
# ----------------------------------------------------------------------------------------------
class RunawayLoop(RuntimeError):
    pass


calls_for_this_email = 0  # reset by main() before each email; used only by the safety net in call_model


def call_model(model, messages):
    """ONE Claude call (provided). This is where the lab touches the API - see claude_client.py.
    output_config.format asks Claude for JSON that matches EXTRACTION_SCHEMA."""
    global calls_for_this_email
    calls_for_this_email += 1
    if calls_for_this_email > HARNESS_CALL_LIMIT:
        raise RunawayLoop(f"more than {HARNESS_CALL_LIMIT} model calls for one email - your loop is not bounded")
    from claude_client import ask  # imported here so check.py can test your validators without an API key
    return ask(messages, system=SYSTEM_PROMPT, model=model, max_tokens=MAX_TOKENS,
               output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}})


def response_text(response):
    return "".join(block.text for block in response.content if block.type == "text")


def format_failures(failures):
    return "\n".join(
        f"- [{f['rule']}] {f['path']}: expected {f['expected']}; got {f['got']}. {f['message']}" for f in failures)


def build_corrective_messages(messages, invalid_output, failures):
    """TODO 5: return (new_messages, feedback_text) for the retry call.
    new_messages = the earlier conversation + the invalid output as an "assistant" message + a "user" message
    that lists the EXACT failures (use format_failures) and asks for the corrected JSON only.
    Appending (not replacing) lets the model see earlier corrections."""
    feedback = ("Your previous JSON failed validation against our purchase-order records:\n" + format_failures(failures) +
                "\nReturn the corrected JSON object only. Fix every listed failure; do not change fields that were not flagged.")
    return messages + [{"role": "assistant", "content": invalid_output}, {"role": "user", "content": feedback}], feedback


def extract_with_retry(model, email, purchase_orders):
    """Returns {"email_id", "status": "accepted"|"needs_review", "attempts", "extraction", "attempt_log": [...]}.
    Each attempt_log entry needs: email_id, attempt, model, valid, failure_rules, failures, feedback,
    input_tokens, output_tokens."""
    user_text = build_request_text(email)
    messages = [{"role": "user", "content": user_text}]
    log = []
    feedback = ""
    # TODO 6: (a) loop at most MAX_ATTEMPTS times, (b) after a failed attempt call build_corrective_messages,
    #         (c) append a log entry for EVERY attempt, (d) if all attempts fail, return status "needs_review"
    #         with extraction None. Never trust the last invalid output.
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


# ----------------------------------------------------------------------------------------------
# STEP 4 (provided): run all emails, print the validator hit table, save evidence.
# ----------------------------------------------------------------------------------------------
def load_data():
    emails = json.loads((DATA / "receiving_emails.json").read_text(encoding="utf-8"))
    po_list = json.loads((DATA / "purchase_orders.json").read_text(encoding="utf-8"))["purchase_orders"]
    truth = json.loads((DATA / "ground_truth.json").read_text(encoding="utf-8"))
    return emails, {po["po_number"]: po for po in po_list}, truth


def matches_truth(extraction, expected):
    got_lines = [(l.get("sku"), l.get("qty_received"), l.get("uom"), l.get("condition")) for l in extraction.get("lines", [])]
    want_lines = [(l["sku"], l["qty_received"], l["uom"], l["condition"]) for l in expected["lines"]]
    return (got_lines == want_lines and extraction.get("po_number") == expected["po_number"]
            and extraction.get("received_date") == expected["received_date"]
            and extraction.get("needs_followup") == expected["needs_followup"])


def main():
    global calls_for_this_email
    from claude_client import MODEL_BALANCED, MODEL_FAST

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="balanced", choices=["balanced", "fast"])
    parser.add_argument("--only", default="", help="comma-separated email ids, e.g. GR-005,GR-017")
    args = parser.parse_args()
    model = MODEL_BALANCED if args.model == "balanced" else MODEL_FAST

    emails, purchase_orders, truth = load_data()
    if args.only:
        emails = [email for email in emails if email["email_id"] in set(args.only.split(","))]
    print(f"model={model}  MAX_ATTEMPTS={MAX_ATTEMPTS}  TODAY={TODAY}")

    results, runaway = [], []
    for email in emails:
        calls_for_this_email = 0
        try:
            result = extract_with_retry(model, email, purchase_orders)
        except RunawayLoop as error:
            print(f"  !! RUNAWAY {email['email_id']}: {error}")
            runaway.append(email["email_id"])
            result = {"email_id": email["email_id"], "status": "runaway", "attempts": calls_for_this_email, "extraction": None, "attempt_log": []}
        results.append(result)
        print(f"  {result['email_id']}  status={result['status']:<12} attempts={result['attempts']}")

    log = [entry for result in results for entry in result["attempt_log"]]
    hits = {}
    for entry in log:
        for rule in entry["failure_rules"]:
            hits[rule] = hits.get(rule, 0) + 1
    accepted = [r for r in results if r["status"] == "accepted"]
    exact = sum(1 for r in accepted if r["extraction"] and matches_truth(r["extraction"], truth[r["email_id"]]))
    review = [r["email_id"] for r in results if r["status"] == "needs_review"]

    print("\nvalidator hit table (failures seen across all attempts):")
    for rule, count in sorted(hits.items()):
        print(f"  {rule:<24}{count}")
    if not hits:
        print("  (none - either every output was perfect or your validators are not firing)")
    print(f"\nemails: {len(results)}  accepted: {len(accepted)} (exact vs ground truth: {exact})  needs_review: {len(review)}  runaway: {len(runaway)}")

    EVIDENCE_FILE.parent.mkdir(exist_ok=True)
    EVIDENCE_FILE.write_text(json.dumps({
        "model": model, "max_attempts": MAX_ATTEMPTS,
        "emails": [{"email_id": r["email_id"], "status": r["status"], "attempts": r["attempts"], "extraction": r["extraction"]} for r in results],
        "attempt_log": log, "validator_hits": hits, "needs_review": review, "runaway": runaway,
        "accepted_exact_vs_truth": exact,
    }, indent=2), encoding="utf-8")
    print("evidence saved - now run: python check.py")


if __name__ == "__main__":
    main()
