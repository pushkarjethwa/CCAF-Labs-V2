---
lab:
    title: 'Harden the Research Desk'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Harden the Research Desk

In Demo 3B, the instructor turned one overloaded research agent into a desk of four specialists: a searcher, an analyst, a fact-checker, and a writer. The desk was then made safe with four ideas: validated hand-offs, isolated briefs, a rule for each kind of failure, and escalation decided in code. In this lab, you write those four ideas yourself, on the same desk, with the same 40-document corpus and the same confidential client note.

The client behind the desk has quietly started due diligence on acquiring Pallo Systems. That note must never reach a specialist or the final report. You make sure it does not, and you make the desk fail safely when things go wrong.

You will complete five small pieces of **lab.py**, which add up to 22 lines of code. The lab takes about 35 minutes, and this guide gives you every line.

This lab continues Demo 3B, so you will recognize the following:

- The research desk, its corpus, and its tools.
- The four specialists, and the questions Q2 (two reliable reports disagree), Q4 (a calculation is needed), and Q5 (a rumour sits next to the confidential note).
- The ideas you write here: contracts and isolated briefs from Stage 4, the failure policy from the Stage 5 hand-off drill, and the escalation rule.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_3/LABS/LAB_3_2_research_desk_handoffs** folder.

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

    > **Note**: The checker fails on purpose. Part A tests each of your five TODOs with hand-made inputs and needs no API key. Part B is skipped until you run the desk.

2. Notice that only two files matter for this lab: **lab.py**, which holds your five TODOs, and **check.py**. The **desk_core.py** file is the machinery from the demo, and you do not need to read it.

## Write the hand-off contracts

A contract says exactly what shape a specialist's reply must have. The contract for the searcher is already in the file as an example.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 5 - CONTRACTS**.

3. Below the `"searcher"` row, find the two rows that start with `"analyst"` and `"fact_checker"`. Replace those two lines with the following code:

    ```python
        "analyst": {"results": ("list", {"label": "str", "value": "str", "inputs": "str"})},
        "fact_checker": {"checks": ("list", {"doc_id": "doc_id", "claim": "str", "verdict": ["SUPPORTED", "NOT_SUPPORTED", "CONFLICT"], "detail": "str"})},
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the six lines under **TODO 1** show `[PASS]`.

    > **Note**: The contract rejects a reply with a missing field, an extra field, a verdict outside the three allowed words, or a `doc_id` that is not in the corpus (a hallucinated source).

## Write the briefs

A brief is the message a specialist receives. The starter code pastes the confidential note into every brief, which is the leak you saw in Stage 3 of the demo.

1. In **lab.py**, search for the comment **TODO 2 of 5 - BRIEFS**.

2. Select the three functions below it, from `def searcher_brief` to the end of `fact_check_brief`, and replace them with the following code:

    ```python
    def searcher_brief(q):
        return f"Question: {q['text']}\nFind the best current sources and the exact facts needed to answer it."


    def analyst_brief(found):
        return f"Compute: {found['calc_request']}\nUse exactly these facts: {json.dumps(found['findings'])}"


    def fact_check_brief(finding):
        return (f"Verify this claim against {finding['doc_id']} and look for any other current, reliable document "
                f"that answers the same question differently.\nClaim: {finding['fact']} ({finding['value']})")
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six lines under **TODO 2** show `[PASS]`.

    > **Note**: Each brief now holds only the task and the facts that specialist needs. This is least privilege: what a specialist never sees, it cannot leak.

## Write the failure policy

The starter code retries every failure ten times, which is the wrong answer to most failures. The Stage 5 drill in the demo showed that different failures need different policies.

1. In **lab.py**, search for the comment **TODO 3 of 5 - POLICY**.

2. Inside the `POLICY = {` block, replace the four rows with the following code:

    ```python
        "malformed_handoff": {"action": "re_ask_with_errors", "max_attempts": 1},
        "specialist_crashed": {"action": "retry_same_call", "max_attempts": 2},
        "confidential_leak": {"action": "block_and_escalate", "max_attempts": 0},
        "no_findings": {"action": "partial_report", "max_attempts": 0},
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six lines under **TODO 3** show `[PASS]`.

5. Review the policy, noting the following details:

    - A malformed reply is a reasoning problem. Repeating the same call gives the same mistake, so the desk re-asks once and quotes the exact problems.
    - A crashed specialist is an environment problem. The next try may work, so the desk retries the same call at most twice.
    - A brief that contains the client note is never acceptable. The desk blocks it before any model sees it, and escalates.
    - When the searcher finds nothing, there is nothing to build on. The desk stops with an honest partial report for a human.

## Decide escalation in code

When two reliable sources disagree, the desk must not pick one. It must tell a human. In this section, you make that a rule in code instead of a hope that the writer remembers.

1. In **lab.py**, search for the comment **TODO 4 of 5 - ESCALATION**.

2. In the `has_conflict` function, replace the line `return False  # replace this line in TODO 4` with the following code:

    ```python
        return any(c["verdict"] == "CONFLICT" for c in checks)
    ```

