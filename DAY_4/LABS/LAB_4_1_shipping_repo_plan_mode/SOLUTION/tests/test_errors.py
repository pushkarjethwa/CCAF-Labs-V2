"""Error-message tests."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc.models import Parcel  # noqa: E402
from shipcalc.quote import get_quote  # noqa: E402


class ErrorTests(unittest.TestCase):
    def test_unknown_carrier_message(self):
        with self.assertRaisesRegex(ValueError, "Unknown carrier: nope"):
            get_quote(Parcel(1.0), "nope")

    def test_unknown_zone_is_a_value_error(self):
        with self.assertRaises(ValueError):
            get_quote(Parcel(1.0), "acme", 4)


if __name__ == "__main__":
    unittest.main()
