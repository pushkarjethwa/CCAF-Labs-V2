---
lab:
    title: 'Make the Payroll Agent Fail Safely'
    module: 'Day 2 - Tool Design and MCP'
---

# Make the payroll agent fail safely

In Demo 2B, you watched a refund assistant crash on its first tool failure, retry a refund that had already been booked, and receive HTTP 400 for a malformed `tool_result`. The team fixed it in layers: typed errors, a bounded retry owned by the harness, an escalation for errors that no retry can fix, and a check before every request. In this lab, you do the same for a payroll adjustment agent.

You will complete five pieces of **lab.py**, which add up to about 50 lines of code. The lab takes about 30 minutes, and this guide gives you every line. At the end, six payroll tickets run through the agent, a transient database lock is retried and recovered, a lock that never clears stops after a budget, and an adjustment above the approval threshold becomes a request for a human, with no retry.

This lab continues Demo 2B, so you will recognize the following:

- The method: run the loop, read what the model was shown, and judge the run by the database calls and the ledger, not by the model's words.
- The fix order: first make the error readable (typed), then make the retry safe (bounded), then stop retrying what cannot be fixed (escalate), then check every request before it leaves (preflight).
- The tool_result contract: every `tool_use` id is answered once, in the next user message, with the results first.

The payroll agent has three tools: `lookup_employee`, `check_pay_period` and `apply_adjustment`. A mock payroll database sits behind them, with a simulated clock, so waiting costs nothing. Six tickets cover the cases that matter: a happy path, a closed pay period, a typo in an employee id, an amount above the approval threshold, a database lock that recovers, and a lock that never clears.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_2/LABS/LAB_2_3_payroll_typed_errors** folder.

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

## Run the raw loop

In this section, you run the six tickets through the loop as it is before any fix. This needs no code from you.

1. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

2. Review the output, noting the following details:

    - The model is shown a bare string such as `Error: Pay period 2026-08 is closed`. There is no category, no retryable flag and no hint.
    - The harness treats every error as transient. It retries a closed period, a mistyped employee id and an approval requirement up to 12 times, and it waits a second between tries.
    - The `db apply` column counts the write attempts that reached the database. The `wait s` column is the simulated waiting. The `runaway` column in the table at the bottom counts the calls that hit the safety cap.

> **Note**: A strong model may still reach the right status on some tickets. Judge the run by the number of database calls and the waiting, which are the cost of the raw loop.

## Make the errors typed

In this section, you describe each error so that the model, and the harness, can tell a closed period from a locked database.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 5**. Below it is the line `ERROR_CATALOG = {}  # replace these lines in TODO 1`.

3. Replace that line with the following code:

    ```python
    ERROR_CATALOG = {
        "PAY_PERIOD_CLOSED": {"category": "tool", "retryable": False, "action": "offer the next open period",
                              "hint": "Period {period} is closed and will not reopen. Do not retry. Tell the requester and offer the next open period, {next_open_period}."},
        "EMPLOYEE_NOT_FOUND": {"category": "input", "retryable": False, "action": "ask the requester to correct the id",
                               "hint": "No such employee. Do not retry the same id. Ask the requester to confirm the employee id."},
        "HR_APPROVAL_REQUIRED": {"category": "permission", "retryable": False, "action": "escalate to an HR manager",
                                 "hint": "This amount needs HR_MANAGER approval. Do not retry or split the amount. An approval request was filed; report its id and stop."},
        "PAYROLL_DB_LOCKED": {"category": "environment", "retryable": True, "action": "retry with backoff",
                              "hint": "The ledger is temporarily locked. Retrying the same call with the same idempotency_key is safe."},
        "UNEXPECTED_ERROR": {"category": "tool", "retryable": False, "action": "stop and report",
                             "hint": "Unexpected failure. Do not retry. Report the problem to the requester and stop."},
    }
    ```

    Noting the following details:

    - The category says who can fix the problem: the tool, the input, the permission or the environment.
    - Only the lock is retryable. A closed period stays closed, so a retry is wasted work.
    - The hint tells the model what to do, and `{next_open_period}` is filled from the error's details.
    - `UNEXPECTED_ERROR` is the fail-closed fallback for any code that you did not plan for.

