"""Unit conversion tests."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc import units  # noqa: E402


class UnitTests(unittest.TestCase):
    def test_lb_to_kg(self):
        self.assertAlmostEqual(units.lb_to_kg(10), 4.5359237, places=9)

    def test_in_to_cm(self):
        self.assertEqual(units.in_to_cm(10), 25.4)


if __name__ == "__main__":
    unittest.main()
