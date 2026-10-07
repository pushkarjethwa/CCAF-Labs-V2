"""The kitchen as an MCP server (the waiter). It adds NO new logic: it only puts the kitchen behind the MCP standard.

Run by the demo as a child process over stdio. Two rules for stdio servers:
  1. stdout is the wire: never print() to it. Log to stderr.
  2. Describe every tool well: the description is all the model sees.
Use --noisy to break rule 1 on purpose (stage 4).
"""
import sys

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

import kitchen

if "--noisy" in sys.argv:
    print("Kitchen is open!", end="", flush=True)   # BUG on purpose: flush sends it onto the wire at once

mcp = MCPServer("pizza-kitchen")


def reply(text, is_error=False):
    """Build a tool result. We set is_error ourselves, so the client sees the real reason."""
    return CallToolResult(is_error=is_error, content=[TextContent(type="text", text=text)])


@mcp.resource("menu://today", mime_type="text/plain")
def todays_menu() -> str:
    """Today's menu board with prices."""
    return kitchen.menu_text()


@mcp.tool()
def check_stock(item: str) -> CallToolResult:
    """How many portions of one menu item are left. Read-only. Use before ordering."""
    try:
        return reply(f"{kitchen.check_stock(item)} {item} left")
    except ValueError as error:
        return reply(str(error), is_error=True)


if kitchen.VERSION == 1:
    @mcp.tool()
    def place_order(item: str, qty: int) -> CallToolResult:
        """Place an order for one menu item. Writes to the kitchen. Fails if the item is out of stock."""
        try:
            return reply(kitchen.place_order(item, qty))
        except ValueError as error:
            return reply(str(error), is_error=True)
else:
    @mcp.tool()
    def place_order(item: str, quantity: int, table: int) -> CallToolResult:
        """Place an order for one menu item at a table. Writes to the kitchen. Fails if the item is out of stock."""
        try:
            return reply(kitchen.place_order(item, quantity, table))
        except ValueError as error:
            return reply(str(error), is_error=True)


if __name__ == "__main__":
    print("kitchen server starting [build 2: tool errors keep their reason] (this line goes to stderr)", file=sys.stderr)
    mcp.run(transport="stdio")
