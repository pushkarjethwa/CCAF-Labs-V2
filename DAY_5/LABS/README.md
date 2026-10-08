---
lab:
    title: 'Day 5 Labs: Memory, Guardrails and Evals'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Day 5 labs

These labs follow the Day 5 morning demos. Each lab repeats the method of the trainer's demo on a new scenario, so if you watched the demo, you will recognize the steps. In every lab you write four small pieces of **lab.py**, and the lab guide gives you every line. Real Claude runs inside each lab.

If you are new to conversation state, memory files, safeguards in code or evals, run the optional intro demo, [DEMO_5_0_intro_to_memory_safeguards_evals](DEMO_5_0_intro_to_memory_safeguards_evals/README.md), before Lab 5.1. It takes about 40 minutes and has no lab. Run `python check_offline.py`, then `python intro_5_0.py --part 1` ... `5`.

To complete these exercises you need Python 3.10 or later and an Anthropic API key. Setup is in **DAY_0_SETUP_GUIDE.md**.

| Lab | Pairs with demo | Time | What you build | How to run |
|---|---|---|---|---|
| [Intro demo 5.0, memory, safeguards and evals](DEMO_5_0_intro_to_memory_safeguards_evals/README.md) | Optional warm-up, no lab | 40 min | Nothing to write: follow the run sheet on a coffee-shop assistant | `python check_offline.py`, then `python intro_5_0.py --part 1` ... `5` |
| [5.1 Build the Memory Layer for a Hotel Reservations Agent](LAB_5_1_support_memory/README.md) | 5A, Memory that survives | 40 min | Save facts, load only the ones a request needs, compact the history with the hard rule pinned, and check that the rule survived (15 lines) | `python lab.py history`, `save`, `load`, `compact` |
| [5.2 Build Guardrails in Code for a Refund Agent](LAB_5_2_refund_guardrails/README.md) | 5B, Safeguards around an agent | 30 min | A fallback lookup, quoted customer text, an approval check and a human queue (about 21 lines) | `python lab.py` |
| [5.3 Grade, Trace and Gate an Invoice Checker](LAB_5_3_invoice_evals/README.md) | 5C, Evals and provenance | 45 min | A grader, a source check, a release gate and a review queue (23 lines) | `python lab.py --stage 1` ... `4` |

In every lab, run `python check.py` as you go. Part A tests your functions with hand-made inputs and needs no key. Part B checks the results of your real run. The last line shows `RESULT: n/n checks passed`.

## Set up each lab folder

Do these steps once per lab folder:

1. Open a terminal in the lab folder, for example **STUDENT_V2/DAY_5/LABS/LAB_5_1_support_memory**.

2. Install the packages:

    ```
    pip install -r requirements.txt
    ```

3. Provide your API key. Either set the `ANTHROPIC_API_KEY` environment variable, or create a file named **.env** in the lab folder with this line:

    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```

    > **Important**: Never paste your key into chat or commit the **.env** file to git.

4. Test your key:

    ```
    python claude_client.py
    ```

    You should see a short greeting followed by a line that starts with `[usage]`.

5. Run `python check.py`. The first time, it reports `[FAIL]` lines because your TODOs are not written yet. That is expected.

## Optional extra: Lab 5.4, Context management

If you finish early, do **Lab 5.4** in `STUDENT_V2/NEW_LABS`: [LAB_5_4_context_management](../../NEW_LABS/LAB_5_4_context_management/README.md). An ops assistant reads 10 long incident reports in one conversation, and you write the step that shrinks old turns without losing the facts you need later. It takes about 40 minutes and needs an API key. It continues the idea of Lab 5.1: decide what to keep before you compact.

## After the labs

The Day 5 capstone pack is planned separately. Your trainer will share it when it is ready.
