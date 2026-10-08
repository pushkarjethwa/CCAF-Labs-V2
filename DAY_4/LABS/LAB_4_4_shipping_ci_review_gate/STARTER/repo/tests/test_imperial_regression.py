import pytest

from shipcalc.models import Parcel
from shipcalc.quote import get_quote


@pytest.mark.parametrize("carrier", ["acme", "zipfast"])
def test_light_imperial_parcel_hits_the_kg_band(carrier):
    assert get_quote(Parcel(6.0, "lb", (2, 2, 2), "in"), carrier) == 900


@pytest.mark.parametrize("carrier", ["acme", "zipfast"])
def test_bulky_imperial_parcel_is_billed_on_dimensional_weight(carrier):
    assert get_quote(Parcel(1.0, "lb", (20, 15, 10), "in"), carrier) == 2200


@pytest.mark.parametrize("carrier", ["acme", "zipfast"])
def test_metric_and_imperial_descriptions_agree(carrier):
    metric = Parcel(2.72155422, "kg", (50.8, 38.1, 25.4), "cm")
    imperial = Parcel(6.0, "lb", (20, 15, 10), "in")
    assert get_quote(metric, carrier, 2) == get_quote(imperial, carrier, 2)
