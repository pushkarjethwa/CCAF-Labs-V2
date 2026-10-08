from shipcalc.models import Parcel
from shipcalc.quote import get_quote


def test_acme_quote_for_a_small_metric_parcel():
    assert get_quote(Parcel(2.0), "acme") == 750


def test_zipfast_converts_pounds_too():
    assert get_quote(Parcel(2.0, "lb"), "zipfast") == 500
