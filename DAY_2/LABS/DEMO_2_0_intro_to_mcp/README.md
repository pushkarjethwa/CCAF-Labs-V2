---
lab:
    title: 'Demo: Intro to MCP'
    module: 'Day 2 - Tool Design and MCP'
---

# Demo: Intro to MCP

A pizza restaurant has one kitchen with three functions: read the menu, check the stock, and place an order. Three apps want to use it: a chatbot, an ordering kiosk and a phone app. In this demo, you first connect them the old way, with a copy of the glue in every app, and watch all three break when the kitchen changes one function. Then you put an MCP server (the waiter) in front of the kitchen, connect a client, and show that the apps discover what the kitchen offers and survive the same change. The demo takes about 15 minutes, needs no API key and no model, and is a gentle start before Demo 2D.

## What the demo shows

1. **Stage 1**: Without MCP. Three apps each hold their own copy of the order call and their own description of it. The kitchen renames `qty` to `quantity` and adds a required `table`, and all three break. This is the N x M problem.
2. **Stage 2**: With MCP. The client connects to the kitchen server, asks what it offers, reads the menu resource, and calls the tools. The client needs no kitchen-specific code.
3. **Stage 3**: The same kitchen change. One shared client reads the new schema every time, so the three apps keep working. N apps and M servers need N + M pieces, not N x M.
4. **Stage 4**: The one rule of stdio servers. A server that prints to stdout corrupts the channel, and the server that logs to stderr works.

## Files in this folder

- **kitchen.py**: The restaurant's kitchen, in plain Python. `KITCHEN_VERSION=2` changes the order function.
- **kitchen_server.py**: The kitchen as an MCP server, about 30 lines. It adds no new logic.
- **demo.py**: The four stages. Run `python demo.py --stage N`.
- **check_offline.py**: A key-free self-check (7 checks).
- **RUN_SHEET.md**: The instructor's script, with the restaurant analogy.

## Run the demo

1. Run the following command:

    ```
    pip install -r requirements.txt
    ```

2. Run the stages in order:

    ```
    python demo.py --stage 1
    python demo.py --stage 2
    python demo.py --stage 3
    python demo.py --stage 4
    ```

3. Check the demo at any time:

    ```
    python check_offline.py
    ```

> **Note**: The build sandbox could not install the real `mcp` package, so the check ran against offline stand-ins, and the stage 4 outcome has not been seen on the real SDK. Run all four stages once with `mcp` 2.3.0 before class. With the real SDK, expect the stdout server to hang or fail, and the demo prints whichever happens.

## How the restaurant maps to MCP

- The kitchen is the system you already have: a CRM, a database or an API.
- The waiter is the MCP server. It speaks one standard language.
- The customers are the MCP clients: any app or model host.
- The menu is the list of tools and resources that the client discovers.

## More information

- The run sheet is **RUN_SHEET.md**.
- The full version, with authentication, roles, logging and HTTP, is Demo 2D in `TRAINER_V2/DAY_2/DEMOS/DEMO_2D_mcp_zero_to_enterprise`.
