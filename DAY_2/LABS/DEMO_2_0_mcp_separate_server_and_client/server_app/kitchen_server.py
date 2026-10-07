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
from mcp.types import CallToolResult, TextContent

import kitchen

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


@mcp.tool()
def place_order(item: str, qty: int) -> CallToolResult:
    """Place an order for one menu item. Writes to the kitchen. Fails if the item is out of stock."""
    try:
        return reply(kitchen.place_order(item, qty))
    except ValueError as error:
        return reply(str(error), is_error=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    port = parser.parse_args().port
    print(f"kitchen server is open at http://127.0.0.1:{port}/mcp  (Ctrl+C to close)  [build 2: tool errors keep their reason]", file=sys.stderr, flush=True)
    uvicorn.run(mcp.streamable_http_app(), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
