"""Rate table.  Input weights are KILOGRAMS (billable weight); output is integer cents."""

BANDS = [(1.0, 500), (5.0, 750), (20.0, 2200), (70.0, 5200)]   # (upper bound kg, base cents)
DIVISORS = {"acme": 5000, "zipfast": 6000}                        # cubic cm per kg, per carrier

ZONE_PERMILLE = {1: 1000, 2: 1150, 3: 1300}                      # zone multiplier x 1000


def price_cents(billable_kg: float, zone: int) -> int:
    for upper, cents in BANDS:
        if billable_kg <= upper:
            return (cents * ZONE_PERMILLE[zone] + 500) // 1000
    raise ValueError("parcel too heavy: %.1f kg" % billable_kg)


def divisor(carrier: str) -> int:
    return DIVISORS[carrier]
