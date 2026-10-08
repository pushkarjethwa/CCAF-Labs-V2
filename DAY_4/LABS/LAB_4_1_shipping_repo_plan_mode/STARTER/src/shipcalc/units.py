"""Unit conversions.  Internal canonical units: kilograms and centimetres."""

KG_PER_LB = 0.45359237
CM_PER_IN = 2.54


def lb_to_kg(lb: float) -> float:
    return lb * KG_PER_LB


def in_to_cm(inches: float) -> float:
    return inches * CM_PER_IN
