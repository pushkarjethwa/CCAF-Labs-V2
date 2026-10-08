"""Reports for the shop owner."""


def inventory_summary(books):
    """One line per book, sorted by title, with the shelf value at the end."""
    lines = ["=== INVENTORY SUMMARY ===", f"{'Title':<28}{'Stock':>6}{'Price':>10}"]
    for book in sorted(books, key=lambda b: b.title):
        lines.append(f"{book.title:<28}{book.stock:>6}{'$' + format(book.price, '.2f'):>10}")
    value = sum(book.price * book.stock for book in books)
    lines.append(f"Total: {len(books)} titles, shelf value ${value:,.2f}")
    return lines


def low_stock_report(books, threshold=5):
    """Books with fewer than `threshold` copies left, in the shop's report style."""
    low = sorted((b for b in books if b.stock < threshold), key=lambda b: b.title)
    lines = [f"=== LOW STOCK (BELOW {threshold}) ===", f"{'Title':<28}{'Stock':>6}"]
    lines += [f"{book.title:<28}{book.stock:>6}" for book in low]
    lines.append(f"Total: {len(low)} titles")
    return lines
