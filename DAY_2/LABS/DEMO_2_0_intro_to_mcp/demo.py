"""Demo: Intro to MCP. A restaurant kitchen, three apps that want to use it, and one waiter (an MCP server) that serves them all.

  python demo.py --stage 1      WITHOUT MCP: every app has its own copy of the glue, and a kitchen change breaks them
  python demo.py --stage 2      WITH MCP: start the kitchen server, discover what it offers, and use it
  python demo.py --stage 3      the same kitchen change, and nothing in the apps has to change
  python demo.py --stage 4      the one rule of stdio servers: never print to stdout

No API key and no model: this demo is only about the plug between an app and a system.
"""
import argparse
import asyncio
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "kitchen_server.py")      # absolute path, so it works from any folder


def title(text):
    print("\n" + "=" * 70 + "\n" + text + "\n" + "=" * 70)


# ---------------------------------------------------------------- stage 1: without MCP
# Each app was written by a different team. Each one copied the kitchen's order call into its own glue,
# and wrote its own description of the tool. These three functions are the three copies.
APPS = {
    "chatbot": {"description": "Order a pizza for the customer.",
                "call": "kitchen.place_order('margherita', 2)"},
    "kiosk":   {"description": "place_order(item, qty): puts an order in.",
                "call": "kitchen.place_order(item='margherita', qty=2)"},
    "phone":   {"description": "Orders food. Needs the item name and how many.",
                "call": "kitchen.place_order('margherita', qty=2)"},
}


def run_app_glue(version):
    """Run each app's own copy of the glue against the kitchen of a given version, in a clean process."""
    results = {}
    for name, app in APPS.items():
        code = f"import kitchen; print({app['call']})"
        proc = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True, text=True,
                              env={**os.environ, "KITCHEN_VERSION": str(version)})
        last_line = (proc.stdout.strip() or proc.stderr.strip().splitlines()[-1])
        results[name] = (proc.returncode == 0, last_line)
    return results


def stage1():
    title("STAGE 1 - without MCP: three apps, three copies of the glue")
    print("Each team wrote its own description of the SAME kitchen function:\n")
    for name, app in APPS.items():
        print(f"  {name:<8} says: \"{app['description']}\"")
    print("\nKitchen version 1 (place_order(item, qty)). Each app runs its own glue:")
    for name, (ok, line) in run_app_glue(1).items():
        print(f"  {name:<8} {'OK    ' if ok else 'BROKEN'} {line}")
    print("\nNow the kitchen team 'improves' place_order: qty becomes quantity, and a table number is required.")
    print("Nobody told the app teams. Kitchen version 2:")
    broken = 0
    for name, (ok, line) in run_app_glue(2).items():
        broken += not ok
        print(f"  {name:<8} {'OK    ' if ok else 'BROKEN'} {line[:80]}")
    print(f"\n{broken} of 3 apps broke. Every app needs its own fix, and with 3 kitchens that is up to 9 fixes.")
    print("This is the N x M problem: N apps times M systems = N x M custom connections.")


# ---------------------------------------------------------------- stages 2-4: with MCP
async def open_session(version=1, noisy=False):
    """Start the kitchen server as a child process and return (context manager) an initialized MCP session."""
    from mcp import ClientSession, StdioServerParameters, stdio_client
    args = [SERVER] + (["--noisy"] if noisy else [])
    params = StdioServerParameters(command=sys.executable, args=args, env={**os.environ, "KITCHEN_VERSION": str(version)})
    return params, ClientSession, stdio_client


async def discover(version=1):
    """The generic client: connect, ask what the server offers, and return the tools."""
    params, ClientSession, stdio_client = await open_session(version)
    with open(os.devnull, "w") as quiet:
        async with stdio_client(params, errlog=quiet) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=20)
                return (await session.list_tools()).tools


