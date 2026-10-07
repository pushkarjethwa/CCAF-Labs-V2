---
lab:
    title: 'Build a Supplier-Payment Release Gate with Human Approval'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Build a Supplier-Payment Release Gate with Human Approval

In Demo 3D, you watched a supplier-payment release process handle six payments. A set of simple rules checked each payment. Small payments were approved automatically. Larger ones waited for a reviewer, who approved them, and only then was the money released. An Agent SDK hook let the release tool run for approved payments. In this lab, you write those pieces yourself, for the same payments, the same rules, and the same reviewers.

You will complete four small pieces of **lab.py**, which add up to 26 lines of code. The lab takes about 40 minutes, and this guide gives you every line. At the end, Claude writes a short note for each of the six payments, and your gate, reviewer choice, and hook release them.

This lab continues Demo 3D, so you will recognize the following:

- The six supplier payments (PAY-1001 to PAY-1006), the policy file, and the three reviewers.
- The release gate: rules that decide whether a payment is released automatically or needs approval.
- The approval step, where a reviewer approves a waiting payment.
- The Agent SDK hook that lets the release tool run for approved payments.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_3/LABS/LAB_3_4_payment_release_guard** folder.

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

    > **Note**: The checker reports `[FAIL]` lines because your four TODOs are not written yet. Part A tests your code with no API key and no model. Part B is skipped until you run the real model.

2. Notice that only two files matter for this lab: **lab.py**, which holds your four TODOs, and **check.py**. The **release_core.py** file is the payment engine from the demo, and you do not need to read it.

3. Open **data/policy.json**. It holds the two numbers your rules use: an approval threshold of 25,000 and a new-vendor age of 90 days.

## Write the release gate

The gate decides, in code, whether a payment is released automatically or goes to a reviewer. It has two small parts: the rules, and the decision.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - THE RELEASE GATE**. Below it are two functions. Each one has a single placeholder line that ends with `# replace these lines in TODO 1`.

3. In the `payment_flags` function, replace the line `return []  # replace these lines in TODO 1` with the following code. Keep the four-space indent:

    ```python
        flags = []
        if case["payment"]["amount"] >= policy["approval_threshold"]:
            flags.append("AMOUNT_NEEDS_APPROVAL")
        if case["payment"]["amount"] > case["approver"]["limit"]:
            flags.append("OVER_APPROVER_LIMIT")
        if case["payee"]["vendor_age_days"] < policy["new_vendor_days"]:
            flags.append("NEW_VENDOR")
        return flags
    ```

4. In the `decide` function, replace the line `return "auto-release"  # replace these lines in TODO 1` with the following code:

    ```python
        if flags:
            return "needs-approval"
        return "auto-release"
    ```

5. Save the file, and then run `python check.py`.

6. Verify that the four lines under **TODO 1** show `[PASS]`.

7. Review the gate, noting the following details:

    - A rule that finds something worth a second look adds a flag. The flags are the reasons shown to the reviewer.
    - A large amount, a payment above the approver's own limit, and a very new vendor each send the payment to a reviewer.
    - A payment with no flags is released automatically.

## Choose the reviewer

A payment that needs approval goes to one reviewer. The reviewer must be allowed to approve that amount, so the choice depends on each reviewer's limit.

1. In **lab.py**, search for the comment **TODO 2 of 4 - THE REVIEWER**. Below it is the function `choose_reviewer(case, reviewers)`, and its only line is `return None  # replace these lines in TODO 2`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        amount = case["payment"]["amount"]
        for name, person in sorted(reviewers.items(), key=lambda item: item[1]["limit"]):
            if person["limit"] >= amount:
                return name
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the three lines under **TODO 2** show `[PASS]`.

5. Review the choice, noting the following details:

    - The reviewers are sorted from the lowest limit to the highest.
    - The first reviewer whose limit covers the amount gets the payment. A 6,500 payment goes to the analyst, and a 182,000 payment goes to the finance controller.
    - The engine puts this name in the review packet, and that reviewer approves the payment.

## Write the release hook

An Agent SDK agent calls a `release_payment` tool. A PreToolUse hook runs before the tool and decides whether the call may go ahead. The hook looks at the state of the payment in the workflow, so the answer comes from the system of record and not from the agent.

1. In **lab.py**, search for the comment **TODO 3 of 4 - THE RELEASE HOOK**. Below it is the function `make_before_release(svc)`, which holds the inner function `before_release`. Its only line is `return {}  # replace these lines in TODO 3`.

2. Replace that line with the following code. Keep the eight-space indent, because the code sits inside two functions:

    ```python
            allowed, why = svc.authorisation(input_data["tool_input"]["case_id"])
            decision = "allow" if allowed else "deny"
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                           "permissionDecisionReason": why}}
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the two lines under **TODO 3** show `[PASS]`.

5. Review the hook, noting the following details:

    - `svc.authorisation(case_id)` tells the hook whether the payment was approved, either by the gate or by a reviewer.
    - The hook returns a PreToolUse decision with a reason. For an approved payment, the decision is `allow`, and the tool runs.
    - The prompt can say "only release approved payments", and the hook is what makes it true.

## Write your Claude API call

In this section, you write the one model call in the lab: a short note that helps the reviewer understand a single payment.

1. In **lab.py**, search for the comment **TODO 4 of 4**. Below it is the function `ask(text)`, and its only line is `raise NotImplementedError("TODO 4 is not done yet")  # replace this line in TODO 4`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        response = get_client().messages.create(
            model=MODEL_BALANCED,
            max_tokens=1024,
            system=core.NOTE_SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        return text_of(response)
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the one line under **TODO 4** shows `[PASS]`.

5. Review the call, noting the following details:

    - `get_client()` returns the Anthropic client. It reads your key from the **.env** file (see **claude_client.py**).
    - `.messages.create(...)` sends your request to Claude.
    - `model` chooses which Claude model answers.
    - `max_tokens` limits the length of the answer. The API requires it.
    - `system` tells the model to write a note of two plain sentences for the reviewer.
    - `messages` holds the evidence for one payment, as JSON.
    - `text_of(response)` pulls the answer text out of the response.

## Run the release process

1. Ask Claude for a note on each of the six payments, and run them through your gate, reviewer choice, approval, and release hook, by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run makes six short calls to Claude, and uses a small amount of API credit.

2. Verify that the output ends with a summary line similar to the following:

    ```
    gate correct 6/6 | released 6 payments, total 276,750.00

    Saved to results/run.json. Now run: python check.py
    ```

    > **Tip**: Read the notes printed above the summary. Three payments were released automatically, and three waited for a reviewer and were approved.

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

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to compare your work. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
