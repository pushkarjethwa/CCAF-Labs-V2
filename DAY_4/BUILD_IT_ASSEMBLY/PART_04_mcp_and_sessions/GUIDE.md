---
lab:
    title: 'Part 4 - Connect a menu tool with MCP and manage sessions'
    module: 'Day 4 - Build-It Assembly'
---

# Part 4 - Connect a menu tool with MCP and manage sessions

So far Claude has used its built-in tools. In this part you connect a new tool from outside: a small MCP server that knows the Brew & Bean menu prices. MCP is the Model Context Protocol, a standard way to give Claude tools. The same standard was used on Day 2 in the kitchen demo. After that, you learn how to keep, shrink, resume and fork a long session. This part takes about 15 minutes.

## Know the menu server

The server is the file **mcp_server/menu_server.py**. It offers two tools. `get_menu_price(item)` returns the price of one item in cents, as a whole number. `list_menu()` returns every item with its price. Both read **mcp_server/menu.json**, which holds the same prices as **docs/MENU.md**.

The two functions are plain Python. A thin wrapper at the bottom of the file exposes them over MCP. The wrapper uses the same import style that the kitchen server in the Day 2 demo (DEMO_2_0) proved. The import sits inside a function, so the file also works without the `mcp` package.

## Add the part files

1. In a terminal in the **BUILD_IT_ASSEMBLY** folder, add this part's files.

    **Run:**
    ```
    python assemble.py --part 4
    ```
    **What it does:** Copies the menu server, the menu data and a reference copy of the MCP settings into your working repository.
    **Why we do it here:** The tool you connect should already exist, so you can focus on how Claude Code uses it.
    **You should see:** One line that says three files were copied.

2. Move into the repository and install the MCP package.

    **Run:**
    ```
    cd work/brewbean-rewards
    pip install mcp
    ```
    **What it does:** Installs the Python package that runs an MCP server.
    **Why we do it here:** Claude Code starts the server as a Python program, and that program needs the package.
    **You should see:** A line that says the package was installed, or that it is already installed.

## Connect the server

1. Register the server with Claude Code.

    **Run:**
    ```
    claude mcp add --transport stdio --scope project menu -- python mcp_server/menu_server.py
    ```
    **What it does:** Tells Claude Code to start `python mcp_server/menu_server.py` as a stdio server named **menu**, and to save it for this project.
    **Why we do it here:** It is the one command that connects an outside tool. Everything after the double dash is the command that Claude Code runs.
    **You should see:** A line that says the server was added, and a new **.mcp.json** file in the repository.

    A server can be saved in one of three scopes. The scope decides who gets it.

    The **local** scope is the default. The server is for you only and for this project only. It is stored in your own Claude Code settings, not in the repository.

    The **project** scope is the one we used. The server is saved in **.mcp.json** in the repository, so every teammate who clones the repository gets it. Claude Code asks each person to approve it before it runs.

    The **user** scope is for you in every project. It is stored in your own settings.

    Verify on your Claude Code version: the exact wording of the approval prompt for a project server.

2. Look at the file the command created.

    **Run:**
    ```
    python -c "print(open('.mcp.json').read())"
    ```
    **What it does:** Prints **.mcp.json**.
    **Why we do it here:** It shows what the add command wrote. You can compare it with the copy in **mcp_server/mcp.json.reference**.
    **You should see:** A server named **menu** with type `stdio`, the command `python` and the argument **mcp_server/menu_server.py**.

3. List the servers.

    **Run:**
    ```
    claude mcp list
    ```
    **What it does:** Lists every server that Claude Code knows, and checks whether each one starts.
    **Why we do it here:** It tells you at once whether your server is healthy before you start a session.
    **You should see:** A line for **menu** with the command and a connected status.

    Verify on your Claude Code version: a project server may show as waiting for approval until you approve it once in a session.

4. Show the details of one server.

    **Run:**
    ```
    claude mcp get menu
    ```
    **What it does:** Prints the scope, type, command and arguments of the **menu** server.
    **Why we do it here:** It confirms the scope and the exact command that Claude Code will run.
    **You should see:** The scope shown as project, and the command `python mcp_server/menu_server.py`.

5. Remove the server, and add it again.

    **Run:**
    ```
    claude mcp remove menu --scope project
    claude mcp add --transport stdio --scope project menu -- python mcp_server/menu_server.py
    ```
    **What it does:** Removes the **menu** server, then registers it again in the same way.
    **Why we do it here:** You now know the whole life cycle: add, list, get, remove. The server is back for the next step.
    **You should see:** A line that says the server was removed, then a line that says it was added.

    Verify on your Claude Code version: the scope flag on `claude mcp remove`. Without it, Claude Code may ask which scope to remove from.

## Use the server in a session

1. Start Claude Code.

    **Run:**
    ```
    claude
    ```
    **What it does:** Opens a new session that starts the menu server.
    **Why we do it here:** A session loads its MCP servers at the start.
    **You should see:** The Claude Code prompt. If it asks you to approve the project server, approve it.

