"""Request handling for the rewards service."""
from . import ledger
from .logging_utils import log_event
from .points import earn_points


def handle_purchase(request: dict) -> dict:
    """Record a purchase. Request keys: customer_id, amount_cents, is_member (optional)."""
    customer_id = request.get("customer_id")
    amount_cents = request.get("amount_cents")
    if not customer_id or not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        return {"ok": False, "error": "customer_id and integer amount_cents are required"}
    if amount_cents < 0:
        return {"ok": False, "error": "amount_cents must not be negative"}
    points = earn_points(amount_cents, bool(request.get("is_member", False)))
    new_balance = ledger.add(customer_id, points)
    log_event("purchase", customer_id, points=points)
    return {"ok": True, "customer_id": customer_id, "points_earned": points, "balance": new_balance}
