"""Points rules. All math is integer math."""

CENTS_PER_POINT = 100  # 1 point per whole currency unit spent
MEMBER_PERCENT = 150  # members earn 150 percent of the base points


def earn_points(amount_cents: int, is_member: bool) -> int:
    """Return the whole points earned for a purchase of amount_cents."""
    if amount_cents < 0:
        raise ValueError("amount_cents must not be negative")
    base = amount_cents // CENTS_PER_POINT
    if is_member:
        return base * MEMBER_PERCENT // 100
    return base
