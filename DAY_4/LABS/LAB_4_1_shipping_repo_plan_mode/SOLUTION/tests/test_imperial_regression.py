"""Regression tests for imperial parcels."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc.models import Parcel  # noqa: E402
from shipcalc.quote import get_quote  # noqa: E402

CARRIERS = ("acme", "zipfast")


class ImperialRegression(unittest.TestCase):
    def test_light_imperial_parcel_hits_the_kg_band(self):
        for carrier in CARRIERS:
            self.assertEqual(get_quote(Parcel(6.0, "lb", (2, 2, 2), "in"), carrier), 900)

    def test_bulky_imperial_parcel_is_billed_on_dimensional_weight(self):
        for carrier in CARRIERS:
            self.assertEqual(get_quote(Parcel(1.0, "lb", (20, 15, 10), "in"), carrier), 2200)

    def test_metric_and_imperial_descriptions_agree(self):
        metric = Parcel(2.72155422, "kg", (50.8, 38.1, 25.4), "cm")
        imperial = Parcel(6.0, "lb", (20, 15, 10), "in")
        for carrier in CARRIERS:
            self.assertEqual(get_quote(metric, carrier, 2), get_quote(imperial, carrier, 2))


if __name__ == "__main__":
    unittest.main()
