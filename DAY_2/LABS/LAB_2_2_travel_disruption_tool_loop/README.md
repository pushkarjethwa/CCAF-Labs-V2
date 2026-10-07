---
lab:
    title: 'Run the Tool Calls of One Turn Safely'
    module: 'Day 2 - Tool Design and MCP'
---

# Run the tool calls of one turn safely

In Demo 2C, you watched an order desk assistant get faster when its five lookups ran at the same time, and then charge a customer twice when its three dependent writes ran at the same time too. The team fixed it in layers: concurrent reads, writes that stay in order, a key that makes a retry safe, and a limit on the loop. In this lab, you do the same for an airline disruption assistant.

You will complete five pieces of **lab.py**, which add up to about 40 lines of code. The lab takes about 35 minutes, and this guide gives you every line. At the end, the assistant reads flight status, alternatives, hotels and the loyalty tier at the same time, books a hotel only with a reference that a tool really returned, books one seat even when the first rebooking times out, and stops a model that never stops.

This lab continues Demo 2C, so you will recognize the following:

- The method: run the loop, read the ledger, and judge the result by what was booked, not by what the model said.
- The split of duties: the model decides how many tool calls to put in a turn, and your code decides whether they overlap.
- The fix order: overlap the reads, order the writes, make a retry safe, and bound the loop.
- The replays: when a strong model does not make the mistake by itself, a recorded model makes it for you, so the failure is repeatable.

Flight XA482 was cancelled. For traveler T-1001, the assistant reads four independent things (flight status, alternatives, airport hotels and the loyalty tier) and then writes three dependent things: rebook the flight, book a hotel with the rebooking reference, and notify the traveler with both references. The mock airline loses the acknowledgement of the first rebooking: the seat is booked, and the call times out.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_2/LABS/LAB_2_2_travel_disruption_tool_loop** folder.

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

## Run the baseline

In this section, you run the whole disruption with a harness that runs one tool call after the other. This needs no code from you.

1. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

2. Review the output, noting the following details:

    - The read phase is the sum of the read latencies, because nothing overlaps.
    - The assistant has no loyalty tool, so it cannot know the hotel rate cap of the traveler.
    - The first rebooking times out and the model sees only a string. If the model retries, as the system prompt tells it to, the ledger shows two rebookings: the traveler has two seats.
    - The last table has one row. Each stage adds a row.

> **Note**: A model may or may not retry the rebooking in a single run. Stage 4 replays a recorded retry, so the lesson does not depend on luck.

## Add the missing tool and overlap the reads

In this section, you write the tool definition that the assistant lacks, and the executor that runs a turn's calls at the same time.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 5**. Below it is the line `LOYALTY_TIER_TOOL = None  # replace these lines in TODO 1`.

3. Replace that line with the following code:

    ```python
    LOYALTY_TIER_TOOL = {
        "name": "loyalty_tier",
        "description": "Read-only. The loyalty tier of one traveler and its perks: change-fee waiver, hotel rate cap, lounge and priority rebooking. Use it before choosing a hotel, to learn the rate cap. Does not change anything.",
        "input_schema": {"type": "object", "properties": {"traveler_id": {"type": "string"}}, "required": ["traveler_id"], "additionalProperties": False},
    }
    ```

    Noting the following details:

    - The description says that the tool is read-only, what it returns, and when to use it. That text is all that the model knows about the tool.
    - `additionalProperties` is `False`, so the model cannot invent an argument.

4. Search for the comment **TODO 2 of 5**. Below it is a function named `run_concurrently`.

5. Replace the line `raise NotImplementedError("TODO 2: run the calls on a thread pool")  # replace these lines in TODO 2` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        with ThreadPoolExecutor(max_workers=8) as pool:
            return list(pool.map(run_one, calls))
    ```

    Noting the following details:

    - `pool.map` returns the results in the order of the calls, which is what the API needs: every `tool_use` id answered, in one user message.

6. Save the file, and then run stage 2:

    ```
    python lab.py --stage 2
    ```

7. Review the output, noting the following details:

    - The read phase falls from the sum of the latencies to about the slowest one, when the model puts the reads in one turn.
    - The progress table now has two rows, so you can compare the read phase across stages.

> **Note**: This executor runs every call of a turn at the same time. That is fine for reads. The next section shows what it does to writes.

## Keep the dependent writes in order

In this section, you write the gate that runs before every write. A recorded model asks for the rebooking, the hotel and the notification in one turn, with a made-up reference, and you compare the stage 2 executor with your gate.

1. Search for the comment **TODO 3 of 5**. Below it is a function named `gate`.

2. Replace the line `raise NotImplementedError("TODO 3: check the prerequisites and the references")  # replace these lines in TODO 3` with the following code. Keep the four-space indent:

    ```python
        missing = [tool for tool in DEPENDS_ON.get(name, ()) if tool not in state.succeeded]
        if missing:
            return {"error": "PREREQUISITE_NOT_MET", "retryable": False, "message": f"{name} needs {', '.join(missing)} to succeed first",
                    "hint": "Call the missing tool first and wait for its result. Do not guess references."}
        unknown = [key for key, value in args.items() if key.endswith("_ref") and value not in state.refs]
        if unknown:
            return {"error": "UNKNOWN_REFERENCE", "retryable": False, "message": f"{', '.join(unknown)} was not returned by any tool",
                    "hint": "Use only references that a tool result returned."}
        return None
    ```

    Noting the following details:

    - The gate returns `None` when the call may run, and an error dictionary when it may not. The harness runs the writes one at a time, in the order requested, and asks the gate before each one.
    - The first check reads the dependencies that the business knows, and that no schema shows: the hotel needs the rebooking, and the notification needs both.
    - The second check refuses a reference that no tool returned. A model can make one up.

