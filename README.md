# CCA-F Student Labs (self-contained edition)

Hands-on labs for the **Claude Certified Architect - Foundations (CCA-F)** course. Each lab is one folder you can open, read top to bottom and run. There is no shared code folder to hunt through: the code that creates the Anthropic client, reads your API key and sends a message lives in a file called `claude_client.py` inside every lab.

New to the Anthropic SDK? Read [HOW_THE_CODE_WORKS.md](HOW_THE_CODE_WORKS.md) first (5 minutes). Machine not set up yet? Follow [DAY_0_SETUP_GUIDE.md](DAY_0_SETUP_GUIDE.md) (about 45 minutes, before Day 1).

## Where to find the labs and the trainer-demo versions

Everything is in `NEW_LABS/` (new labs and the run-it-yourself versions of the trainer's demos) and in `DAY_1/LABS`, `DAY_2/LABS`. The demo versions let you re-run what the trainer showed:

| Trainer demo | Your version | What you run |
|---|---|---|
| Day 1, Demo 1A: Model behavior tournament | [Lab 1A](DAY_1/LABS/LAB_1A_model_tournament) | `python lab.py --stage 0` ... `4` |
| Day 1, Demo 1B: Prompt evolution workshop | [Lab 1B](DAY_1/LABS/LAB_1B_prompt_evolution) | `python lab.py --stage 0` ... `5`, `gate` |
| Day 1, Demo 1C: Structured-output failure lab | [Lab 1C](DAY_1/LABS/LAB_1C_structured_output_failure_lab) | `python lab.py --stage 1` ... `5` |
| Day 1, Demo 1D: Cost engineering | [Lab 1D](DAY_1/LABS/LAB_1D_cost_engineering) | `python lab.py --stage 1` ... `4` |
| Day 2, Demo 2.0: Intro to tool use | [Lab 2.0](NEW_LABS/LAB_2_0_intro_to_tool_use) | `python lab.py --step 1` ... `3` |

The Day 3 demos (3A to 3G) are the trainer's, in `TRAINER_V2/DAY_3/DEMOS`. If your trainer shares that folder you can re-run any of them: see [Day 3 demos](#day-3-demos-what-the-trainer-shows) below.

## About the course

A five-day course that prepares you for the CCA-F exam by building, breaking and measuring small systems on the Claude API. The exam domains and their weight:

| Day | Topic | Exam domain | Weight |
|---|---|---|---|
| 1 | Prompt engineering and structured output | D4 | 20% |
| 2 | Tool design and MCP integration | D2 | 18% |
| 3 | Agentic architecture and orchestration | D1 | 27% |
| 4 | Claude Code configuration and workflows | D3 | 20% |
| 5 | Context management and reliability, plus capstone | D5 | 15% |

How the days run: the trainer shows a short demo, you do a lab, and at the end of the day there is a review. The full timetable is in the course schedule (`02_MASTER_5_DAY_SCHEDULE.md` in the course folder).

## How every lab works

Each lab folder looks like this:

| File | What it is for |
|---|---|
| `README.md` | The story, what you build, how to run, time and cost |
| `lab.py` | The file you edit. Numbered steps; your tasks are marked `TODO 1`, `TODO 2`, ... |
| `claude_client.py` | The only file that talks to Claude (key, client, `messages.create`). Read it once |
| `data/` (Day 3: `data.json`) | The lab's input files |
| `check.py` | Run it any time. Prints `[PASS]`/`[FAIL]` and `RESULT: n/m`. **Part A** tests your code without an API key. **Part B** checks the evidence from a real run |
| `BREAK_IT.md` | Deliberate failures to try after the lab passes: this is where the exam-style lessons are |
| `CHALLENGE.md` | Optional stretch goals |

The loop for every lab: read the README, edit `lab.py`, run `python check.py` until Part A is green, run `python lab.py` (this calls the real Claude), run `python check.py` again, then try `BREAK_IT.md`. The starter fails its checks on purpose.

## Lab list

### Day 0 / warm-up

| Lab | What it is about | Time | Key |
|---|---|---|---|
| [0.1 Hello Claude](NEW_LABS/LAB_0_1_hello_claude) | The Messages API from scratch: one call, a follow-up, `max_tokens` cut-off, a deliberate error, cost. Also proves your setup works | 20 min | yes |

### Day 1: Prompt engineering and structured output (D4)

| Lab | What it is about | Time |
|---|---|---|
| [1A Model tournament](DAY_1/LABS/LAB_1A_model_tournament) | Run Demo 1A's stages on invoices: three model classes, structured output, an escalation rule. You write 23 lines | 30 min |
| [1B Prompt evolution](DAY_1/LABS/LAB_1B_prompt_evolution) | Run Demo 1B's prompt versions v0 to v6 on invoices, add a schema, and write the regression gate. You write 12 lines | 35 min |
| [1C Structured-output failure lab](DAY_1/LABS/LAB_1C_structured_output_failure_lab) | Valid JSON that is wrong about money: business rules, grounding, a bounded retry loop and a review queue. You write 29 lines | 35 min |
| [1D Cost engineering](DAY_1/LABS/LAB_1D_cost_engineering) | Token counting, prompt caching (and how it breaks silently) and batch processing. You write 19 lines | 40 min |
| [1.5 Prompt caching (new)](NEW_LABS/LAB_1_5_prompt_caching) | Mark a long prefix as cacheable, read cache hits, see what breaks the cache | 30 min |

### Day 2: Tool design and MCP (D2)

| Lab | What it is about | Time | Key needed |
|---|---|---|---|
| [2.0 Intro to tool use (new)](NEW_LABS/LAB_2_0_intro_to_tool_use) | Run-and-read walkthrough: why tools, how to create one, the full tool round trip. Do it before 2.1 | 20-25 min | lab.py |
| [2.1 Facilities tool boundaries](DAY_2/LABS/LAB_2_1_facilities_tool_boundaries) | Follows Demo 2A: descriptions, consolidation, pruning, per-desk scoping and a gate; five stages | 35 min | `lab.py --stage 1` ... `5`, `gate` |
| [2.2 Travel disruption tool loop](DAY_2/LABS/LAB_2_2_travel_disruption_tool_loop) | Follows Demo 2C: concurrent reads, ordered writes, a safe retry, an iteration guard | 35 min | `lab.py --stage 1` ... `5` |
| [2.3 Payroll typed errors](DAY_2/LABS/LAB_2_3_payroll_typed_errors) | Follows Demo 2B: typed errors, bounded retries, escalation, preflight | 30 min | `lab.py --stage 1` ... `5` |
| [2.4 Procurement MCP server](DAY_2/LABS/LAB_2_4_procurement_mcp_server) | Follows Demo 2D: stderr logging, resources, validated tools, config linter, authentication (401 vs 403), redaction | 40 min | `lab.py --stage 1` ... `6` (no key) |
| [2.5 Build a tool and its loop (new)](NEW_LABS/LAB_2_5_build_a_tool_and_loop) | Write a tool schema, dispatcher and loop from the raw SDK | 45 min | lab.py |
| [2.6 Use an MCP server (new)](NEW_LABS/LAB_2_6_use_an_mcp_server) | Be the MCP client: connect to a server and let Claude use its tools | 45 min | lab.py |

### Day 3: Agentic architecture and orchestration (D1)

Four labs, all built the same way. In each one you write **a few small decisions** (12 to 57 lines), not plumbing. Everything else is already written and marked "do not edit". A real Claude model runs inside each lab.

| Lab | The story | What you decide (you write) | Real Claude does | Time |
|---|---|---|---|---|
| [3.1 Expense desk: review claims two ways](DAY_3/LABS/LAB_3_1_expense_desk_architecture/README.md) | ACME Finance (Demo 3A). Vote on the five briefs, then review six claims as a conversation and as a workflow | The rubric and two Claude calls (26 lines) | Both reviews | 25 min |
| [3.2 Research desk: hand-offs](DAY_3/LABS/LAB_3_2_research_desk_handoffs/README.md) | The research desk (Demo 3B). What a valid hand-off is, what each specialist may see, and what to do when two reliable reports disagree | Contracts, minimal briefs, a conflict rule and one writer call (22 lines) | The writer | 45 min |
| [3.3 Warranty claims: failure recovery](DAY_3/LABS/LAB_3_3_warranty_failure_recovery/README.md) | Warranty intake (Demo 3C). Classify each failure and pick the recovery | Classifier, recovery table, corrective message and one call (26 lines) | The intake agent | 30 min |
| [3.4 Supplier payments: release guard](DAY_3/LABS/LAB_3_4_payment_release_guard/README.md) | Payment release (Demo 3D). The model proposes; code decides and a hook enforces | Gate rules, idempotency key, release hook and one call (43 lines) | The proposal | 40 min |
| [3.5 First agent with the Agent SDK](DAY_3/LABS/LAB_3_5_first_agent_with_agent_sdk/README.md) | Incident INC-7741 (Demo 3E). Configure a read-only agent | Tool specs, system prompt, options and the run (32 lines) | The whole agent | 30 min |
| [3.6 Two ways to build an agent](DAY_3/LABS/LAB_3_6_two_ways_to_build_an_agent/README.md) | The same incident agent (Demo 3F), as a manual loop and with the Tool Runner | Loop pieces and Tool Runner functions (26 lines) | The whole agent | 30 min |
| [3.7 Research desk with subagents](DAY_3/LABS/LAB_3_7_research_desk_with_subagents/README.md) | The research desk again (Demo 3G), built with Agent SDK subagents | Two subagents, a leak guard and options (38 lines) | The coordinator and writer | 40 min |

How a Day 3 lab differs from the labs above:

- **One file to edit.** `lab.py` has numbered sections: your TODOs first, plumbing last (read it only if you are curious). The scenario data is a single `data.json`; there is no `data/` folder.
- **`check.py` Part A needs no key and tests your own functions** with hand-made inputs, so each TODO turns green as you finish it. Part B checks the saved result of the real run.
- **The starter is naive on purpose** (it accepts everything, retries everything, allows everything). Run `python lab.py` once before you change anything and read what goes wrong. Lab 3.4 also has `python lab.py --dry-run` (no key) that shows this.
- **Install the lab's own packages:** `pip install -r requirements.txt` inside the lab folder. Lab 3.4 adds `claude-agent-sdk`. Its optional `live_run.py` needs the Claude Code CLI as well and is not graded.
- The loop is the usual one: edit a TODO, `python check.py`, repeat; then `python lab.py` (real Claude), then `python check.py` again, then `BREAK_IT.md`.
- If a Part B line fails and the message says Claude gave an unexpected answer, run `python lab.py` again. A real model varies a little. If it keeps failing, tell the trainer.

#### Day 3 demos (what the trainer shows)

The Day 3 demos are in the trainer's folder (`TRAINER_V2/DAY_3/DEMOS`). Each demo folder runs on its own, has a README and needs `ANTHROPIC_API_KEY` for its live stages (each stage says whether it needs a key). Pair each demo with the lab in the right-hand column.

| Demo | The idea in one line | Pairs with |
|---|---|---|
| 3A Should this be an agent? | Choose chat, workflow or agent by who controls the next step | Lab 3.1 |
| 3B Monolith to multi-agent | One 12-tool agent becomes a small desk of specialists with checked hand-offs | Lab 3.2 |
| 3C Agent failure lab | Tool, reasoning and environment errors each need a different recovery | Lab 3.3 |
| 3D Human escalation | A human approval is a saved state change, with a policy gate and an audit trail | Lab 3.4 |
| 3E First agent with the Agent SDK | The smallest useful Claude Agent SDK agent (an incident triage) | Before Lab 3.4 |
| 3F Four ways to build an agent | Same task as a manual loop, Tool Runner, Managed Agents and the Agent SDK, and how to deploy each | Lab 3.4, decision matrix |
| 3G Research orchestrator with the Agent SDK | The final multi-agent design with subagents, a safety hook and a scorer | Lab 3.2 |

Demos 3E to 3G use the `claude-agent-sdk` package and the Claude Code CLI; 3A to 3D use only `anthropic`.

### Day 5 (one new lab so far)

| Lab | What it is about | Time |
|---|---|---|
| [5.4 Context management (new)](NEW_LABS/LAB_5_4_context_management) | Shrink old turns in a long run without losing the facts you need later | 40 min |

### Days 4 and 5 (other labs)

Not yet rebuilt in this self-contained format. Until they are, use the original labs in the course folder's `STUDENT/DAY_4` and `DAY_5`.

## Quick start

```
cd STUDENT_V2
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
# set your key (hidden prompt, see DAY_0_SETUP_GUIDE.md section 5), then:
cd NEW_LABS\LAB_0_1_hello_claude
python claude_client.py             # should print a short greeting and a [usage] line
```

## Solutions

Every lab folder has a `SOLUTION/` folder with a `SOLUTION_GUIDE.md` (what the lab teaches, the solution for each TODO with the TODO text, what a passing `check.py` looks like, common mistakes, answers to BREAK_IT) and the complete reference solution file. For the run-it-yourself labs (1A, 1B and 2.0) the guide is an answer key for the PREDICT prompts and the expected shape of the output. Try the lab first. To test a reference solution, copy it over `lab.py` (or `toolset.py`, `security.py` and `server.py` for Labs 2.1 and 2.4) in a scratch copy of the lab folder. Trainers who do not want students to see solutions up front can delete the `SOLUTION/` folders before sharing.

## Cost and safety

Your class key is capped at about USD 50 for the whole course, and each lab README states its cost (most are a few cents, Lab 2.1 under $1). Never put the key in code, chat, screenshots or a git repo. If it leaks, tell the trainer at once.

## Notes

- Models are named `MODEL_FAST`, `MODEL_BALANCED`, `MODEL_PREMIUM` in `claude_client.py`. Override with the environment variables `CLAUDE_MODEL_FAST`, `CLAUDE_MODEL_BALANCED`, `CLAUDE_MODEL_PREMIUM` if a model name is retired.
- These labs have not all been run against the live API yet. If one behaves unexpectedly, tell the trainer which lab and paste the output (never the key).
