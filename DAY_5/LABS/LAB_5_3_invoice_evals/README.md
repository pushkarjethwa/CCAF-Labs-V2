---
lab:
    title: 'Grade, Trace and Gate an Invoice Checker'
    module: 'Day 5 - Evaluation, Provenance and Production Readiness'
---

# Grade, trace and gate an invoice checker

The accounts-payable team at a food company uses Claude to check supplier invoices before payment. Claude reads an invoice and returns a decision (pay, hold, reject or escalate), the line ids it relied on, the invoice total, and an escalate flag. A finance manager asks two questions: "How do we know the new prompt is better than the old one?" and "How do we know the decision is based on the invoice?" In this lab, you answer both with eight test invoices, a grader written in plain Python, a source check, a release gate, and a human-review queue.

You will complete four small pieces of **lab.py**, which add up to 23 lines of code. The lab takes about 45 minutes, and this guide gives you every line. At the end, you have run two prompt versions on the same eight invoices, compared them case by case, and written the risky invoices to a review file.

This lab continues Demo 5C, so you will recognize the following:

- The same stages: a grading harness in plain code, a check that every cited id exists, a comparison of prompt v1 and prompt v2 with a release gate, and a human-review queue.
- The same answer shape: a decision, the ids it cites, a total, and an escalate flag.
- The same idea: code grades what code can check, and a person decides the big calls.
- The same test-set labels, written by a person before any model ran. Here the documents are invoices instead of contracts.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_5/LABS/LAB_5_3_invoice_evals** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

    This installs the Anthropic SDK, which sends requests to Claude, and `python-dotenv`, which reads your key from a file.

3. Create a new file named **.env** in the lab folder, and add the following line, replacing the value with your own API key:

    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```

    > **Important**: Never paste your key into chat or commit the **.env** file to git.

4. Save the file, and then test your key by running the following command:

    ```
    python claude_client.py
    ```

    This sends one short message to Claude. It proves that your key works before you spend time on the lab.

5. Verify that you see a short greeting followed by a line that starts with `[usage]`.

## Review the starting point

1. Run the checker by running the following command:

    ```
    python check.py
    ```

    This runs a set of tests on your four TODOs. It needs no key and calls no model.

    > **Note**: The checker reports `[FAIL]` lines because your four TODOs are not written yet. Part B is skipped until you run the model.

2. Notice that only two files matter for your work: **lab.py**, which holds your four TODOs, and **check.py**. The **invoice_core.py** file holds the data loading and the grade table, and you do not need to read it.

3. Open **data/invoices.json** at invoice I08, and **data/cases.json** at I08. Review the files, noting the following details:

    - An invoice has item lines (L1, L2), a purchase-order line (PO), a goods-receipt line (GR), and a payment-record line (AP).
    - The label next to the invoice was written by a person before any model ran. It holds the expected decision, the line ids the answer must cite, the expected total, and the expected escalate flag.
    - In I08, line L1 bills a year in advance, but line PO approves monthly billing only. The right answer is to escalate.

4. Open **prompts/v1.txt** and **prompts/v2.txt** side by side. Prompt v1 is the first draft. Prompt v2 adds seven short rules, such as how to compute the total and when to escalate.

5. In **lab.py**, find the function `ask` below the line **RUNNING THE STAGES**. This is the Claude call that every stage uses. It sends one request with `client.messages.create(...)` and returns the reply text. You do not edit it.

## Write the grader

A grader decides whether one answer is right, without asking a model. It compares the answer with the label, and it returns five checks: the shape, the decision, the cited ids, the total, and the escalate flag.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - THE GRADER**. Below it is the function `grade(output, case)`. Its only line is `return {name: False for name in core.CHECKS}  # replace these lines in TODO 1`.

3. Replace that line with the following code. Keep the four-space indent:

    ```python
        if not core.schema_ok(output):
            return {name: False for name in core.CHECKS}
        return {
            "schema": True,
            "decision": output["decision"] == case["expected_decision"],
            "items": set(case["required_items"]) <= set(output["citations"]),
            "total": abs(output["total"] - case["expected_total"]) <= 0.01 * case["expected_total"],
            "escalate": output["escalate"] == case["expected_escalate"],
        }
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the six lines under **TODO 1** show `[PASS]`.

6. Review the grader, noting the following details:

    - `core.schema_ok(output)` checks that the answer has every key with the right type. If it does not, all five checks are False.
    - `set(...) <= set(...)` is True when every required id is in the cited ids. Extra ids are allowed.
    - The total may be off by 1 percent, so a small rounding difference does not fail a case.
    - A case passes only if all five checks are True.

7. Run prompt v1 on the eight invoices and grade it by running the following command:

    ```
    python lab.py --stage 1
    ```

    This sends the eight invoices to Claude with prompt v1, saves the answers to **results/run_v1.json**, and prints one row per invoice with your five checks. It makes eight short calls and uses a small amount of API credit.

    > **Note**: A score on a fixed test set is the baseline. Every later change is measured against it.

8. Verify that you see a table with eight rows, a `Pass rate for v1: n/8` line, and a cost line. The number is your own measured result.

## Check the sources

Provenance means that every claim traces back to its source. The check is simple: every line id that Claude cites must exist in that invoice. An id that does not exist is a break in the lineage.

1. In **lab.py**, search for the comment **TODO 2 of 4 - THE SOURCE CHECK**. Below it is the function `coverage(output, invoice)`. Its only line is `return 0.0  # replace these lines in TODO 2`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        ids = {line["id"] for line in invoice["lines"]}
        cited = output["citations"]
        return sum(item in ids for item in cited) / len(cited)
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the three lines under **TODO 2** show `[PASS]`.

