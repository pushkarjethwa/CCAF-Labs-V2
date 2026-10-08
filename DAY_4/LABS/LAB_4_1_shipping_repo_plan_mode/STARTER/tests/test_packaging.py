"""Packaging tests."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from shipcalc import packaging  # noqa: E402


class PackagingTests(unittest.TestCase):
    def test_dim_weight_cm(self):
        self.assertEqual(packaging.dim_weight_kg((50, 40, 25), 5000), 10.0)

    def test_billable_is_max(self):
        self.assertEqual(packaging.billable_weight_kg(2.0, (50, 40, 25), 5000), 10.0)
        self.assertEqual(packaging.billable_weight_kg(12.0, (50, 40, 25), 5000), 12.0)


if __name__ == "__main__":
    unittest.main()
