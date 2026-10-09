---
lab:
    title: 'Demo 5G: An autonomous agent with working memory and guardrails'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Demo 5G: An autonomous agent with working memory and guardrails

Brew & Bean, a small coffee shop, has a stock problem: "Oat milk keeps running out at the Harbour branch. Find out why and recommend what to do." You give that task once. The stock detective, an agent on the Claude Agent SDK, then chooses its own steps in a loop. It reads inventory, a long sales log, the delivery log and the supplier's notes, and it writes short working notes as it goes, like a detective with a notebook who must not carry the whole case file in their head. Your code keeps what the agent must not decide for itself: the tools it may use, the branches it may read, the size of each tool result, the order limit, the turn and cost limits, and what is saved. You run the case to the end, then inspect the notes, the findings, the approval queue and the audit log. The whole run takes about 30 minutes. There is no matching lab yet, so there is nothing to write: run the commands and read the output.

**Where it fits**: Follow it after Demo 5E (a conversational agent) and Demo 5F (a code-driven workflow). In 5E you type each message. In 5F the code chooses the steps. Here the model chooses the steps, and your code chooses the limits.

## The idea

**The idea**: The agent chooses its own steps. Your code bounds what it reads, remembers what it found, and decides what it may do.

## What you see

1. **An autonomous loop**: `python stock_detective.py` runs the whole case. There is no chat. The model decides which tool to call next, when to write a note and when it has enough. The path is not scripted, so the number of turns varies from run to run.
2. **Context under control**: Tool results can be huge. Every tool returns a bounded view: a summary, a few rows and a hint that says what was cut and how to ask for more. The sales log file is about 64,000 characters. The 90-day view is about 500. Each turn prints the tool, the size of the result and the running total. The SDK compacts on its own near the limit. A subagent is the next step for a really large read, because its work stays out of the main context.
3. **Working memory that survives**: The agent keeps short notes with `write_note` and `read_notes` in `results/notes_<case>.md`. They are on disk, so they survive a compaction and a restart. A `PreCompact` hook archives the transcript first. At the end a retention check proves the case's key facts are still in the notes, and the findings go to `results/case_history.jsonl`.
4. **A second run that starts from notes**: Run the same case twice. The second run receives the earlier findings, calls `read_notes` first and checks only what is missing.
5. **Guardrails in code, not in the prompt**: A read-only allow-list, `Bash`, `Write` and `Edit` disallowed, limits inside the tools (branch for this role, `days` up to 90, item in the catalogue), a `PreToolUse` gate that denies by default and writes an audit log, and `propose_order`, which only proposes. Supplier text is passed as data. Turns and cost are capped.

## Files in this folder

