"""Demo 5G - The guardrail rules, as plain Python. No SDK, no model, no network.

Two kinds of rule live here:
    argument limits   used INSIDE the tools: which branch, which item, how many days, how large an order
    the gate rule     used by the PreToolUse hook: only the listed tools may run, everything else is denied
The model never sees these rules and cannot change them.
"""
import shop_data

# -- Settings ---------------------------------------------------------------------------------------------

SERVER = "stock"
PREFIX = f"mcp__{SERVER}__"  # the full name of a tool, as the SDK knows it: mcp__stock__read_inventory
TOOLS = ["read_inventory", "read_sales_log", "read_supplier_notes", "read_delivery_log", "write_note", "read_notes", "propose_order"]
ALLOWED_TOOLS = [PREFIX + name for name in TOOLS]  # the allow-list. Anything else is denied.
DENIED_BUILT_INS = ["Bash", "Write", "Edit"]  # belt and braces: also named in disallowed_tools
MAX_DAYS = 90  # the longest sales window a tool will read
MAX_NOTE_CHARS = 400  # one working note is short on purpose
MAX_ORDER_QTY = 1000  # cartons or kg in one proposal
ORDER_LIMIT_USD = 150.00  # a proposal above this needs a manager
DEFAULT_ROLE = "branch_manager"
REFUSED = "Refused: "  # every refusal from a tool starts with this, so the screen can show it

ROLES = shop_data.load("roles")  # role -> the branches it may read
CATALOGUE = shop_data.load("catalogue")  # item -> unit, price, supplier


# -- Argument limits (used inside the tools) --------------------------------------------------------------------

def check_branch(role, branch):
    """None when this role may read this branch, otherwise a refusal text."""
    allowed = ROLES.get(role, [])
    if branch in allowed:
        return None
    return f"{REFUSED}the role {role} may not read the branch '{branch}'. It may read: {', '.join(allowed) or 'none'}."


def check_item(item):
    """None when the item is in the catalogue, otherwise a refusal text."""
    if item in CATALOGUE:
        return None
    return f"{REFUSED}'{item}' is not in the catalogue. Items: {', '.join(CATALOGUE)}."


def check_days(days):
    """None when days is a whole number from 1 to MAX_DAYS, otherwise a refusal text."""
    if isinstance(days, int) and 1 <= days <= MAX_DAYS:
        return None
    return f"{REFUSED}days must be a whole number from 1 to {MAX_DAYS}."


def check_note(text):
    """None when the note is short enough, otherwise a refusal text."""
    if 0 < len(text) <= MAX_NOTE_CHARS:
        return None
    return f"{REFUSED}a note must be 1 to {MAX_NOTE_CHARS} characters. Write the fact, not the raw rows."


def check_qty(qty):
    """None when qty is a whole number from 1 to MAX_ORDER_QTY, otherwise a refusal text."""
    if isinstance(qty, int) and 1 <= qty <= MAX_ORDER_QTY:
        return None
    return f"{REFUSED}qty must be a whole number from 1 to {MAX_ORDER_QTY}."


def first_problem(*problems):
    """The first refusal text in the list, or None when every check passed."""
    return next((problem for problem in problems if problem), None)


# -- Order cost -------------------------------------------------------------------------------------------

def order_cost(item, qty):
    """What a proposal would cost, in dollars."""
    return round(CATALOGUE[item]["price_usd"] * qty, 2)


def needs_manager(item, qty):
    """True when the proposal costs more than the limit."""
    return order_cost(item, qty) > ORDER_LIMIT_USD


# -- The gate rule (used by the PreToolUse hook) ---------------------------------------------------------------

def gate(full_tool_name):
    """Deny by default. Return (allowed, reason) for one tool call."""
    if full_tool_name in ALLOWED_TOOLS:
        return True, "on the allow-list"
    return False, f"{full_tool_name} is not on the allow-list (deny by default)"
