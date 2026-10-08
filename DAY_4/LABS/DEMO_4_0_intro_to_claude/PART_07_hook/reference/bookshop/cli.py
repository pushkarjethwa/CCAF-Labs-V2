"""Command line: python -m bookshop summary | low-stock"""
from bookshop import inventory, reports


def main(argv):
    command = argv[0] if argv else "summary"
    books = inventory.load_books()
    if command == "summary":
        print("\n".join(reports.inventory_summary(books)))
        return 0
    if command == "low-stock":
        print("\n".join(reports.low_stock_report(books)))
        return 0
    print(f"unknown command: {command}")
    return 2
