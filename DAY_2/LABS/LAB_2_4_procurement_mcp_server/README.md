---
lab:
    title: 'Build and Lock Down a Procurement MCP Server'
    module: 'Day 2 - Tool Design and MCP'
---

# Build and lock down a procurement MCP server

In Demo 2D, you watched the Northwind CRM move from a hand-written CLI to one MCP server. A stray `print()` hung the server, an API key leaked into a log, and a reader role tried to write a ticket and got a 403. In this lab, you do the same for a procurement server. Procurement wants an AI assistant to look up suppliers and purchase orders and, for people who are allowed to, approve them.

You will complete six pieces of **lab.py**, which add up to about 40 lines of code. The lab takes about 40 minutes, it needs no API key and no model, and this guide gives you every line. At the end, a real MCP client connects to your server over stdio and over streamable HTTP, a purchase order is read through a resource and a validated tool, an analyst is refused with a 403 and a caller with no key is refused with a 401, and no key appears in a log.

This lab continues Demo 2D, so you will recognize the following:

- The stages: a stdio server and the stdout trap, resources, validated tools with structured errors, a client and a config linter, authentication with roles and safe logging, and then the same server over HTTP.
- The three kinds of failure: a print that corrupts the wire, a key that leaks into a log, and a caller who is known but not allowed.
- The vocabulary: a tool is controlled by the model, a resource by the application, a prompt by the user. A 401 means no identity, and a 403 means known but not allowed.

The procurement server has three tools, `find_supplier`, `get_po` and `approve_po`, two resources, `supplier://{supplier_id}` and `po://{po_id}`, and one prompt. Two roles use it. An **analyst** may read. An **approver** may also approve a pending purchase order whose supplier is active. A mock database sits behind it, with 8 suppliers and 7 purchase orders, so you can run it as often as you like.

## Set up the lab folder

You need Python 3.10 or later. You do not need an API key.

1. Open a terminal in the **STUDENT_V2/DAY_2/LABS/LAB_2_4_procurement_mcp_server** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

3. Open **lab.py** in your code editor, and then read the three pieces that are already written: the `supplier_resource` resource, the `find_supplier` tool and the `approve_po` tool. Your pieces copy their shape.

> **Note**: You never type a key in this lab. Each stage creates throw-away keys for its own run, hands them to the server through its environment, and never prints or saves them.

## Run the broken server

In this section, you run stage 1 before any fix. The starter server has one defect, and this stage shows you how it looks from the client.

1. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

2. Wait about 8 seconds, and then review the output, noting the following details:

    - The line `initialize FAILED (TimeoutError)` means that the client sent its first request, and the server never answered in a way the client could read.
    - The server did answer. The starter prints a banner with `print(..., end="")`, which leaves a partial line on stdout. The first JSON reply is written onto the end of that line, so the combined line is not valid JSON and the client drops it.
    - A stdio server uses stdout as the protocol wire. Anything else written there is corruption.

## Keep stdout clean

In this section, you send the server's log lines to stderr, which is the right place for them.

1. In **lab.py**, search for the comment **TODO 1 of 6**. Below it is a function named `setup_logging`.

2. Replace the line `print("procurement server starting", end="", flush=True)  # replace these lines in TODO 1` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="procurement %(levelname)s %(message)s")
        logging.getLogger("procurement").info("procurement server starting")
    ```

    Noting the following details:

    - `stream=sys.stderr` sends every log record to stderr. The MCP client ignores stderr, and you can read it when something goes wrong.
    - Never use `print()` in a stdio server. If a connection fails with no useful error, run the server alone and read its stderr first.

3. Save the file, and then run stage 1 again:

    ```
    python lab.py --stage 1
    ```

4. Review the output, noting the following details:

    - The three lines now start with `ok`. The client connected, it logged no JSON-RPC parse error, and the server's log line arrived on stderr.
    - The tool list shows `approve_po`, `find_supplier` and `get_po`. The starter has no `get_po` tool yet, so your server may list only two until you do TODO 3.

## Add a resource template

In this section, you add the `po://{po_id}` resource, so an application can attach one purchase order to a conversation. In Demo 2D, this was `kb://articles/{article_id}`.

1. Search for the comment **TODO 2 of 6**. Below it is the line `# replace this line in TODO 2`.

2. Replace that line with the following code. This time the code is not inside a function, so there is no indent:

    ```python
    @mcp.resource("po://{po_id}", mime_type="application/json")
    def po_resource(po_id: str) -> str:
        po = pdb.po_row(CON, po_id)
        if po is None:
            raise ValueError(f"unknown purchase order {po_id}")
        return json.dumps(po, sort_keys=True)
    ```

    Noting the following details:

    - A resource with `{po_id}` in its URI is a template. A client finds it in `resources/templates/list`, and not in `resources/list`.
    - An unknown id raises an error. The client gets an error back and the session survives. Errors are data, not crashes.

