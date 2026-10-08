import unittest

from bookshop import inventory, reports


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.lines = reports.inventory_summary(inventory.load_books())

    def test_starts_with_title_line(self):
        self.assertEqual(self.lines[0], "=== INVENTORY SUMMARY ===")

    def test_rows_are_sorted_by_title(self):
        titles = [line[:28].strip() for line in self.lines[2:-1]]
        self.assertEqual(titles, sorted(titles))

    def test_footer_counts_titles(self):
        self.assertTrue(self.lines[-1].startswith("Total: 8 titles"))


if __name__ == "__main__":
    unittest.main()
