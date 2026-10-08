"""In-memory points ledger."""

_balances = {}


def add(customer_id: str, points: int) -> int:
    """Add points to a customer and return the new balance."""
    _balances[customer_id] = _balances.get(customer_id, 0) + points
    return _balances[customer_id]


def balance(customer_id: str) -> int:
    """Return the customer's points balance (0 for an unknown customer)."""
    return _balances.get(customer_id, 0)


def reset() -> None:
    """Clear all balances (used by tests)."""
    _balances.clear()
