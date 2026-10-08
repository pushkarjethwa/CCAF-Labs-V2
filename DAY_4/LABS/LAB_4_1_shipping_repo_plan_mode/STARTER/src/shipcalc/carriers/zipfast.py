"""ZipFast adapter (added later by another team; mirrors acme but not quite)."""
from .. import packaging, rates
from ..models import Parcel


def quote(parcel: Parcel, zone: int) -> int:
    weight = parcel.weight
    billable = packaging.billable_weight_kg(weight, parcel.dims, rates.divisor("zipfast"))
    return rates.price_cents(billable, zone)
