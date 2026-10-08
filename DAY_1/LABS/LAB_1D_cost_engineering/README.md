---
lab:
    title: 'Cut the Cost of a Policy Check Without Breaking It'
    module: 'Day 1 - Prompt Engineering and Structured Output'
---

# Cut the cost of a policy check without breaking it

In Demo 1D, you watched an accounts-payable team check supplier invoices against a 6,000-token procurement policy. The policy is the same on every request, so about 95 percent of every request is the same text, billed at full price 100,000 times a month. The team then applied three cost levers: counting tokens before sending, caching the policy, and batching the work. Each lever has a silent way to fail, and the demo showed all of them: an oversized scan that costs more than the whole day's budget, an audit stamp that makes the cache useless without any error, and a batch whose results come back in a different order. In this lab, you run the same stages yourself, and you write four small pieces along the way.

You will complete four pieces of **lab.py**, which add up to 19 lines of code. The lab takes about 40 minutes, and this guide gives you every line. At the end, you have a checker that caches its policy, refuses oversized requests, and joins batch results safely.

This lab continues Demo 1D, so you will recognize the following:

- The Group Accounts Payable policy checker: a verdict for each invoice (compliant or not, with the clauses it violates), checked against ground truth.
- The 30 invoices and the 25,000-character procurement policy. The lab uses 10 of the 30 invoices so that it runs quickly and cheaply.
- The fast model (Claude Haiku 5.5, which needs a prefix of at least 512 tokens before it caches anything) and the balanced model.
- The projection to 100,000 invoices a month, and the cost table that compares normal, cached, batch, and batch plus cache.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_1/LABS/LAB_1D_cost_engineering** folder.

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

## Write the call that every stage uses

In this section, you write the Claude API call. Every stage sends a complete request to Claude through this function.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4**. Below it is a function named `ask_checker`.

3. Replace the line `raise NotImplementedError("TODO 1: send the request to Claude")  # replace these lines in TODO 1` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        return get_client().messages.create(
            model=request["model"],
            max_tokens=request["max_tokens"],
            system=request["system"],
            messages=request["messages"],
            output_config=request["output_config"],
        )
    ```

    Noting the following details:

    - `get_client().messages.create(...)` is the Claude Messages API call.
    - The `request` is already complete. It holds the model, the `max_tokens` limit, the `system` blocks (the instructions and the policy), the `messages` (the invoice), and the `output_config` (the JSON schema for the verdict).
    - The `system` value is a list of blocks instead of a string. That is what lets you mark a block for caching in a later section.

4. Save the file, and then run the checker:

    ```
    python check.py
    ```

5. Verify that the four **TODO 1** checks pass. The other checks still fail.

## Run stage 1: meter the baseline

1. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

2. Review the output, noting the following details:

    - Each row is one request. The columns are the uncached input tokens, the tokens written to the cache, the tokens read from the cache, the output tokens, and the cost. Cache columns are 0 because nothing is cached yet.
    - The policy is about 95 percent of every request, and every request pays full price for it.
    - The projection at the end multiplies the measured average by 100,000 invoices a month. Note the difference between the fast and the balanced model.

## Write the token counter

In this section, you write the call that counts the tokens of a request without running it. A gate in front of every send can then refuse a request that is too big, before it costs anything.

1. In **lab.py**, search for the comment **TODO 2 of 4**. Below it is a function named `count_request_tokens`.

2. Replace the line `raise NotImplementedError("TODO 2: count the tokens")  # replace these lines in TODO 2` with the following code. Keep the four-space indent:

    ```python
        counted = get_client().messages.count_tokens(
            model=request["model"],
            system=request["system"],
            messages=request["messages"],
        )
        return counted.input_tokens
    ```

    Noting the following details:

    - `count_tokens` is free, and it does not use caching. It is rate-limited separately from message creation, and it returns an estimate.
    - It accepts the model, the system blocks and the messages. It does not accept `max_tokens`, so you must not pass it.

3. Save the file, run the checker, and then run stage 2:

    ```
    python check.py
    python lab.py --stage 2
    ```

4. Review the output, noting the following details:

    - A normal request is several thousand tokens, and the policy is most of it.
    - The ceiling is set 20 percent above the largest normal request. The gate allows a normal invoice and refuses a 60-page OCR dump, which would have been sent to the model at full price.

## Write the cache breakpoint

In this section, you write the code that marks the policy for prompt caching. The cache stores everything up to a marked block, so the second request pays one tenth of the normal price for it.

