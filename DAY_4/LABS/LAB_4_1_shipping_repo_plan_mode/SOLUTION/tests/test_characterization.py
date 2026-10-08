"""Characterization tests: pin TODAY's correct behaviour before any change."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc.models import Parcel  # noqa: E402
from shipcalc.quote import get_quote  # noqa: E402


class UnitCharacterization(unittest.TestCase):
    def test_metric_parcel_prices_the_same_on_both_carriers(self):
        for carrier in ("acme", "zipfast"):
            self.assertEqual(get_quote(Parcel(3.0, "kg", (20, 20, 20), "cm"), carrier), 900)

    def test_acme_converts_pounds_to_kilograms(self):
        self.assertEqual(get_quote(Parcel(6.0, "lb", (2, 2, 2), "in"), "acme"), 900)


if __name__ == "__main__":
    unittest.main()
