import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rewards import ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        ledger.reset()

    def test_add_and_balance(self):
        self.assertEqual(ledger.add("c1", 5), 5)
        self.assertEqual(ledger.add("c1", 7), 12)
        self.assertEqual(ledger.balance("c1"), 12)

    def test_unknown_customer(self):
        self.assertEqual(ledger.balance("nobody"), 0)


if __name__ == "__main__":
    unittest.main()