async def stage2_async():
    params, ClientSession, stdio_client = await open_session(1)
    with open(os.devnull, "w") as quiet:
        async with stdio_client(params, errlog=quiet) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=20)
                print("1. The client connected and said hello (initialize). Now it asks: what do you offer?\n")
                for tool in (await session.list_tools()).tools:
                    arguments = ", ".join(tool.input_schema["properties"])
                    print(f"   tool {tool.name}({arguments})\n        {tool.description}")
                print("\n2. A resource is data the app can read without asking the model. The menu board:")
                menu = await session.read_resource("menu://today")
                for line in menu.contents[0].text.splitlines():
                    print("   " + line)
                print("\n3. Call a tool, exactly as an app (or a model) would:")
                for name, arguments in [("check_stock", {"item": "margherita"}), ("place_order", {"item": "margherita", "qty": 2}),
                                        ("place_order", {"item": "pepperoni", "qty": 1})]:
                    reply = await session.call_tool(name, arguments)
                    print(f"   {name}({arguments}) -> {'ERROR: ' if reply.is_error else ''}{reply.content[0].text}")
                print("\nNotice what the client needed to know about the kitchen: nothing. It asked, and the server told it.")


def stage2():
    title("STAGE 2 - with MCP: the waiter tells you what the kitchen offers")
    asyncio.run(stage2_async())


def pick_arguments(schema):
    """A stand-in for the model: read the tool's schema and fill each parameter. A real model does this from the description."""
    known = {"item": "margherita", "qty": 2, "quantity": 2, "table": 5}
    return {name: known[name] for name in schema["properties"]}


async def use_kitchen(app_name, version):
    """ONE function used by every app: no kitchen-specific code at all."""
    params, ClientSession, stdio_client = await open_session(version)
    with open(os.devnull, "w") as quiet:
        async with stdio_client(params, errlog=quiet) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=20)
                tools = {t.name: t for t in (await session.list_tools()).tools}
                arguments = pick_arguments(tools["place_order"].input_schema)
                reply = await session.call_tool("place_order", arguments)
                return arguments, reply


async def stage3_async():
    for version in (1, 2):
        print(f"\nKitchen version {version}. The same client code, run for each app:")
        for app in APPS:
            arguments, reply = await use_kitchen(app, version)
            print(f"  {app:<8} {'OK    ' if not reply.is_error else 'BROKEN'} sent {arguments} -> {reply.content[0].text}")


def stage3():
    title("STAGE 3 - the same kitchen change, and the apps do not change")
    print("The kitchen team makes the SAME change as in stage 1 (qty -> quantity, table required).")
    print("This time the apps share one client, and the client asks the server for the schema every time.")
    print("(A tiny stand-in for the model reads each tool's schema and fills the arguments. A real model does the same from the description.)")
    asyncio.run(stage3_async())
    print("\nThe server was changed in one place. The three apps were not touched.")
    print("N apps + M servers = N + M pieces, not N x M. Build the connector once, and every MCP app can use it.")


async def noisy_attempt(noisy):
    params, ClientSession, stdio_client = await open_session(1, noisy=noisy)
    with open(os.devnull, "w") as quiet:
        async with stdio_client(params, errlog=quiet) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=8)
                return "connected and said hello"


def stage4():
    title("STAGE 4 - the one rule of stdio servers: stdout is the wire")
    print("With stdio, the app starts the server as a child process, and the server's stdout is the channel.")
    print("The server below prints one friendly line to stdout before it starts (a very common mistake).\n")
    for noisy, label in ((True, "server that prints to stdout"), (False, "server that logs to stderr")):
        try:
            outcome = asyncio.run(noisy_attempt(noisy))
        except asyncio.TimeoutError:
            outcome = "HANG: initialize timed out after 8 seconds (the reply was glued to the stray text)"
        except Exception as error:  # noqa: BLE001 - any failure is the lesson here
            outcome = f"FAILED: {type(error).__name__}"
        print(f"  {label:<32} -> {outcome}")
    print("\nThe fix is one line: send logs to stderr (print(..., file=sys.stderr) or the logging module).")
    print("When a host says 'connection closed' or the server just hangs, search the server for print( first.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4"])
    args = parser.parse_args()
    {"1": stage1, "2": stage2, "3": stage3, "4": stage4}[args.stage]()


if __name__ == "__main__":
    main()
