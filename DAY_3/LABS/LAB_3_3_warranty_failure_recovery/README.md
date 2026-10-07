---
lab:
    title: 'Make the Warranty Intake Agent Survive Failure'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Make the Warranty Intake Agent Survive Failure

In Demo 3C, you watched a warranty-claim intake agent meet injected faults. The agent files a claim with four tools: it looks up the product registration, checks the warranty terms, creates the claim, and schedules a pickup. A blanket "retry three times" handled only one of the faults. The fix was to classify each error first, and then use the recovery that fits. In this lab, you write that fix yourself, for the same agent, the same tools, and the same faults.

You will complete four small pieces of **lab.py**, which add up to 26 lines of code. The lab takes about 35 minutes, and this guide gives you every line. At the end, a real Claude agent runs four faults through your recovery layer.

This lab continues Demo 3C, so you will recognize the following:

- The agent, its four tools, and the customer case C01 (a swollen laptop battery).
- The fault injector, and the faults `tool_drift`, `env_outage`, `permission`, and `reasoning`.
- The three families of failure (tool, reasoning, and environment), plus permission errors that are never retried.
- The ground truth from the chaos matrix, which the checker uses to test your work.

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

    > **Note**: The checker fails on purpose. Part A tests your recovery layer against the ground truth from Demo 3C, and needs no API key and no model. Part B is skipped until you run the live agent.

2. Notice that only two files matter for this lab: **lab.py**, which holds your four TODOs, and **check.py**. The **warranty_core.py** file holds the mock services, the fault injector, and the agent loop from the demo, and you do not need to read it.

3. Notice that the starter code retries every failure three times, whatever the error says. This is the naive agent from Stage 1 of the demo.

## Classify each error

The first decision is what kind of failure an error is. The classifier looks only at the error's status and code, never at its message text, because message text changes and can mislead.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - CLASSIFY**. Below it is the function `classify(exc)`, and its only line is `return "environment"  # replace this line in TODO 1`.

3. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        status, code = getattr(exc, "status_code", None), getattr(exc, "code", "")
        if status == 403:
            return "permission"
        if status in (503, 504):
            return "environment"
        if code in ("E_ARG_RENAMED", "E_SCHEMA_REJECTED"):
            return "tool"
        if status in (404, 422):
            return "reasoning"
        return "unknown"
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the nine lines under **TODO 1** show `[PASS]`.

6. Review the classifier, noting the following details:

    - A 403 means the agent has no permission. Retrying cannot help.
    - A 503 or 504 means the service is unavailable or slow. This is an environment problem that may pass.
    - An `E_ARG_RENAMED` or `E_SCHEMA_REJECTED` code means the tool's contract changed. This is a tool problem.
    - A 404 or 422 means the caller sent a bad request or a wrong rule. This is a reasoning problem, because the model caused it.
    - Anything else, such as a corrupt reply from an adapter, is unknown.

## Write the recovery rules

The second decision is what to do about each kind of failure. The starter code uses the same blanket retry for all five kinds.

1. In **lab.py**, search for the comment **TODO 2 of 4 - RECOVERY**.

2. Inside the `RECOVERY = {` block, replace the five rows with the following code:

    ```python
        "tool": ("retry_renamed_then_fallback", 1),
        "reasoning": ("corrective_message", 2),
        "environment": ("backoff_then_breaker", 3),
        "permission": ("escalate", 0),
        "unknown": ("escalate", 0),
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six matrix lines under **TODO 2** show `[PASS]`, along with the two lines about the reasoning policy and the single alert.

5. Review the rules, noting the following details:

    - A tool failure is retried once with the renamed argument, and then falls back to a degraded endpoint. A second identical retry would fail the same way.
    - A reasoning failure sends the model a corrective message at most twice, and then a human takes over.
    - An environment failure is retried with backoff, up to three attempts in total. Then a circuit breaker pauses the run and raises one alert, instead of one alert per failed call.
    - A permission or unknown failure is never retried and never routed around. The agent stops and hands over to a human.

    > **Note**: The checker compares your rules with the chaos-matrix ground truth from Demo 3C: 6 faults across 4 steps, each with the expected outcome and the expected number of attempts.

## Write the corrective message

When the model caused the error, the executor sends it a corrective message. A vague message such as "Try again." gives the model nothing to fix.

1. In **lab.py**, search for the comment **TODO 3 of 4 - CORRECTIVE MESSAGE**. Below it is the function `corrective_message(exc)`, and its only line is `return "Try again."  # replace this line in TODO 3`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        if exc.code == "E_COVERAGE_MISMATCH":
            return ("The coverage rule you used does not match the warranty terms for this serial and issue. "
                    "Call check_warranty_terms again and use exactly the rule_id it returns.")
        return f"The call failed: {exc.message}. Fix the arguments (check the format) and call the tool again."
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the two lines under **TODO 3** show `[PASS]`.

    > **Note**: A good corrective message names the tool to call again and the exact value to use. Without that detail, the model tends to repeat the same mistake.

