# CCA-F Student Labs (self-contained edition)

Hands-on labs for the **Claude Certified Architect - Foundations (CCA-F)** course. Each lab is one folder you can open, read top to bottom and run. There is no shared code folder to hunt through: the code that creates the Anthropic client, reads your API key and sends a message lives in a file called `claude_client.py` inside every lab.

New to the Anthropic SDK? Read [HOW_THE_CODE_WORKS.md](HOW_THE_CODE_WORKS.md) first (5 minutes). Machine not set up yet? Follow [DAY_0_SETUP_GUIDE.md](DAY_0_SETUP_GUIDE.md) (about 45 minutes, before Day 1).

## Where to find the labs and the demos

| Folder | What is in it |
|---|---|
| `NEW_LABS/` | Warm-up and extra labs: 0.1, 1.5, 2.0 and 5.4 |
| `DAY_1/LABS` | Labs 1A to 1D, each one replays a trainer demo |
| `DAY_2/LABS` | Two MCP demos you can run before the labs, and Labs 2.1 to 2.6 |
| `DAY_3/LABS` | Labs 3.1 to 3.7 |
| `DAY_4/LABS` | Labs 4.1 to 4.4, done in Claude Code |
| `STUDY_GUIDE/` | Reading: MCP best practices and MCP security architecture |
| `LAB_Test/` | The runner that tests every lab and packs the results to submit |

Most labs are a replay of what the trainer showed, so the demo and the lab match closely:

| Trainer demo | Your version | What you run |
|---|---|---|
| Day 1, Demo 1A: Model behavior tournament | [Lab 1A](DAY_1/LABS/LAB_1A_model_tournament) | `python lab.py --stage 0` ... `4` |
| Day 1, Demo 1B: Prompt evolution workshop | [Lab 1B](DAY_1/LABS/LAB_1B_prompt_evolution) | `python lab.py --stage 0` ... `5`, `gate` |
| Day 1, Demo 1C: Structured-output lab | [Lab 1C](DAY_1/LABS/LAB_1C_structured_output_failure_lab) | `python lab.py --stage 1` ... `5` |
| Day 1, Demo 1D: Cost engineering | [Lab 1D](DAY_1/LABS/LAB_1D_cost_engineering) | `python lab.py --stage 1` ... `4` |
| Day 2, Demos 2A to 2D | [Labs 2.1 to 2.4](DAY_2/LABS/README.md) | `python lab.py --stage 1` ... |
| Day 3, Demos 3A to 3G | [Labs 3.1 to 3.7](DAY_3/LABS/README.md) | `python lab.py`, then `python check.py` |
| Day 4, Demos 4A to 4D | [Labs 4.1 to 4.4](DAY_4/LABS/README.md) | Claude Code in the lab's `STARTER` folder |

The Day 2 MCP demos `DEMO_2_0_intro_to_mcp` and `DEMO_2_0_mcp_separate_server_and_client` are in `DAY_2/LABS`. Run them before Lab 2.4. The Day 3 and Day 4 demos are the trainer's, in `TRAINER_V2/DAY_3/DEMOS` and `TRAINER_V2/DAY_4/DEMOS`. If your trainer shares those folders you can re-run any of them: see [Day 3 demos](#day-3-demos-what-the-trainer-shows) and [Day 4](#day-4-claude-code-configuration-and-workflows-d3) below.

## About the course

A five-day course that prepares you for the CCA-F exam by building and measuring small systems on the Claude API and in Claude Code. The exam domains and their weight:

| Day | Topic | Exam domain | Weight |
|---|---|---|---|
| 1 | Prompt engineering and structured output | D4 | 20% |
| 2 | Tool design and MCP integration | D2 | 18% |
| 3 | Agentic architecture and orchestration | D1 | 27% |
| 4 | Claude Code configuration and workflows | D3 | 20% |
| 5 | Context management and reliability, plus capstone | D5 | 15% |

How the days run: the trainer shows a short demo, you do a lab, and at the end of the day there is a review. The full timetable is in the course schedule (`02_MASTER_5_DAY_SCHEDULE.md` in the course folder).

## How every lab works

Most labs (Days 0 to 3) look like this:

