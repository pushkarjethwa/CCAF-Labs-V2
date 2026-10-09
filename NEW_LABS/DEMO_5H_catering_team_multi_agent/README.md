---
lab:
    title: 'Demo 5H: A multi-agent team with isolated context, shared memory and guardrails'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Demo 5H: A multi-agent team with isolated context, shared memory and guardrails

Brew & Bean, a small coffee shop, has three catering requests for the week. A catering manager (the orchestrator) delegates to three specialist subagents: a stock checker, a pricer and a scheduler. Think of a restaurant kitchen brigade. The head chef hands each cook a ticket with only what that cook needs, and takes back a short note. The cooks never see each other's tickets. You run one command, the whole week runs to completion, and then you inspect what happened. This guide is for you to follow along on your own machine, in about 30 minutes.

## What you will see

1. **Context isolation**: Each subagent starts fresh and receives only a short brief. You see every brief and its size, the raw data the subagent read in its own context, and the short result that came back. At the end you see the manager's context compared with one agent that holds everything.
2. **Shared memory**: The manager owns `results/week_ledger.json`. Subagents cannot write it. Code writes it, after a reply passed its schema check. `--resume` continues from it.
3. **Guardrails in code**: Each agent has its own tool list. One `PreToolUse` gate uses the agent identity and one table, `data/policy.json`. Replies are checked against a schema. Argument limits apply. An order above $300 goes to an approval queue, and no slot is reserved for it. An audit log records every decision.

## Files in this folder

- **catering_team.py**: The run, about 290 lines. It is the only file that uses the SDK.
- **team_policy.py**: The gate, the argument limits, the schema check. No SDK.
- **ledger.py**: The ledger, the approval queue and the transcript archive. No SDK.
- **catering_tools.py**: What each tool does, including the idempotent `reserve_slot`. No SDK.
- **audit_log.py**: One JSON line per tool decision. No SDK.
- **context_sizes.py**: Token estimates and the size comparison. No SDK.
- **data/**: Author-written fixtures (`requests.json`, `stock.json`, `prices.json`, `calendar.json`) and the one table, `policy.json`.
- **results/**: Written by the demo. It starts empty.
- **check_offline.py**: A self-check that needs no key.

## Prerequisites

- Python 3.10 or later: `python --version`.
- The Agent SDK: `pip install claude-agent-sdk==0.2.163`. It bundles the Claude Code CLI.
- `ANTHROPIC_API_KEY` set in your terminal, or in a **.env** file in this folder or a parent folder. The self-check, `--show-ledger` and `--approve` need neither.

## Step 1. Check the files

```
python check_offline.py
```

**What it does**: It runs the whole team against a scripted fake SDK and prints PASS and FAIL lines.

**Why we run it here**: It shows the code and the data are intact before you use a key. The last line should be `ALL OK`. It does not prove the real models behave the same way.

## Step 2. Run the week

```
python catering_team.py
```

**What it does**: It starts a new week. The manager receives the three requests and delegates to the subagents. For each delegation it prints the brief, the raw data the subagent read, the short result and the manager's running context. Then it prints the plan and a size comparison.

**Why we run it here**: It is the demo. Look for these:

1. **The brief**: A line such as `brief to stock_checker (25 tokens): ...`. It holds a request id and a list of items, and nothing else.
2. **The short result**: Only a small JSON comes back. The raw data stayed in the subagent's context.
3. **The gate lines**: Each tool call prints the agent name, such as `[pricer] get_price(...) -> ALLOW`.
4. **The one DENY**: For R-3 the scheduler asks to reserve a slot, and the gate refuses because the order is above $300 and waits for a person.
5. **The plan**: R-1 and R-2 are planned with slots. R-3 is `waiting_approval`.

The model words its replies differently every time. The slots, totals and statuses are decided by code and the data, so they should match this table:

| Request | Order | Total | Result |
|---|---|---|---|
| R-1 | 40 drip coffee, 20 croissants, Tue 09:00 | $164.00 | Planned, slot 09:30 |
| R-2 | 25 lattes, 25 muffins, Wed 14:00 | $162.50 | Planned, slot 14:30 |
| R-3 | 150 drip coffee, 80 croissants, Fri 08:00 | $567.90 | Waiting for a person, no slot |

## Step 3. Inspect the memory and the log

```
python catering_team.py --show-ledger
```

**What it does**: It prints the plan, the ledger file, the approval queue and the bookings. It needs no key.

**Why we run it here**: It shows the manager's memory as a file. Find `handoffs` (the checked notes), `decisions`, `slots_reserved` and `pending_approvals`.

```
type results\audit_log.jsonl
```

On macOS or Linux: `cat results/audit_log.jsonl`.

**What it does**: It prints one JSON line per decision.

**Why we run it here**: It shows the agent name, the tool, a short argument summary and the decision. No brief and no secret is written.

## Step 4. Resume, then approve

```
python catering_team.py --resume
```

**What it does**: It reopens the ledger and runs the manager only on requests that are not finished.

**Why we run it here**: R-1 and R-2 are finished and R-3 waits for a person, so nothing runs. It shows that the memory survives a restart.

```
python catering_team.py --approve R-3
```

**What it does**: You act as the person. Code reserves the slot the scheduler proposed and marks R-3 planned. No model is called.

**Why we run it here**: It closes the approval loop. The booking is made by code after the decision.

## Step 5. Try a change

1. Open `data/policy.json` and change `approval_limit_usd` to `700`. Run `python catering_team.py` again. R-3 is no longer above the limit, so the scheduler reserves its slot.
2. Change `max_quantity_per_line` to `100`. Run again. The gate denies the 150-cup lines, and you see the reason in the gate lines.
3. Change the value back when you are done.

**What it does**: Both limits are read from one table by the gate and the ledger.

**Why we run it here**: It shows the rules are code and data, so changing a number changes behavior everywhere at once.

## What is saved where

| What | Where |
|---|---|
| The ledger | `results/week_ledger.json` |
| The approval queue | `results/approval_queue.json` |
| The bookings | `results/reservations.json` |
| The audit log | `results/audit_log.jsonl` |
| Archived transcripts | `results/transcripts/` (only if the SDK compacts a long context) |

A run without `--resume` clears the first four files and starts a new week.

## Verified and not verified

**Verified offline** (`python check_offline.py`, with a scripted fake SDK): the briefs and short results, the gate and its use of the agent identity, the hand-off schema, the ledger written by code, `--resume`, the approval queue, the idempotent booking, the argument limits, the audit log, `--show-ledger`, `--approve` and the `PreCompact` archive. The replies in the fake are author-written. They are not model results.

**Not verified**: Nothing in this demo has been run live. Check these on your SDK version: that `agent_type` is in the `PreToolUse` input for calls inside a subagent, the shape of `tool_response` in the `PostToolUse` hook, that `AgentDefinition` accepts a full model id and `maxTurns`, and that the models keep their briefs short.

## More information

- Demo 5E shows memory and compaction in one conversation. Demo 5D shows guardrails across an agent stack. Demo 3G shows a research team with a coordinator.
