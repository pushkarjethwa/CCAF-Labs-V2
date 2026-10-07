"""The kitchen as an MCP server (the waiter). It adds NO new logic: it only puts the kitchen behind the MCP standard.

Run by the demo as a child process over stdio. Two rules for stdio servers:
  1. stdout is the wire: never print() to it. Log to stderr.
  2. Describe every tool well: the description is all the model sees.
Use --noisy to break rule 1 on purpose (stage 4).
"""
import sys

from mcp.server.mcpserver import MCPServer

import kitchen

if "--noisy" in sys.argv:
    print("Kitchen is open!", end="")          # BUG on purpose: this goes onto the wire

mcp = MCPServer("pizza-kitchen")


@mcp.resource("menu://today", mime_type="text/plain")
def todays_menu() -> str:
    """Today's menu board with prices."""
    return kitchen.menu_text()


@mcp.tool()
def check_stock(item: str) -> str:
    """How many portions of one menu item are left. Read-only. Use before ordering."""
    return f"{kitchen.check_stock(item)} {item} left"


if kitchen.VERSION == 1:
    @mcp.tool()
    def place_order(item: str, qty: int) -> str:
        """Place an order for one menu item. Writes to the kitchen. Fails if the item is out of stock."""
        return kitchen.place_order(item, qty)
else:
    @mcp.tool()
    def place_order(item: str, quantity: int, table: int) -> str:
        """Place an order for one menu item at a table. Writes to the kitchen. Fails if the item is out of stock."""
        return kitchen.place_order(item, quantity, table)


if __name__ == "__main__":
    print("kitchen server starting (this line goes to stderr)", file=sys.stderr)
    mcp.run(transport="stdio")
