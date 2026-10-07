---
lab:
    title: 'Build the Same Agent Two Ways with the Anthropic SDK'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Build the Same Agent Two Ways with the Anthropic SDK

In Demo 3F, you watched the same incident-triage agent built four ways. The goal, the prompt, the tools, and the data never changed. Only one thing changed from build to build: who runs the loop, and where. In this lab, you build the first two of those ways yourself: a manual loop, where you write the loop around `client.messages.create`, and the Tool Runner, where the SDK runs the loop for you. You then compare them on the same incident, INC-7741 at Nordlicht Logistics.

You will complete five small pieces of **lab.py**, which add up to 26 lines of code. The lab takes about 30 minutes, and this guide gives you every line. At the end, both builds triage the incident for real.

This lab continues Demo 3F, so you will recognize the following:

- The goal, the system prompt, and the three read-only tools: `list_alerts`, `get_log_lines`, and `lookup_indicator`.
- Build 1, the manual loop, where you see every moving part of the Messages API.
- Build 2, the Tool Runner, which gives the same result with a fraction of the code.
- The comparison point of the demo: the loop is the only thing that changes, and the answer stays the same.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key. You do not need any other tool for this lab.

1. Open a terminal in the **STUDENT_V2/DAY_3/LABS/LAB_3_6_two_ways_to_build_an_agent** folder.

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

    > **Note**: The checker fails on purpose. Part A tests your code with a scripted stand-in for Claude, so it needs no API key. Part B is skipped until you run the real agents.

2. Notice that only two files matter for this lab: **lab.py**, which holds your two builds, and **check.py**. The **incident_kit.py** file holds the goal, the prompt, and the three tools that every build shares, and you do not need to read it.

## Ask Claude in the manual loop

In the manual loop, you keep the whole conversation in a list called `messages`. Each turn, you ask Claude, keep its answer, run any tools it asked for, and send the results back. The loop is already in **lab.py**. You write three pieces inside it.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 2 - BUILD 1: THE MANUAL LOOP**. Below it is the function `manual_loop(client)`, with a `for` loop that has three placeholder lines marked 1a, 1b, and 1c.

3. Under the comment `# 1a - ask Claude`, replace the line `raise NotImplementedError("TODO 1a is not done yet")  # replace these lines in TODO 1a` with the following code. Keep the eight-space indent, because the code sits inside the `for` loop:

    ```python
            response = client.messages.create(
                model=kit.MODEL,
                max_tokens=4096,
                system=kit.SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
    ```

4. Save the file, and then review the call, noting the following details:

    - `model` chooses which Claude model answers.
    - `max_tokens` limits the length of the answer. The API requires it, and on the latest models it also covers hidden thinking, so keep it generous.
    - `system` holds the standing instruction.
    - `tools` lists the three tools that Claude may ask you to run.
    - `messages` is the whole conversation so far.

## Keep Claude's turn and answer its tool requests

1. Under the comment `# 1b - keep Claude's turn`, replace the line `pass  # replace this line in TODO 1b` with the following code. Keep the eight-space indent:

    ```python
            messages.append({"role": "assistant", "content": response.content})
    ```

2. Under the comment `# 1c - answer EVERY tool request`, replace the line `pass  # replace these lines in TODO 1c` with the following code. Keep the eight-space indent:

    ```python
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    called.append(block.name)
                    text, is_error = run_tool(block.name, block.input)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": is_error})
            messages.append({"role": "user", "content": results})
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six lines under **TODO 1** show `[PASS]`.

5. Review the loop, noting the following details:

    - You keep Claude's whole turn, including its `tool_use` blocks, because the next request must show Claude what it asked for.
    - Claude can ask for several tools in one turn. All the results go back together in one user message, and each result carries the `tool_use_id` of the request it answers.
    - A tool that fails is reported to Claude as a readable error result, so Claude can recover. It does not crash the loop.
    - The loop stops when Claude says `end_turn`, and it is cut off after `MAX_TURNS` turns. That brake is yours to keep.

## Let the Tool Runner run the loop

The Tool Runner uses the same Messages API, but it runs the loop for you. You hand it plain Python functions, and it calls them, builds the tool results, and asks Claude again until Claude stops asking for tools.

1. In **lab.py**, search for the comment **TODO 2 of 2 - BUILD 2: THE TOOL RUNNER**. Below it are two functions with a placeholder line each: `as_runner_tool(spec)` and `runner_loop(client)`.

2. In the `as_runner_tool` function, replace the line `raise NotImplementedError("TODO 2 is not done yet")  # replace these lines in TODO 2` with the following code. Keep the four-space indent:

    ```python
        def call(**kwargs):
            return spec.run(kwargs)
        return beta_tool(call, name=spec.name, description=spec.description, input_schema=spec.input_schema)
    ```

