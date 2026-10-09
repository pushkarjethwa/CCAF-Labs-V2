"""Demo 5H - The tool bodies, as plain Python. No SDK, no model, no network.

Read-only tools: check_stock, get_price, read_calendar. One write tool: reserve_slot (idempotent, one booking per request).
The data in data/*.json is author-written. Argument limits are enforced in the gate (team_policy.py) and again here.
"""
import json
from pathlib import Path

from team_policy import DATA, POLICY, WEEK_DAYS

STOCK = json.loads((DATA / "stock.json").read_text(encoding="utf-8"))["items"]
PRICE_FILE = json.loads((DATA / "prices.json").read_text(encoding="utf-8"))
PRICES, BULK = PRICE_FILE["items"], PRICE_FILE["bulk_discount"]
RESERVATIONS_FILE = "reservations.json"  # the kitchen's booking record, in the results folder


def slot_times():
    """Every half-hour slot start inside business hours: 08:00, 08:30 ... 15:30."""
    limits = POLICY["limits"]
    first, last = (int(limits[key][:2]) * 60 + int(limits[key][3:]) for key in ("first_slot", "last_slot"))
    return [f"{m // 60:02d}:{m % 60:02d}" for m in range(first, last + 1, 30)]


# -- Reads ------------------------------------------------------------------------------------------------------

def check_stock(items):
    """One line per item: how many are needed, how many are on the shelf, where, and when the next delivery comes."""
    lines = []
    for line in items:
        row = STOCK[line["item"]]
        verdict = "ok" if row["on_hand"] >= line["quantity"] else "SHORT"
        lines.append(f"{line['item']}: need {line['quantity']} {row['unit']}, on hand {row['on_hand']} ({row['lot']}, {row['supplier']}, "
                     f"{row['location']}), restock {row['restock']} -> {verdict}")
    return "\n".join(lines)


def quote(items):
    """Price the lines. A line of BULK['min_quantity'] units or more gets the bulk discount. Return (lines, total, discount)."""
    lines, total, discount = [], 0.0, 0.0
    for line in items:
        cost = PRICES[line["item"]]["unit_price"] * line["quantity"]
        saved = cost * BULK["percent"] / 100 if line["quantity"] >= BULK["min_quantity"] else 0.0
        lines.append(f"{line['item']}: {line['quantity']} x {PRICES[line['item']]['unit_price']:.2f} = {cost:.2f}, discount {saved:.2f}")
        total, discount = total + cost - saved, discount + saved
    return lines, round(total, 2), round(discount, 2)


def get_price(items):
    """The priced lines, the discount and the total in USD."""
    lines, total, discount = quote(items)
    return "\n".join(lines + [f"discount total {discount:.2f}", f"order total {total:.2f} USD"])


def load_reservations(results):
    """The booking record: request id -> slot. Empty when nothing is booked."""
    path = Path(results) / RESERVATIONS_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_calendar(results, date):
    """Every slot of the day with 'free' or the reason it is busy. Slots already reserved by this team count as busy."""
    busy = WEEK_DAYS[date]["busy"]
    reserved = {slot.split("T")[1]: request_id for request_id, slot in load_reservations(results).items() if slot.startswith(date)}
    rows = [f"{date}T{clock}  " + (busy.get(clock) or (f"reserved for {reserved[clock]}" if clock in reserved else "free"))
            for clock in slot_times()]
    return "\n".join(rows)


def reservation_for(results, request_id):
    """The slot booked for this request, or None."""
    return load_reservations(results).get(request_id)


# -- The one write ----------------------------------------------------------------------------------------------

def reserve_slot(results, request_id, slot):
    """Book a slot. Idempotent: a request that already has a booking gets the same booking back, and nothing changes."""
    bookings = load_reservations(results)
    if request_id in bookings:
        return f"{request_id} already holds {bookings[request_id]}. Nothing changed."
    date, clock = slot.split("T")
    if WEEK_DAYS[date]["busy"].get(clock) or slot in bookings.values():
        return f"Slot {slot} is not free. Nothing reserved."
    bookings[request_id] = slot
    Path(results).mkdir(parents=True, exist_ok=True)
    (Path(results) / RESERVATIONS_FILE).write_text(json.dumps(bookings, indent=2), encoding="utf-8")
    return f"Reserved {slot} for {request_id}."
