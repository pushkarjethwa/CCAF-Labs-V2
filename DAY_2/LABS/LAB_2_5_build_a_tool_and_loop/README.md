---
lab:
    title: 'Build a Tool and the Tool Loop'
    module: 'Day 2 - Tool Design and MCP (optional extension lab)'
---

# Build a tool and the tool loop

A library assistant needs facts that Claude cannot know: where a book is shelved and when a member's loan is due. In Demos 2B and 2C, you watched the tool-use loop as a state machine (`AWAITING_MODEL`, `EXECUTING_TOOLS`, `DONE`), you saw two tool results go back in one message, and you saw what happens when a tool fails. In this lab, you build one small version of that loop yourself, with the plain Anthropic SDK and no framework.

You will complete four pieces of **lab.py**, which add up to about 30 lines of code. The lab takes about 25 to 30 minutes, and this guide gives you every line. It is an optional extension after Labs 2.1 to 2.4. At the end, four library questions run through your loop, Claude asks for the right tool, your code runs it, the answers are grounded in the data, and a failing tool or a model that never stops asking cannot break the loop.

This lab continues Demos 2B and 2C, so you will recognize the following:

- The loop as a state machine. Each stage prints the states the loop went through, for example `AWAITING_MODEL -> EXECUTING_TOOLS -> AWAITING_MODEL -> DONE`.
- Claude only asks for a tool. Your program runs it and sends the result back.
- Every `tool_use` is answered with one `tool_result` that carries the same id, and all results of one turn go back in one user message.
- A failing tool is a result that the model can read, flagged with `is_error`. It is not an exception that kills the run.

The assistant has two tools: `find_book` (given, with its schema) and `check_due_date` (you write its schema). The data is tiny on purpose: two books and two loans.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_2/LABS/LAB_2_5_build_a_tool_and_loop** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

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

## Ask without tools

In this section, you ask the four questions with no tools at all. This needs no code from you.

1. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

2. Review the output, noting the following details:

    - Claude cannot know a shelf code or a due date. It says so, or it guesses.
    - The last line reads `RESULT: 1/4 answers grounded (no tools)`. Only the question about France is grounded, because it needs no tool.
    - This is the number that your loop must move to 4 of 4.

## Write the tool schema

In this section, you describe the second tool. The description is all that Claude knows about it, so it must say when to use the tool.

1. Open **lab.py** in your code editor, and read **FIND_BOOK_TOOL**. It is a finished example. Notice that its description says when to use it, and that it names the required input.

2. Search for the comment **TODO 1 of 4**. Below it is the line `CHECK_DUE_DATE_TOOL = {}  # replace these lines in TODO 1`.

3. Replace that line with the following code:

    ```python
    CHECK_DUE_DATE_TOOL = {
        "name": "check_due_date",
        "description": "Look up the due date of the book that one library member has on loan. Use when someone asks when a loan is due or when a book must come back. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {"member_id": {"type": "string", "description": "Member id, e.g. M-100"}},
            "required": ["member_id"],
        },
    }
    ```

    Noting the following details:

    - The `name` is what Claude sends back when it wants the tool, so it must match the function name your dispatcher will use.
    - The `description` has two jobs: what the tool returns, and when to use it.
    - `required` tells Claude that a call without a `member_id` is not valid.

4. Save the file, and then run stage 2:

    ```
    python lab.py --stage 2
    ```

5. Review the output, noting the following details:

    - For each question, Claude stops with `stop_reason: tool_use` and names the tool it wants, with the arguments it chose. The France question gets `end_turn` and no tool.
    - The last line reads `RESULT: 4/4 first requests right (nothing was executed)`. Nothing ran. Claude only asked.
    - The question about member M-100 may ask for one tool first or for both at once. Both are fine, and the loop in the next section handles either.

> **Note**: If you see `TODO 1 is not done`, the placeholder line is still in **lab.py**. Stage 1 is the only stage that runs without TODO 1.

## Run the tools and write the loop

In this section, you write the two pieces that turn a request into an answer: the dispatcher that runs the function, and the loop that sends the result back.

1. Search for the comment **TODO 2 of 4**. Below it is a function named `run_tool`.

2. Replace the line `raise NotImplementedError("TODO 2: run the function Claude asked for")  # replace these lines in TODO 2` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        if name == "find_book":
            return find_book(**tool_input)
        if name == "check_due_date":
            return check_due_date(**tool_input)
        return {"error": "unknown_tool", "name": name}
    ```

    Noting the following details:

    - `**tool_input` turns the dictionary Claude sent, for example `{"title": "Dune"}`, into the keyword arguments of the function.
    - An unknown name returns an error result instead of raising an exception. Claude can read it, and your program keeps running.

3. Search for the comment **TODO 3 of 4**. Below it is the function `answer`, and inside its `for` loop is the line `return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}  # replace these lines in TODO 3`.