4. Search for the comment **TODO 2 of 5**. Below it is a function named `to_tool_result`.

5. Replace the line `raise NotImplementedError("TODO 2: build the structured tool_result")  # replace these lines in TODO 2` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        entry = ERROR_CATALOG.get(exc.code, ERROR_CATALOG["UNEXPECTED_ERROR"])
        details = {**exc.details, **(extra or {})}
        return json.dumps({
            "error_code": exc.code,
            "category": entry["category"],
            "retryable": entry["retryable"] if retryable is None else retryable,
            "message": exc.message,
            "hint": hint if hint is not None else entry["hint"].format_map(defaultdict(str, details)),
            "details": details,
        }, sort_keys=True)
    ```

    Noting the following details:

    - The model receives one JSON object that it can branch on, instead of a sentence.
    - `format_map` with a `defaultdict` means that a placeholder with no value becomes an empty string instead of a crash.
    - `retryable` and `hint` can be overridden. The harness uses that in the next section, when a retry budget runs out.

6. Save the file, and then run stage 2:

    ```
    python lab.py --stage 2
    ```

7. Review the output, noting the following details:

    - The block under the table shows what the model saw on S2, now a JSON error with a hint.
    - The harness makes one attempt per call, so the `db apply` and `wait s` columns fall sharply. The model decides alone whether to retry the lock, so S5 and S6 depend on how well it follows `retryable`.
    - The progress table now has two rows. The first is the raw loop.

## Bound the retries

In this section, you move the retry decision from the model to the harness. A model has no clock and no count. The harness has both.

1. Search for the comment **TODO 3 of 5**. Below it is the line `RETRY_POLICY = {}  # replace this line in TODO 3`.

2. Replace that line with the following code:

    ```python
    RETRY_POLICY = {"PAYROLL_DB_LOCKED": RetryPolicy(max_attempts=4, base_delay_s=1.0, factor=2.0, max_delay_s=8.0)}
    ```

    Noting the following details:

    - Only the lock is retried: 4 attempts in total, and a wait of 1 second, then 2, then 4. No wait is longer than 8 seconds.
    - Every other code uses `DEFAULT_POLICY`, which is one attempt.

3. A few lines below, in the function `policy_for`, replace the line `raise NotImplementedError("TODO 3: look the code up in RETRY_POLICY")  # replace this line in TODO 3` with the following code. Keep the four-space indent:

    ```python
        return RETRY_POLICY.get(code, DEFAULT_POLICY)
    ```

    Noting the following details:

    - An unknown error code gets the default policy, so it **fails closed**: one attempt, no retry.

4. Save the file, and then run stage 3:

    ```
    python lab.py --stage 3
    ```

5. Review the output, noting the following details:

    - S5 (the lock that clears after two failures) now succeeds on the third attempt, and the wait grows between the tries.
    - S6 (the lock that never clears) stops after four attempts. The model is told `retries_exhausted`, `retryable` false, and to stop.
    - If the model repeats a call that already failed for good, the harness answers it without touching the database, and marks it `repeat_blocked`.

> **Note**: The retry is safe here because `apply_adjustment` carries an idempotency key, and the same key never writes two rows. Without the key, the same retry would pay twice, which is the duplicate refund of Demo 2B.

## Escalate what no retry can fix

In this section, you hand a human a complete request when an adjustment is above the approval threshold.

1. Search for the comment **TODO 4 of 5**. Below it is a function named `build_approval_request`.

