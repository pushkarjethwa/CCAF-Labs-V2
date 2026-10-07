---
lab:
    title: 'Instructor Run Sheet: MCP Server and Client as Separate Apps'
    module: 'Day 2 - Tool Design and MCP'
---

# Instructor Run Sheet: MCP server and client as separate apps

This run sheet covers the separate server and client demo, which takes about 10 minutes. It answers a question that students ask after the intro demo: "What if the server and the client are different apps?" Run it after `DEMO_2_0_intro_to_mcp` and before Demo 2D.

## Before class

1. Run `pip install -r server_app/requirements.txt`, and then `python check_offline.py`. If it prints `NOT VERIFIED`, the real `mcp` package was not installed on that machine.

2. Open two terminals side by side, with a large font. Label them **SERVER** and **CLIENT**. The room should see both at once.

3. Do one full dry run with the real package. If the client cannot connect, check that the server's port is free.

4. Open these files in tabs: **server_app/kitchen_server.py** and **client_app/kitchen_client.py**.

## Run the demo

1. **Minutes 0-2, set the scene**.

    > **Say**: "In the last demo, my script started the server for me, so it looked like one app. That is how a local server works, but it hides something. A real MCP server is its own program. Often another team wrote it, and it may run on another machine. Today the kitchen is its own app, and the customer is another app. They share no code. Let me prove it."

    > **Note**: Show the two files, one after the other. Point at the imports of the client: no `kitchen`. Say: "The client has never seen the kitchen's code. It only has an address."

2. **Minutes 2-3, start the server (terminal SERVER)**: Run `cd server_app`, and then `python kitchen_server.py`.

    > **Say**: "The waiter opens the restaurant, and waits at an address. Nobody has come in yet."

    > **Note**: Point at the line it prints: the address. It will show nothing else until a client arrives.

3. **Minutes 3-7, run the client (terminal CLIENT)**: Run `cd client_app`, and then `python kitchen_client.py`.

    > **Say**: "A different program, in a different terminal. It knows one thing: the address. Watch the four steps."

    > **Note**: Narrate each numbered step with its MCP method. Step 1, `initialize`, is the hello. Step 2, `tools/list`, is "what do you offer?", and the answer comes from the server, not from the client's code. Step 3, `resources/read`, is the menu on the table. Step 4, `tools/call`, is the order. Point at the order total, and say that the server did the work.

    > **Say**: "Look at what crossed the address: questions and answers in a standard format. No shared code, no shared files."

4. **Minutes 7-8, change the order**: Run `python kitchen_client.py --item pepperoni --qty 1`.

    > **Say**: "Same client, same server, a different order. The pepperoni is out of stock. It comes back as an error, not a crash, and the client carries on."

    > **Note**: The client can be run as many times as you like. The server stays up, and each run is a new customer.

5. **Minutes 8-10, take the server away**: Press Ctrl+C in terminal SERVER, and run `python kitchen_client.py` again.

    > **Say**: "The restaurant is closed, and the customer says so, in plain words. This is the first thing to check when a client cannot connect: is the server running, and is the address right?"

    > **Note**: Then close the topic: "Two apps, one standard. Change the kitchen, and the customer finds out by asking. Replace the client with a chatbot, an IDE or an agent, and the server does not change at all."

## Optional extras

- **Another machine**: If you want to show a different machine, start the server with `uvicorn` on an address that the network can reach, and give the client that address with `--url`. Do this only on a network you trust, because this server has no login.
- **Another client**: A ready-made client, such as the MCP Inspector, can connect to the same address and list the tools. Neither it nor Claude Code was tested for this course, so try it before you promise it.
- **Two clients at once**: Run the client in two terminals, one after the other, and show that the stock goes down for both.

## Audience questions

1. "Who starts the server?" You, or a service on a machine. With HTTP, it runs on its own. With stdio, the client starts it.
2. "How does the client know the tools?" It asks the server, with `tools/list`, every time it connects.
3. "Can the client and server be in different languages?" Yes. The standard is language-neutral.
4. "Is it safe?" Not yet. This server has no login. Demo 2D adds keys, roles and safe logging.
5. "What changes if the kitchen adds a new tool?" Nothing in the client. It will see the tool the next time it asks.

## Troubleshooting

- **The client says "Could not talk to the server"**: Start the server first, and check that the address and the port match.
- **Port 8000 is busy**: Start the server with `--port 9000`, and give the client `--url http://127.0.0.1:9000/mcp`.
- **`ModuleNotFoundError`**: Run `pip install -r server_app/requirements.txt` in the Python that you use.
- **The server prints nothing after the first line**: That is normal. It only waits for clients.
- **The second run shows less stock**: The kitchen's stock is in memory, and each order reduces it. Restart the server to reset it.

## Clean up

Press Ctrl+C in the server terminal. Nothing is written to disk.

## More information

- The matching ideas are in `DEMO_2_0_intro_to_mcp` (the waiter, stage by stage) and Demo 2D (security and transports).
