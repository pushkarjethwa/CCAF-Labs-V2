---
lab:
    title: 'Harden the Research Desk'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Build the Research Desk

In Demo 3B, the instructor turned one overloaded research agent into a desk of four specialists: a searcher, an analyst, a fact-checker, and a writer. The desk works because of four ideas: validated hand-offs, minimal briefs, escalation decided in code, and a writer that turns verified facts into a report. In this lab, you write those four ideas yourself, on the same desk, with the same 40-document corpus.

You will complete four small pieces of **lab.py**, which add up to 14 lines of code. The lab takes about 30 minutes, and this guide gives you every line.

This lab continues Demo 3B, so you will recognize the following:

- The research desk, its corpus, and its tools.
- The four specialists, and the questions Q2 (two reliable reports disagree), Q4 (a calculation is needed), and Q5 (a rumour sits next to the real answer).
- The ideas you write here: contracts and minimal briefs from Stage 4, and the escalation rule.

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

    > **Note**: The checker reports `[FAIL]` lines until you finish the TODOs. Part A tests each of your four TODOs with hand-made inputs and needs no API key. Part B is skipped until you run the desk.

2. Notice that only two files matter for this lab: **lab.py**, which holds your four TODOs, and **check.py**. The **desk_core.py** file is the machinery from the demo, and you do not need to read it.

## Write the hand-off contracts

A contract says exactly what shape a specialist's reply must have. The contract for the searcher is already in the file as an example.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - CONTRACTS**.

3. Below the `"searcher"` row, find the two rows that start with `"analyst"` and `"fact_checker"`. Replace those two lines with the following code:

    ```python
        "analyst": {"results": ("list", {"label": "str", "value": "str", "inputs": "str"})},
        "fact_checker": {"checks": ("list", {"doc_id": "doc_id", "claim": "str", "verdict": ["SUPPORTED", "NOT_SUPPORTED", "CONFLICT"], "detail": "str"})},
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the three lines under **TODO 1** show `[PASS]`.

    > **Note**: A contract lists the fields a reply must have and their types. The `verdict` field accepts only the three words listed, and every `doc_id` must be a document that exists in the corpus.

## Write the briefs

A brief is the message a specialist receives. Each brief should carry only the task and the facts that specialist needs, and nothing else. The starter code returns an empty string for each brief.

1. In **lab.py**, search for the comment **TODO 2 of 4 - BRIEFS**.

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

4. Verify that the three lines under **TODO 2** show `[PASS]`.

    > **Note**: This is least privilege. The searcher gets the question, the analyst gets the calculation and the facts, and the fact-checker gets one claim and its document. No specialist reads the whole conversation.

## Decide escalation in code

When two reliable sources disagree, the desk must not pick one. It must tell a human. In this section, you make that a rule in code instead of a hope that the writer remembers.

1. In **lab.py**, search for the comment **TODO 3 of 4 - ESCALATION**.

2. In the `has_conflict` function, replace the line `return False  # replace this line in TODO 3` with the following code:

    ```python
        return any(c["verdict"] == "CONFLICT" for c in checks)
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the three lines under **TODO 3** show `[PASS]`.

    > **Note**: The function spots a conflict among the fact-checks. When it returns `True`, **desk_core.py** adds a line to the writer's brief that tells it to report both values and escalate to a human.

## Write the writer's Claude API call

The searcher, analyst, and fact-checker run as real Claude agents inside **desk_core.py**. The writer is a single call with no tools, and you write it.

1. In **lab.py**, search for the comment **TODO 4 of 4**. Below it is the function `call_writer(brief)`.

2. Replace the last line of the function, `return ""  # replace this line in TODO 4`, with the following code. Keep the four-space indent, because the code sits inside the function:

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
    Q2: PASS | {'checks': 2}
    Q4: PASS | {'checks': 2}
    Q5: PASS | {'checks': 1}

    Saved to results/run.json. Now run: python check.py
    ```

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 14/14 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
