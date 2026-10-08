"""Public entry point: price a parcel with one carrier."""
from .carriers import acme, zipfast
from .models import Parcel

CARRIERS = {"acme": acme.quote, "zipfast": zipfast.quote}


def get_quote(parcel: Parcel, carrier: str, zone: int = 1) -> int:
    if carrier not in CARRIERS:
        raise ValueError("Unknown carrier: %s" % carrier)
    return CARRIERS[carrier](parcel, zone)
