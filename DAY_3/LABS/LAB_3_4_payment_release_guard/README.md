---
lab:
    title: 'Guard Supplier-Payment Release with Code, Not Prompts'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Guard Supplier-Payment Release with Code, Not Prompts

In Demo 3D, you watched an agent propose what to do with twelve supplier payments: release, hold, or reject. Many of its proposals came with high confidence, and some were wrong. The lesson was that a confidence score is not a control, and that a sentence in a prompt is not a guard. The control has to be code: a policy gate, a human review that really pauses the payment, a bank call that cannot pay twice, and an Agent SDK hook that blocks the release tool. In this lab, you write those controls yourself, for the same payments, the same policy, and the same reviewers.

You will complete five small pieces of **lab.py**, which add up to 43 lines of code. The lab takes about 45 minutes, and this guide gives you every line. At the end, Claude proposes an outcome for each of the twelve payments, and your controls decide what actually happens.

This lab continues Demo 3D, so you will recognize the following:

- The twelve labelled supplier payments (PAY-1001 to PAY-1012), the policy file, and the three scripted reviewers.
- The policy gate, where the model's proposal can only add doubt and can never remove a hard flag.
- The pause, review, and resume cycle, and the idempotent payment that moves money once.
- The Agent SDK hook that blocks the release tool, and the six hook scenarios from Stage 5.

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

    > **Note**: The checker fails on purpose. Part A tests your five TODOs with no API key and no model. Part B is skipped until you run the real model.

2. Notice that only two files matter for this lab: **lab.py**, which holds your five TODOs, and **check.py**. The **release_core.py** file is the payment engine from the demo, and you do not need to read it.

3. Notice that the starter code approves every payment and refuses nothing. That is what trusting the model looks like.

## Write the policy gate

The gate decides, in code, whether a payment is released, sent to a human, or rejected. It has three small parts: the flags raised by the evidence, the flags raised by the model's proposal, and the decision rule.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 5 - THE POLICY GATE**. Below it are three functions. Each one has a single placeholder line that ends with `# replace these lines in TODO 1`.

3. In the `payment_flags` function, replace the line `return []  # replace these lines in TODO 1` with the following code. Keep the four-space indent:

    ```python
        flags = []
        if case["invoice"]["bank_last4"] != case["bank_history"]["on_file_last4"]:
            flags.append("BANK_MISMATCH")
        if case["payment"]["amount"] > case["approver"]["limit"]:
            flags.append("OVER_APPROVER_LIMIT")
        if case["payment"]["amount"] >= policy.cfg["amount_dual_control"]:
            flags.append("HV_DUAL_CONTROL")
        return flags
    ```

4. In the `proposal_flags` function, replace the line `return []  # replace these lines in TODO 1` with the following code:

    ```python
        if proposal is None:
            return ["NO_MODEL_PROPOSAL"]
        if proposal.get("decision") == "reject":
            return ["MODEL_RECOMMENDS_REJECT"]
        return []
    ```

5. In the `decide` function, replace the line `return "auto-release"  # replace these lines in TODO 1` with the following code:

    ```python
        if reject_flags:
            return "reject"
        if hard_flags or score >= escalate_at:
            return "escalate"
        return "auto-release"
    ```

6. Save the file, and then run `python check.py`.

7. Verify that the six lines under **TODO 1** show `[PASS]`.

8. Review the gate, noting the following details:

    - A hard flag always forces a human. The model's confidence can never remove it.
    - If the model gave nothing usable, a human decides. Silence is never a yes.
    - If the model says reject, a human decides. The model does not get to reject silently.
    - A reject flag, such as a duplicate invoice, wins over everything else. Otherwise any hard flag, or a risk score at the limit, escalates. Only a payment with no flags and a low score is released.

## Write the human review checks

When the gate pauses a payment, a human reviewer decides. A real approval process refuses some decisions, and so should yours.

1. In **lab.py**, search for the comment **TODO 2 of 5 - THE HUMAN REVIEW**. Below it is the function `decision_problem(case, decision, reviewer)`, and its only line is `return None  # replace these lines in TODO 2`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        if decision["reviewer"] == case["payment"]["requested_by"]:
            return "reviewer cannot review a payment they requested (four-eyes)"
        if reviewer["limit"] < case["payment"]["amount"]:
            return f"reviewer limit {reviewer['limit']:,.0f} < amount {case['payment']['amount']:,.0f}"
        if decision.get("evidence_digest") != core.digest(case):
            return "stale decision: the evidence changed since the reviewer saw it; re-review required"
        if decision.get("decision") not in ("approve", "reject") or not decision.get("reason", "").strip():
            return "decision must be approve or reject, with a non-empty reason"
        return None
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six lines under **TODO 2** show `[PASS]`.