2. Replace the line `raise NotImplementedError("TODO 4: build the approval request")  # replace these lines in TODO 4` with the following code. Keep the four-space indent:

    ```python
        return {
            "type": "hr_approval_request",
            "request_id": "HRA-" + args["idempotency_key"],
            "status": "PENDING",
            "error_code": exc.code,
            "required_role": exc.details.get("required_role"),
            "employee_id": args["employee_id"],
            "period": args["period"],
            "amount_cents": args["amount_cents"],
            "currency": "USD",
            "threshold_cents": exc.details.get("threshold_cents"),
            "reason": args["reason"],
            "requested_by": "payroll-agent",
            "original_call": {"tool": tool_name, "idempotency_key": args["idempotency_key"]},
        }
    ```

    Noting the following details:

    - The request id is built from the idempotency key, so asking twice files one request.
    - The request is complete enough that the approver needs nothing else: who, how much, why, which role, and which call to replay once it is approved.

3. Save the file, and then run stage 4:

    ```
    python lab.py --stage 4
    ```

4. Review the output, noting the following details:

    - S4 (the 12,500 dollar adjustment) makes one database call, and the `escal` column shows one approval request.
    - The model is told the request id and to stop. It cannot split the amount or retry its way around the rule.

## Check every request before it is sent

In this section, you write the check that Demo 2B added last. A tool_result mistake costs a failed request, so you refuse the mistake locally.

1. Search for the comment **TODO 5 of 5**. Below it is a function named `preflight`.

2. Replace the line `raise NotImplementedError("TODO 5: check the tool_use and tool_result ids")  # replace these lines in TODO 5` with the following code. Keep the four-space indent:

    ```python
        problems = []
        for i, message in enumerate(messages):
            if message["role"] != "assistant":
                continue
            asked = [b["id"] for b in message["content"] if isinstance(b, dict) and b.get("type") == "tool_use"] if isinstance(message["content"], list) else []
            reply = messages[i + 1]["content"] if i + 1 < len(messages) and isinstance(messages[i + 1]["content"], list) else []
            answered = [b.get("tool_use_id") for b in reply if b.get("type") == "tool_result"]
            if sorted(asked) != sorted(answered):
                problems.append(f"message {i}: tool_use ids {asked} but tool_result ids {answered}")
            if answered and reply[0].get("type") != "tool_result":
                problems.append(f"message {i + 1}: tool_result blocks must come first")
        return problems
    ```

    Noting the following details:

    - The function returns a list of problems, and an empty list means the conversation is fine.
    - One comparison catches three of the four mistakes: an orphan result (nothing was asked), a wrong id, and a missing result for a parallel call. The second check catches text placed before a result.

3. Save the file, and then run stage 5:

    ```
    python lab.py --stage 5
    ```

4. Review the output, noting the following details:

    - The first table replays four broken conversations and one correct one through your preflight. Each broken one should be caught, with no API call.
    - The agent loop now calls your preflight before every request, so a malformed message stops locally with a clear reason.
    - The last line is the gate: at least 5 of the 6 tickets right, no runaway retries, and a correct preflight table.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 33/33 checks passed`.

> **Note**: Part A of the checker tests your code with hand-made failures and needs no key. Part B reads the stages you ran with Claude, and it reports model variance as `[info]` lines, not failures.

## Troubleshooting

- **`ANTHROPIC_API_KEY` is missing**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the piece to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **`NotImplementedError` when you run a stage**: The TODO for that stage is not done yet. Stage 1 needs none.
- **Stage 3 shows no retries**: `RETRY_POLICY` still holds the starter line.
- **S6 ends as `failed` instead of `failed_transient`**: This is the model's wording. Read the `details` the model saw. If `retries_exhausted` is there, your code is right.
- **A connection error on one call**: Run the stage again.
- **Your numbers differ from a classmate's**: This is normal. Models answer differently between runs. The database calls and the waiting are the stable evidence.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private.

## More information

- Demo 2B used a refund assistant, injected a timeout that happens after the refund is booked, and fixed it with an idempotency key. The old version of this lab, with nine open edits, is archived.
- The next lab, Lab 2.2, is about the loop itself: reading in parallel, and writing in order.
