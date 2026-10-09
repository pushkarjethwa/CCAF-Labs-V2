"""Demo 5F - The step rules, as plain Python. No SDK, no model, no network.

data/steps.json is the single source: the options, the gate, the input fields, the output check and the prompts all read it.
The model never sees these rules and cannot change them.
"""
import json
from pathlib import Path

import catering_tools

TABLE = json.loads((Path(__file__).parent / "data" / "steps.json").read_text(encoding="utf-8"))
STEPS = TABLE["steps"]
ORDER = TABLE["order"]
SERVER = TABLE["server"]
PREFIX = f"mcp__{SERVER}__"  # the full name of a tool, as the SDK knows it: mcp__catering__check_stock
APPROVAL_LIMIT = TABLE["approval_limit_usd"]
UNTRUSTED_FIELD = "request_text"  # the only field that holds text typed by a customer
TYPES = {"str": str, "list": list, "bool": bool, "number": (int, float)}


# -- What a step is given -------------------------------------------------------------------------------------

def tools_for(step):
    """The short tool names this step may call. An unknown step may call nothing."""
    return STEPS.get(step, {}).get("tools", [])


def inputs_for(step, state):
    """ONLY the state fields this step reads. This is the whole 'context' of the step."""
    return {field: state[field] for field in STEPS[step]["reads"]}


def quote_untrusted(text):
    """Wrap customer text in tags, so the prompt shows it as data."""
    return f"<customer_request>\n{text}\n</customer_request>"


def build_prompt(given):
    """The user message of a step: one line per field. Customer text is quoted, everything else is JSON."""
    lines = []
    for field, value in given.items():
        shown = quote_untrusted(value) if field == UNTRUSTED_FIELD else json.dumps(value)
        lines.append(f"{field}: {shown}")
    return "\n".join(lines)


def system_prompt(step):
    """The short system prompt of a step."""
    return STEPS[step]["prompt"].replace("{item_names}", catering_tools.item_names())


def rough_tokens(text):
    """About four characters to a token. Good enough to compare sizes."""
    return max(1, len(text) // 4)


# -- Checking what a step returned --------------------------------------------------------------------------

def parse_reply(text):
    """The JSON object in a model reply, or None. A reply wrapped in a code fence is accepted."""
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        value = json.loads(cleaned)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def check_shape(step, output):
    """Return None when every promised field is there with the right type, or a short reason."""
    for field, type_name in STEPS[step]["writes"].items():
        if field not in output:
            return f"{step} did not return the field '{field}'"
        value = output[field]
        if not isinstance(value, TYPES[type_name]) or (type_name == "number" and isinstance(value, bool)):
            return f"{step} returned '{field}' with the wrong type (expected {type_name})"
    return None


def check_items(output, state):
    """parse: every line is a known item with a whole quantity above zero."""
    for item in output["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("qty"), int) or item["qty"] <= 0 or "name" not in item:
            return "parse returned an item line that is not {'name', 'qty'} with a whole quantity above zero"
    unknown = catering_tools.unknown_items(output["items"])
    return f"parse returned items we do not sell: {unknown}" if unknown or not output["items"] else None


def check_stock(output, state):
    """stock: the whole order is on the shelf."""
    return None if output["in_stock"] else f"not enough stock: {output['shortages']}"


def check_total(output, state):
    """price: the total matches the price table, worked out again in code."""
    expected = catering_tools.price_total(state["items"])
    return None if abs(output["total"] - expected) < 0.005 else f"the total {output['total']} does not match the price table ({expected})"


def check_sent(output, state):
    """confirm: a message was written and sent."""
    return None if output["sent"] and output["message"].strip() else "confirm did not send a message"


MEANING = {"parse": check_items, "stock": check_stock, "price": check_total, "confirm": check_sent}


def keep_declared(step, output):
    """Drop any field the step did not promise, so the state stays small and known."""
    return {field: output[field] for field in STEPS[step]["writes"] if field in output}


def validate(step, output, state):
    """Return None when the output may go on to the next step, or a short reason. Runs in plain code, before the next step."""
    problem = check_shape(step, output)
    if problem is None and step in MEANING:
        problem = MEANING[step](output, state)
    return problem


# -- The rules that are not the model's to decide -----------------------------------------------------------

def approval_decision(total):
    """The approval gate, in code. At or under the limit the order is approved here, over it a manager must approve."""
    if total > APPROVAL_LIMIT:
        return {"approved": False, "approved_by": ""}
    return {"approved": True, "approved_by": f"auto (at or under ${APPROVAL_LIMIT})"}


def gate_decision(step, tool, state):
    """Return (allowed, reason) for one tool call. Anything this step's list does not allow is denied."""
    if tool not in tools_for(step):
        return False, f"step {step} may not use {tool}"
    if tool == "send_confirmation" and not state.get("approved"):
        return False, "the order is not approved yet"
    return True, f"step {step} may use {tool}"
