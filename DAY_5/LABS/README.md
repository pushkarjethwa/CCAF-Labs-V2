---
lab:
    title: 'Day 5 Labs: Memory, Guardrails and Evals'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Day 5 labs

These labs follow the Day 5 morning demos. Each lab repeats the method of the trainer's demo on a new scenario, so if you watched the demo, you will recognize the steps. In every lab you write four small pieces of **lab.py**, and the lab guide gives you every line. Real Claude runs inside each lab.

If you are new to conversation state, memory files, safeguards in code or evals, run the optional intro demo, [DEMO_5_0_intro_to_memory_safeguards_evals](DEMO_5_0_intro_to_memory_safeguards_evals/README.md), before Lab 5.1. It takes about 40 minutes and has no lab. Run `python check_offline.py`, then `python intro_5_0.py --part 1` ... `5`.

If you want the whole map of guardrails before the labs, run [DEMO_5D_guardrails_across_the_agent_stack](DEMO_5D_guardrails_across_the_agent_stack/README.md). An orchestrator and two subagents handle support tickets, and each stage adds one layer: the prompt, the tools, the MCP server, the agent gate and the audit log. It takes about 40 minutes and has no matching lab yet. Keep its one-page reference card, **GUARDRAILS_BY_LAYER.md**, next to you. The recommended order is 5.0, 5D, 5E, 5A, 5B, 5C. Run `python check_offline.py`, then `python guardrails_stack.py --stage 1` ... `5`.

If you want to see what the Claude Agent SDK handles for memory and context, run [DEMO_5E_pip_with_the_agent_sdk](DEMO_5E_pip_with_the_agent_sdk/README.md). It runs the coffee-shop assistant Pip from Demo 5.0 on the SDK, and you chat with it by typing each message: the SDK keeps the conversation and reads a `CLAUDE.md` of standing rules, and you still own one memory file for each customer card, the token limit with its compaction, and the tier rules. A guest, a member and a gold customer get different tools. It takes about 20 minutes and has no matching lab. Run `python check_offline.py`, then `python pip_agent_sdk.py`.

To complete these exercises you need Python 3.10 or later and an Anthropic API key. Setup is in **DAY_0_SETUP_GUIDE.md**.

| Lab | Pairs with demo | Time | What you build | How to run |
|---|---|---|---|---|
| [Intro demo 5.0, memory, safeguards and evals](DEMO_5_0_intro_to_memory_safeguards_evals/README.md) | Optional warm-up, no lab | 40 min | Nothing to write: follow the README on a coffee-shop assistant | `python check_offline.py`, then `python intro_5_0.py --part 1` ... `5` |
| [Demo 5D, guardrails across the agent stack](DEMO_5D_guardrails_across_the_agent_stack/README.md) | Optional map of the guardrail layers, no lab yet | 40 min | Nothing to write: follow the README on a support desk with an orchestrator and two subagents | `python check_offline.py`, then `python guardrails_stack.py --stage 1` ... `5` |
| [Demo 5E, Chat with Pip on the Claude Agent SDK](DEMO_5E_pip_with_the_agent_sdk/README.md) | Optional, shows what the SDK handles, no matching lab | 20 min | Nothing to write: chat with the coffee-shop assistant, built with the Agent SDK | `python check_offline.py`, then `python pip_agent_sdk.py` |
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
