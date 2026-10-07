---
lab:
    title: 'Review Expense Claims Two Ways'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Review Expense Claims Two Ways

In Demo 3A, you watched ACME's finance team decide whether an expense review should be a conversation, a workflow, or an agent. You voted on five briefs, and then you saw the same claim review built three ways and measured. The cheapest design that was reliable won. In this lab, you build the first two of those designs yourself, with the same briefs, the same T&E policy (**ACME-T&E-2026.2**), and the same claims.

You will complete three small pieces of **lab.py**, which add up to 26 lines of code. The lab takes about 25 minutes, and this guide gives you every line. At the end, you see both builds review six real claims side by side, so you can compare them.

This lab continues Demo 3A, so you will recognize the following:

- The five briefs: the HR-policy FAQ bot, the expense-report review, the nightly KPI digest, the open-ended competitive research question, and the production-incident triage.
- The rule from the demo: if a *human* decides the next step, use a conversation; if a *process* decides, use a workflow; if the *model* decides, use an agent.
- The claims **R01** to **R12**, with their expected decisions: approve, reject, or escalate to a human.
- Build 1, the conversational build, where one Claude call reads the whole policy and decides alone.
- Build 2, the workflow build, where one Claude call reads the claim into fields and plain code applies the policy.

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

## Review the starting point

1. Open the **data** folder, and look at the following files, which are the same files you saw in the demo:

    - **briefs.json**: the five briefs, each with the signals that decide its architecture.
    - **policy.json**: the ACME travel and expense policy.
    - **expense_reports.json**: the twelve claims, with the decision each one should get.

2. Run the checker to see your starting point:

    ```
    python check.py
    ```

    > **Note**: The checker fails on purpose, because the starter code contains placeholders. The last line shows that only a few of the 16 checks passed.

## Write the rubric from the demo

In this section, you write the rule that picks an architecture from a brief's signals. This is the same function that ran during the vote in Demo 3A.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 3**. Below it is a function named `architecture_for` that currently returns `"agentic"` for every brief.

3. Replace the line `return "agentic"  # replace this line in TODO 1` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        controller = signals["next_step_controller"]
        if controller == "human":
            return "conversational"
        if controller == "process":
            return "workflow"
        return "agentic"
    ```

4. Save the file, and then run the checker:

    ```
    python check.py
    ```

5. Verify that the five **TODO 1** checks pass.

## Build the conversational review

In this section, you write your first Claude API call. Build 1 sends the whole policy and one claim to Claude, and Claude decides alone.

1. In **lab.py**, search for the comment **TODO 2 of 3**. Below it is a function named `run_conversational` that currently returns `"invalid"`.

2. Replace the line `return "invalid"  # replace this line in TODO 2` with the following code. Keep the four-space indent:

    ```python
        system = f"You review expense claims against this policy ({POLICY['version']}).\n{policy_text()}\n{ANSWER_FORMAT}"
        response = get_client().messages.create(
            model=MODEL_BALANCED,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": claim_facts(claim)}],
        )
        return decision_in(text_of(response))
    ```

    Noting the following details:

    - `get_client().messages.create(...)` is the Claude Messages API call. Every Claude app you build sends a request like this one.
    - `system` holds the instructions and the policy. `messages` holds the claim, as the user's turn.
    - `max_tokens` is required. It is set high because Claude may use some of it to think before answering.
    - `decision_in` and `text_of` are in **expense_core.py**. They turn the reply into `approve`, `reject`, or `escalate`.

3. Save the file, and then run the checker:

    ```
    python check.py
    ```

4. Verify that the five **TODO 2** checks pass.

## Build the workflow review

In this section, you write Build 2. Claude does one job, which is to read the free-text claim into fields. Plain code then applies the policy, so the decision is the same every time for the same fields.

1. In **lab.py**, search for the comment **TODO 3 of 3**. Below it is a function named `run_workflow` that currently returns `"escalate"`.

2. Replace the line `return "escalate"  # replace these lines in TODO 3` with the following code. Keep the four-space indent:

    ```python
        system = ("Extract the expense fields from the claim text. Reply with JSON only, matching this schema exactly:\n"
                  + json.dumps(EXTRACTION_SCHEMA))
        response = get_client().messages.create(
            model=MODEL_BALANCED,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": claim["text"]}],
        )
        fields = json_in(text_of(response))
        if not isinstance(fields, dict) or any(key not in fields for key in EXTRACTION_SCHEMA["required"]):
            return "escalate"
        return apply_policy(fields, claim)[0]
    ```

    Noting the following details:

    - The call looks like Build 1, but the instruction is different. Claude gets the schema, not the policy.
    - If Claude's reply is missing a field, the claim is escalated to a human. The model never gets to guess a decision.
    - `apply_policy` is plain Python in **expense_core.py**. It holds the caps, the receipt rule, and the duplicate check.

3. Save the file, and then run the checker:

    ```
    python check.py
    ```

4. Verify that the six **TODO 3** checks pass and that Part A shows no `[FAIL]` lines.

## Run both builds on real claims

1. Run the lab by running the following command:

    ```
    python lab.py
    ```

    > **Note**: This calls Claude 12 times (6 claims, 2 builds) and takes about a minute.

2. Review the output, noting the following details:

    - Part 1 lists the five briefs with the architecture your rubric chose. The expense-report review is a **workflow**, not an agent.
    - Part 2 is a table with one row per claim: the expected decision, then what each build decided.
    - The last line shows how many claims each build got right. The workflow should get at least 5 of 6.

3. Run the checker again:

    ```
    python check.py
    ```

4. Verify that the last line reads `RESULT: 22/22 checks passed`.

## Troubleshooting

- **`ANTHROPIC_API_KEY is missing`**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the line to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **A conversational answer shows `invalid`**: Claude's reply was not the JSON asked for. Check that `ANSWER_FORMAT` is part of the `system` text in TODO 2.
- **Part B says the saved run is not from your current code**: You edited a TODO after the last run. Run `python lab.py` again.
- **The workflow got fewer than 5 of 6 right**: Read the table. A miss means Claude read a field wrongly, not that the policy was wrong. Run `python lab.py` again, because model output varies slightly between runs.

## Clean up

Close the terminal. Keep your **.env** file private, and do not copy it to another folder.

## More information

- Demo 3A showed all three builds on all twelve claims, and measured accuracy, cost, and how often the same claim got a different answer. The agentic build comes back in Labs 3.5 to 3.7.
- To see how a design handles a failure at runtime, continue with Lab 3.3.
