"""Dimensional (volumetric) weight.  A carrier bills the larger of actual and dimensional weight."""


def dim_weight_kg(dims, divisor: int) -> float:
    """dims are L, W, H in cm; divisor is cubic centimetres per kilogram (carrier specific)."""
    length, width, height = dims
    return (length * width * height) / divisor


def billable_weight_kg(actual_kg: float, dims, divisor: int) -> float:
    return max(actual_kg, dim_weight_kg(dims, divisor))
