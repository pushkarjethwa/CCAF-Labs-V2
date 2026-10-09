"""Demo 5D - The rules, as plain Python. No model, no SDK, no network.

Every guardrail in this demo that is a decision (is this id valid? may this agent call this tool?) is a small function here.
The model never sees these rules and cannot change them.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"
POLICY = json.loads((DATA / "policy.json").read_text(encoding="utf-8"))
DELEGATE_TOOLS = ("Agent", "Task")  # the delegation tool was renamed Task -> Agent in Claude Code 2.1.63
SERVER = "customers"


def mcp(name):
    """The full name of one tool, as the SDK knows it: mcp__customers__<tool>."""
    return f"mcp__{SERVER}__{name}"


# -- Argument checks. Each returns None when the value is fine, or a short reason when it is not. ------------------

def check_customer_id(value, policy=POLICY):
    if not isinstance(value, str) or not re.fullmatch(policy["customer_id_pattern"], value):
        return "customer_id must look like C-1234"


def check_country(value, policy=POLICY):
    if value not in policy["allowed_countries"]:
        return f"country {value} is not one this agent may read"


def check_refund_amount(value, policy=POLICY):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "amount must be a number"
    if value <= 0:
        return "amount must be greater than zero"
    if value > policy["refund_cap"]:
        return "amount is above the per-refund cap"


def check_key(value, policy=POLICY):
    if not isinstance(value, str) or not re.fullmatch(policy["idempotency_key_pattern"], value):
        return "idempotency_key must be 8 to 64 letters, digits, - or _"


# -- The gate. One function decides, so it is easy to read and easy to test. ---------------------------------------

def gate_decision(role, tool, args, state, policy=POLICY):
    """Return ("allow" | "deny" | "queue", reason). Anything that no rule allows is denied."""
    if tool not in policy["roles"].get(role, []):
        return "deny", f"role {role} may not call {tool}"
    if tool in DELEGATE_TOOLS:
        if args.get("subagent_type") not in policy["roles"] or args.get("subagent_type") == "orchestrator":
            return "deny", "unknown subagent"
        return "allow", "delegation to a known subagent"
    if tool == mcp("read_customer"):
        problem = check_customer_id(args.get("customer_id"), policy) or check_country(args.get("country"), policy)
        if problem:
            return "deny", f"{problem}. Do not retry. Report this to a person."
        return "allow", "id and country are inside the read rules"
    if tool == mcp("issue_refund"):
        problem = (check_customer_id(args.get("customer_id"), policy) or check_refund_amount(args.get("amount"), policy)
                   or check_key(args.get("idempotency_key"), policy))
        if problem:
            return "deny", problem
        order_amount = state["handoffs"].get(args["customer_id"])
        if order_amount is None:
            return "deny", "no validated account check for this customer yet"
        if args["amount"] > order_amount:
            return "deny", "amount is above the order amount"
        if args["amount"] > policy["approval_limit"]:
            return "queue", "amount is above the approval limit, so a person must approve it"
        return "allow", "within the approval limit"
    return "deny", "no rule allows this tool (deny by default)"


# -- Untrusted text, schemas and secrets ---------------------------------------------------------------------------

def wrap_untrusted(text, label="customer_message"):
    """Put outside text inside tags that mark it as data. The text cannot close the tag."""
    clean = text.replace("<", "(").replace(">", ")")
    return f'<{label} trust="untrusted">\n{clean}\n</{label}>'


def find_instructions(text, policy=POLICY):
    """Return the instruction-like phrases found in a text. This is a signal for people, not the defence."""
    return [m.group(0) for p in policy["instruction_patterns"] for m in re.finditer(p, text, re.IGNORECASE)]


def extract_json(text):
    """Return the first JSON object in a model reply, or None."""
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return None


def check_schema(obj, schema):
    """Return a list of problems. An empty list means the object matches the schema."""
    if not isinstance(obj, dict):
        return ["the reply is not a JSON object"]
    problems = [f"unexpected field {name}" for name in obj if name not in schema]
    for name, rule in schema.items():
        if name not in obj:
            problems.append(f"missing {name}")
            continue
        value, kind = obj[name], {"string": str, "number": (int, float)}[rule["type"]]
        if not isinstance(value, kind) or isinstance(value, bool):
            problems.append(f"{name} must be a {rule['type']}")
        elif "enum" in rule and value not in rule["enum"]:
            problems.append(f"{name} must be one of {rule['enum']}")
        elif "min" in rule and value < rule["min"]:
            problems.append(f"{name} must be at least {rule['min']}")
        elif "pattern" in rule and not re.fullmatch(rule["pattern"], value):
            problems.append(f"{name} has the wrong format")
    return problems


def mask_secret(token):
    """Show only the start of a secret and its length, never the whole value."""
    return f"{token[:5]}... ({len(token)} chars)"


def mask_id(customer_id):
    """C-1001 becomes C-10**."""
    return customer_id[:-2] + "**" if isinstance(customer_id, str) else "?"


def redact(text, secrets=()):
    """Remove tokens, emails and phone numbers from a line before it is logged or printed."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"\b(demo-(read|write)-\w+|sk-ant-[\w-]+)", "[REDACTED]", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", text)
    return re.sub(r"\+\d[\d-]{7,}", "[phone]", text)
