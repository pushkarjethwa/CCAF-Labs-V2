"""Dimensional (volumetric) weight.  A carrier bills the larger of actual and dimensional weight.

Inputs are canonical: dimensions in CENTIMETRES, weight in KILOGRAMS (see docs/UNITS.md).  Callers convert first."""


def dim_weight_kg(dims_cm, divisor: int) -> float:
    """dims_cm are L, W, H in centimetres; divisor is cubic centimetres per kilogram (carrier specific)."""
    length, width, height = dims_cm
    return (length * width * height) / divisor


def billable_weight_kg(actual_kg: float, dims_cm, divisor: int) -> float:
    return max(actual_kg, dim_weight_kg(dims_cm, divisor))
