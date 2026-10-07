---
lab:
    title: 'Build the Warranty Claims Agent'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Build the warranty claims agent

In Demo 3C, you built a warranty claims agent in stages. It works a customer request with five tools: it looks up the product registration, checks the warranty terms, creates the claim, schedules a pickup, and submits the decision. Every tool returns the same structured result, a fixed pipeline decides from the warranty terms, and a live Claude agent loop runs the same tools and stops at its decision or at a turn limit. In this lab, you write the key pieces of that agent yourself.

You will complete four small pieces of **lab.py**, which add up to 23 lines of code. The lab takes about 30 minutes, and this guide gives you every line. At the end, a real Claude agent works four warranty requests.

This lab continues Demo 3C, so you will recognize the following:

- The five tools and the four requests C01 to C04. C01 to C03 are covered by the warranty, and C04 is not.
- The structured result shape: `tool`, `ok` and `data`.
- The one-rule decision: covered means approved, and anything else means denied.
- The agent loop with a limit of 10 turns, and the check that a decision matches the tool results.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_3/LABS/LAB_3_3_warranty_failure_recovery** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

3. Create a new file named **.env** in the lab folder, and add the following line, replacing the value with your own API key:

    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```

    > **Important**: Never paste your key into chat or commit the **.env** file to git.

4. Save the file, and then test your key by running the following command:

    ```
    python claude_client.py
    ```

5. Verify that you see a short greeting followed by a line that starts with `[usage]`.

## Review the starting point

1. Run the checker by running the following command:

    ```
    python check.py
    ```

    > **Note**: The checker fails for now, because the four pieces are not written yet. Part A tests your code on the four requests and needs no API key and no model. Part B is skipped until you run the live agent.

2. Notice that only two files matter for this lab: **lab.py**, which holds your four TODOs, and **check.py**. The **warranty_core.py** file holds the mock tools, the tool definitions, and the decision check from the demo, and you do not need to read it.

3. Open **data/cases.json** and notice the four requests. C01 is a swollen laptop battery, C02 is a dead display, C03 is a shattered phone with accidental-damage cover, and C04 is a monitor whose warranty has expired.

## Run a tool and return a structured result

Every tool in the agent answers in the same shape, so the loop and the model always read results the same way. The first piece runs one tool and wraps its result.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - RUN A TOOL**. Below it is the function `run_tool(name, args)`, and its only line is `return {}  # replace this line in TODO 1`.

3. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        return {"tool": name, "ok": True, "data": core.TOOL_FUNCTIONS[name](**args)}
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the two lines under **TODO 1** show `[PASS]`.

6. Review the line, noting the following details:

    - `core.TOOL_FUNCTIONS[name]` looks up the tool function by its name.
    - `(**args)` calls that function with the arguments as keyword arguments.
    - The result goes under `data`, next to the tool name and an `ok` flag, so every result has the same three keys.

## Decide from the warranty terms

The second piece is the decision itself. The `check_warranty_terms` tool returns whether the issue is covered, the rule that says so, and a reason. Your function turns that into a decision.

1. In **lab.py**, search for the comment **TODO 2 of 4 - DECIDE**. Below it is the function `decide(terms)`, and its only line is `return {"decision": "approved", "rule_id": "", "reason": ""}  # replace this line in TODO 2`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        return {"decision": "approved" if terms["covered"] else "denied", "rule_id": terms["rule_id"], "reason": terms["reason"]}
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the three lines under **TODO 2** show `[PASS]`, along with the four lines under **TODO 1 and 2 together**. These lines run the fixed pipeline from stage 2 of the demo on all four requests.

    > **Note**: The decision comes from the terms and not from the customer's message. The reason in the decision is the reason from the warranty terms.

## Write your Claude API call

All the checks that need no model pass for these two pieces. In this section, you write the call that gives the agent a brain. Each turn of the agent is one call to Claude, with the five tool definitions attached.

1. In **lab.py**, search for the comment **TODO 3 of 4**. Below it is the function `ask(messages)`, and its only line is `raise NotImplementedError("TODO 3 is not done yet")  # replace this line in TODO 3`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        return get_client().messages.create(
            model=MODEL_BALANCED,
            max_tokens=4096,
            system=core.AGENT_SYSTEM,
            tools=core.TOOLS,
            messages=messages,
        )
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the one line under **TODO 3** shows `[PASS]`.

5. Review the call, noting the following details:

    - `get_client()` returns the Anthropic client. It reads your key from the **.env** file (see **claude_client.py**).
    - `.messages.create(...)` sends your request to Claude.
    - `model` chooses which Claude model answers.
    - `max_tokens` limits the length of the answer. The API requires it.
    - `system` holds the standing instruction for the claims agent.
    - `tools` lists the five tools that Claude may ask the loop to run.
    - `messages` holds the conversation so far, including the results of earlier tool calls.
    - The function returns the whole response, because the agent loop reads its content blocks to find the tool calls.

## Write the agent loop

The last piece is the loop that makes the agent work. Each turn, the loop asks Claude what to do next, runs the tools that Claude picked, and sends the results back.

1. In **lab.py**, search for the comment **TODO 4 of 4 - THE AGENT LOOP**. Below it is the function `run_agent(case, ask_fn=None)`. After the lines that build `messages`, `records`, and `turns`, the only line is `pass  # replace this line in TODO 4`.

2. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        for turns in range(1, core.MAX_TURNS + 1):
            response = ask_fn(messages)
            messages.append({"role": "assistant", "content": response.content})
            calls = [block for block in response.content if block.type == "tool_use"]
            if not calls:
                break
            results = []
            for call in calls:
                record = run_tool(call.name, call.input)
                records.append(record)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(record)})
            messages.append({"role": "user", "content": results})
            if any(call.name == "submit_decision" for call in calls):
                break
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the five lines under **TODO 4** show `[PASS]`.

    > **Note**: The checker drives your loop with a tiny stand-in for Claude that follows the same five steps. This proves that your loop runs the tools, sends the results back, and stops.

5. Review the loop, noting the following details:

    - `range(1, core.MAX_TURNS + 1)` limits the loop to 10 turns, so it always ends.
    - Each reply from Claude is added to `messages` as the assistant, so Claude sees its own earlier steps.
    - The `tool_use` blocks in the reply are the tool calls that Claude chose. A reply with none means Claude is finished.
    - `run_tool` runs each call, and the record is kept for the final check.
    - The results go back as one user message of `tool_result` blocks. Each one carries the `tool_use_id` of its call.
    - The loop stops after the turn in which Claude calls `submit_decision`.

## Run the live agent

1. Run the agent on the four requests by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run uses a small amount of API credit. Each request is a separate agent run that makes several calls to Claude.

2. Verify that the output is similar to the following. The claim and pickup numbers are not printed here, and the turn counts can vary a little with the model:

    ```
    C01  decision=approved  turns=5  tools=5  verified=True
    C02  decision=approved  turns=5  tools=5  verified=True
    C03  decision=approved  turns=5  tools=5  verified=True
    C04  decision=denied    turns=3  tools=3  verified=True

    Saved to results/run.json. Now run: python check.py
    ```

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 22/22 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
