---
lab:
    title: 'Choose the Architecture for the ACME Expense Desk'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Choose the Architecture for the ACME Expense Desk

In Demo 3A, you watched ACME's finance team review expense claims three ways: as a conversation, as a workflow, and as an agent. The cheapest design that worked was the winner. ACME Finance Operations now wants to build four more things, and to add an investigation step to the claim review. In this lab, you decide which architecture each one needs, and which kind of component each step of the claim review should be.

You will fill in two small tables and write one **Claude API** call. The lab takes about 25 minutes. You write 19 lines of code, and this guide gives you every one of them.

This lab continues Demo 3A, so you will recognize the following:

- The company (ACME) and its travel and expense policy, `ACME-T&E-2026.2`.
- The five signals from the demo: who controls the next step, how predictable the path is, reliability need, cost of error, and latency.
- The rule from the demo: if a *human* decides the next step, use a conversation; if a *process* decides, use a workflow; if the *model* decides, use an agent.
- The claim-review steps: read the claim, convert to USD, check for duplicates, check pre-approval, and apply the policy.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_3/LABS/LAB_3_1_expense_desk_architecture** folder.

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

## Review the briefs and steps

1. Display the lab data by running the following command:

    ```
    python lab.py --show
    ```

2. Review the four briefs (**FB-1** to **FB-4**) and the seven steps (**E1** to **E7**), noting the following details:

    - Each brief and step lists its **facts**.
    - You will decide from the facts, not from instinct.

3. Run the checker to see your starting point:

    ```
    python check.py
    ```

    > **Note**: The checker fails on purpose, because the starter code contains wrong answers. The last line shows fewer than 16 checks passed.

## Choose an architecture for each brief

In this section, you fill in Table 1, which assigns an architecture to each of the four briefs.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - TABLE 1: the four briefs**. Below it is a block that starts with `ARCHITECTURE = {` and ends with `}`.

3. Select the whole block, and replace it with the following code:

    ```python
    ARCHITECTURE = {
        "FB-1": ("conversational", "human", "single_step"),
        "FB-2": ("workflow", "process", "fixed_sequence"),
        "FB-3": ("workflow", "process", "known_branches"),
        "FB-4": ("agentic", "model", "open_ended"),
    }
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the four lines under **TODO 1** show `[PASS]`. The lines for Table 2 still fail, which is expected.

6. Review your answers. Each row reads *(architecture, who decides the next step, how predictable the path is)*:

    - **FB-1**: The employee types each next question, and each question has one answer. That is a conversation with a `single_step` path.
    - **FB-2**: The month-end checklist decides, and the steps are the same every month. That is a workflow with a `fixed_sequence` path.
    - **FB-3**: A routing table sends each receipt to one of three queues. That is a workflow with `known_branches`.
    - **FB-4**: Each lookup decides the next one, and nobody can write the path in advance. That is an agent with an `open_ended` path.

    This is the same rule you used in Demo 3A: whoever controls the next step decides the architecture.

## Choose a kind of component for each step

In this section, you fill in Table 2, which assigns a kind of component to each of the seven steps of the claim review.

1. In **lab.py**, search for the comment **TODO 2 of 4 - TABLE 2: the seven steps of the claim review**. Below it is a block that starts with `STEPS = {` and ends with `}`.

2. Select the whole block, and replace it with the following code:

    ```python
    STEPS = {
        "E1": ("fixed_step", "The claim text is free-form but the step never changes, so one scripted model call turns it into fields.", "schema"),
        "E2": ("tool", "The finance rates are fixed and the conversion is plain arithmetic with no judgment.", "exact"),
        "E3": ("tool", "Comparing employee, merchant, date and amount with history is a deterministic lookup.", "exact"),
        "E4": ("tool", "A pre-approval ticket either exists and is valid or it does not, so a lookup decides.", "exact"),
        "E5": ("tool", "The caps and violation codes are written in the policy so plain code applies them every time.", "exact"),
        "E6": ("agent", "Which record to pull next depends on what the last lookup revealed, so nobody can write the path in advance.", "rubric"),
        "E7": ("fixed_step", "The decision and codes are fixed inputs and only the wording needs one scripted model call.", "schema"),
    }
    ```

3. Save the file, and then run `python check.py`.

4. Verify that all seven lines under **TODO 2** show `[PASS]`.

5. Review your answers. Each row reads *(kind, reason, how you will test it)*:

    - **E1** and **E7** are `fixed_step`. The path is fixed, but reading or writing free text needs one model call, and a tool never calls a model. Their output has a shape, so you test it with a `schema`.
    - **E2** to **E5** are `tool`. Rates, lookups, and policy caps are plain code, so the same input always gives the same output. You test them with `exact` answers.
    - **E6** is the only `agent`. It is the only step whose path is unknown. Its output varies, so you score it against a `rubric`.

    > **Note**: E2 to E5 could also be `fixed_step`, and the checker accepts either. A `tool` is the least power, so it is the answer used here.

## Decide how the steps pass the claim along

1. In **lab.py**, search for the comment **TODO 3 of 4**.

2. Replace the line `DATA_FLOW = "one_shared_db"` with the following code:

    ```python
    DATA_FLOW = "explicit_handoffs"
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the **TODO 3** section shows only `[PASS]` lines.

    > **Note**: If E5 (apply policy) and E6 (investigate) both write to one shared claim record, one can overwrite the other's result. With explicit hand-offs, each step receives the claim, returns a new version, and passes that to the next step.