1. In **lab.py**, search for the comment **TODO 3 of 4**. Below it is a function named `system_blocks`.

2. Replace the line `return [{"type": "text", "text": text}]  # replace these lines in TODO 3` with the following code. Keep the four-space indent:

    ```python
        block = {"type": "text", "text": text}
        if cache:
            block["cache_control"] = {"type": "ephemeral", **({"ttl": ttl} if ttl else {})}
        return [block]
    ```

    Noting the following details:

    - `cache_control={"type": "ephemeral"}` marks the end of the part of the prompt that can be cached. Everything before it must be byte-for-byte identical in the next request.
    - The optional `ttl` of `"1h"` keeps the entry for an hour, instead of the default five minutes. A one-hour write costs twice the normal price, and a five-minute write costs 1.25 times.
    - There is no error if caching does not work. You can only see it in the cache columns of the usage.

3. Save the file, run the checker, and then run stage 3:

    ```
    python check.py
    python lab.py --stage 3
    ```

4. Review the output, noting the following details:

    - **A**: The first request writes the cache. Every later request reads it, and its cost falls by about 90 percent for the policy part.
    - **B**: The audit stamp, which holds a request id and a timestamp, is added to the top of the system prompt. Caching is still switched on, and there is no error, but the cache reads stay 0. Every call pays the write surcharge, so the bill is higher than with no caching at all.
    - **C**: The prefix comparison finds the first differing line, and it names the request id and the timestamp as the volatile content.
    - **D**: The same stamp moves into the user turn, after the cache breakpoint. The prefix is the same on every request, and the reads come back.

## Write the batch code

In this section, you write two small functions for the Message Batches API. A batch is half the price, and it can take up to 24 hours, so it suits work that can wait. Its results come back in any order.

1. In **lab.py**, search for the comment **TODO 4 of 4**. Below it are two functions.

2. Replace the line `return []  # replace these lines in TODO 4 (first function)` with the following code. Keep the four-space indent:

    ```python
        return [{"custom_id": invoice_id, "params": request} for invoice_id, request in zip(invoice_ids, requests)]
    ```

3. Replace the line `return {}  # replace these lines in TODO 4 (second function)` with the following code. Keep the four-space indent:

    ```python
        return {entry.custom_id: entry for entry in entries}
    ```

    Noting the following details:

    - A batch is a list of requests. Each one has a `custom_id` and the `params` that you would send to `messages.create`.
    - The `custom_id` is the only safe way to match a result to its invoice. The results do not come back in the order you submitted them.

4. Save the file, run the checker, and then run stage 4:

    ```
    python check.py
    python lab.py --stage 4
    ```

    > **Note**: A batch usually finishes in a few minutes, but the API allows up to 24 hours. The stage waits up to 10 minutes. If the batch has not ended, the stage prints a batch id. Run `python lab.py --stage 4 --collect <the batch id>` later to continue.

5. Review the output, noting the following details:

    - Whether the results arrived in the order that you submitted them. Do not rely on it.
    - The positional join pairs several invoices with another invoice's verdict. It raises no exception, and ten results for ten invoices look perfect.
    - The join on `custom_id`, with the checks for missing results and for an `invoice_id` that does not match the `custom_id`, passes.
    - The cost table for the same invoices: normal, cached, and batch plus cache. A batch is a flat 50 percent discount, and its caching is best-effort. Below the break-even hit rate, caching costs more than not caching.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 32/32 checks passed`. The exact count may differ if you did not run every stage.

## Troubleshooting

- **`ANTHROPIC_API_KEY` is missing**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the line to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **`NotImplementedError` when you run a stage**: TODO 1 or TODO 2 is not done yet.
- **`count_tokens() got an unexpected keyword argument 'max_tokens'`**: Remove `max_tokens` from the counting call.
- **The cache reads are 0 in stage 3 A**: TODO 3 still holds the starter line, or the fast model's prefix is under 512 tokens. Check that you did not use the short policy.
- **A connection error on one call**: Run the stage again.
- **Your cost numbers differ from a classmate's**: This is normal. Token counts and prices depend on the model version, and a batch's cache hits are best-effort.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Cache entries expire by themselves after five minutes (or one hour for the batch). Keep your **.env** file private.

## More information

- Demo 1D ran all 30 invoices, and it added the second silent no-cache: a prefix below the model's minimum, which the API ignores without any error. To use all 30 invoices here, add `--all-docs` to a stage.
- Day 2 moves from single requests to tool use: Claude choosing and calling your functions.
