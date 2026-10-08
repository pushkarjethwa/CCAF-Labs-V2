import contextlib
import io
import unittest

from bookshop import cli


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return code, out.getvalue()

    def test_low_stock_command(self):
        code, text = self.run_cli("low-stock")
        self.assertEqual(code, 0)
        self.assertTrue(text.startswith("=== LOW STOCK (BELOW 5) ==="))

    def test_summary_still_works(self):
        code, text = self.run_cli("summary")
        self.assertEqual(code, 0)
        self.assertIn("INVENTORY SUMMARY", text)


if __name__ == "__main__":
    unittest.main()