## Write your first Claude API call

All the rules pass now. In this section, you write the Claude call that reviews your design.

1. In **lab.py**, search for the comment **TODO 4 of 4**. Below the `CRITIC_SYSTEM` text is the function `call_claude(prompt)`.

2. Replace the last line of the function, `return ""  # replace this line in TODO 4`, with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        response = get_client().messages.create(
            model=MODEL_BALANCED,
            max_tokens=2048,
            system=CRITIC_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return text_of(response)
    ```

3. Save the file. Review the call, noting the following details:

    - `get_client()` returns the Anthropic client. It reads your key from the **.env** file (see **claude_client.py**).
    - `.messages.create(...)` sends your request to Claude.
    - `model` chooses which Claude model answers.
    - `max_tokens` limits the length of the answer. The API requires it.
    - `system` holds the standing instruction: act as an architecture reviewer and reply in JSON.
    - `messages` holds the conversation, which here is one user message that contains your design.
    - `text_of(response)` pulls the answer text out of the response.

4. Run your design through Claude by running the following command:

    ```
    python lab.py
    ```

5. Verify that the output is similar to the following. Claude's wording will differ:

    ```
    All rules pass.

    Asking Claude for a second opinion ...
      weakest pick : E3 - <one sentence from Claude>
      - E3: <issue>
      verdict      : <one sentence>
    (Advisory. Where Claude and the rules disagree, the rules win, but ask yourself why.)

    Saved to results/design.json. Now run: python check.py
    ```

6. Read Claude's weakest pick, and decide whether you agree. The rules are the judge, and Claude is a second opinion.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 16/16 checks passed
    ```

3. Submit the **results/design.json** file as your evidence. There is nothing else to write up.

## Try breaking it (optional)

After you reach 16/16, change one thing at a time, run `python check.py`, and then undo the change.

1. Change **E2** to `"agent"`. Which rule fires, and why is a good-sounding reason not enough when the path is known?

2. Change **E6** to `"tool"`. What does the rule say about a step whose path is unknown?

3. Change the test of **E6** to `"exact"`. Why can't an exact-match test check an agent?

4. Change **FB-3** to `"agentic"`. Which rule catches it?

## Troubleshooting

- **ANTHROPIC_API_KEY is missing**: The **.env** file is not in the lab folder, or it has a typo. Repeat the steps in *Add your Claude API key*.

- **IndentationError after TODO 4**: The pasted lines lost their four-space indent. Indent every pasted line by four spaces.

- **A row still shows `[FAIL]` after pasting**: The old block is still in the file, or you pasted only the rows. Delete the old block, and paste the whole snippet, including the first line (`ARCHITECTURE = {` or `STEPS = {`) and the closing `}`.

- **Part B says to fix Part A first**: A rule still fails. Read the first `[FAIL]` line in the output of `python check.py`.

- **Part B says the reply was empty or not JSON**: The `call_claude` function does not return the text. Check that the `return ""` line is gone and that `return text_of(response)` is present.

- **Part B says you edited a table after the last run**: Run `python lab.py` again.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