3. In the `must_re_ask_writer` function, replace the line `return False  # replace this line in TODO 4` with the following code:

    ```python
        return conflict and not core.escalated(report)
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the four lines under **TODO 4** show `[PASS]`.

    > **Note**: The first function spots a conflict among the fact-checks. The second says that if there was a conflict and the report did not escalate it, the desk asks the writer once more.

## Write the writer's Claude API call

The searcher, analyst, and fact-checker run as real Claude agents inside **desk_core.py**. The writer is a single call with no tools, and you write it.

1. In **lab.py**, search for the comment **TODO 5 of 5**. Below it is the function `call_writer(brief)`.

2. Replace the last line of the function, `return ""  # replace this line in TODO 5`, with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        response = get_client().messages.create(
            model=MODEL_BALANCED,
            max_tokens=2048,
            system=core.WRITER_SYSTEM,
            messages=[{"role": "user", "content": brief}],
        )
        return text_of(response)
    ```

3. Save the file, and then run `python check.py`.

4. Verify that Part A is now all `[PASS]`.

5. Review the call, noting the following details:

    - `get_client()` returns the Anthropic client. It reads your key from the **.env** file (see **claude_client.py**).
    - `.messages.create(...)` sends your request to Claude.
    - `model` chooses which Claude model answers.
    - `max_tokens` limits the length of the answer. The API requires it.
    - `system` holds the standing instruction that tells the writer how to write the report.
    - `messages` holds the conversation, which here is one user message that contains the verified facts.
    - `text_of(response)` pulls the answer text out of the response.

## Run the desk on real questions

1. Run the desk on questions Q2, Q4, and Q5 by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run uses a small amount of API credit and takes a few minutes, because each question involves several specialists.

2. Verify that you see one line per question, similar to the following. The counts will differ:

    ```
    Q2: PASS | leaks 0 | {'reworks': 0, 'leaks_blocked': 0, 'checks': 2, 'status': 'complete'}
    Q4: PASS | leaks 0 | {'reworks': 0, 'leaks_blocked': 0, 'checks': 2, 'status': 'complete'}
    Q5: PASS | leaks 0 | {'reworks': 0, 'leaks_blocked': 0, 'checks': 1, 'status': 'complete'}

    Saved to results/run.json. Now run: python check.py
    ```

    > **Tip**: A model can occasionally slip on one question. If a line shows `FAIL`, run `python lab.py` once more before you change any code.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 28/28 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Try breaking it (optional)

After you reach 28/28, change one thing at a time, run `python check.py`, and then undo the change.

1. Set `"malformed_handoff"` to `"max_attempts": 5`. Which line fails, and what would five re-asks cost on a long brief?

2. Set `"confidential_leak"` to `"action": "retry_same_call"`. Which line fails, and why is a blocked brief better than a retry?

3. Put `{desk.PRIVATE_NOTE}` back into `analyst_brief`. Which lines fail?

4. Make `has_conflict` return `False`. Which Part B line would fail on a real run, and why?

## Troubleshooting

- **ANTHROPIC_API_KEY is missing**: The **.env** file is not in the lab folder, or it has a typo. Repeat the steps in *Set up the lab folder*.

- **IndentationError**: A pasted line lost its indent. Match the indent shown in the snippet, which is four spaces inside a function or a dictionary.

- **A TODO line still fails after pasting**: The old lines are still in the file, or only some were replaced. Delete the old lines named in the step, and paste the whole snippet.

- **Part B says you edited lab.py after the last run**: Run `python lab.py` again.

- **Part B says a report is empty**: The `call_writer` function still returns an empty string. Check that the `return ""` line is gone from TODO 5.

- **One question shows FAIL on a real run**: This is normal model variation. Run `python lab.py` once more.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
