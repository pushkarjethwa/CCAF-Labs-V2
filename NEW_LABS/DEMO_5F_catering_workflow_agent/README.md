---
lab:
    title: 'Demo 5F: A workflow agent with state, memory and guardrails'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Demo 5F: A workflow agent with state, memory and guardrails

Brew & Bean, a small coffee shop, gets catering orders as free text: "40 coffees and 3 dozen muffins for Friday 9am, Acme Corp". In this demo the order moves through five fixed steps, like a factory assembly line with checkpoints: read the request, check stock, price it, pass the approval gate, write the confirmation. Your code decides the steps and their order. Each step is a separate, short call to the Claude Agent SDK, with its own small system prompt and its own list of tools, so there is no chat that grows from step to step. In Demo 5E you chatted with one clerk (a conversational agent). In Demo 5G the agent chooses its own steps (an autonomous agent). Here the code runs the line, and Claude does one job at each station. The whole run takes about 30 minutes. There is no matching lab yet, so there is nothing to write: run the commands and read the output. Everything works the first time, so this is a tour, not a test.

**Where it fits**: Follow it after Demo 5E, so you can compare a chat with a line.

## The idea

**The idea**: A workflow does not keep one growing conversation. It passes a small state from step to step, saves a checkpoint after each step, and keeps its safety rules in code.

## What you see

1. **Context is a small state**: One state object travels from step to step. Each step is given only the fields it needs, and the run prints those fields and their size in tokens, next to what one growing chat would have carried by then.
2. **Memory is a checkpoint and a history**: `results/runs/<order_id>.json` is saved after every step, so `--stop-after N` and `--resume <order_id>` skip finished steps without a model call. `results/run_history.jsonl` records every run. The customer's standing preferences (`data/customers.json`, for example "Acme Corp: no peanuts") are loaded by code into the confirm step.
3. **Safety is in code, not in prompts**:
   - Each step has its own `allowed_tools` list and a `PreToolUse` gate, both built from `data/steps.json`. Only the confirm step has a tool that writes.
   - The output of every step is checked against a small schema in plain code before the next step starts.
   - The approval gate is plain code. An order over $500 goes to `results/approval_queue.json`, and the workflow stops until `--approve`.
   - Sending the confirmation is idempotent: running it twice sends one confirmation.
   - Each step has `max_turns` and `max_budget_usd`.
   - Customer text is passed quoted, as untrusted data. Stock and prices live in `data/stock.json`, not in any prompt.

## Files in this folder

