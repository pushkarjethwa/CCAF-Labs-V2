import unittest

from bookshop import inventory, reports


class LowStockTests(unittest.TestCase):
    def setUp(self):
        self.books = inventory.load_books()

    def test_lists_four_books_below_five(self):
        lines = reports.low_stock_report(self.books)
        self.assertEqual(len(lines) - 1, 4)

    def test_fewest_first(self):
        lines = reports.low_stock_report(self.books)
        self.assertEqual(lines[1], "- Small Gardens: 0 left")

    def test_threshold_can_change(self):
        lines = reports.low_stock_report(self.books, threshold=1)
        self.assertEqual(lines[1:], ["- Small Gardens: 0 left"])


if __name__ == "__main__":
    unittest.main()
