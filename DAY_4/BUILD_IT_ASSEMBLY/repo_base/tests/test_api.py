import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rewards import ledger
from rewards.api import handle_purchase
from rewards.logging_utils import log_event


class ApiTests(unittest.TestCase):
    def setUp(self):
        ledger.reset()

    def test_purchase_adds_points(self):
        result = handle_purchase({"customer_id": "c1", "amount_cents": 2000})
        self.assertEqual(result, {"ok": True, "customer_id": "c1", "points_earned": 20, "balance": 20})

    def test_member_purchase(self):
        result = handle_purchase({"customer_id": "c2", "amount_cents": 1000, "is_member": True})
        self.assertEqual(result["points_earned"], 15)

    def test_bad_request(self):
        self.assertFalse(handle_purchase({"customer_id": "c1"})["ok"])
        self.assertFalse(handle_purchase({"customer_id": "c1", "amount_cents": -5})["ok"])

    def test_log_line_has_id_only(self):
        line = log_event("purchase", "c1", points=3)
        self.assertEqual(line, "event=purchase customer_id=c1 points=3")
        with self.assertRaises(ValueError):
            log_event("purchase", "c1", email="a@b.c")


if __name__ == "__main__":
    unittest.main()
