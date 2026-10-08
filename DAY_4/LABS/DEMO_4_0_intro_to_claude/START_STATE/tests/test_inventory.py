import unittest

from bookshop import inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.books = inventory.load_books()

    def test_loads_eight_books(self):
        self.assertEqual(len(self.books), 8)

    def test_total_value(self):
        self.assertEqual(inventory.total_value(self.books), 790.92)

    def test_find_by_author_ignores_case(self):
        found = inventory.find_by_author(self.books, "mira voss")
        self.assertEqual(sorted(b.title for b in found), ["Paper Moons", "The Salt Road"])


if __name__ == "__main__":
    unittest.main()