4. Replace that line with the following code. Keep the eight-space indent, because the code sits inside the loop:

    ```python
            if response.stop_reason != "tool_use":
                return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in tool_calls_of(response):
                content, is_error = run_tool_safely(block.name, block.input)
                tools_used.append(block.name)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error})
            messages.append({"role": "user", "content": results})
    ```

    Noting the following details:

    - When `stop_reason` is not `tool_use`, Claude has written its answer and the loop ends. This is the `DONE` state.
    - Otherwise the loop is in `EXECUTING_TOOLS`. It first appends Claude's own message, because the next request must show the `tool_use` that each `tool_result` answers.
    - Each `tool_result` carries `block.id` as its `tool_use_id`. A different id makes the API answer with HTTP 400.
    - All results go in **one** user message, even when Claude asked for two tools at once. This is the parallel rule from Demo 2C.
    - The `for turn in range(1, MAX_TURNS + 1)` line that is already there is the exit. A loop must always be able to stop.

5. Save the file, and then run stage 3:

    ```
    python lab.py --stage 3
    ```

6. Review the output, noting the following details:

    - Each question shows the tools your loop ran, the number of turns, and whether the answer is grounded.
    - The state trace of the "needs both" question reads `AWAITING_MODEL -> EXECUTING_TOOLS -> AWAITING_MODEL -> DONE`.
    - The last line reads `RESULT: 4/4 answers grounded (tools run by your loop)`. In stage 1 it was 1 of 4.

> **Note**: A strong model may phrase an answer differently between runs, for example `October 8` instead of `2026-10-08`. The check accepts both spellings.

## Make the loop survive failures

In this section, you make the loop safe. Tools fail: a book that is not in the catalog, a member with no loan, or a bug inside the tool. A failure must reach Claude as a readable result, not stop the program.

1. Run stage 4 now, before you write any code, by running the following command:

    ```
    python lab.py --stage 4
    ```

2. Review the output, noting the following details:

    - In part 1, the two failing questions show `tool errors flagged is_error: 0`. The tool returned an error, but nothing told Claude that the call had failed.
    - In part 2, the tool that crashes on a bad argument would have crashed the program. This part is recorded and makes no model call.
    - In part 3, a recorded model asks for a missing book again and again. The loop stops after 6 turns, because of the exit you already have.

3. Search for the comment **TODO 4 of 4**. Below it is the function `run_tool_safely`, and its line `return json.dumps(run_tool(name, tool_input)), False  # replace these lines in TODO 4`.

4. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        try:
            result = run_tool(name, tool_input)
        except Exception as exc:
            return json.dumps({"error": "tool_crashed", "detail": str(exc)}), True
        return json.dumps(result), "error" in result
    ```

    Noting the following details:

    - A crash becomes a result with the error code `tool_crashed`. The loop sends it to Claude, which can tell the member what went wrong.
    - A result with an `error` key, such as `book_not_found`, is flagged `is_error=True`. Claude then knows that the call failed and does not present the error as a fact.
    - This is the same idea as the typed errors of Demo 2B and Lab 2.3, in its smallest form: an error code, and a flag that says the call failed.

5. Save the file, and then run stage 4 again:

    ```
    python lab.py --stage 4
    ```

6. Review the output, noting the following details:

    - Part 1 now shows `tool errors flagged is_error: 1` for each question, and Claude tells the member that the book or the loan was not found.
    - Part 2 shows `run_tool_safely returned is_error=True` with a `tool_crashed` result, instead of a crash.
    - The last line reads `RESULT: 2 live tool errors flagged, crash caught: yes, runaway loop stopped: yes`.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 25/25 checks passed`.

> **Note**: Part A of the checker tests your code with hand-made model replies and needs no key. Part B reads the stages you ran with Claude, and it reports model variance as `[info]` lines, not failures. If you ran fewer than four stages, the total is lower.

## Troubleshooting

- **`ANTHROPIC_API_KEY` is missing**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **`TODO 1 is not done`**: The line `CHECK_DUE_DATE_TOOL = {}` is still in **lab.py**. Paste the snippet from TODO 1.
- **A TODO check fails**: Read the line next to the failed check. It names the piece to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. The TODO 2 and TODO 4 code sits inside a function (four spaces), and the TODO 3 code sits inside a loop (eight spaces).
- **`NotImplementedError` when you run stage 3**: TODO 2 is not done yet.
- **Stage 3 shows `grounded: no` and no tools run**: The loop still holds the starter line from TODO 3.
- **HTTP 400 about `tool_use_id`**: A `tool_result` has an id that does not match its `tool_use`. Use `block.id`.
- **A connection error on one call**: Run the stage again.
- **Your numbers differ from a classmate's**: This is normal. Models word answers differently between runs. The grounded count and the flagged errors are the stable evidence.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private.

## More information

- Demo 2B showed the loop as a state machine on a refund assistant, and Demo 2C showed parallel tool calls and why all results go back in one message.
- The next lab, Lab 2.6, uses the same loop with a tool server. The schemas and the functions come from an MCP server, and your code only forwards the calls.
- The old version of this lab, with a single run and no stages, is archived.