5. Review the checks, noting the following details:

    - Four-eyes: nobody approves a payment they requested.
    - Limit: a reviewer cannot approve more than their own limit.
    - Stale evidence: the reviewer's decision is bound to the evidence digest they saw. If the evidence changed, the decision is refused.
    - Valid decision: the answer must be approve or reject, and it must come with a reason.

    > **Note**: The function returns a message when a decision must be refused, and `None` when it is fine. The engine turns the message into a refusal.

## Write the payment key

If the process dies right after the bank pays, a retry must not pay again. The bank remembers an idempotency key, and the same key twice moves money once.

1. In **lab.py**, search for the comment **TODO 3 of 5 - THE PAYMENT KEY**. Below it is the function `payment_key(case_id, digest)`, and its only line is `return None  # replace this line in TODO 3`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        return f"{case_id}:{digest}"
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the two lines under **TODO 3** show `[PASS]`.

    > **Note**: The key is the same for the same case and the same evidence, and it changes if the evidence changes. Returning `None` means no key, which is the version that pays twice after a crash.

## Write the release hook

An Agent SDK agent calls a `release_payment` tool. A PreToolUse hook runs before the tool and can block it. The prompt may say "only release approved payments", but the hook is what makes it true.

1. In **lab.py**, search for the comment **TODO 4 of 5 - THE RELEASE HOOK**. Below it is the function `make_before_release(svc)`, which holds the inner function `before_release`. Its only line is `return {}  # replace these lines in TODO 4`.

2. Replace that line with the following code. Keep the eight-space indent, because the code sits inside two functions:

    ```python
            try:
                allowed, why = svc.authorisation(input_data["tool_input"]["case_id"])
            except Exception as exc:  # a broken guard must refuse, not shrug
                allowed, why = False, f"guard error ({type(exc).__name__}): refusing"
            if allowed:
                return {}
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": f"Release refused: {why}"}}
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six lines under **TODO 4** show `[PASS]`.

5. Review the hook, noting the following details:

    - The hook asks the workflow whether money may move for this case right now. The answer comes from the case's state, not from the agent.
    - Returning `{}` allows the tool call. Returning a `deny` decision blocks it before it runs, and the reason is passed back to the agent.
    - The hook fails closed. If the guard itself errors, or the tool input is malformed, it refuses.

## Write your Claude API call

In this section, you write the one model call in the lab: the agent's proposal for a single payment.

1. In **lab.py**, search for the comment **TODO 5 of 5**. Below it is the function `ask(text)`, and its only line is `raise NotImplementedError("TODO 5 is not done yet")  # replace this line in TODO 5`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        response = get_client().messages.create(
            model=MODEL_BALANCED,
            max_tokens=4096,
            system=core.PROPOSAL_SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        return text_of(response)
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the one line under **TODO 5** shows `[PASS]`.

5. Review the call, noting the following details:

    - `get_client()` returns the Anthropic client. It reads your key from the **.env** file (see **claude_client.py**).
    - `.messages.create(...)` sends your request to Claude.
    - `model` chooses which Claude model answers.
    - `max_tokens` limits the length of the answer. The API requires it.
    - `system` tells the model to reply with a JSON proposal.
    - `messages` holds the evidence for one payment, as JSON.
    - `text_of(response)` pulls the answer text out of the response.

## Run the real model through your controls

1. Ask Claude for a proposal on each of the twelve payments, and run them through your gate, review, payment, and audit controls, by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run makes about twelve short calls to Claude, and uses a small amount of API credit.

2. Verify that the output ends with a summary line similar to the following. The counts of payments can differ with the model:

    ```
    gate correct 12/12 | unsafe auto-releases 0 | payments 6 for 6 executed cases | audit chain intact: True

    Saved to results/run.json. Now run: python check.py
    ```

    > **Tip**: Read the proposals printed above the summary. Notice how confident the model is on payments that your gate escalates. The gate does not care.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 26/26 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Try breaking it (optional)

After you reach 26/26, change one thing at a time, run `python check.py`, and then undo the change.

1. Make `proposal_flags` return an empty list for `None`. Which line fails, and what does a missing model answer then mean?

2. Make `payment_key` return `None`. Which line fails, and what does a crash after payment now cost?

3. Remove the `except` branch from the hook so that a malformed input raises an error. Which line fails, and why must a guard fail closed?

4. Make `decide` return `"auto-release"` when the score is high but there are no hard flags. Which lines fail?

## Troubleshooting

- **ANTHROPIC_API_KEY is missing**: The **.env** file is not in the lab folder, or it has a typo. Repeat the steps in *Set up the lab folder*.

- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces, and the code inside the hook is indented eight spaces.

- **A TODO line still fails after pasting**: The old placeholder line is still in the file, or you pasted only part of the snippet. Delete the placeholder line named in the step, and paste the whole snippet.

- **NotImplementedError: TODO 5 is not done yet**: The `ask` function still has the placeholder line. Repeat the steps in *Write your Claude API call*.

- **Part B says you edited lab.py after the last run**: Run `python lab.py` again.

- **Part B says fewer than eleven proposals were usable**: The model's replies were not valid JSON. Run `python lab.py` once more.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder.
