"""ACME Freight adapter."""
from .. import packaging, rates, units
from ..models import Parcel


def quote(parcel: Parcel, zone: int) -> int:
    kg = units.lb_to_kg(parcel.weight) if parcel.weight_unit == "lb" else parcel.weight
    billable = packaging.billable_weight_kg(kg, parcel.dims, rates.divisor("acme"))
    return rates.price_cents(billable, zone)