| File | What it is for |
|---|---|
| `README.md` | The lab guide: the story, numbered steps, the exact code to paste, expected output |
| `lab.py` | The file you edit. Numbered steps; your tasks are marked `TODO 1`, `TODO 2`, ... |
| `claude_client.py` | The only file that talks to Claude (key, client, `messages.create`). Read it once |
| `data/` (Day 3: `data.json`) | The lab's input files |
| `check.py` | Run it any time. Prints `[PASS]`/`[FAIL]` and `RESULT: n/m`. **Part A** tests your code without an API key. **Part B** checks the evidence from a real run |
| `SOLUTION/` | The finished version. Try the lab first |

The loop for every lab: read the README, paste each snippet at its `TODO`, run `python check.py` until Part A is green, run `python lab.py` (this calls the real Claude), then run `python check.py` again.

Day 4 labs are different. You work in Claude Code inside the lab's `STARTER` folder, and `check.py` (no key needed) checks the files you and Claude created.

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

Start with the two MCP demos in `DAY_2/LABS`: [DEMO_2_0_intro_to_mcp](DAY_2/LABS/DEMO_2_0_intro_to_mcp) (a kitchen server and a waiter client in one app) and [DEMO_2_0_mcp_separate_server_and_client](DAY_2/LABS/DEMO_2_0_mcp_separate_server_and_client) (the same idea as two separate apps). They run as they are, with no edits.

| Lab | What it is about | Time | Key needed |
|---|---|---|---|
| [2.0 Intro to tool use (new)](NEW_LABS/LAB_2_0_intro_to_tool_use) | Run-and-read walkthrough: why tools, how to create one, the full tool round trip. Do it before 2.1 | 20-25 min | lab.py |
| [2.1 Facilities tool boundaries](DAY_2/LABS/LAB_2_1_facilities_tool_boundaries) | Follows Demo 2A: descriptions, consolidation, pruning, per-desk scoping and a gate; five stages | 35 min | `lab.py --stage 1` ... `5`, `gate` |
| [2.2 Travel disruption tool loop](DAY_2/LABS/LAB_2_2_travel_disruption_tool_loop) | Follows Demo 2C: concurrent reads, ordered writes, a safe retry, an iteration guard | 35 min | `lab.py --stage 1` ... `5` |
| [2.3 Payroll typed errors](DAY_2/LABS/LAB_2_3_payroll_typed_errors) | Follows Demo 2B: typed errors, bounded retries, escalation, preflight | 30 min | `lab.py --stage 1` ... `5` |
| [2.4 Procurement MCP server](DAY_2/LABS/LAB_2_4_procurement_mcp_server) | Follows Demo 2D: stderr logging, resources, validated tools, config linter, authentication (401 vs 403), redaction | 40 min | `lab.py --stage 1` ... `6` (no key) |
| [2.5 Build a tool and its loop](DAY_2/LABS/LAB_2_5_build_a_tool_and_loop) | Write a tool schema, dispatcher and loop from the raw SDK | 45 min | `lab.py --stage 1` ... `4` |
| [2.6 Use an MCP server](DAY_2/LABS/LAB_2_6_use_an_mcp_server) | Be the MCP client: connect to a server and let Claude use its tools | 45 min | `lab.py --stage 1` ... `4` |

### Day 3: Agentic architecture and orchestration (D1)

Seven labs, all built the same way. In each one you write **a few small decisions** (14 to 32 lines), not plumbing. Everything else is already written and marked "do not edit". A real Claude model runs inside each lab.

