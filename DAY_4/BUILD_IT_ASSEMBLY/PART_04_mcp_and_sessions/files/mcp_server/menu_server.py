"""The Brew & Bean menu as an MCP server (stdio). Prices are in cents and come from menu.json.

Claude Code starts this file as a child process. A stdio server must never print() to stdout,
because stdout is the wire. Needs:  pip install mcp
The two functions below are plain Python, so this file imports and the functions run without `mcp`.
"""
import json
import pathlib
import sys

MENU_FILE = pathlib.Path(__file__).resolve().parent / "menu.json"


def _load():
    with open(MENU_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def get_menu_price(item: str) -> int:
    """Price of one menu item in cents, for example 450 for a Latte. Read-only. Matches the name without case."""
    wanted = item.strip().lower()
    for name, cents in _load().items():
        if name.lower() == wanted:
            return cents
    raise ValueError("%r is not on the menu. Use list_menu to see the items." % item)


def list_menu() -> list:
    """Every menu item with its price in cents, one entry each. Read-only."""
    return [{"item": name, "price_cents": cents} for name, cents in _load().items()]


def main():
    try:
        from mcp.server.mcpserver import MCPServer as Server  # the import style proven in DEMO_2_0
    except ImportError:
        from mcp.server.fastmcp import FastMCP as Server  # older mcp releases

    server = Server("brewbean-menu")
    server.tool()(get_menu_price)
    server.tool()(list_menu)
    print("menu server starting (this line goes to stderr)", file=sys.stderr)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