3. Save the file, and then run stage 2:

    ```
    python lab.py --stage 2
    ```

4. Review the output, noting the following details:

    - The fixed list shows only `procurement://suppliers/index`. The template list shows `po://{po_id}` and `supplier://{supplier_id}`.
    - `supplier://S-100` shows the bank account as `****3000`. A resource is attached to a conversation, so it holds the minimum necessary data.
    - `po://PO-9999` ends as an error, and the next call still works.

## Validate a tool

In this section, you add the `get_po` tool with two layers of protection. The schema rejects a badly formed id before your code runs. Your code then answers an unknown id with a stable error code.

1. Search for the comment **TODO 3 of 6**. Below it is the line `# replace this line in TODO 3`.

2. Replace that line with the following code. There is no indent here either:

    ```python
    PoId = Annotated[str, Field(pattern=r"^PO-\d{4}$", description="Purchase order id such as PO-2001")]


    @mcp.tool()
    def get_po(ctx: Context, po_id: PoId) -> CallToolResult:
        """Look up one purchase order by id. Returns supplier, amount, status and approvals. Error po_not_found if unknown."""
        def work():
            po = pdb.po_row(CON, po_id)
            if po is None:
                raise core.ProcError("po_not_found", f"No purchase order {po_id}")
            return po
        return core.run(ctx, "get_po", work)
    ```

    Noting the following details:

    - The docstring becomes the tool description, and the model reads it, so write it for the model.
    - `PoId` is layer one. The pattern appears in the schema that the client sees, and a bad id is rejected before `get_po` runs.
    - `core.ProcError` is layer two. The gate in **procurement_core.py** turns it into a result with `is_error` set and a stable `code`, so a script or a model can branch on it without reading prose.

3. Save the file, and then run stage 3:

    ```
    python lab.py --stage 3
    ```

4. Review the output, noting the following details:

    - `get_po PO-9999` returns the code `po_not_found`. `get_po 'po-1'` and the unknown tool `delete_po` are rejected before any code of yours runs.
    - `approve_po PO-2004` returns `supplier_not_active` with status 422, and `approve_po PO-2002` returns `po_not_pending` with status 409. Those rules were already written for you.
    - Authentication is still off in this stage, so `approve_po PO-2001` succeeds for anyone. That is the problem stage 5 fixes.

## Lint a client configuration

In this section, you write a small linter for the file that tells a client such as Claude Code how to reach your server. It finds three mistakes that people really commit.

1. Search for the comment **TODO 4 of 6**. Below it is a function named `lint_config`.

2. Replace the line `return []  # replace these lines in TODO 4` with the following code. Keep the four-space indent:

    ```python
        problems = []
        for name, server in config.get("mcpServers", {}).items():
            if server.get("type") == "sse":
                problems.append(f"R2 {name}: type 'sse' is deprecated, use 'http'")
            url = server.get("url", "")
            if url.startswith("http://") and urlparse(url).hostname not in ("127.0.0.1", "localhost"):
                problems.append(f"R5 {name}: plain http to a non-local host")
            for key, value in {**server.get("headers", {}), **server.get("env", {})}.items():
                if re.search(r"(?i)key|token|secret|authorization", key) and "${" not in value:
                    problems.append(f"R4 {name}: {key} holds a literal secret, use ${{VAR}}")
        return problems
    ```

    Noting the following details:

    - R2 catches the deprecated `sse` transport. R5 catches a key that travels over plain http to another machine. R4 catches a secret that is typed into the file instead of being a `${VAR}` reference.
    - An empty list means the file is fine.

3. Save the file, and then run stage 4:

    ```
    python lab.py --stage 4
    ```

4. Review the output, noting the following details:

    - The first line is your own MCP client listing the tools, resources, templates and prompts. A host such as Claude Code gives the model the same tools named `mcp__procurement__<tool>`. MCP changes where the tool lives, and the tool-use loop stays the same.
    - **mcp.stdio.json** and **mcp.http.json** in the **CONFIGS** folder pass.
    - **mcp.leaky.json** fails, and that is expected. It lists four problems: one R2, two R4 and one R5.

## Authenticate and authorize

In this section, you answer the two questions in order: who are you, and what may you do. They fail in two different ways, so they have two different status codes.

1. Search for the comment **TODO 5 of 6**. Below it are three lines: `ROLE_TOOLS = {}`, a function `authenticate` that returns `None`, and a function `is_allowed` that returns `False`.

2. Replace those lines, from `ROLE_TOOLS = {}` to `return False`, with the following code:

    ```python
    ROLE_TOOLS = {"analyst": {"find_supplier", "get_po"}, "approver": {"find_supplier", "get_po", "approve_po"}}


    def authenticate(token):
        found = None
        for role, key in core.load_keyring().items():
            if token and hmac.compare_digest(token.encode(), key.encode()):
                found = role
        return found


    def is_allowed(role, tool):
        return tool in ROLE_TOOLS.get(role, set())
    ```

    Noting the following details:

    - `hmac.compare_digest` takes the same time however many characters match. The loop checks every key and never returns early, so the time taken does not reveal which key matched.
    - An empty token is never valid.
    - `is_allowed` denies by default. A role that is not in the table, or a tool that is not listed for the role, gets nothing, so a new tool can never silently become available to everyone.
    - A 401 is raised by the authentication layer, and a 403 is raised by the gate in **procurement_core.py**, which calls your `is_allowed`.

