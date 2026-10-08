import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rewards.points import earn_points


class EarnPointsTests(unittest.TestCase):
    def test_one_point_per_whole_unit(self):
        self.assertEqual(earn_points(1250, False), 12)

    def test_member_bonus_is_integer(self):
        self.assertEqual(earn_points(1000, True), 15)
        self.assertIsInstance(earn_points(1050, True), int)

    def test_zero_and_negative(self):
        self.assertEqual(earn_points(0, True), 0)
        with self.assertRaises(ValueError):
            earn_points(-1, False)


if __name__ == "__main__":
    unittest.main()
