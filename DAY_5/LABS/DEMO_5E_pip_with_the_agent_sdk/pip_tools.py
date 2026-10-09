"""Demo 5E - What the Pip tools do. Plain Python: no SDK, no model, no network.

Every function here takes the card id as a normal argument. pip_agent_sdk.py binds that id per customer, so the model never passes one.
The demo does not change any balance: redeem_points only reports what would happen.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
MENU = json.loads((DATA / "menu.json").read_text(encoding="utf-8"))
CUSTOMERS = json.loads((DATA / "customers.json").read_text(encoding="utf-8"))
SERVER = "pip"
PREFIX = f"mcp__{SERVER}__"  # the full name of a tool, as the SDK knows it: mcp__pip__read_menu


def card_for(tier):
    """The first demo customer with this tier, or None."""
    for card, customer in CUSTOMERS.items():
        if customer["tier"] == tier:
            return card
    return None


def balance_of(card_id):
    """The points balance for a card, or 0 for an unknown card."""
    return CUSTOMERS.get(card_id, {}).get("balance", 0)


def customer_lines():
    """One line per demo customer, for the start-up screen."""
    return [f"{card}  {customer['name']:<5} default tier: {customer['tier']}" for card, customer in CUSTOMERS.items()]


def read_menu():
    """The menu as one line of text."""
    return "Menu: " + ", ".join(f"{item} ${price:.2f}" for item, price in MENU["items"].items())


def opening_hours():
    """The opening hours as one line of text."""
    return "Hours: " + "; ".join(f"{days} {time}" for days, time in MENU["hours"].items())


def get_points_balance(card_id):
    """The points balance of ONE customer."""
    customer = CUSTOMERS[card_id]
    return f"{customer['name']} has {customer['balance']} points."


def redeem_points(card_id, points):
    """Report a redemption for ONE customer. The balance is not changed in this demo."""
    customer = CUSTOMERS[card_id]
    return f"Redeemed {points} points for {customer['name']}. New balance: {customer['balance'] - points}."
