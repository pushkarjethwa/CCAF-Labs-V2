from shipcalc import units
from shipcalc.models import Parcel


def test_pounds_and_inches_become_kg_and_cm():
    kg, dims = units.to_metric(Parcel(10, "lb", (10, 10, 10), "in"))
    assert round(kg, 3) == 4.536
    assert dims == (25.4, 25.4, 25.4)


def test_metric_parcel_is_unchanged():
    assert units.to_metric(Parcel(2.0)) == (2.0, (10.0, 10.0, 10.0))
