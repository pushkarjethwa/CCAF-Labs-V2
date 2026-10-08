"""Parcel model.  Customers enter US units or metric; internals are kg / cm."""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Parcel:
    weight: float
    weight_unit: str = "kg"          # "kg" | "lb"
    dims: Tuple[float, float, float] = (10.0, 10.0, 10.0)
    dim_unit: str = "cm"             # "cm" | "in"
