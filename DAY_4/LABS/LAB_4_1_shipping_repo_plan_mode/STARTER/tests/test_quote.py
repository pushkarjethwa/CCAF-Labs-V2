"""Quote tests."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc.models import Parcel  # noqa: E402
from shipcalc.quote import get_quote  # noqa: E402


class QuoteTests(unittest.TestCase):
    def test_acme_metric(self):
        self.assertEqual(get_quote(Parcel(3.0, "kg", (20, 20, 20), "cm"), "acme"), 900)

    def test_zipfast_metric(self):
        self.assertEqual(get_quote(Parcel(3.0, "kg", (20, 20, 20), "cm"), "zipfast"), 900)

    def test_acme_pounds_light_parcel(self):
        self.assertEqual(get_quote(Parcel(6.0, "lb", (2, 2, 2), "in"), "acme"), 900)

    def test_unknown_carrier(self):
        with self.assertRaises(ValueError):
            get_quote(Parcel(1.0), "nope")


if __name__ == "__main__":
    unittest.main()
