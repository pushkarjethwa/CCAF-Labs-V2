"""The restaurant's kitchen: plain Python, no MCP in this file."""

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


def place_order(item, qty):
    """Take an order and reduce the stock."""
    if check_stock(item) < qty:
        raise ValueError(f"only {STOCK[item]} {item} left")
    STOCK[item] -= qty
    return f"order placed: {qty} x {item} = ${MENU[item] * qty}"
