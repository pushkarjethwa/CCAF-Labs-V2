"""APP 2: an MCP client. A separate program with NO code from the kitchen. It only knows the server's address.

    python kitchen_client.py                          tour the kitchen, then order 2 margherita
    python kitchen_client.py --item pepperoni --qty 1 order something else
    python kitchen_client.py --url http://127.0.0.1:9000/mcp

Start the server first, in another terminal.
"""
import argparse
import asyncio

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def step(number, text):
    print(f"\n{number}. {text}")


async def tour(url, item, qty):
    async with httpx2.AsyncClient(timeout=20.0) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                step(1, "Say hello to the server (MCP method: initialize)")
                await session.initialize()
                print("   connected to", url)

                step(2, "Ask what the server offers (MCP method: tools/list)")
                for tool in (await session.list_tools()).tools:
                    print(f"   tool {tool.name}({', '.join(tool.input_schema['properties'])}): {tool.description}")

                step(3, "Read the menu board (MCP method: resources/read)")
                menu = await session.read_resource("menu://today")
                for line in menu.contents[0].text.splitlines():
                    print("   " + line)

                step(4, "Check the stock, then order (MCP method: tools/call)")
                for name, arguments in [("check_stock", {"item": item}), ("place_order", {"item": item, "qty": qty})]:
                    reply = await session.call_tool(name, arguments)
                    print(f"   {name}({arguments}) -> {'ERROR: ' if reply.is_error else ''}{reply.content[0].text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--item", default="margherita")
    parser.add_argument("--qty", type=int, default=2)
    args = parser.parse_args()
    try:
        asyncio.run(tour(args.url, args.item, args.qty))
    except Exception as error:  # noqa: BLE001 - the usual cause is that the server is not running
        print(f"\nCould not talk to the server at {args.url}  ({type(error).__name__}).")
        print("Is the kitchen server running? Start it in another terminal: python kitchen_server.py")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