2. Check the connection from inside the session.

    **Type in Claude Code:**
    ```
    /mcp
    ```
    **What it does:** Shows the MCP servers of this session and their status.
    **Why we do it here:** It proves that Claude can see the **menu** server and its two tools.
    **You should see:** **menu** with a connected status. Press Escape to leave the view.

3. Give Claude a task that needs the tool and the team rules together.

    **Type in Claude Code:**
    ```
    Price a 3-drink order from the menu, then work out the points a member earns for it.
    ```
    **What it does:** Makes Claude call the menu tools for prices, then use the points rules from this repository for the points.
    **Why we do it here:** The prices come from the tool, not from guessing. The points come from the rule in memory: one point per whole currency unit, and members earn 150 percent, in whole numbers.
    **You should see:** Claude asks permission to use a **menu** tool, or uses it directly, and then gives the total in cents and the member points as a whole number. For example, three drinks at 1250 cents give 12 base points and 18 member points.

## Manage a long session

1. See what is using the context window.

    **Type in Claude Code:**
    ```
    /context
    ```
    **What it does:** Shows how much of the context window is used and by what.
    **Why we do it here:** You saw this view in Part 1. Now the tool results and memory files have added to it. Note the number.
    **You should see:** A usage bar with groups such as system prompt, tools, memory files and messages.

2. Shrink the conversation.

    **Type in Claude Code:**
    ```
    /compact keep the order total, the member points and the menu prices
    ```
    **What it does:** Replaces the long conversation with a short summary and keeps what you named.
    **Why we do it here:** Long sessions fill the window. A summary keeps the facts and frees the space.
    **You should see:** A short message that the conversation was compacted.

3. Check the context again.

    **Type in Claude Code:**
    ```
    /context
    ```
    **What it does:** Shows the usage after the summary.
    **Why we do it here:** You can compare it with the number from before.
    **You should see:** A smaller number in the messages group.

4. Leave the session.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the session. Claude Code saves it on disk.
    **Why we do it here:** Saved sessions can be continued, which is the next step.
    **You should see:** Your terminal prompt.

## Continue, resume and fork

1. Continue the most recent session.

    **Run:**
    ```
    claude -c
    ```
    **What it does:** Reopens the latest session in this folder with its history.
    **Why we do it here:** You can pick up work after a break without explaining it again.
    **You should see:** The earlier conversation, or its summary, and the prompt.

2. Ask a question that only the old session can answer.

    **Type in Claude Code:**
    ```
    What was the order total and how many member points did it earn?
    ```
    **What it does:** Asks about the order from before.
    **Why we do it here:** It proves the session came back with its facts.
    **You should see:** The same total and points as before.

3. Open the session picker from inside the session.

    **Type in Claude Code:**
    ```
    /resume
    ```
    **What it does:** Shows a list of saved sessions in this project.
    **Why we do it here:** You can return to any older session, not only the latest one.
    **You should see:** A list with your sessions. Press Escape to stay where you are.

4. Leave the session.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the session.
    **Why we do it here:** The next command starts from the terminal.
    **You should see:** Your terminal prompt.

5. Open the picker from the terminal.

    **Run:**
    ```
    claude -r
    ```
    **What it does:** Opens the same list of saved sessions at start-up. You can also give a session id or a name.
    **Why we do it here:** It is the terminal form of `/resume`.
    **You should see:** A list of sessions. Choose the latest one, or press Escape to cancel.

    Verify on your Claude Code version: the flag may be written `--resume`. Leave the session with `/exit` if you opened one.

6. Fork the latest session.

    **Run:**
    ```
    claude -c --fork-session
    ```
    **What it does:** Continues the latest session in a new session with a new id, and leaves the original untouched.
    **Why we do it here:** A fork lets you try a different direction, for example a different order, without changing the saved original.
    **You should see:** The earlier history and the prompt, in a session that is separate from the first one.

    Verify on your Claude Code version: `--fork-session` works together with `-c` and `-r`.

7. Leave the forked session.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the fork.
    **Why we do it here:** Both sessions are now saved, and you can resume either one.
    **You should see:** Your terminal prompt.

## Commit the server

1. Save this part in git.

    **Run:**
    ```
    git add -A
    git commit -m "Add menu MCP server"
    ```
    **What it does:** Commits the server, its data and **.mcp.json**.
    **Why we do it here:** The project scope exists so the team shares the server through git.
    **You should see:** A commit summary that lists **.mcp.json** and the three files in **mcp_server**.

## Verify the part

1. Go back to the **BUILD_IT_ASSEMBLY** folder and run the verification.

    **Run:**
    ```
    cd ../..
    python verify.py --upto 4
    ```
    **What it does:** Calls the two menu functions directly, compares the prices with **docs/MENU.md**, and checks the shape of **.mcp.json**.
    **Why we do it here:** It proves the tool returns the right prices and that the Part 3 settings are still in place.
    **You should see:** `[PASS]` lines and the line ALL PARTS PASS.
