"""ZipFast adapter: identical unit handling to acme (single conversion point in units.py)."""
from .. import packaging, rates, units
from ..models import Parcel


def quote(parcel: Parcel, zone: int) -> int:
    billable = packaging.billable_weight_kg(units.parcel_kg(parcel), units.parcel_dims_cm(parcel), rates.divisor("zipfast"))
    return rates.price_cents(billable, zone)