3. In the `runner_loop` function, replace the line `raise NotImplementedError("TODO 2 is not done yet")  # replace these lines in TODO 2` with the following code. Keep the four-space indent:

    ```python
        runner = client.beta.messages.tool_runner(
            model=kit.MODEL,
            max_tokens=4096,
            system=kit.SYSTEM_PROMPT,
            tools=[as_runner_tool(spec) for spec in kit.TOOL_SPECS],
            messages=[{"role": "user", "content": kit.GOAL}],
            max_iterations=kit.MAX_TURNS,
        )
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the five lines under **TODO 2** show `[PASS]`.

6. Review the runner, noting the following details:

    - The runner passes the model's arguments to your function as keyword arguments, so `as_runner_tool` adapts the shared tool functions, which take a dictionary.
    - `beta_tool` needs the function, a name, a description, and an input schema. They are the same ones the manual loop sent.
    - `max_iterations` is the same brake as the manual loop, so the comparison is fair.
    - The code that reads the runner is already written. It iterates over the turns, and then asks for the final message.

    > **Note**: The Tool Runner is still marked as beta in the SDK, so its details can change between versions.

## Run both builds

1. Run both builds on the incident by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run uses a small amount of API credit. Each build makes several calls to Claude, and the tool order differs from run to run.

2. Verify that the output starts with one summary line per build, similar to the following. The numbers will differ:

    ```
    manual loop  stop_reason=end_turn  turns=3   tools called=3 tokens in/out=2400/450
    tool runner  stop_reason=end_turn  turns=3   tools called=3 tokens in/out=1100/220
    ```

3. Read the two reports printed below the summary, noting the following details:

    - Both builds should name `bastion-02` as the compromised host. The loop changed, but the answer did not.
    - The runner reports the tokens of its last turn only, so its token count is not comparable to the manual loop's total.

    > **Tip**: A model can occasionally take a different route. If the checker complains about the run, run `python lab.py` once more before you change any code.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 15/15 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Try breaking it (optional)

After you reach 15/15, change one thing at a time, run `python check.py`, and then undo the change.

1. Delete the line that keeps Claude's turn (1b). Which lines fail, and what would the real API say about the next request?

2. Send each tool result in its own user message instead of one message. Which line fails?

3. Set `max_iterations` to 2 in the runner. What stop reason does the final message have?

4. Count the lines you wrote for the manual loop and for the runner. What do you get from the extra lines, and what do you give up with the runner?

## Troubleshooting

- **ANTHROPIC_API_KEY is missing**: The **.env** file is not in the lab folder, or it has a typo. Repeat the steps in *Set up the lab folder*.

- **IndentationError**: A pasted line lost its indent. The manual loop code is indented eight spaces, and the runner code is indented four spaces.

- **NotImplementedError: TODO 1a is not done yet**: The placeholder line is still in the file. Repeat the steps in *Ask Claude in the manual loop*.

- **NotImplementedError: TODO 2 is not done yet**: One of the two placeholder lines in the runner section is still in the file. There is one in `as_runner_tool` and one in `runner_loop`.

- **A TODO line still fails after pasting**: The old placeholder line is still in the file, or you pasted only part of the snippet. Delete the placeholder line named in the step, and paste the whole snippet.

- **Part B says you edited lab.py after the last run**: Run `python lab.py` again.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
