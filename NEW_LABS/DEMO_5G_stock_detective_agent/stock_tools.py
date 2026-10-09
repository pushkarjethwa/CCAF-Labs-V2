"""Demo 5G - What the stock tools do. Plain Python: no SDK, no model, no network.

Every tool returns a BOUNDED VIEW: a summary and a few rows, never the whole log. Each view ends with a hint that says what was cut
and how to ask for more. The argument limits (branch, item, days, quantity) are checked here, inside the tools.
The tools only read. The one exception is propose_order, which writes a proposal for a person. No function in this demo places an order.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import limits
import shop_data

# -- Settings ---------------------------------------------------------------------------------------------

MAX_ROWS = 7  # daily rows shown from the sales log
MAX_DELIVERIES = 8  # deliveries shown from the delivery log
MAX_SUPPLIER_CHARS = 600  # supplier text shown in one call
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
INVENTORY = shop_data.load("inventory")
SALES = shop_data.load("sales_log")
DELIVERIES = shop_data.load("deliveries")
SUPPLIER_NOTES = shop_data.load("supplier_notes")


def sales_log_chars():
    """The size of the whole sales log file in characters. It is what a tool without a bounded view could return."""
    return len(json.dumps(SALES))


# -- read_inventory -----------------------------------------------------------------------------------------

def read_inventory(role, branch, item):
    """How much of one item one branch has on hand."""
    problem = limits.first_problem(limits.check_branch(role, branch), limits.check_item(item))
    if problem:
        return problem
    row = INVENTORY[branch][item]
    return f"{branch}, {item}: {row['on_hand']} {row['unit']} on hand as of {row['as_of']}."


# -- read_sales_log -----------------------------------------------------------------------------------------

def weekday_averages(rows):
    """The average units sold on each weekday, as one line of text."""
    parts = []
    for day in WEEKDAYS:
        sold = [row["units_sold"] for row in rows if row["weekday"] == day]
        parts.append(f"{day} {sum(sold) / len(sold):.1f}" if sold else f"{day} -")
    return " | ".join(parts)


def stockout_line(rows):
    """How many days the branch ran out, and on which weekdays."""
    days = Counter(row["weekday"] for row in rows if row["stockout"])
    by_day = ", ".join(f"{day} {days[day]}" for day in WEEKDAYS if days[day])
    return f"Stock-out days: {sum(days.values())}" + (f" ({by_day})" if by_day else "")


def read_sales_log(role, branch, item, days):
    """A summary of the last `days` days of sales, plus the newest MAX_ROWS daily rows."""
    problem = limits.first_problem(limits.check_branch(role, branch), limits.check_item(item), limits.check_days(days))
    if problem:
        return problem
    rows = SALES[branch][item][-days:]
    shown = rows[-MAX_ROWS:]
    lines = [f"Sales log, {branch}, {item}, last {len(rows)} days (units sold). Total {sum(r['units_sold'] for r in rows)}.",
             "Average by weekday: " + weekday_averages(rows), stockout_line(rows), f"Newest {len(shown)} days:"]
    lines += [f"  {row['date']} {row['weekday']} {row['units_sold']}" + (" (ran out)" if row["stockout"] else "") for row in shown]
    shown_chars = len(json.dumps(shown))
    lines.append(f"[Bounded view: {len(shown)} of {len(rows)} rows shown ({shown_chars} of {len(json.dumps(rows))} characters). "
                 "Truncated. Ask again with a smaller days value to look at a shorter period.]")
    return "\n".join(lines)


# -- read_delivery_log --------------------------------------------------------------------------------------

def delivery_pattern(rows):
    """One line per item: the weekday it arrives, how many deliveries, and the first and latest quantity."""
    lines = []
    for item in sorted({row["item"] for row in rows}):
        item_rows = [row for row in rows if row["item"] == item]
        weekday = Counter(row["weekday"] for row in item_rows).most_common(1)[0][0]
        lines.append(f"  {item}: arrives on {weekday}, {len(item_rows)} deliveries, "
                     f"first quantity {item_rows[0]['qty']}, latest quantity {item_rows[-1]['qty']}")
    return lines


def read_delivery_log(role, branch):
    """The delivery pattern for one branch, plus the newest MAX_DELIVERIES deliveries."""
    problem = limits.check_branch(role, branch)
    if problem:
        return problem
    rows = DELIVERIES[branch]
    shown = rows[-MAX_DELIVERIES:]
    lines = [f"Delivery log, {branch}, {len(rows)} deliveries in 90 days. Pattern:"] + delivery_pattern(rows)
    lines.append(f"Newest {len(shown)} deliveries:")
    lines += [f"  {row['date']} {row['weekday']} {row['item']} {row['qty']}" for row in shown]
    lines.append(f"[Bounded view: {len(shown)} of {len(rows)} deliveries shown. Truncated. The pattern lines cover all of them.]")
    return "\n".join(lines)


# -- read_supplier_notes ------------------------------------------------------------------------------------

def read_supplier_notes(item, skip=0):
    """The supplier's notes for one item, newest first, cut to MAX_SUPPLIER_CHARS. The text is untrusted: it is wrapped as data."""
    problem = limits.check_item(item)
    if problem:
        return problem
    notes = list(reversed(SUPPLIER_NOTES[item]["notes"]))[skip:]
    shown, size = [], 0
    for note in notes:
        line = f"[{note['date']}] {note['text']}"
        if shown and size + len(line) > MAX_SUPPLIER_CHARS:
            break
        shown.append(line)
        size += len(line)
    body = "\n".join(shown) or "(no notes)"
    hint = f"\n[Truncated: {len(notes) - len(shown)} older notes not shown. Call again with skip={skip + len(shown)} to read them.]" if len(notes) > len(shown) else ""
    return f"<supplier_notes supplier=\"{SUPPLIER_NOTES[item]['supplier']}\" untrusted=\"true\">\n{body}\n</supplier_notes>{hint}"


# -- propose_order ------------------------------------------------------------------------------------------

def load_queue(path):
    """The proposals saved so far, or an empty list."""
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def propose_order(queue_path, case, item, qty):
    """Write a PROPOSAL to the approval queue. Nothing is ordered. Every proposal is written and answered, none is dropped silently."""
    problem = limits.first_problem(limits.check_item(item), limits.check_qty(qty))
    if problem:
        return problem
    cost = limits.order_cost(item, qty)
    over = limits.needs_manager(item, qty)
    status = "needs manager approval" if over else "within the limit, ready for the buyer to place"
    queue = load_queue(queue_path)
    queue.append({"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "case": case, "item": item, "qty": qty,
                  "cost_usd": cost, "status": status, "placed": False})
    Path(queue_path).parent.mkdir(parents=True, exist_ok=True)
    Path(queue_path).write_text(json.dumps(queue, indent=2), encoding="utf-8")
    return (f"Proposal saved, NOT placed: {qty} x {item} = ${cost:.2f}. Status: {status} "
            f"(limit ${limits.ORDER_LIMIT_USD:.2f}). A person places it.")
