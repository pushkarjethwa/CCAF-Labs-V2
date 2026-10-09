"""Demo 5F - What the catering tools do. Plain Python: no SDK, no model, no network.

Stock and prices live in data/stock.json. The model never sees these numbers, it only calls the tools.
send_confirmation does not send real email: it writes one file in the outbox folder, and it writes it only once per order.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
CATALOG = json.loads((DATA / "stock.json").read_text(encoding="utf-8"))["items"]
CUSTOMERS = json.loads((DATA / "customers.json").read_text(encoding="utf-8"))


def item_names():
    """The item names we sell, for example 'coffee, muffin, bagel, cookie'."""
    return ", ".join(CATALOG)


def preferences_for(customer):
    """The standing preferences saved for a customer, for example ['no peanuts']. Empty for a customer we do not know."""
    return CUSTOMERS.get(customer, [])


def unknown_items(items):
    """The names in an item list that we do not sell."""
    return [item["name"] for item in items if item["name"] not in CATALOG]


def check_stock(items):
    """Compare each line with the stock on the shelf. Return {'in_stock': bool, 'shortages': [text, ...]}."""
    shortages = []
    for item in items:
        on_shelf = CATALOG[item["name"]]["stock"]
        if item["qty"] > on_shelf:
            shortages.append(f"{item['name']}: need {item['qty']}, have {on_shelf}")
    return {"in_stock": not shortages, "shortages": shortages}


def price_total(items):
    """The total in dollars for an item list, from the price table."""
    return round(sum(CATALOG[item["name"]]["price"] * item["qty"] for item in items), 2)


def price_items(items):
    """Price each line. Return {'total': dollars, 'lines': [{'name', 'qty', 'line_total'}, ...]}."""
    lines = [{"name": item["name"], "qty": item["qty"], "line_total": round(CATALOG[item["name"]]["price"] * item["qty"], 2)}
             for item in items]
    return {"total": price_total(items), "lines": lines}


def send_confirmation(outbox, order_id, message):
    """Write the confirmation for this order. Return True when it was sent now, False when it had been sent before."""
    path = Path(outbox) / f"{Path(order_id).name}.txt"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(message, encoding="utf-8")
    return True
