"""Demo 5H - The team's rules, as plain Python. No model, no SDK, no network.

Every guardrail that is a decision (may this agent call this tool? is this quantity allowed? is this reply well formed?)
is a small function here. The model never sees these rules and cannot change them. They all read ONE table: data/policy.json.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"
POLICY = json.loads((DATA / "policy.json").read_text(encoding="utf-8"))
CATALOGUE = json.loads((DATA / "prices.json").read_text(encoding="utf-8"))["items"]
WEEK_DAYS = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))["days"]
DELEGATE_TOOLS = ("Agent", "Task")  # the delegation tool was renamed Task -> Agent in Claude Code 2.1.63
SERVER = "catering"
SLOT_PATTERN = r"\d{4}-\d\d-\d\dT\d\d:(00|30)"


def mcp(name):
    """The full name of one tool, as the SDK knows it: mcp__catering__<tool>."""
    return f"mcp__{SERVER}__{name}"


def short_name(tool):
    """The plain tool name. mcp__catering__reserve_slot becomes reserve_slot, and Task becomes Agent."""
    return "Agent" if tool in DELEGATE_TOOLS else tool.removeprefix(mcp(""))


def role_of(input_data):
    """Who is calling? Subagent calls carry agent_type (verify on your SDK version). No identity means the orchestrator.

    The orchestrator owns only two tools, so a call with no identity can never use a subagent's tool.
    """
    return input_data.get("agent_type") or "orchestrator"


# -- Argument checks. Each returns None when the value is fine, or a short reason when it is not. -----------------

def check_items(items, policy=POLICY):
    """Items must be catalogue items with a quantity from 1 up to the cap."""
    limits = policy["limits"]
    if not isinstance(items, list) or not items or len(items) > limits["max_lines_per_request"]:
        return f"items must be a list of 1 to {limits['max_lines_per_request']} lines"
    for line in items:
        if not isinstance(line, dict) or line.get("item") not in CATALOGUE:
            return "an item is not in the catalogue"
        quantity = line.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= limits["max_quantity_per_line"]:
            return f"quantity must be a whole number from 1 to {limits['max_quantity_per_line']}"


def check_date(date):
    """The date must be a day of this week's kitchen calendar."""
    if date not in WEEK_DAYS:
        return "date is not a day of this week's calendar"


def check_slot(slot, policy=POLICY):
    """The slot must be YYYY-MM-DDTHH:MM on a half hour, on a calendar day, inside business hours."""
    if not isinstance(slot, str) or not re.fullmatch(SLOT_PATTERN, slot):
        return "slot must look like 2026-10-13T09:30"
    date, clock = slot.split("T")
    limits = policy["limits"]
    if check_date(date):
        return check_date(date)
    if not limits["first_slot"] <= clock <= limits["last_slot"]:
        return f"slot is outside business hours ({limits['first_slot']} to {limits['last_slot']})"


# -- One rule per tool. Each gets the tool arguments and the ledger entry of the order (or None). ----------------

def rule_items(args, order, policy):
    return check_items(args.get("items"), policy)


def rule_calendar(args, order, policy):
    return check_date(args.get("date"))


def rule_reserve(args, order, policy):
    """A slot may be reserved only for a known order with a validated in-stock check, a validated price, and no approval pending."""
    if order is None:
        return "unknown request"
    problem = check_slot(args.get("slot"), policy)
    if problem:
        return problem
    stock, price = order["handoffs"].get("stock_checker"), order["handoffs"].get("pricer")
    if not stock or not price:
        return "no validated stock check and price for this request yet"
    if stock["status"] != "in_stock":
        return "the stock check says short, so nothing is reserved"
    if price["total_usd"] > policy["limits"]["approval_limit_usd"] and order["status"] != "approved":
        return "this order waits for a person to approve it, so no slot is reserved. Do not retry"


def rule_record(args, order, policy):
    return None if order else "unknown request"


RULES = {"check_stock": rule_items, "get_price": rule_items, "read_calendar": rule_calendar,
         "reserve_slot": rule_reserve, "record_order": rule_record}


def gate_decision(role, tool, args, order=None, policy=POLICY):
    """Return ("allow" | "deny", reason). Anything that no rule allows is denied."""
    allowed = policy["roles"].get(role)
    if allowed is None:
        return "deny", f"unknown agent {role}"
    if tool not in allowed:
        return "deny", f"{role} may not call {tool}"
    if tool == "Agent":
        known = args.get("subagent_type") in policy["roles"] and args.get("subagent_type") != "orchestrator"
        return ("allow", "delegation to a known subagent") if known else ("deny", "unknown subagent")
    problem = RULES[tool](args, order, policy)
    return ("deny", problem) if problem else ("allow", "inside the role and argument rules")


# -- Replies from subagents are untrusted data: parse, then check against the schema -----------------------------

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
        elif "max_len" in rule and len(value) > rule["max_len"]:
            problems.append(f"{name} is longer than {rule['max_len']} characters")
    return problems


def wrap_untrusted(text, label="request"):
    """Put outside text inside tags that mark it as data. The text cannot close the tag."""
    clean = text.replace("<", "(").replace(">", ")")
    return f'<{label} trust="untrusted">\n{clean}\n</{label}>'


def redact(text):
    """Remove API keys, emails and phone numbers from a line before it is logged."""
    text = re.sub(r"sk-ant-[\w-]+", "[REDACTED]", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", text)
    return re.sub(r"\+\d[\d-]{7,}", "[phone]", text)