| Lab | The story | What you decide (you write) | Real Claude does | Time |
|---|---|---|---|---|
| [3.1 Expense desk: review claims two ways](DAY_3/LABS/LAB_3_1_expense_desk_architecture/README.md) | ACME Finance (Demo 3A). Vote on the five briefs, then review six claims as a conversation and as a workflow | The rubric and two Claude calls (24 lines) | Both reviews | 25 min |
| [3.2 Research desk: hand-offs](DAY_3/LABS/LAB_3_2_research_desk_handoffs/README.md) | The research desk (Demo 3B). What a valid hand-off is, what each specialist may see, and what to do when two reliable reports disagree | Contracts, minimal briefs, a conflict rule and one writer call (14 lines) | The writer | 45 min |
| [3.3 Warranty claims agent](DAY_3/LABS/LAB_3_3_warranty_failure_recovery/README.md) | Warranty claims (Demo 3C). Tools, a decision rule and an agent loop | Tool runner, decision, one call and the loop (23 lines) | The intake agent | 30 min |
| [3.4 Supplier payments: release guard](DAY_3/LABS/LAB_3_4_payment_release_guard/README.md) | Payment release (Demo 3D). Small payments approved by rule, larger ones by a reviewer | Gate rules, reviewer choice, release hook and one call (26 lines) | The proposal | 40 min |
| [3.5 First agent with the Agent SDK](DAY_3/LABS/LAB_3_5_first_agent_with_agent_sdk/README.md) | Incident INC-7741 (Demo 3E). Configure a read-only agent | Tool specs, system prompt, options and the run (32 lines) | The whole agent | 30 min |
| [3.6 Two ways to build an agent](DAY_3/LABS/LAB_3_6_two_ways_to_build_an_agent/README.md) | The same incident agent (Demo 3F), as a manual loop and with the Tool Runner | Loop pieces and Tool Runner functions (26 lines) | The whole agent | 30 min |
| [3.7 Research desk with subagents](DAY_3/LABS/LAB_3_7_research_desk_with_subagents/README.md) | The research desk again (Demo 3G), built with Agent SDK subagents | Two subagents and the coordinator options (28 lines) | The coordinator and writer | 40 min |

How a Day 3 lab works:

- **One file to edit.** `lab.py` has numbered TODOs first and plumbing last (read the plumbing only if you are curious). Each TODO has exact code in the lab guide to paste in.
- **`check.py` Part A needs no key and tests your own functions**, so each TODO turns green as you finish it. Part B checks the saved result of the real run.
- **Install the lab's own packages:** `pip install -r requirements.txt` inside the lab folder. Labs 3.5 and 3.7 use `claude-agent-sdk` and need the Claude Code CLI as well.
- The loop is the usual one: edit a TODO, run `python check.py`, repeat; then `python lab.py` (real Claude), then `python check.py` again.
- A real model varies a little. If a Part B line fails because Claude answered differently, run `python lab.py` again, and tell the trainer if it keeps happening.

#### Day 3 demos (what the trainer shows)

The Day 3 demos are in the trainer's folder (`TRAINER_V2/DAY_3/DEMOS`). Each demo folder runs on its own, has a README and needs `ANTHROPIC_API_KEY` for its live stages (each stage says whether it needs a key). Pair each demo with the lab in the right-hand column.

| Demo | The idea in one line | Pairs with |
|---|---|---|
| 3A Should this be an agent? | Choose chat, workflow or agent by who controls the next step | Lab 3.1 |
| 3B Monolith to multi-agent | One 12-tool agent becomes a small desk of specialists with clean hand-offs | Lab 3.2 |
| 3C Warranty claims agent | An agent runs a claim through clean tools to a decision | Lab 3.3 |
| 3D Payment release | A rule approves small payments, a reviewer approves large ones, and an audit trail records each release | Lab 3.4 |
| 3E First agent with the Agent SDK | The smallest useful Claude Agent SDK agent (an incident triage) | Lab 3.5 |
| 3F Four ways to build an agent | Same task as a manual loop, Tool Runner, Managed Agents and the Agent SDK | Lab 3.6 |
| 3G Research orchestrator with the Agent SDK | The research desk as a multi-agent system with subagents and a scorer | Lab 3.7 |

Demos 3E to 3G use the `claude-agent-sdk` package and the Claude Code CLI; 3A to 3D use only `anthropic`.

### Day 4: Claude Code configuration and workflows (D3)

The four Day 4 trainer demos are rebuilt as self-contained, live Claude Code demos on small sample repos, in `TRAINER_V2/DAY_4/DEMOS` (read its README for the list and the trainer transcript). They need the Claude Code CLI (`claude --version`).

| Demo | The idea in one line | Pairs with |
|---|---|---|
| 4A Repository exploration and Plan Mode | Explore a repo, then plan a cross-file change before editing | Lab 4.1 |
| 4B CLAUDE.md and rules | Layer CLAUDE.md files and path-scoped rules so Claude follows the right guidance | Lab 4.2 |
| 4C Skill, hook and subagent | One reusable review capability built from a skill, a hook and a subagent | Lab 4.3 |
| 4D CI review gate | Claude Code reviews a pull request in CI and a gate script decides pass or fail | Lab 4.4 |

Each Day 4 lab repeats its demo's method on a new repo (`shipcalc`, a shipping-price calculator). Open the lab folder's `README.md` and follow it. Each lab has a `STARTER/` folder to work in, a `check.py` that needs no key, and a `SOLUTION/` folder. You need the Claude Code command-line tool (`claude --version`) and a login or API key.

