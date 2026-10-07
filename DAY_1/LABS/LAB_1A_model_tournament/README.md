---
lab:
    title: 'Choose a Claude Model for 100,000 Invoices'
    module: 'Day 1 - Prompt Engineering and Structured Output'
---

# Choose a Claude Model for 100,000 Invoices

In Demo 1A, you watched Larkspur Components try to label every inbound invoice **low**, **medium**, **high**, or **hold** before any money moves. The company has 100,000 invoices to label, and an old rules engine that gets half of the test invoices wrong. In the demo, you ran the same invoices through three Claude models, and found that the answer to "which model?" is usually a design, not the biggest model. In this lab, you run the same stages yourself, and you write three small pieces along the way.

You will complete three pieces of **lab.py**, which add up to 23 lines of code. The lab takes about 30 minutes, and this guide gives you every line. At the end, you have a measured recommendation for 100,000 invoices.

This lab continues Demo 1A, so you will recognize the following:

- The company (Larkspur Components), the 24 labelled invoices, and the four risk labels. This lab uses 8 of the 24 so that it runs quickly.
- The three model tiers: fast (Haiku class), balanced (Sonnet class), and premium (Opus class).
- The stages from the demo: one hard invoice in plain text, the strict answer format, the tournament, and cheap-first routing.
- The hard invoice **inv_017**, where the bank account on the invoice has changed.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_1/LABS/LAB_1A_model_tournament** folder.

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

## Look at the invoices before using any model

1. Run stage 0 by running the following command:

    ```
    python lab.py --stage 0
    ```

    > **Note**: Stage 0 makes no Claude call, so it is free.

2. Review the output, noting the following details:

    - The invoice text that a model is shown for **inv_017**. The model never sees the right answer.
    - How many invoices the old rules engine gets right, and how many of the **hold** invoices it catches.
    - The price table, which shows what each model costs for 100,000 invoices at about 650 tokens in and 140 tokens out per invoice.

3. Run the checker to see your starting point:

    ```
    python check.py
    ```

    > **Note**: The checker fails on purpose, because the starter code contains placeholders. Only the checks on the given data pass.

## Ask the three models in plain text

In this section, you write your first Claude API call. It sends one invoice to a model and returns the answer.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 3**. Below it is a function named `ask_plain` that currently stops with `NotImplementedError`.

3. Replace the line `raise NotImplementedError("TODO 1: write the Claude call")  # replace these lines in TODO 1` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        return get_client().messages.create(
            model=model,
            max_tokens=2000,
            system=plain_system(policy),
            messages=[{"role": "user", "content": case.view}],
        )
    ```

    Noting the following details:

    - `get_client().messages.create(...)` is the Claude Messages API call. Every Claude app sends a request like this one.
    - `system` holds the instructions, which include the four labels and what each means. `messages` holds the invoice text, as the user's turn.
    - `model` is passed in, so the same function can talk to all three models.
    - `max_tokens` is required, and it is generous because Claude may use some of it to think before answering.

4. Save the file, and then run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

5. Review the output, noting the following details:

    - Each model's answer to **inv_017**, with its tokens, speed, and cost.
    - The table at the end, which shows the label that a naive script would read from each answer. A model may say "hold" while the script reads a different word, because free text is not a contract.

## Ask for an answer your code can read

In this section, you change the call so that Claude must answer in a fixed JSON format.

1. In **lab.py**, search for the comment **TODO 2 of 3**. Below it is a function named `ask_structured`.

2. Replace the line `raise NotImplementedError("TODO 2: write the Claude call with output_config")  # replace these lines in TODO 2` with the following code. Keep the four-space indent:

    ```python
        return get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=structured_system(policy),
            messages=[{"role": "user", "content": case.view}],
            output_config={"format": OUTPUT_FORMAT},
        )
    ```

    Noting the following details:

    - The call is the same as in TODO 1, with one new argument: `output_config={"format": OUTPUT_FORMAT}`. `OUTPUT_FORMAT` is a JSON schema that allows only the four labels, a list of reasons, and a confidence number.
    - `structured_system` asks for a label, one to four short reasons that cite facts, and a confidence between 0 and 1.

