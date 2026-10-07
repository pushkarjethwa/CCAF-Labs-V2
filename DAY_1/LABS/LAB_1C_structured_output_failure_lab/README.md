---
lab:
    title: 'Catch Records That Are Valid but Wrong'
    module: 'Day 1 - Prompt Engineering and Structured Output'
---

# Catch Records That Are Valid but Wrong

In Demo 1C, you watched an accounts-payable team send supplier invoices through Claude with a JSON schema. Every record passed the schema, and some of them were still wrong about money. The team then added defences one at a time: business rules, a single corrective retry that made one record worse, a grounding check that compares every number with the document, a bounded retry loop, and a human review queue. After each defence, the demo printed how many wrong records still reached the ledger. In this lab, you run the same stages yourself, and you write four small pieces along the way.

You will complete four pieces of **lab.py**, which add up to 29 lines of code. The lab takes about 35 minutes, and this guide gives you every line. At the end, you have a validate-and-retry loop that accepts a record only when its numbers are printed in the document, and sends everything else to a human.

This lab continues Demo 1C, so you will recognize the following:

- The Larkspur supplier invoices: an itemised Acme invoice, a lump-sum Acme invoice (**inv_002**, the demo's failure), a Northwind invoice with sales tax, a German invoice with decimal commas, a Lantern invoice in yuan, an invoice with three lines that must add up, an invoice with an illegible tax line (**inv_009**), and an invoice with 12 line items (**inv_010**). The lab uses 8 of the 11 invoices.
- The recorded bad outputs: four records that the demo saved. Each one is valid against the schema.
- The five stages, in the same order as the demo.
- The ledger, where a posted row is the point of no return because payments are scheduled from it.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_1/LABS/LAB_1C_structured_output_failure_lab** folder.

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

In this section, you write the Claude API call. Every stage sends an invoice to Claude through this function, and asks for structured output, which means that the reply must match a JSON schema.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4**. Below it is a function named `ask_extraction`.

3. Replace the line `raise NotImplementedError("TODO 1: call Claude with the system prompt and the schema")  # replace these lines in TODO 1` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        return get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=core.SYSTEM,
            messages=[{"role": "user", "content": user}],
            output_config={"format": core.OUTPUT_FORMAT},
        )
    ```

    Noting the following details:

    - `get_client().messages.create(...)` is the Claude Messages API call.
    - `system` holds the extraction rules. `messages` holds the invoice, as the user's turn. `max_tokens` is the reply limit, and on newer models it also covers hidden thinking tokens.
    - `output_config={"format": core.OUTPUT_FORMAT}` is how the API accepts a JSON schema. The reply is then valid JSON with the required fields. There is no `temperature`, no forced tool, and no prefill, because newer models reject them.

4. Save the file, and then run the checker:

    ```
    python check.py
    ```

5. Verify that the five **TODO 1** checks pass. The other checks still fail.

## Run stage 1: the schema passes, the business is wrong

1. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

2. Review the output, noting the following details:

    - Part A replays four outputs that the demo recorded, without calling Claude. Every one is valid against the schema, and the table shows which fields disagree with the document.
    - Part B extracts the 8 invoices live and posts every schema-valid record to the ledger. A strong model may get all of them right. The schema is still not what made them right: it checks the shape, not the money.

## Write the arithmetic rule

In this section, you write the first business rule: subtotal plus tax must equal the total. The other rules (tax rate, dates, currency, line items) are already written.

1. In **lab.py**, search for the comment **TODO 2 of 4**. Below it is a function named `arithmetic_issues`.

2. Replace the line `return []  # replace these lines in TODO 2` with the following code. Keep the four-space indent:

    ```python
        expected = core.money(core.D(rec["subtotal"]) + core.D(rec["tax_amount"]))
        if abs(expected - core.D(rec["total"])) > core.TOLERANCE:
            return [core.issue("total", "semantic", f"total {rec['total']} != subtotal {rec['subtotal']} + tax_amount {rec['tax_amount']} = {expected}")]
        return []
    ```

    Noting the following details:

    - The function returns a list of issues. An empty list means that the record adds up.
    - `core.TOLERANCE` is two cents, which lets a rounded amount pass.
    - The message says what the total should be, because the retry in stage 3 sends this message back to the model.

3. Save the file, run the checker, and then run stage 2:

    ```
    python check.py
    python lab.py --stage 2
    ```

4. Review the output, noting the following details:

    - The rules catch the recorded wrong total, which is the original error on **inv_002**.
    - The rules miss the other three recorded outputs, including the **silent subtotal edit** and the **locale misparse**. Both are perfectly consistent, and both are wrong.

## Run stage 3: one corrective retry

1. Run stage 3 by running the following command:

    ```
    python lab.py --stage 3
    ```

2. Review the output, noting the following details:

    - A record that fails a rule is sent back to the model once, with the original request, the invalid output, and the failures. A record that then passes every rule is accepted.
    - The replay at the end shows the failure that matters. Told that the total did not match, a model can make the arithmetic pass by rewriting the subtotal and the tax instead of fixing the total. Every rule is green, and the ledger holds a wrong record.
    - A live model often repairs **inv_002** correctly, especially because the correction prompt says that printed figures are authoritative. To see the weaker prompt that many teams write first, run `python lab.py --stage 3 --prompt naive`.

