"""The supplier's stock list, as plain functions. The MCP server only wraps these."""

SUPPLIER_STOCK = {
    "9780000000011": {"in_stock": 120, "ships_in_days": 2},
    "9780000000028": {"in_stock": 40, "ships_in_days": 2},
    "9780000000035": {"in_stock": 0, "ships_in_days": 21},
    "9780000000042": {"in_stock": 75, "ships_in_days": 2},
    "9780000000059": {"in_stock": 15, "ships_in_days": 5},
    "9780000000066": {"in_stock": 90, "ships_in_days": 2},
    "9780000000073": {"in_stock": 60, "ships_in_days": 3},
    "9780000000080": {"in_stock": 8, "ships_in_days": 7},
}


def supplier_stock(isbn):
    """Text line with the supplier's copies and shipping time for one ISBN."""
    if isbn not in SUPPLIER_STOCK:
        raise ValueError(f"supplier does not list ISBN {isbn}")
    row = SUPPLIER_STOCK[isbn]
    return f"{isbn}: supplier has {row['in_stock']} copies, ships in {row['ships_in_days']} days"


def supplier_catalog():
    """One text line per ISBN the supplier lists."""
    return "\n".join(supplier_stock(isbn) for isbn in sorted(SUPPLIER_STOCK))