| Lab | What it is about | Time |
|---|---|---|
| [4.1 Explore, plan and refactor](DAY_4/LABS/LAB_4_1_shipping_repo_plan_mode/README.md) | Demo 4A on `shipcalc`: explore, triage, Plan Mode, then implement and verify | 35 min |
| [4.2 Layer CLAUDE.md, rules and hooks](DAY_4/LABS/LAB_4_2_shipping_config_layers/README.md) | Demo 4B on `shipcalc`: layered CLAUDE.md, path-scoped rules, a hook and a project MCP file | 30 min |
| [4.3 Skill, hook and subagent](DAY_4/LABS/LAB_4_3_shipping_skill_hook_subagent/README.md) | Demo 4C on `shipcalc`: an API-contract review skill, an audit hook and a read-only subagent | 40 min |
| [4.4 CI review gate](DAY_4/LABS/LAB_4_4_shipping_ci_review_gate/README.md) | Demo 4D on `shipcalc`: findings schema, review runner, gate script and workflow | 40 min |

### Day 5: Context management and reliability (D5)

| Lab | What it is about | Time |
|---|---|---|
| [5.4 Context management (new)](NEW_LABS/LAB_5_4_context_management) | Shrink old turns in a long run without losing the facts you need later | 40 min |

The other Day 5 labs are not rebuilt in this self-contained format yet. Until then, use the original labs in the course folder's `STUDENT/DAY_5`.

## Study guide

Reading material that goes with the labs is in [STUDY_GUIDE](STUDY_GUIDE/README.md):

| Guide | What it covers |
|---|---|
| [MCP Best Practices](STUDY_GUIDE/MCP_BEST_PRACTICES.md) | Designing tools, results and servers that Claude uses well, transports, context cost, and choosing the Claude model and loop |
| [MCP Security Architecture](STUDY_GUIDE/MCP_SECURITY_ARCHITECTURE.md) | Threats, a layered design, OAuth based authorization, securing the model and the server, and a review checklist |
| [Anthropic SDK vs Claude Agent SDK](DAY_3/ANTHROPIC_SDK_VS_CLAUDE_AGENT_SDK.md) | A table-based comparison of the ways to build an agent |
| [Day 2 study guides](STUDY_GUIDES/DAY_2) | The tool-use loop, explained step by step |

## Test your labs and submit the results

`LAB_Test/run_all_labs.py` runs the labs one at a time and saves a summary and logs. Run it from this folder with your lab Python environment active:

```
python LAB_Test\run_all_labs.py --list                        # the labs it knows
python LAB_Test\run_all_labs.py --preflight --day 3           # check packages, key and the Claude CLI
python LAB_Test\run_all_labs.py --day 3                       # Day 3 labs with the reference solutions
python LAB_Test\run_all_labs.py --day 4 --mode live           # Day 4 labs, run live through Claude Code
```

Open `LAB_Test\results\<timestamp>\SUMMARY.md` first. Every run also writes `SUBMISSION_<timestamp>.zip` in that folder (logs only, your key is never included). Send that zip to the trainer. Details are in [LAB_Test/README.md](LAB_Test/README.md).

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

Every lab folder has a `SOLUTION/` folder with the complete reference solution. Try the lab first. To test a reference solution, copy it over `lab.py` in a scratch copy of the lab folder, or let `LAB_Test/run_all_labs.py` do it for you. Trainers who do not want students to see solutions up front can delete the `SOLUTION/` folders before sharing.

## Cost and safety

Your class key is capped at about USD 50 for the whole course, and each lab README states its cost (most are a few cents, Lab 2.1 under $1; a live Day 4 run costs a few dollars per lab). Never put the key in code, chat, screenshots or a git repo. If it leaks, tell the trainer at once.

## Notes

- Models are named `MODEL_FAST`, `MODEL_BALANCED`, `MODEL_PREMIUM` in `claude_client.py`. Override with the environment variables `CLAUDE_MODEL_FAST`, `CLAUDE_MODEL_BALANCED`, `CLAUDE_MODEL_PREMIUM` if a model name is retired.
- Not every lab has been run against the live API and Claude Code yet. If one behaves unexpectedly, tell the trainer which lab and paste the output (never the key).