## Write your Claude API call

All the checks that need no model pass now. In this section, you write the call that gives the agent a brain. Each turn of the agent is one call to Claude, with the four tool definitions attached.

1. In **lab.py**, search for the comment **TODO 4 of 4**. Below it is the function `ask(messages)`, and its only line is `raise NotImplementedError("TODO 4 is not done yet")  # replace this line in TODO 4`.

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

4. Verify that the one line under **TODO 4** shows `[PASS]`.

5. Review the call, noting the following details:

    - `get_client()` returns the Anthropic client. It reads your key from the **.env** file (see **claude_client.py**).
    - `.messages.create(...)` sends your request to Claude.
    - `model` chooses which Claude model answers.
    - `max_tokens` limits the length of the answer. The API requires it.
    - `system` holds the standing instruction for the intake agent.
    - `tools` lists the four tools that Claude may ask the loop to run.
    - `messages` holds the conversation so far, including the results of earlier tool calls.
    - The function returns the whole response, because the agent loop reads its content blocks to find the tool calls.

## Run the live agent

1. Run the agent through four faults, one from each family, by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run uses a small amount of API credit. Each fault is a separate agent run that makes several calls to Claude.

2. Verify that the output is similar to the following. The wording of the last line for `reasoning` depends on the model:

    ```
    tool_drift   at create_claim         status=completed            faulted-step attempts=2 alerts=[]
    env_outage   at create_claim         status=paused_alerted       faulted-step attempts=3 alerts=['create_claim service']
    permission   at schedule_pickup      status=escalated            faulted-step attempts=1 alerts=[]
    reasoning    at check_warranty_terms status=completed            faulted-step attempts=2 alerts=[]

    Saved to results/run.json. Now run: python check.py
    ```

    > **Tip**: A model can occasionally behave differently on the `reasoning` fault. If that line shows an unexpected status, run `python lab.py` once more before you change any code.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 25/25 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Try breaking it (optional)

After you reach 25/25, change one thing at a time, run `python check.py`, and then undo the change.

1. Change the `"permission"` row to `("retry_same_call", 3)`. Which lines fail, and what does a retry do to a 403?

2. Change the `"environment"` limit from 3 to 10. Which lines fail, and what would ten attempts do to a service that is down?

3. Make `classify` return `"environment"` for every error. Which lines fail?

4. Change the corrective message to `"Try again."`. Which line fails, and why does the model need more than that?

## Troubleshooting

- **ANTHROPIC_API_KEY is missing**: The **.env** file is not in the lab folder, or it has a typo. Repeat the steps in *Set up the lab folder*.

- **IndentationError**: A pasted line lost its indent. The code inside a function must be indented four spaces, and the code inside a dictionary must be indented four spaces.

- **A TODO line still fails after pasting**: The old line is still in the file, or you pasted only part of the snippet. Delete the old line named in the step, and paste the whole snippet.

- **NotImplementedError: TODO 4 is not done yet**: The `ask` function still has the placeholder line. Repeat the steps in *Write your Claude API call*.

- **Part B says you edited lab.py after the last run**: Run `python lab.py` again.

- **The reasoning fault shows an unexpected status**: This is normal model variation. Run `python lab.py` once more.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