## Write the grounding check

In this section, you write the check that stops the failure in stage 3. The rules check that the numbers agree with each other. Grounding checks that the numbers agree with the document: every number in the record must be printed in the invoice.

1. In **lab.py**, search for the comment **TODO 3 of 4**. Below it is a function named `grounding_issues`.

2. Replace the line `return []  # replace these lines in TODO 3` with the following code. Keep the four-space indent:

    ```python
        printed = core.extract_numbers(source_text)
        issues = []
        for path, value in core.numeric_fields(rec):
            if not any(abs(value - number) <= core.TOL for number in printed):
                issues.append(core.issue(path, "grounding", f"{path}={value} is not printed anywhere in the document; do not change printed figures to make totals balance"))
        return issues
    ```

    Noting the following details:

    - `core.extract_numbers` reads every number that is printed in the invoice, including `1.000,00` in European format.
    - A number that is not printed, such as a subtotal of 109.32 that the model computed, becomes an issue.
    - Grounding is a tripwire, not proof. It cannot check dates or text, and it can be fooled when a wrong number happens to appear in the document.

3. Save the file, and then run the checker:

    ```
    python check.py
    ```

## Write the retry policy

In this section, you write the decision that follows every model response. Retrying is a decision, not a reflex: a refusal must not be retried, a truncated reply needs more room, and an invoice that contradicts itself must go to a human.

1. In **lab.py**, search for the comment **TODO 4 of 4**. Below it is a function named `decide`.

2. Replace the line `return core.ACCEPT, "TODO 4 not written yet"  # replace these lines in TODO 4` with the following code. Keep the four-space indent:

    ```python
        attempts_left = attempt < max_attempts
        if status == "refusal":
            return core.REVIEW, "refusal: not retried"
        if status == "truncated":
            if attempts_left and max_tokens < max_tokens_cap:
                return core.RETRY_LARGER, "stop_reason=max_tokens: retry with larger max_tokens"
            return core.REVIEW, "truncated and cannot retry"
        if not issues:
            return core.ACCEPT, "all validators passed"
        if attempts_left:
            return core.RETRY_CORRECT, f"{len(issues)} issue(s): retry with a correction prompt"
        return core.REVIEW, f"exhausted {max_attempts} attempts with {len(issues)} open issue(s)"
    ```

    Noting the following details:

    - The function branches on what happened (`status`) before it looks at the issues. A refusal and a truncated reply have no usable content.
    - A truncated reply is retried with a bigger `max_tokens`, because a correction prompt cannot fix a reply that was cut off.
    - When attempts run out, the decision is `REVIEW`. The loop never edits a record. It accepts the model's output unchanged, or it refuses it.

3. Save the file, run the checker, and then run stage 4:

    ```
    python check.py
    python lab.py --stage 4
    ```

    > **Note**: Stage 4 starts every invoice with `max_tokens` of 400, which is too small for the 12-line invoice on purpose.

4. Review the output, noting the following details:

    - Part A shows that grounding catches all four recorded outputs, including the two that every rule accepted.
    - **inv_010** is truncated on its first attempt and retried with a larger limit.
    - **inv_009** has an illegible tax line and a handwritten total written over a printed one. No retry can fix a document that contradicts itself, so it ends in review.
    - The last line counts silent corruptions: accepted records that disagree with the document. With grounding, it should be 0.

## Run stage 5: review queue, metrics, and a cheaper first pass

1. Run stage 5 by running the following command:

    ```
    python lab.py --stage 5
    ```

    > **Note**: This runs the whole set twice, so it calls Claude about 30 times.

2. Review the output, noting the following details:

    - Each document that the loop gives up on goes to a review queue, and the ledger gets a parked row that payment runs ignore. Dropping the record and posting the last attempt are the two wrong answers.
    - The three numbers that tell you whether the design is healthy: the retry rate, the fallback rate (the human workload you are buying), and the cost per accepted record.
    - The second configuration tries the fast model twice and escalates to the balanced model. Compare its cost per accepted record and its fallback rate with the first configuration. Cheaper is only better if the silent corruptions stay at 0.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 41/41 checks passed`. The exact count may differ if you did not run every stage.

## Troubleshooting

- **`ANTHROPIC_API_KEY` is missing**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the line to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **`NotImplementedError` when you run a stage**: TODO 1 is not done yet.
- **Stage 4 accepts everything in one attempt**: TODO 3 or TODO 4 still holds the starter lines.
- **A connection error on one call**: Run the stage again.
- **Your numbers differ from a classmate's**: This is normal. Models give different answers between runs, and the live parts of stages 1 to 3 depend on whether the model makes a mistake that day. The recorded outputs always give the same result.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private.

## More information

- Demo 1C ran all 11 invoices. To use them here, add `--all-docs` to a stage.
- The next lab, Lab 1D, is about the cost of running a pipeline like this one: prompt caching, token counting, and batch processing.