5. Review the check, noting the following details:

    - `ids` is a set of the line ids in the invoice, so a lookup is instant.
    - `item in ids` is True for a real id and False for an invented one, and `sum(...)` counts the True values.
    - The result is the share of cited ids that exist: 1.0 means all of them, 0.5 means half.

6. Check the sources of the v1 run by running the following command:

    ```
    python lab.py --stage 2
    ```

    This reads **results/run_v1.json**, runs your `coverage` function on every answer, and prints the share for each invoice. It also prints the audit record for one answer: a hash of the invoice, the prompt version and hash, and the model. It needs no key.

7. Verify that you see one coverage row for each invoice and a `Provenance coverage for v1` line.

    > **Note**: The check proves that the cited ids are real. It does not prove that they justify the decision. That is a question for a person, or for a judge.

## Write the release gate

A new prompt must prove that it is safe to ship. The gate compares the v1 and v2 results case by case, and it decides from written rules, not from the average.

1. In **lab.py**, search for the comment **TODO 3 of 4 - THE RELEASE GATE**. Below it is the function `release_gate(old, new)`. Its only line is `return "GATE: PASS"  # replace these lines in TODO 3`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        regressed = [case for case in old if old[case] and not new[case]]
        missed = [case["id"] for case in core.CASES if case["expected_escalate"] and not new[case["id"]]]
        if regressed or missed or sum(new.values()) < sum(old.values()):
            return "GATE: BLOCKED"
        return "GATE: PASS"
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the three lines under **TODO 3** show `[PASS]`.

5. Review the gate, noting the following details:

    - `old` and `new` map each case id to True when the case passed all five checks.
    - A regression is a case that passed with v1 and fails with v2. One regression blocks the release.
    - A must-escalate case that v2 gets wrong also blocks the release, because that is the costliest mistake.
    - The release is blocked if fewer cases pass with v2 than with v1.

6. Run prompt v2 and apply the gate by running the following command:

    ```
    python lab.py --stage 3
    ```

    This runs prompt v2 on the same eight invoices, saves **results/run_v2.json**, lists each case as improved, same, or regressed, and prints the result of your gate. It makes eight short calls.

7. Verify that you see a comparison table, a `Pass rate` line for v1 and v2, and one line that reads either `GATE: PASS` or `GATE: BLOCKED`.

    > **Note**: The gate result comes from your data. Whichever it prints is a real result, so read the cases in the table before you change anything.

## Write the review queue

Some decisions should not be made by a model alone. An answer goes to a person when its total is USD 100,000 or more, or when Claude set the escalate flag. The queue is a file where those cases wait for a reviewer.

1. In **lab.py**, search for the comment **TODO 4 of 4 - THE REVIEW QUEUE**. Below it is the function `write_queue(outputs, path)`. Its only line is `return []  # replace these lines in TODO 4`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        queue = []
        for case_id, output in outputs.items():
            if output["total"] >= core.ESCALATION_VALUE or output["escalate"]:
                queue.append({"case": case_id, "total": output["total"], "evidence": output["citations"]})
        path.write_text(json.dumps(queue, indent=2), encoding="utf-8")
        return queue
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the three lines under **TODO 4** show `[PASS]`.

5. Review the queue, noting the following details:

    - The first rule does not depend on the model. It compares a number with a limit that the business sets.
    - The second rule uses Claude's own flag, for cases such as two lines that contradict each other.
    - Each item carries the cited ids as evidence, so the reviewer does not start from zero.

6. Write the queue by running the following command:

    ```
    python lab.py --stage 4
    ```

    This reads **results/run_v2.json**, calls your `write_queue` function, and saves **results/human_review_queue.json**. It needs no key.

7. Verify that you see one line for each queued invoice, and a line that starts with `Written to results/human_review_queue.json`.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

    This tests your four functions again, and then checks the saved runs and the queue file in Part B.

2. Verify that the last line reads:

    ```
    RESULT: 21/21 checks passed
    ```

    > **Note**: The `info:` lines in Part B print your own pass rates, your gate result, and your coverage. They are not pass or fail checks.

3. Submit the output of `python check.py` as your evidence. There is nothing else to write up.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

- The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to compare your work. The **SOLUTION/SOLUTION_GUIDE.md** file explains each block.
- To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
