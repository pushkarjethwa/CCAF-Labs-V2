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
    return []


def check_lines(extraction, po):
    """TODO 2: for every line -> NOTE_REQUIRED, SKU_NOT_ON_PO, UOM_INVALID, QTY_CONDITION_MISMATCH.
    `po` is None when po_number is null or unknown: skip the checks that need the PO."""
    return []


def check_dates(extraction, po, today):
    """TODO 3: DATE_FORMAT, DATE_BEFORE_PO (only if po is known), DATE_FUTURE. `today` is a datetime.date."""
    return []


def check_followup(extraction):
    """TODO 4: FOLLOWUP_INCONSISTENT."""
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
    return messages, ""


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
    attempts = 0
    while True:  # no cap, no log, no fallback: these are the defects you fix
        attempts += 1
        response = call_model(model, messages)
        extraction, failures = parse_model_output(response_text(response))
        if extraction is not None:
            failures = validate_extraction(extraction, email["text"], purchase_orders, TODAY)
        if not failures:
            break
        messages = [{"role": "user", "content": user_text}]  # re-sends the SAME request: the model learns nothing
    return {"email_id": email["email_id"], "status": "accepted", "attempts": attempts, "extraction": extraction, "attempt_log": []}


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
