"""The restaurant's kitchen: plain Python, no MCP. Every app in this demo wants to use it.

Set KITCHEN_VERSION=2 to simulate the kitchen changing its order function (the day someone "improves" it).
"""
import os

VERSION = int(os.environ.get("KITCHEN_VERSION", "1"))
MENU = {"margherita": 9, "pepperoni": 11, "veggie": 10}      # price in dollars
STOCK = {"margherita": 5, "pepperoni": 0, "veggie": 3}       # portions left


def menu_text():
    """The menu board as plain text."""
    return "\n".join(f"{name}: ${price}" for name, price in MENU.items())


def check_stock(item):
    """How many portions of one item are left."""
    if item not in MENU:
        raise ValueError(f"'{item}' is not on the menu")
    return STOCK[item]


if VERSION == 1:
    def place_order(item, qty):
        """Version 1: item and qty."""
        if check_stock(item) < qty:
            raise ValueError(f"only {STOCK[item]} {item} left")
        return f"order placed: {qty} x {item} = ${MENU[item] * qty}"
else:
    def place_order(item, quantity, table):
        """Version 2: renamed qty to quantity, and a table number is now required."""
        if check_stock(item) < quantity:
            raise ValueError(f"only {STOCK[item]} {item} left")
        return f"order placed for table {table}: {quantity} x {item} = ${MENU[item] * quantity}"
