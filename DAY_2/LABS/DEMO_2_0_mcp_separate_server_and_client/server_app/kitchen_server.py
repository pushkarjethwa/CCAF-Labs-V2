"""APP 1: the kitchen's MCP server (the waiter). It runs on its own, in its own terminal, over HTTP.

    python kitchen_server.py              listens on http://127.0.0.1:8000/mcp
    python kitchen_server.py --port 9000  use another port

It knows nothing about the client. Any MCP client that can reach the address can use it.
No login yet: Demo 2D adds keys and roles. Keep this on your own machine.
"""
import argparse
import sys

import uvicorn
from mcp.server.mcpserver import MCPServer

import kitchen

mcp = MCPServer("pizza-kitchen")


@mcp.resource("menu://today", mime_type="text/plain")
def todays_menu() -> str:
    """Today's menu board with prices."""
    return kitchen.menu_text()


@mcp.tool()
def check_stock(item: str) -> str:
    """How many portions of one menu item are left. Read-only. Use before ordering."""
    return f"{kitchen.check_stock(item)} {item} left"


@mcp.tool()
def place_order(item: str, qty: int) -> str:
    """Place an order for one menu item. Writes to the kitchen. Fails if the item is out of stock."""
    return kitchen.place_order(item, qty)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    port = parser.parse_args().port
    print(f"kitchen server is open at http://127.0.0.1:{port}/mcp  (Ctrl+C to close)", file=sys.stderr, flush=True)
    uvicorn.run(mcp.streamable_http_app(), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