3. Save the file, and then run stage 3:

    ```
    python lab.py --stage 3
    ```

4. Review the output, noting the following details:

    - The replay through the stage 2 executor books a hotel with an unverified reference, and the order violations column is not zero.
    - The replay through your gate books no hotel and sends no notification. The rebooking timed out, so the hotel was refused, and nothing was booked on a guess.
    - The live run follows with the same gate.

## Make a retry safe

In this section, you write the key and the timeout result that turn a retry into a replay. A recorded model rebooks, sees the timeout, and retries with identical arguments.

1. Search for the comment **TODO 4 of 5**. Below it is a function named `key_for`.

2. Replace the line `raise NotImplementedError("TODO 4: build the idempotency key")  # replace these lines in TODO 4` with the following code. Keep the four-space indent:

    ```python
        canonical = json.dumps({"tool": name, "args": args}, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    ```

    Noting the following details:

    - `sort_keys=True` makes the key the same for the same call, whatever the order of the arguments.
    - The harness builds the key, never the model.

3. A few lines below, in the function `timeout_result`, replace the line `raise NotImplementedError("TODO 4: build the structured timeout result")  # replace these lines in TODO 4` with the following code. Keep the four-space indent:

    ```python
        return {"error": "TIMEOUT", "retryable": True, "outcome_unknown": True, "message": str(error),
                "hint": f"{name} may or may not have been applied. Retry with IDENTICAL arguments: the same idempotency key makes the retry safe."}
    ```

    Noting the following details:

    - The timeout result says what the model needs to know: the outcome is unknown, and a retry with identical arguments is safe.

4. Save the file, and then run stage 4:

    ```
    python lab.py --stage 4
    ```

5. Review the output, noting the following details:

    - The replay without a key shows two rebookings. The replay with your key shows one rebooking and one replay: the second call returned the first booking.
    - The live run books one seat, even if the model retries.

## Stop a loop that never ends

In this section, you bound the loop. A recorded model that never stops asking for the flight status is run through it.

1. Search for the comment **TODO 5 of 5**. Below it are the lines `turn = 0` and `while True:`, in the function `run_agent`.

2. Replace the six lines of the starter loop, from `turn = 0` to the line `return done`, with the following code. Keep the four-space indent:

    ```python
        for turn in range(1, max_turns + 1):
            done = core.take_turn(create, services, state, messages, log, stage, turn)
            if done:
                return done
        return {"turns": max_turns, "stopped": "max_turns", "final_text": "", **log}
    ```

    Noting the following details:

    - The `for` loop is the iteration guard. A loop must end, whatever the model does.
    - The result says `stopped` is `max_turns`, so the caller can tell a guard from a finished answer.

3. Save the file, and then run stage 5:

    ```
    python lab.py --stage 5
    ```

4. Review the output, noting the following details:

    - The runaway model is cut off after 8 turns.
    - The last line is the gate: one rebooking, nothing unverified, writes in order, and the runaway stopped.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 21/21 checks passed`.

> **Note**: Part A of the checker tests your code directly and needs no key. Part B reads the stages you ran with Claude, and it reports model variance as `[info]` lines, not failures.

## Troubleshooting

- **`ANTHROPIC_API_KEY` is missing**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the piece to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **`NotImplementedError` when you run a stage**: The TODO for that stage is not done yet. Stage 1 needs none.
- **Stage 2 shows no faster read phase**: The model put the reads in separate turns this time. Run the stage again, and read the turn trace.
- **The live run shows one rebooking in stage 1**: The model did not retry. Stage 4 replays a recorded retry, so the comparison does not depend on it.
- **A connection error on one call**: Run the stage again.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private.

## More information

- Demo 2C used an order desk with five lookups and three dependent writes, and its last step was a hardened executor with declared prerequisites and keys injected by the harness. The old version of this lab, with four open defects in one file, is archived.
- The next lab, Lab 2.3, is about what happens when a tool fails: typed errors, a bounded retry, and an escalation.
