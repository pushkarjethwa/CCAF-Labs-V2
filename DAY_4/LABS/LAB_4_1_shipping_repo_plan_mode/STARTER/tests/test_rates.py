"""Rate tests."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc import rates  # noqa: E402


class RateTests(unittest.TestCase):
    def test_bands_and_zone(self):
        self.assertEqual(rates.price_cents(0.5, 1), 500)
        self.assertEqual(rates.price_cents(4.9, 2), 1035)
        self.assertEqual(rates.price_cents(20.0, 1), 2200)

    def test_too_heavy(self):
        with self.assertRaises(ValueError):
            rates.price_cents(71, 1)


if __name__ == "__main__":
    unittest.main()
