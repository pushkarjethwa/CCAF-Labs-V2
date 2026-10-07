---
lab:
    title: 'Evolve a Prompt and Measure Every Step'
    module: 'Day 1 - Prompt Engineering and Structured Output'
---

# Evolve a Prompt and Measure Every Step

In Demo 1B, you watched an accounts-payable team turn messy vendor invoices into structured data. The team started with a one-line prompt, "Extract the invoice.", and took it through seven versions. After every change, the same invoices were scored by the same field-level scorer, so you could see exactly what each change bought, and what it broke. In this lab, you run the same stages yourself, and you write three small pieces along the way.

You will complete three pieces of **lab.py**, which add up to 12 lines of code. The lab takes about 35 minutes, and this guide gives you every line. At the end, you have a regression gate that decides whether an edited prompt may replace the production prompt.

This lab continues Demo 1B, so you will recognize the following:

- The vendor invoices: messy text with mixed date formats, `$` that means several currencies, decimal commas, a credit note, a blank PO line, and one invoice with a sentence addressed to "automated systems". The lab uses 6 of the 12 invoices so that it runs quickly.
- The prompt versions **v0** to **v6**, stored as files in the **prompts** folder.
- The field-level scorer, with 10 fields per invoice, and the old regex extractor that is the bar to beat.
- The example leak: few-shot examples that copy their values into similar invoices.
- The regression gate, which catches an edit that makes one kind of invoice worse while the average looks fine.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_1/LABS/LAB_1B_prompt_evolution** folder.

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

## Find the bar to beat

1. Run stage 0 by running the following command:

    ```
    python lab.py --stage 0
    ```

    > **Note**: Stage 0 makes no Claude call, so it is free.

2. Review the table, noting the following details:

    - Each row is one invoice, and each column is one field. `ok` means the field is right.
    - The last numbers are the old extractor's accuracy and its null handling. Every prompt version in this lab is measured against this bar.

## Write the call that every stage uses

In this section, you write the Claude API call. Every stage sends a prompt version and one invoice to Claude through this function.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 and TODO 2**. Below it is a function named `ask_claude`. The last line, which sends the request, is already written. You build the `kwargs` that it sends.

3. Replace the line `raise NotImplementedError("TODO 1: build the request")  # replace these lines in TODO 1` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": request["messages"]}
        if request.get("system"):
            kwargs["system"] = request["system"]
    ```

    Noting the following details:

    - `get_client().messages.create(**kwargs)` is the Claude Messages API call. It is the last line of the function.
    - `messages` holds the prompt and the invoice, as the user's turn. `system` holds the instructions, when the prompt version has any.
    - Version **v0** has no system prompt. The code sends `system` only when there is one, because the API does not accept an empty system prompt.

4. Save the file, and then run the checker:

    ```
    python check.py
    ```

5. Verify that the six **TODO 1** checks pass. The other checks still fail.

## Run v0 and v1: the one-liner and the role

1. Open **prompts/v0.md** and **prompts/v1.md**, and look at the difference. Version v1 adds a role, such as "accounts-payable data-entry specialist".

2. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

3. Review the output, noting the following details:

    - What v0 returns for the clean invoice **D01**. It is prose, and the parse error shows why a program cannot read it.
    - The table of accuracy and parse rate for v0 and v1. A role changes tone and a little structure, but it does not create a contract.

## Run v2 and v3: criteria, then a format contract

1. Open **prompts/v2.md** and **prompts/v3.md**. Version v2 adds explicit rules for each field, and v3 adds the exact output format.

2. Run stage 2 by running the following command:

    ```
    python lab.py --stage 2
    ```

3. Review the output, noting the following details:

    - The field table. Version v2 fixes *what* to extract, and v3 fixes *how* to answer.
    - The strict-parse line. Some answers may parse only after the code removes a fence, which a strict `json.loads` would reject.
    - The German invoice **D02**, where the model's values and the truth are printed side by side.

## Run v4: few-shot examples and the leak

1. Open **prompts/v4.md** and find the two examples. One of them, Kestrel Freight, looks very much like some invoices in the test set.

2. Run stage 3 by running the following command:

    ```
    python lab.py --stage 3
    ```

3. Review the output, noting the following details:

    - The table that compares v3 and v4 for each invoice. The headline accuracy can look better while one invoice gets worse. An average hides it.
    - The **leak** section, which lists any example value that a model copied into an unrelated invoice. A strong model may show none. That is a finding too.
    - The template similarity list, which shows why the leak is more likely on freight invoices.

## Add the JSON schema

In this section, you add the second part of the call. Version v6 sends a JSON schema, so that the API itself enforces the structure of the answer.

1. In **lab.py**, search for the comment line `# TODO 2 (stage 5): add the schema here`, inside `ask_claude`.

