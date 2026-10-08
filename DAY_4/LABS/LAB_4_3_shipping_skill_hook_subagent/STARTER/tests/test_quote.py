from shipcalc.models import Parcel
from shipcalc.quote import get_quote


def test_acme_metric():
    assert get_quote(Parcel(3.0, "kg", (20, 20, 20), "cm"), "acme") == 900


def test_zipfast_metric():
    assert get_quote(Parcel(3.0, "kg", (20, 20, 20), "cm"), "zipfast") == 900


def test_acme_pounds_light_parcel():
    assert get_quote(Parcel(6.0, "lb", (2, 2, 2), "in"), "acme") == 900


def test_unknown_carrier():
    import pytest
    with pytest.raises(ValueError):
        get_quote(Parcel(1.0), "nope")
