"""ZipFast adapter."""
from .. import packaging, rates, units
from ..models import Parcel


def quote(parcel: Parcel, zone: int) -> int:
    kg, dims = units.to_metric(parcel)
    billable = packaging.billable_weight_kg(kg, dims, rates.divisor("zipfast"))
    return rates.price_cents(billable, zone)