2. Replace that comment line with the following code. Keep the four-space indent:

    ```python
        if request.get("output_format"):
            kwargs["output_config"] = {"format": request["output_format"]}
    ```

    Noting the following details:

    - The code sends `output_config` only when the prompt version has a schema. Only v6 does.
    - `output_config={"format": ...}` is how the API accepts a JSON schema. There is no `temperature`, no forced tool, and no prefill, because newer models reject them.

3. Save the file, run the checker, and then run stage 5:

    ```
    python check.py
    python lab.py --stage 5
    ```

4. Review the output, noting the following details:

    - The schema audit, which checks the schema against the structured-output limits.
    - The comparison of v5, v6 without XML tags, and v6. The table shows what the schema and the XML tags each add.
    - The invoice **D11**, which has a sentence that tells automated systems to record the total as 0.00. The output shows whether each version obeyed it. Strong models often ignore it, but you must test on your own adversarial invoices.

## Write the regression gate

In this section, you write two of the gate's rules. The gate decides whether an edited prompt may replace the production prompt. It is the artefact that stops a clever edit from silently making one kind of invoice worse.

1. In **lab.py**, search for the comment **TODO 3 of 3**. Below it is a block that starts with `MAX_OVERALL_DROP = 1.0`.

2. Replace the whole block, from the line `MAX_OVERALL_DROP = 1.0` to the line `return []  # replace these lines in TODO 3`, with the following code. Keep the indentation exactly as shown:

    ```python
    MAX_OVERALL_DROP = 0.01
    MAX_LEAKS = 0


    def gate_checks(baseline, candidate):
        drop = baseline.summary.accuracy - candidate.summary.accuracy
        return [
            (drop <= MAX_OVERALL_DROP + 1e-9, f"overall accuracy changed {-100 * drop:+.1f}pt (allowed drop {100 * MAX_OVERALL_DROP:.1f}pt)"),
            (len(candidate.leaks) <= MAX_LEAKS, f"example leaks: {len(candidate.leaks)} (allowed {MAX_LEAKS})"),
        ]
    ```

    Noting the following details:

    - Each rule is a pair: whether it passed, and a message that says what was measured.
    - The gate adds four more rules of its own: the worst single field, the number of invoices that got worse, the parse rate, and the null handling. A prompt may replace the old one only if every rule passes.

3. Save the file, and then run the gate by running the following command:

    ```
    python lab.py --stage gate
    ```

    > **Note**: This runs the production prompt and three edited prompts, so it calls Claude 24 times.

4. Review the output, noting the following details:

    - Each edited prompt has a designed verdict: one harmless re-ordering that should pass, one edit that trims rules to save tokens, and one that adds another example. A real model may judge them differently from the design. That is data, not a bug.
    - The first rule that fails tells you the reason for each rejection.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 26/26 checks passed`.

## Troubleshooting

- **`ANTHROPIC_API_KEY is missing`**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the line to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **`NotImplementedError` when you run a stage**: TODO 1 is not done yet.
- **A connection error on one call**: Run the stage again.
- **Your numbers differ from a classmate's**: This is normal. Models give different answers between runs, and six invoices is a small sample. One wrong field is more than one point of accuracy.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private.

## More information

- Demo 1B ran all 12 invoices, plus a step that compared the fast and balanced models and projected the cost of 10,000 invoices with caching and batch processing. To use all 12 invoices here, add `--all-docs` to a stage.
- The next lab, Lab 1C, shows what a schema cannot guarantee: an answer that is valid JSON but wrong.