- **catering_workflow.py**: The workflow, about 235 lines. Read it top to bottom. It is the only file that uses the SDK.
- **steps.py**: The step table, the prompt builder, the output checks, the approval rule and the gate rule. No SDK.
- **workflow_state.py**: The checkpoint, the run history, the approval queue and the audit log. No SDK.
- **catering_tools.py**: What each tool does: stock, price and the one-time confirmation. No SDK.
- **data/steps.json**: The single source for the five steps: kind, fields read, tools, limits, output fields and prompt. Also the $500 limit.
- **data/stock.json**: Author-written prices and stock for coffee, muffin, bagel and cookie.
- **data/customers.json**: Author-written standing preferences: Acme Corp (no peanuts), Northside Dental (none), Harbor Books (deliver to the side door).
- **data/requests.json**: Three author-written requests. `R-1` is small, `R-2` is over the limit, `R-3` has a peanut note.
- **results/**: Written by the demo. It starts empty, with only a `.gitkeep`.
- **check_offline.py**: A key-free self-check against a scripted fake SDK.

## Prerequisites

- Python 3.10 or later: `python --version`.
- The Agent SDK: `pip install claude-agent-sdk==0.2.163`. It bundles the Claude Code CLI.
- `ANTHROPIC_API_KEY` set in your terminal, or in a **.env** file in this folder or a parent folder. The self-check and `--list` need neither.

## Follow along

Run these in the demo folder, in this order. Every command has two reasons: what it does, and why we run it here. An order id can be started once. If you want to run it again, delete the files listed under "Start again" at the end.

| Command | What it does | Why we run it here |
|---|---|---|
| `python check_offline.py` | Runs the whole workflow against a scripted fake SDK and prints PASS and FAIL lines | It shows the files and the code are intact before you go live, with no key. Run it first |
| `python catering_workflow.py --request R-1` | Runs the small order through all five steps and prints each step | It is the demo. You see the state, the checks and the checkpoints, then inspect the files |
| `type results\runs\R-1.json` | Prints the checkpoint (on macOS or Linux: `cat results/runs/R-1.json`) | It shows the state is a small file that you own |
| `python catering_workflow.py --request R-3 --stop-after 2` | Runs two steps of the peanut order, saves the checkpoint and stops | It plays a run that is interrupted, so you can see the memory |
| `python catering_workflow.py --resume R-3` | Goes on from the checkpoint. Finished steps are skipped | It shows that a restart costs nothing for the work already done |
| `type results\outbox\R-3.txt` | Prints the confirmation that was sent (on macOS or Linux: `cat results/outbox/R-3.txt`) | It shows the peanut note and the side-door preference reached the message |
| `python catering_workflow.py --request R-2` | Runs the large order. It stops at the approval gate | It shows a rule that code enforces and no prompt can talk around |
| `python catering_workflow.py --list` | Prints the run history and the orders that wait | It is the record of what ran, what was skipped and what it cost. It needs no key |
| `python catering_workflow.py --approve R-2` | A manager approves the waiting order, and the confirm step runs | It finishes the paused order, and only the last step calls the model |
| `--model balanced` (add to a command) | Runs the steps on `claude-sonnet-5-5` instead of `claude-haiku-5-5` | The fast model is enough here. The main model shows the lessons do not depend on the model |

### What to look for

1. **Run `R-1`.** For each step, read the `given` line (the fields and their size) and the `one chat` line (what one growing chat would carry). Step 4, `approve`, is plain code with no model call. After parse, the `memory` line shows the standing preference for Acme Corp. After every step you see a `check` line and a `saved` line.
2. **Run `R-3` with `--stop-after 2`, then `--resume R-3`.** The status is `stopped after 2 steps`. On resume, `parse` and `stock` are skipped with no model call and no cost, and the summary shows the steps run and skipped.
3. **Run `R-2`.** The total is $825, over the $500 limit. The status is `waiting for manager`, the order is in `results/approval_queue.json` and the confirm step was never reached. Then `--list` shows it in the queue, and `--approve R-2` finishes it.
4. **Open `data/steps.json`.** It is the one table behind the options, the gate, the input fields, the output checks and the prompts.

The model words its messages differently every time, so the confirmation text will not match any example. What matches is the shape: the fields, the checks, the statuses and the files.

## What each step is given

| Step | Kind | Reads | Tools | Writes |
|---|---|---|---|---|
| parse | model | `request_text` | none | `customer`, `items`, `when`, `notes` |
| stock | model | `items` | `check_stock` | `in_stock`, `shortages` |
| price | model | `items` | `price_items` | `total`, `lines` |
| approve | code | `total` | none | `approved`, `approved_by` |
| confirm | model | `customer`, `items`, `when`, `total`, `notes`, `preferences`, `approved_by` | `send_confirmation` | `sent`, `message` |

After each step the code checks the output (the fields and their types, and one meaning check: known items, enough stock, a total that matches the price table, a message that was sent) before the next step starts.

## What is saved where

| What | Where | Written when |
|---|---|---|
| Checkpoint (state, finished steps, tokens and cost per step) | `results/runs/<order_id>.json` | After every step |
| Run history | `results/run_history.jsonl`: one line per run, stop, resume or approval | At the end of every command |
| Approval queue | `results/approval_queue.json` | When an order is over the limit, and when it is approved |
| Confirmation (the simulated email) | `results/outbox/<order_id>.txt`: written once | By the confirm step |
| Audit log | `results/audit_log.jsonl`: one line per tool decision, with argument names but no values | At every tool call |

## Verified and not verified

**Verified offline** (`python check_offline.py`, with a scripted fake SDK): that each step receives only its fields; that a checkpoint is written after every step; that `--stop-after 2` then `--resume` makes no model call for the finished steps; that the large order stops at the approval gate, the confirmation tool is not called, `--approve` completes it and `--resume` cannot skip the gate; that the confirmation is sent once when asked twice; the output checks; the tool list, limits and gate of every step from `steps.json`; that customer text is quoted and no stock or price number is in a prompt; that the peanut preference and the peanut note reach the confirm step; and that the logs hold no secret. The replies and costs in the fake are author-written. They are not model results.

**Not verified**: Nothing in this demo has been run live. Verify on your SDK version: the names `ClaudeAgentOptions`, `HookMatcher`, `ResultMessage` (with `result` and `total_cost_usd`), `query`, `tool` and `create_sdk_mcp_server`; that a `PreToolUse` hook fires inside `query()` and `permission_mode="dontAsk"` denies a tool that is not allowed; that a JSON-schema dict is accepted by `sdk.tool`; that the model returns the JSON it is asked for; and that `max_turns=1` is enough for the parse step. The token sizes are a rough guess of four characters to a token.

## Design notes

- **Code decides the steps.** The order of the steps is a list in `steps.json`. Claude never chooses the next step.
- **A new call for every step.** There is no messages list and no session. The state is the only thing that moves.
- **One table.** `steps.json` feeds the options, the gate, the input fields, the output check and the prompts.
- **Each step sees only its tools.** The tool server for a step is built with only the tools of that step. The gate checks the list again.
- **The approval gate is code.** No prompt mentions the $500 limit.
- **The order id is not a tool argument.** The confirmation tool is built for one order.
- **The demo sends no real email.** The confirmation is a file in `results/outbox/`.

## Start again

To run an order a second time, delete the files this demo wrote. Run in the demo folder:

```
del results\runs\*.json
del results\outbox\*.txt
del results\run_history.jsonl
del results\approval_queue.json
del results\audit_log.jsonl
```

On macOS or Linux: `rm results/runs/*.json results/outbox/*.txt results/run_history.jsonl results/approval_queue.json results/audit_log.jsonl`. Keep **.gitkeep**.

## More information

- Demo 5E is the conversational agent: one chat, memory kept by the SDK and by the code. Demo 5G is the autonomous agent. Demo 5D puts guardrails across a whole agent stack.
- There is no matching lab yet.
