"""Acceptance script for imperial parcels (deliberately NOT in tests/).

An imperial parcel must be priced the same through every carrier, and the same as the identical
metric parcel.  Run: python scripts/hidden_regression_units.py
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc.models import Parcel  # noqa: E402
from shipcalc.quote import get_quote  # noqa: E402


class ImperialAcceptance(unittest.TestCase):
    def test_zipfast_converts_pounds_to_kilograms(self):
        # 6 lb = 2.72 kg -> the 1-5 kg band (900), not the 5-20 kg band a raw "6" would hit
        self.assertEqual(get_quote(Parcel(6.0, "lb", (2, 2, 2), "in"), "zipfast"), 900)

    def test_acme_dimensional_weight_uses_centimetres(self):
        # 20x15x10 in = 49,161 cm3 -> 9.83 kg dimensional weight at divisor 5000 -> 5-20 kg band (2200)
        self.assertEqual(get_quote(Parcel(1.0, "lb", (20, 15, 10), "in"), "acme"), 2200)

    def test_zipfast_dimensional_weight_uses_centimetres(self):
        # same parcel, divisor 6000 -> 8.19 kg -> 2200
        self.assertEqual(get_quote(Parcel(1.0, "lb", (20, 15, 10), "in"), "zipfast"), 2200)

    def test_metric_and_imperial_descriptions_of_one_parcel_agree(self):
        metric = Parcel(2.72155422, "kg", (50.8, 38.1, 25.4), "cm")
        imperial = Parcel(6.0, "lb", (20, 15, 10), "in")
        for carrier in ("acme", "zipfast"):
            self.assertEqual(get_quote(metric, carrier, 2), get_quote(imperial, carrier, 2))


if __name__ == "__main__":
    unittest.main()