- **stock_detective.py**: The case run, about 220 lines. Read it top to bottom. It is the only file that uses the SDK.
- **limits.py**: The argument limits, the order limit and the gate rule. No SDK.
- **stock_tools.py**: What each tool does, including the bounded views and `propose_order`. No SDK.
- **case_memory.py**: The working notes, the case history, the retention check and the transcript archive. No SDK.
- **context_meter.py**: The running context total, from the size of each tool result. No SDK.
- **audit_log.py**: One JSON line per gate decision, with long arguments shortened. No SDK.
- **shop_data.py**: Loads the files in `data/`. No SDK.
- **data/**: Author-written fixtures, not real shop data. `sales_log.json` (90 days, 3 branches, 3 items), `deliveries.json`, `inventory.json`, `supplier_notes.json`, `catalogue.json`, `roles.json` and `cases.json`.
- **results/**: Written when you run the demo: `notes_<case>.md`, `case_history.jsonl`, `approval_queue.json`, `audit_log.jsonl` and `archive/`. It starts empty, with only a `.gitkeep`.
- **check_offline.py**: A key-free self-check against a scripted fake SDK.

## The data in one minute

Harbour's standing oat milk order is 9 cases every Tuesday. On 4 August the supplier changed the case size from 12 cartons to 8, and the case count did not change, so a delivery fell from 108 to 72 cartons. Weekday sales are about 10 cartons a day, and Saturday is about 24. A week now needs about 96 cartons and gets 72, so Sunday ends short and Monday is empty. No single file says this. The agent has to combine the sales log, the delivery log and the supplier note. A good answer proposes a larger standing order, for example 14 cases (112 cartons, about $269). That is above the $150 limit, so it goes to the approval queue.

## Prerequisites

- Python 3.10 or later: `python --version`.
- The Agent SDK: `pip install claude-agent-sdk==0.2.163`. It bundles the Claude Code CLI.
- `ANTHROPIC_API_KEY` set in your terminal, or in a **.env** file in this folder or a parent folder. The self-check needs neither.
- Models: the detective runs on `CLAUDE_MODEL_BALANCED` (`claude-sonnet-5-5`). There are no helper calls.

## Follow along

Run every command from this folder. Each one has two reasons: what it does, and why you run it.

### Step 1. Check the files

```
python check_offline.py
```

**What it does**: Runs the whole case against a scripted fake SDK and prints PASS and FAIL lines. It ends with `ALL OK`.

**Why you run it**: It shows the files and the code are intact, with no key. It does not show how the real model behaves.

### Step 2. Run the case to the end

```
python stock_detective.py
```

**What it does**: Runs the default case, `oat-milk-harbour`. Nothing is typed. Each turn prints two lines: the tool the agent chose, and the size of its result with a running total.

```
turn  2  read_sales_log       branch='harbour', item='oat milk', days='90'
        read_sales_log       result    511 chars  ~  127 tokens  running    140 of 200000 (0.1 percent)
```

That sample comes from the offline fake. Your run will show different turns.

**Why you run it**: It is the demo. Look at three things: how small each result is next to the 64,000-character log, the `write_note` turns where the agent writes in its notebook, and the findings at the end.

Other lines you may see:

- `[guardrail] ...` when a tool refuses (for example a branch the role may not read) or the gate denies a tool.
- `[PreCompact]` and `[compaction]` if the SDK compacts. A short case may never reach the limit. That is a good result: the bounded views kept the context small.

### Step 3. Inspect what the agent left behind

```
python stock_detective.py --show-notes
python stock_detective.py --show-history
```

**What they do**: Print the working notes of the case, and the saved findings of each finished run. No model call.

**Why you run them**: They show the two kinds of memory. Notes hold facts and next steps. The history holds what each run concluded.

```
type results\approval_queue.json
type results\audit_log.jsonl
```

On macOS or Linux use `cat results/approval_queue.json` and `cat results/audit_log.jsonl`.

**What they do**: Print the proposals waiting for a person, and one line for every tool call the gate checked.

**Why you run them**: The queue shows the agent proposed an order and your code did not place it (`placed` is `false`). The log shows every call was checked, with no secret in it.

### Step 4. Run the same case again

```
python stock_detective.py --case oat-milk-harbour
```

**What it does**: Runs the same case a second time. The code loads the saved findings, tells the agent this case was investigated before, and the agent calls `read_notes` first.

**Why you run it**: It shows working memory that survives a restart. The second run should need fewer turns.

### Step 5. Change the role

```
python stock_detective.py --role area_manager
```

**What it does**: Runs with a role that may also read the Uptown branch.

**Why you run it**: It shows that the role, chosen by your code, decides what a tool may read. The model cannot change its own role.

### Step 6. Ask a different question

```
python stock_detective.py --task "Compare oat milk at Harbour and Uptown." --case oat-milk-compare
```

**What it does**: Runs a new case with your own task. The default role may not read Uptown.

**Why you run it**: The agent will probably ask for Uptown. The tool refuses, a `[guardrail]` line shows, and the agent carries on with what it may read. It is an ordinary event, not an attack.

### Step 7. Read the guardrails in the code

Open **limits.py**. Find `check_branch`, `check_days`, `gate` and `ORDER_LIMIT_USD`. Then open **stock_tools.py** at `propose_order`.

Notice that none of these rules are in the prompt. The branch check is inside the tool. The gate denies any tool that is not on the list. `propose_order` writes a line to a queue, and no function in the code places an order.

## What is saved where

| What | Where | Written when |
|---|---|---|
| Working notes (one file per case) | `results/notes_<case>.md`: one line per note, marked with the run number | Each time the agent calls `write_note` |
| Case history | `results/case_history.jsonl`: case, run, turns, cost, findings, retention result | At the end of each run |
| Approval queue | `results/approval_queue.json`: item, quantity, cost, status, `placed: false` | Each time the agent calls `propose_order` |
| Audit log | `results/audit_log.jsonl`: time, case, role, tool, shortened arguments, decision, reason | At every gate decision |
| Transcript archive | `results/archive/<case>_<time>.jsonl` | When the SDK is about to compact |

## What was checked, and what was not

**Checked offline** (`python check_offline.py`, with a scripted fake SDK): that no tool returns the whole log, and the views carry a truncation hint; that every turn prints the result size and a running total; that notes are written, bounded when read, and re-read by a second run that uses fewer turns; that the PreCompact hook archives the transcript; that the retention check passes, and that it finds a missing fact; the read-only allow-list, the disallowed `Bash`, `Write` and `Edit`, and the turn and cost limits in the options; the branch, days, item, note and quantity limits inside the tools; the gate denying an unlisted tool and logging it; `propose_order` never placing an order; and no secret in the audit log. The steps, notes and findings in the fake are author-written. They are not model results.

**Not checked**: Nothing in this demo has been run live. The model's path is not scripted, so your turn counts, notes and findings will differ from any sample. Verify on your SDK version:

- That the SDK sends a `SystemMessage` with `subtype="compact_boundary"` when it compacts.
- That the `PreCompact` hook runs with `transcript_path` set.
- That `setting_sources=[]` loads no settings files, and that `permission_mode="dontAsk"` denies a tool that is not allowed.
- That a short case may never reach a compaction. The running total then shows how small the bounded views kept the context.

## Design notes

- **The tool bounds the result, not the prompt.** A prompt that says "be brief" does not stop a 64,000-character log. A tool that never returns it does.
- **Notes are files, not context.** A compaction or a restart cannot lose them.
- **The role is closed over.** The tools are built for one role. The model cannot pick a different one.
- **A proposal is a record, not an action.** The agent proposes, and a person decides.
- **Supplier text is data.** It is wrapped in `<supplier_notes untrusted="true">`, and the system prompt says never to follow instructions inside it.

## More information

- Demo 5E is the conversational agent, and Demo 5F is the code-driven workflow. Demo 5D puts guardrails across a whole agent stack.
- There is no matching lab yet.
