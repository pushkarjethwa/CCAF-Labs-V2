---
lab:
    title: 'Instructor Run Sheet: Demo, Intro to MCP'
    module: 'Day 2 - Tool Design and MCP'
---

# Instructor Run Sheet: Demo, Intro to MCP

This run sheet covers the intro to MCP demo, which takes about 15 minutes. It uses one story, a restaurant, from the first command to the last. It comes before Demo 2D.

## Before class

1. Run `pip install -r requirements.txt`, and then run `python check_offline.py`. If it prints `NOT VERIFIED`, the real `mcp` package was not installed on that machine.

2. Run `python demo.py --stage 1` through `--stage 4` once. Write down what stage 4 prints for the stdout server.

3. Open these files in tabs, in this order: **kitchen.py**, **demo.py** (the `APPS` block), **kitchen_server.py**.

4. Use a terminal at least 110 columns wide, with a font of 18 points or more.

## Run the demo

Run every command from the demo folder.

1. **Minutes 0-4, stage 1**: Run `python demo.py --stage 1`.

    > **Say**: "A restaurant has one kitchen and three customers: a chatbot, a kiosk and a phone app. Each customer walks into the kitchen alone and negotiates in its own way. Look at the three descriptions of the same function. Three teams, three versions of the truth."

    > **Note**: Ask for a prediction: "The kitchen team renames one parameter and adds one. How many apps break?" All three. Then say: "Three apps and three kitchens is nine of these. This is the N x M problem."

2. **Minutes 4-9, stage 2**: Run `python demo.py --stage 2`.

    > **Say**: "Now a waiter stands in front of the kitchen. The waiter is an MCP server, and it speaks one standard language. The customer sits down, and the first thing it asks is: what do you offer?"

    > **Note**: Point at the three numbered parts of the output. Part 1 is discovery, so the tool names and descriptions come from the server. Part 2 is a resource, the menu board on the table: data the app reads without a model deciding. Part 3 is tools, the orders. The pepperoni order fails with a clear message, and the session survives. Open **kitchen_server.py** and show how short it is: it only wraps the kitchen.

3. **Minutes 9-13, stage 3**: Run `python demo.py --stage 3`.

    > **Say**: "The kitchen team makes the same change as in stage 1. Watch the apps. Nobody touched them."

    > **Note**: Point at the arguments in the output. In version 1 the client sent `qty`, and in version 2 it sent `quantity` and `table`, because it read the schema again. Say that the small function that fills the arguments stands in for a model, which does the same from the description.

4. **Minutes 13-15, stage 4**: Run `python demo.py --stage 4`.

    > **Say**: "One rule, and it is the one that wastes the most hours. A stdio server talks to its app through one pipe, its stdout. If the server mutters into that pipe, the app hears garbage. Log to stderr instead."

    > **Note**: Read the two result lines aloud. If the noisy server connected on your machine, say so: some SDK versions rescue a stray line. The rule stays the same. Then close with the board: "MCP is a universal plug. Build the connector once, and every MCP app can use it." Say that Demo 2D adds the front desk (401), the key card (403) and the safe logbook.

## Audience questions

1. "Is MCP the same as a function call?" No. A function call is how a model asks for a tool. MCP is how the tool is packaged and found, so any app can use it.

2. "Do I need MCP for one app and one system?" No. The value grows with the number of apps and systems.

3. "Where does the model fit?" In a real app, the client hands the discovered tools to the model, and the model chooses which to call. This demo skips the model to show only the plug.

## Troubleshooting

- **`ModuleNotFoundError` for `mcp`**: Run `pip install -r requirements.txt` in the Python that you run the demo with.
- **Stage 4 connects for both servers**: The SDK rescued the stray line. Say so, and keep the rule.
- **Stage 4 takes 8 seconds**: That is the timeout of the noisy server.
- **A server process is left running**: Close the terminal. The stages stop their own servers.

## Clean up

Nothing is written to disk by the demo.

## More information

- The next demo is Demo 2D, which grows a server like this into an authenticated, role-scoped, log-safe service.