3. Search for the comment **TODO 6 of 6**. Below it is a function named `redact`.

4. Replace the line `return text  # replace these lines in TODO 6` with the following code. Keep the four-space indent:

    ```python
        text = re.sub(r"(?i)bearer\s+[\w.~+/=-]+", "Bearer " + core.MASK, text)
        for secret in core.known_secrets():
            text = text.replace(secret, core.MASK)
        return text
    ```

    Noting the following details:

    - Every audit line passes through `redact` before it is written. The server logs the `Authorization` header of a rejected request, the way a developer would while chasing a 401, so this function is what keeps the key out of the log.
    - The first line removes anything shaped like a `Bearer` token. The loop removes the exact keys of this process, which catches a key that appears anywhere else, for example inside an error message.

5. Save the file, and then run stage 5:

    ```
    python lab.py --stage 5
    ```

6. Review the output, noting the following details:

    - In section 1, five failures give 401, and the analyst key and the approver key get through with 200. The 401 body is the same for every failure, so an attacker cannot tell which part was wrong.
    - In section 2, the number of comparisons is 2 for the first key, the last key and an unknown key.
    - In section 3, a real stdio server runs once per role. The analyst gets `approve_po DENIED`, and the approver does not. The refusal is a tool result with status 403, and the session stays alive, so a model can read it and adapt.
    - In section 4, the grep for the keys finds none. To see the leak, you can temporarily change `redact` to `return text` and run stage 5 again.
    - In section 5, a server started with no key exits with code 2 and prints no key.

## Serve the same server over HTTP

In this section, you run the same server over streamable HTTP. This stage needs no new code.

1. Run stage 6 by running the following command:

    ```
    python lab.py --stage 6
    ```

2. Review the output, noting the following details:

    - The same client code gives identical results over stdio and over HTTP. The transport is configuration, and the design is the same.
    - A rejected key shows as `ExceptionGroup[MCPError(-32603)]` in the client, because the SDK hides the HTTP status. The raw HTTP view below it shows the real answer, `401`, with a `WWW-Authenticate` header.
    - Over HTTP, the analyst is refused with 403 and the approver succeeds.
    - The server log shows the statuses 200 and 401, the audited denial of the analyst's write, and no key.
    - The server process is stopped when the stage ends.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 41/41 checks passed`.

> **Note**: Part A of the checker tests your code with hand-made inputs and starts no server. Part B reads the stages you ran, and it only checks the stages that you have run so far.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'mcp'`, `httpx2` or `uvicorn`**: Run `pip install -r requirements.txt` again, in the same Python that you use to run **lab.py**. The lab was written for the `mcp` package, version 2.3.0, which imports `MCPServer` from `mcp.server.mcpserver`.
- **Stage 1 still ends with `initialize FAILED`, or any stage says `Connection closed`**: The server stopped or wrote something that is not JSON-RPC. The stage prints the last lines of the server's stderr. Look for a `print(` in **lab.py**, an `ImportError`, or a `SyntaxError` from a paste that lost its indent. Run `python check.py` to see which TODO fails.
- **A stage after stage 1 says it could not talk to the server**: Finish TODO 1 first. A server that prints to stdout breaks every stage.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces, and the resource and tool code of TODOs 2 and 3 has no indent.
- **Stage 3 shows no `get_po` tool**: The TODO 3 placeholder line is still in **lab.py**.
- **Stage 5 shows `five failures give 401` as TODO**: `authenticate` still returns `None`, or `core.load_keyring()` found no keys. Run the stage again, because each stage creates its own keys.
- **Stage 5 or 6 says no key appears in the log is TODO**: `redact` still returns the text unchanged.
- **Stage 6 fails to start the server, or the port is busy**: The stage picks a free port by itself. Close an older terminal that is still running **lab.py**, and run the stage again.
- **A `PermissionError` when a temporary file is cleaned up (Windows)**: The lab closes its log handles before it cleans up, and ignores this error. If you still see it, close any editor tab that has the file open, and run the stage again.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Each stage stops every server process that it starts. If a terminal was closed in the middle of stage 6, end any leftover `python` process that runs **lab.py --serve**.

## More information

- Demo 2D used a CRM and a hand-written CLI, and showed the same three failures: stdout pollution, a key in a log, and a 401 compared with a 403.
- The previous lab, Lab 2.3, made tool failures typed and bounded, and this lab uses the same idea of a stable error code for the MCP tool `get_po`.
