"""Unit conversions.  Internal canonical units: kilograms and centimetres."""

KG_PER_LB = 0.45359237
CM_PER_IN = 2.54


def lb_to_kg(lb: float) -> float:
    return lb * KG_PER_LB


def in_to_cm(inches: float) -> float:
    return inches * CM_PER_IN


def to_metric(parcel):
    """Return (weight_kg, (length_cm, width_cm, height_cm)) whatever units the customer used."""
    kg = lb_to_kg(parcel.weight) if parcel.weight_unit == "lb" else parcel.weight
    factor = CM_PER_IN if parcel.dim_unit == "in" else 1.0
    return kg, tuple(side * factor for side in parcel.dims)
