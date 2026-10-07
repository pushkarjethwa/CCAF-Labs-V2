---
lab:
    title: 'Use an MCP Server from Your Own Agent'
    module: 'Day 2 - Tool Design and MCP (optional extension lab)'
---

# Use an MCP server from your own agent

The team keeps its notes behind a small MCP server: an on-call rotation, an expense policy and a release checklist. In Lab 2.5, you wrote the tool schemas and the tool functions yourself. In this lab, you are the MCP client. The server describes its own tools, you hand those descriptions to Claude, and you forward Claude's requests to the server. In Demo 2D, you watched a client list a server's tools and call one, and you saw that descriptions are advice while the client does the enforcing.

You will complete six pieces of **lab.py**, which add up to about 25 lines of code. The lab takes about 25 to 30 minutes, and this guide gives you every line. It is an optional extension after Labs 2.1 to 2.4. At the end, your client connects to the server, Claude answers three questions from the notes, a missing note comes back as an error that Claude can read, and a newer server that adds a dangerous `delete_note` tool cannot make your client delete anything.

This lab continues Demo 2D, so you will recognize the following:

- The client handshake: start the server, `initialize`, `list_tools`, then `call_tool`.
- An MCP tool carries the same three things that Claude needs: a name, a description and an input schema.
- A tool error is data. The server returns it with `is_error` set, and the session stays alive.
- The server is not the policy. The client decides which tools Claude may use, and it enforces the decision.

The server is **notes_server.py** (given), and it starts as a child process of your program over stdio. It offers two read-only tools: `search_notes` and `get_note`. Stage 4 uses **notes_server_plus.py** (given), the same server one release later, with an extra admin tool named `delete_note`.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_2/LABS/LAB_2_6_use_an_mcp_server** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

    > **Note**: This lab uses the MCP Python SDK version 2.3.0, which is pinned in **requirements.txt**.

## Add your Claude API key

1. In the lab folder, create a new file named **.env**.

2. Add the following line to the file, replacing the value with your own API key:

    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```

    > **Important**: Never paste your key into chat or commit the **.env** file to git.

3. Save the file, and then test your key by running the following command:

    ```
    python claude_client.py
    ```

4. Verify that you see a short greeting followed by a line that starts with `[usage]`.

## Connect to the server

In this section, you write the connection. Stage 1 makes no model call: it lists the server's tools and calls one by hand.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 6**. Below it is the function `open_session`, which holds two lines: a `raise NotImplementedError(...)` line and a `yield` line.

3. Replace both of those lines with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        from mcp import ClientSession, StdioServerParameters, stdio_client

        server = StdioServerParameters(command=sys.executable, args=[str(core.HERE / server_file)])
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    ```

    Noting the following details:

    - `StdioServerParameters` says how to start the server: this Python, running the server file.
    - `stdio_client` starts the process and gives you its two pipes. The server's standard input and output are the MCP channel, which is why a server must never print to standard output.
    - `ClientSession` speaks MCP over those pipes, and `initialize()` is the handshake. Nothing else works before it.
    - The `yield` hands the ready session to the code that called `open_session`.

4. Save the file, and then run stage 1:

    ```
    python lab.py --stage 1
    ```

5. Review the output, noting the following details:

    - The server describes its two tools, with their names, arguments and descriptions. You wrote none of them.
    - `search_notes('pager')` returns a JSON list that holds the on-call note, `N-1`.
    - `get_note('N-9')` comes back with `is_error=True` and the server's message. The call did not crash your program.
    - The last line reads `RESULT: 2 tools discovered, one call answered, one error carried as data (no crash)`.

## Give Claude the server's tools

In this section, you convert what the server describes into what Claude reads.

1. Search for the comment **TODO 2 of 6**. Below it is the function `mcp_tool_to_claude`, with the line `return {}  # replace these lines in TODO 2`.

2. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        return {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.input_schema,
        }
    ```

    Noting the following details:

    - Claude wants exactly three keys: `name`, `description` and `input_schema`. The API rejects unknown fields, so do not copy the whole tool object.
    - On MCP SDK 2.3.0 the schema is `tool.input_schema`. Older SDKs called it `inputSchema`.

3. Save the file, and then run stage 2:

    ```
    python lab.py --stage 2
    ```

4. Review the output, noting the following details:

    - The first block lists the tools Claude will read, with their required arguments.
    - For each question, Claude stops with `stop_reason: tool_use` and names a tool from the server, with the arguments it chose. Nothing is forwarded to the server yet.
    - The last line reads `RESULT: 3/3 questions made Claude ask for a server tool (nothing was forwarded)`.

> **Note**: Which tool Claude asks for first on the second and third question is its own choice. The result only counts that it asked for a tool that the server offers.

## Forward Claude's requests to the server

In this section, you write the two conversions and the forwarding step. Claude asks, the server answers, and Claude replies.

1. Search for the comment **TODO 3 of 6**. Below it is the function `result_to_text`, with the line `return "", False  # replace these lines in TODO 3`.

2. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        texts = [item.text for item in result.content if item.type == "text"]
        return "\n".join(texts) or "(empty result)", result.is_error
    ```

    Noting the following details:

    - A result holds a list of content items. Only the items of type `text` have a `.text`, so the others are skipped.
    - The function returns the text and the error flag together, which is what a `tool_result` block needs.

3. Search for the comment **TODO 4 of 6**. It sits inside the function `answer`, in the `for block in tool_calls_of(response)` loop. Find the line `pass  # replace these lines in TODO 4`.

