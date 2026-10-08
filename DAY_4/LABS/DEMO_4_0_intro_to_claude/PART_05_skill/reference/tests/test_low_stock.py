import unittest

from bookshop import inventory, reports


class LowStockTests(unittest.TestCase):
    def setUp(self):
        self.books = inventory.load_books()

    def test_title_line_and_total_line(self):
        lines = reports.low_stock_report(self.books)
        self.assertEqual(lines[0], "=== LOW STOCK (BELOW 5) ===")
        self.assertEqual(lines[-1], "Total: 4 titles")

    def test_rows_sorted_by_title(self):
        lines = reports.low_stock_report(self.books)
        titles = [line[:28].strip() for line in lines[2:-1]]
        self.assertEqual(titles, ["Harbour Lights", "Night Ferry", "Small Gardens", "The Quiet Engine"])

    def test_threshold_can_change(self):
        lines = reports.low_stock_report(self.books, threshold=1)
        self.assertEqual(lines[0], "=== LOW STOCK (BELOW 1) ===")
        self.assertEqual(lines[-1], "Total: 1 titles")


if __name__ == "__main__":
    unittest.main()
