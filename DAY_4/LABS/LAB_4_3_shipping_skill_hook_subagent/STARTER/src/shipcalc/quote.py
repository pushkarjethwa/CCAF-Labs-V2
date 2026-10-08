"""Public entry point: price a parcel with one carrier."""
from .carriers import acme, zipfast
from .models import Parcel

CARRIERS = {"acme": acme.quote, "zipfast": zipfast.quote}


def get_quote(parcel: Parcel, carrier: str, zone: int = 1, rush: bool = False) -> int:
    if carrier not in CARRIERS:
        raise ValueError("unknown carrier: %s" % carrier)
    cents = CARRIERS[carrier](parcel, zone)
    return cents * 5 // 4 if rush else cents