4. Replace that line with the following code. Keep the twelve-space indent, because the code sits inside two loops:

    ```python
                try:
                    result = await session.call_tool(block.name, dict(block.input))
                    text, is_error = result_to_text(result)
                except Exception as exc:
                    text, is_error = f"The call to the server failed: {exc}", True
                tools_used.append(block.name)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": is_error})
    ```

    Noting the following details:

    - `session.call_tool(name, arguments)` is the only line that reaches the server. The loop around it is the loop you wrote in Lab 2.5.
    - The `tool_result` carries `block.id`, the same id as the request. All results of one turn go back in one user message, which the code after your lines already does.
    - If the call itself raises an exception, for example because the server went away, Claude gets an error result and the loop continues.

5. Save the file, and then run stage 3:

    ```
    python lab.py --stage 3
    ```

6. Review the output, noting the following details:

    - The on-call and expense questions each use the server twice: a search, then a read of the note. The answers hold `555-0142` and `75`.
    - The question about note `N-9` shows `errors flagged: 1`. The server's error reached Claude, which says that the note does not exist.
    - The last line reads `RESULT: 3/3 questions answered from the server`.

## Do not hand over every tool

In this section, you fence the client. A server can add tools after you wrote your client, and a model can ask for a tool that you never offered, because of a mistake or because of text inside a note. Stage 4 uses the newer server, and a recorded model that asks for `delete_note`. The recorded part makes no model call.

1. Run stage 4 before you write any code, by running the following command:

    ```
    python lab.py --stage 4
    ```

2. Review the output, noting the following details:

    - The newer server offers three tools, and your client hands Claude all three.
    - The recorded request for `delete_note('N-3')` is forwarded to the server, and the note count falls from 3 to 2.
    - The last line reads `RESULT: Claude offered 3 of 3 tools, delete_note FORWARDED and a note was DELETED (notes 3 -> 2)`.

3. Search for the comment **TODO 5 of 6**. It sits inside the function `answer`, at the top of the `for block in tool_calls_of(response)` loop. Find the line `# TODO 5: the guard goes here  # replace this line in TODO 5`.

4. Replace that line with the following code. Keep the twelve-space indent, because the code sits inside two loops:

    ```python
                if block.name not in ALLOWED_TOOLS:
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"The tool {block.name} is not allowed.", "is_error": True})
                    continue
    ```

    Noting the following details:

    - The guard runs before the forwarding, so a refused request never reaches the server.
    - The request still gets exactly one `tool_result` with its id, flagged as an error, so the conversation stays valid.
    - `ALLOWED_TOOLS` is still empty, so for now the guard refuses everything. This is deny by default.

5. Save the file, and then run stage 4 again:

    ```
    python lab.py --stage 4
    ```

6. Verify that the last line now reads `RESULT: Claude offered 3 of 3 tools, delete_note REFUSED (notes 3 -> 3)`. The note is safe, but Claude is still offered `delete_note`, and a real question would be refused too.

7. Search for the comment **TODO 6 of 6**. Below it are the line `ALLOWED_TOOLS = set()  # replace this line in TODO 6`, and a function named `offer` with the line `return claude_tools  # replace this line in TODO 6`.

8. Replace the `ALLOWED_TOOLS` line with the following code:

    ```python
    ALLOWED_TOOLS = {"search_notes", "get_note"}
    ```

9. Replace the line `return claude_tools  # replace this line in TODO 6` with the following code. Keep the four-space indent:

    ```python
        return [tool for tool in claude_tools if tool["name"] in ALLOWED_TOOLS]
    ```

    Noting the following details:

    - The allow-list names the tools you approved. A tool the server adds later is not on it, so it is neither offered nor forwarded.
    - `offer` is the first fence: Claude never sees `delete_note`. The guard from TODO 5 is the second fence, for a request that comes anyway. A description is advice. Your client is the enforcement.

10. Save the file, and then run stage 4 a third time:

    ```
    python lab.py --stage 4
    ```

11. Verify that the output now says `your client hands Claude 2 of them: ['get_note', 'search_notes']`, and that the last line reads `RESULT: Claude offered 2 of 3 tools, delete_note REFUSED (notes 3 -> 3)`.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 29/29 checks passed`.

> **Note**: Part A of the checker tests your code with fake MCP objects and hand-made model replies, so it needs no key and no MCP server. Part B reads the stages you ran, and it reports model variance as `[info]` lines, not failures. If you ran fewer than four stages, the total is lower.

## Troubleshooting

- **`ANTHROPIC_API_KEY` is missing**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **`ModuleNotFoundError: No module named 'mcp'`**: Run `pip install -r requirements.txt` in this folder.
- **`TODO 1: connect to the MCP server`** or **`TODO 2 is not done`**: The placeholder for that TODO is still in **lab.py**. Paste the snippet from the guide.
- **A TODO check fails**: Read the line next to the failed check. It names the piece to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. The TODO 1, 2, 3 and 6 code sits inside a function (four spaces), and the TODO 4 and 5 code sits inside two loops (twelve spaces).
- **Stage 3 shows `server calls: none`**: The starter line `pass` from TODO 4 is still in the loop.
- **Stage 1 hangs**: The server is waiting for the handshake. Check that **TODO 1** calls `await session.initialize()` before it yields the session.
- **The server prints garbage and the session fails**: Never add a `print` to a stdio server, because standard output is the protocol channel.
- **A connection error on one call**: Run the stage again.
- **An attribute name differs on your MCP version**: Run `pip show mcp`. This lab was written for 2.3.0.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private. The server processes end when each stage ends.

## More information

- Demo 2D built an MCP server step by step and ended with authentication and roles. The allow-list in this lab is the client's half of the same idea: the server says what exists, and the client says what Claude may use.
- Lab 2.4 builds a server. Lab 2.6 uses one. Together they cover both sides of MCP.
- The old version of this lab, with a single run and no stages, is archived.
