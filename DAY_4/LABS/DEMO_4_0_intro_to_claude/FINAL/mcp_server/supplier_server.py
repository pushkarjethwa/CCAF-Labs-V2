"""The supplier's stock list as an MCP server. It adds NO new logic: it wraps supplier.py.

Claude Code starts it as a child process over stdio. stdout is the wire, so never print() to it.
"""
import sys

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

import supplier

mcp = MCPServer("supplier")


def reply(text, is_error=False):
    """Build a tool result."""
    return CallToolResult(is_error=is_error, content=[TextContent(type="text", text=text)])


@mcp.tool()
def supplier_stock(isbn: str) -> CallToolResult:
    """How many copies the supplier has for one ISBN, and how many days it takes to ship. Read-only."""
    try:
        return reply(supplier.supplier_stock(isbn))
    except ValueError as error:
        return reply(str(error), is_error=True)


@mcp.tool()
def supplier_catalog() -> CallToolResult:
    """The supplier's stock for every ISBN they list, one line each. Read-only."""
    return reply(supplier.supplier_catalog())


if __name__ == "__main__":
    print("supplier server starting (this line goes to stderr)", file=sys.stderr)
    mcp.run(transport="stdio")
