# CCA-F Student Labs (self-contained edition)

Hands-on labs for the **Claude Certified Architect - Foundations (CCA-F)** course. Each lab is one folder you can open, read top to bottom and run. There is no shared code folder to hunt through: the code that creates the Anthropic client, reads your API key and sends a message lives in a file called `claude_client.py` inside every lab.

New to the Anthropic SDK? Read [HOW_THE_CODE_WORKS.md](HOW_THE_CODE_WORKS.md) first (5 minutes). Machine not set up yet? Follow [DAY_0_SETUP_GUIDE.md](DAY_0_SETUP_GUIDE.md) (about 45 minutes, before Day 1).

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
| `data/` | The lab's input files |
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
| [1.1 HR roster classification](DAY_1/LABS/LAB_1_1_hr_roster_classification) | Compare model sizes on one task: which is good enough, and what does it cost at scale | 30 min |
| [1.2 IT incident normalization](DAY_1/LABS/LAB_1_2_it_incident_normalization) | Evolve a prompt and a JSON schema step by step, and measure each change | 35 min |
| [1.3 Warehouse receiving emails](DAY_1/LABS/LAB_1_3_warehouse_receiving_extraction) | Extract data, validate it, and retry with the error fed back to the model | 35 min |
| [1.4 PO reconciliation service](DAY_1/LABS/LAB_1_4_po_reconciliation_service) | A validated, cached, batched service: cost engineering | 40 min |
| [1.5 Prompt caching (new)](NEW_LABS/LAB_1_5_prompt_caching) | Mark a long prefix as cacheable, read cache hits, see what breaks the cache | 30 min |

### Day 2: Tool design and MCP (D2)

| Lab | What it is about | Time | Key needed |
|---|---|---|---|
| [2.1 Facilities tool boundaries](DAY_2/LABS/LAB_2_1_facilities_tool_boundaries) | Fix overlapping tools: descriptions, consolidation, pruning, per-desk scoping; measure selection accuracy | 60-75 min | lab.py |
| [2.2 Travel disruption tool loop](DAY_2/LABS/LAB_2_2_travel_disruption_tool_loop) | The tool loop: parallel reads, dependent writes, safe handling of failures | 35 min | lab.py |
| [2.3 Payroll typed errors](DAY_2/LABS/LAB_2_3_payroll_typed_errors) | Typed tool errors, bounded retries, escalation of permission errors | 75-90 min | lab.py |
| [2.4 Procurement MCP server](DAY_2/LABS/LAB_2_4_procurement_mcp_server) | Build an MCP server with authentication (401 vs 403), safe logging, stdio and HTTP | 60 min | none |
| [2.5 Build a tool and its loop (new)](NEW_LABS/LAB_2_5_build_a_tool_and_loop) | Write a tool schema, dispatcher and loop from the raw SDK | 45 min | lab.py |
| [2.6 Use an MCP server (new)](NEW_LABS/LAB_2_6_use_an_mcp_server) | Be the MCP client: connect to a server and let Claude use its tools | 45 min | lab.py |

### Day 5 (one new lab so far)

| Lab | What it is about | Time |
|---|---|---|
| [5.4 Context management (new)](NEW_LABS/LAB_5_4_context_management) | Shrink old turns in a long run without losing the facts you need later | 40 min |

### Days 3, 4 and 5 (other labs)

Not yet rebuilt in this self-contained format. Until they are, use the original labs in the course folder's `STUDENT/DAY_3`, `DAY_4` and `DAY_5`.

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

## Cost and safety

Your class key is capped at about USD 50 for the whole course, and each lab README states its cost (most are a few cents, Lab 2.1 under $1). Never put the key in code, chat, screenshots or a git repo. If it leaks, tell the trainer at once.

## Notes

- Models are named `MODEL_FAST`, `MODEL_BALANCED`, `MODEL_PREMIUM` in `claude_client.py`. Override with the environment variables `CLAUDE_MODEL_FAST`, `CLAUDE_MODEL_BALANCED`, `CLAUDE_MODEL_PREMIUM` if a model name is retired.
- These labs have not all been run against the live API yet. If one behaves unexpectedly, tell the trainer which lab and paste the output (never the key).
