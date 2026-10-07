---
lab:
    title: 'Demo: MCP Server and Client as Separate Apps'
    module: 'Day 2 - Tool Design and MCP'
---

# Demo: MCP server and client as separate apps

In the intro to MCP demo, one script started the server for you, so the server and the client looked like one app. In real life they are two separate programs, often written by different teams and running on different machines. In this demo, you run the pizza kitchen's server in one terminal and a client in another, with no code shared between them. The client only knows the server's address. The demo takes about 10 minutes, has no stages, and needs no API key and no model.

## What the demo shows

1. **Two apps.** The server app and the client app are in separate folders, and they share no files. Only the MCP standard connects them.
2. **A conversation.** The client says hello, asks what the server offers, reads the menu, checks the stock, and places an order. Each step prints the MCP method that it uses.
3. **A server that is not there.** With the server stopped, the client explains the problem instead of crashing.
4. **Independence.** You can run the client as often as you like, with different orders, against the same running server.

## Files in this folder

- **server_app/kitchen_server.py**: App 1. The MCP server (the waiter), over HTTP on port 8000.
- **server_app/kitchen.py**: The kitchen, in plain Python. Only the server uses it.
- **client_app/kitchen_client.py**: App 2. The MCP client. It knows only the server's address.
- **check_offline.py**: A key-free self-check (7 checks).
- **RUN_SHEET.md**: The instructor's script.

## Run the demo

You need two terminals.

1. In both terminals, install the packages once:

    ```
    pip install -r server_app/requirements.txt
    ```

2. In **terminal 1**, start the server and leave it running:

    ```
    cd server_app
    python kitchen_server.py
    ```

    You should see: `kitchen server is open at http://127.0.0.1:8000/mcp (Ctrl+C to close)`.

3. In **terminal 2**, run the client:

    ```
    cd client_app
    python kitchen_client.py
    ```

4. Run the client again with another order:

    ```
    python kitchen_client.py --item pepperoni --qty 1
    ```

5. Stop the server with Ctrl+C in terminal 1, and run the client once more. It tells you that the server is not running.

6. Check the demo without a real setup at any time:

    ```
    python check_offline.py
    ```

> **Note**: The build sandbox could not install the real `mcp` package, so the check ran on stand-ins. Run steps 2 to 5 once with `mcp` 2.3.0 before class.

## How it works

The server and the client never share code. They agree on a standard, and they talk over HTTP.

1. The **server** starts, and listens at an address: `http://127.0.0.1:8000/mcp`.
2. The **client** connects to that address, and sends `initialize`. This is the hello.
3. The client sends `tools/list`. The server answers with its tools: names, descriptions and inputs. The client learns what the kitchen offers.
4. The client sends `resources/read` for `menu://today`, and gets the menu board.
5. The client sends `tools/call` for `check_stock` and `place_order`, and gets the results. An error, such as an out-of-stock item, comes back as a result, and the conversation continues.

Because the client learns everything from the server, the server can change its tools, and the client keeps working.

## Why HTTP, and when to use stdio

- **Streamable HTTP** is for a server that runs on its own, which is what this demo needs. Many clients can connect to it, and it can be on another machine.
- **stdio** is for a local server that the client starts itself as a child process, as in the intro demo. It is simple, and it is for one person.

> **Important**: This server has no login. It listens only on your own machine (`127.0.0.1`). Do not make it reachable from the network until it has authentication. Demo 2D adds keys, roles and safe logging.

## More information

- The run sheet is **RUN_SHEET.md**.
- The intro demo, where the client starts the server itself, is `DEMO_2_0_intro_to_mcp`.
- The full version, with authentication and HTTP, is Demo 2D in `DEMO_2D_mcp_zero_to_enterprise`.