3. Save the file, and then run stage 2 by running the following command:

    ```
    python lab.py --stage 2
    ```

4. Review the output, noting the following details:

    - Part A shows each model's label, confidence, and whether the answer passed the structure check and the meaning check. A script can now route on `label` and `confidence`.
    - Part B shows requests that the API rejects on purpose, such as sending `temperature`. These cost no tokens. They show what your models accept today.

## Run the tournament

There is no code to write in this section. The tournament runs all three models over eight invoices, using the two calls you wrote.

1. Run stage 3 by running the following command:

    ```
    python lab.py --stage 3
    ```

    > **Note**: This calls Claude 24 times and takes a few minutes. Read the **PREDICT** line first, and make your own guess before the tables print.

2. Review the tables, noting the following details:

    - Table 1 shows how many invoices each model got right and how many of the **hold** invoices it caught. A missed **hold** is paid out, so the hold recall matters more than the accuracy.
    - Table 2 shows the cost of 100,000 invoices on each model.
    - The final lines show what the extra money bought. With only eight invoices, one invoice is not evidence.

## Route cheap-first

In this section, you write the rule that decides when the cheap model's answer is not trusted. A router sends every invoice to the fast model first, and asks a stronger model only when your rule says so.

1. In **lab.py**, search for the comment **TODO 3 of 3**. Below it is a block that starts with `MIN_CONFIDENCE = 0.0`.

2. Replace the whole block, from the line `MIN_CONFIDENCE = 0.0` to the line `return []  # replace these lines in TODO 3`, with the following code. Keep the indentation exactly as shown:

    ```python
    MIN_CONFIDENCE = 0.75
    HIGH_VALUE_USD = 10_000


    def escalation_reasons(first, amount_usd):
        reasons = []
        if not first.verdict.usable:
            reasons.append("unusable_output")
        elif first.verdict.confidence < MIN_CONFIDENCE:
            reasons.append("low_confidence")
        if abs(amount_usd) >= HIGH_VALUE_USD:
            reasons.append("high_value")
        return reasons
    ```

    Noting the following details:

    - An empty list means that the fast model's answer stands. Any reason sends the invoice to the balanced model.
    - `abs(amount_usd)` makes a credit note of -15,000 count as high value, the same as an invoice of 15,000.

3. Save the file, and then run stage 4 by running the following command:

    ```
    python lab.py --stage 4
    ```

4. Review the output, noting the following details:

    - The table lists the invoices that the router escalated, with the reason. Every invoice of 10,000 or more is in it.
    - The **BLIND SPOT** line tells you whether the fast model was wrong with high confidence on any invoice. Confidence alone would have let those through.
    - Part B compares the strategies and ends in a **RECOMMENDATION**: the cheapest option that meets the risk rule of catching every **hold**.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 31/31 checks passed`.

## Troubleshooting

- **`ANTHROPIC_API_KEY is missing`**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the line to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **`model not found`**: A model name is retired. Set `CLAUDE_MODEL_FAST`, `CLAUDE_MODEL_BALANCED`, or `CLAUDE_MODEL_PREMIUM` to a current model, and run again.
- **A connection error on one call**: Run the stage again. Network errors are not part of the lab.
- **Your tournament numbers differ from a classmate's**: This is normal. Models give different answers between runs, and eight invoices is a small sample.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private.

## More information

- Demo 1A ran the same stages on all 24 invoices, with an effort sweep and a hardened router that survives a model outage. To use all 24 invoices here, add `--all-cases` to stages 0, 3 and 4.
- The next lab, Lab 1B, takes a one-line prompt through several versions and measures each change.
