"""Unit conversions.  Internal canonical units: kilograms and centimetres.  The ONLY place that knows the constants."""

KG_PER_LB = 0.45359237
CM_PER_IN = 2.54


def lb_to_kg(lb: float) -> float:
    return lb * KG_PER_LB


def in_to_cm(inches: float) -> float:
    return inches * CM_PER_IN


def parcel_kg(parcel) -> float:
    """Actual weight of a Parcel in kilograms, whatever unit the customer used."""
    if parcel.weight_unit == "kg":
        return parcel.weight
    if parcel.weight_unit == "lb":
        return lb_to_kg(parcel.weight)
    raise ValueError("unknown weight unit: %r" % parcel.weight_unit)


def parcel_dims_cm(parcel):
    """(L, W, H) of a Parcel in centimetres, whatever unit the customer used."""
    if parcel.dim_unit == "cm":
        return tuple(parcel.dims)
    if parcel.dim_unit == "in":
        return tuple(in_to_cm(d) for d in parcel.dims)
    raise ValueError("unknown dimension unit: %r" % parcel.dim_unit)
