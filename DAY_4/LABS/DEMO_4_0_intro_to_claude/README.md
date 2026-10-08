---
lab:
    title: 'Demo 4.0: Intro to Claude Code'
    module: 'Day 4 - Claude Code in the Development Workflow'
---

# Demo 4.0: Intro to Claude Code

A bookshop owner hires a new assistant. On day one the assistant needs a handbook on the desk (CLAUDE.md), a sticky note for a task the owner asks for every week (a slash command), a style binder to open when writing a report (a skill), a colleague in the back room who checks the work (a subagent), a door chime that rings every time someone walks in (a hook), and a phone line to the supplier (MCP). In this demo you meet each of these in Claude Code, one at a time, on one small use case: **add a low-stock report to a tiny bookshop app**. The full run takes about 43 minutes, the core path for a short session takes about 30 minutes. It runs live in Claude Code and stands alone: it needs no other demo, and every term is explained when it first appears. In parts 4 to 7, students write the small files live. Students who have never used Claude Code leave knowing what each building block is and when to reach for it. Every part is short and everything works the first time: this is a tour, not a test.

## Core path for a short session

**The pitch**: A new assistant gets the tour: handbook, sticky note, style binder, back-room colleague and door chime.

For a short session of about 30 minutes, run the parts in the table. The full run of about 43 minutes is still the default when you have the time.

| Part | Minutes | What students see |
|---|---|---|
| 1. Start and look around | 5 | `claude`, a project question, `@file`, `!tests`, `/permissions`, Shift+Tab modes and a quick plan-mode question |
| 2. Memory | 3 | `/init` writes CLAUDE.md, and you add one rule by hand |
| 4. Custom slash command | 5 | You write `/add-feature` as one markdown file, then use it to build the low-stock report |
| 5. Skill | 4 | You write the `report-style` skill, and the report follows the shop's format |
| 6. Subagent | 4 | You write a read-only reviewer, and it sends back six lines |
| 7. Hook | 4 | You write a hook in `settings.json`, and the tests run by themselves after every edit |
| 8. MCP (mention only) | 1 | One sentence and a look at `.mcp.json`, with no live run |
| 9. Headless | 3 | `claude -p`, a pipe and JSON output: Claude as a plain command for scripts and CI |
| 10. Wrap-up | 1 | The cheat table |

**Optional for a short session**:

- **Part 3, context** (4 minutes): `/context`, `/compact` and `claude -c`. Skip it, or say in one sentence that the context window is the fuel gauge and `/compact` empties it.
- **Part 8, MCP, full run** (4 minutes): Registering the supplier server with `claude mcp add` and asking for the supplier's numbers. In a short session, open `.mcp.json` and say: "MCP is the phone line to outside data and tools."

> **Note**: The parts build on each other, but none of them needs part 3 or the MCP run. Use `python reset.py --to 4` to start at the right project state, and `claude -c` where the run sheet says it, which works with or without part 3. The run sheet keeps the full-run timings per part.

## What the demo shows

1. **Start and look around** (7 minutes): Start `claude`, ask about the project, mention a file with `@`, run a shell command with `!`, switch permission modes with Shift+Tab, and ask for a plan in plan mode, where nothing changes.
2. **Memory** (4 minutes): `/init` writes CLAUDE.md. You add one rule by hand, and see why a file beats a chat message.
3. **Context** (4 minutes): See what fills the conversation with `/context`, shrink it with `/compact`, and pick it up again with `claude -c`.
4. **A custom slash command** (5 minutes): You write one markdown file live, and it becomes `/add-feature`. You run it to build the low-stock report.
5. **A skill** (5 minutes): You write the shop's report format as a skill. Claude loads it when the work calls for it.
6. **A subagent** (4 minutes): You write a read-only reviewer. It works in its own context and reports back in six lines.
7. **A hook** (5 minutes): You write the hook in `settings.json`. The tests run after every edit, without anyone asking.
8. **MCP** (4 minutes): A small local server gives Claude the supplier's stock numbers.
9. **Headless** (3 minutes): `claude -p` runs one prompt with no chat, so a script or a CI job can call Claude.
10. **Wrap-up** (2 minutes): One table: building block, when to use it, and where to practise later (optional).

## Files in this folder

- **START_STATE/**: The sample project, `bookshop`: four small Python files, a JSON data file, six passing tests, and a README.
- **LIVE_TYPED/**: The four small files that students write live in parts 4 to 7: `add-feature.md`, `report-style_SKILL.md`, `reviewer.md` and `settings.json`. Use them as a safety net if typing goes wrong.
- **PART_02_memory/** to **PART_08_mcp/**: One folder for each part that adds files. The **add** folder holds the files you copy in (parts 2 and 8). In parts 4 to 7, students type the files live, and these folders are the catch-up copies. The **reference** folder holds the code Claude is expected to write, so you can compare or catch up. The **catch_up** folder holds what a command creates (the `.mcp.json` file).
- **FINAL/**: The finished project after part 10.
- **reset.py**: Rebuilds the working copy in **workspace/bookshop** at the start of any part: `python reset.py --to 5`, or `python reset.py --final`.
- **check_offline.py**: A key-free self-check. It does not need Claude Code. It runs the sample project's tests at every point, parses every file (the **LIVE_TYPED** files too), and runs the hook script on sample input.
- **requirements.txt**: `mcp`, needed for part 8 only.
- **RUN_SHEET.md**: The instructor's script, with every prompt and command to type.

## Prerequisites

- Claude Code is installed. Run `claude --version` to check.
- You are signed in to Claude Code, or `ANTHROPIC_API_KEY` is set.
- Python 3.10 or later: `python --version`.
- For part 8 only, the `mcp` package: `pip install -r requirements.txt`.

## Parts table

| Part | Minutes | Feature | You type | Plain result |
|---|---|---|---|---|
| 1 | 7 | Start, `@`, `!`, modes, plan mode, permissions | `claude`, `/help`, `@file`, `!cmd`, Shift+Tab, `/permissions` | Claude explains the project, runs the tests, plans without editing, and shows who may do what |
| 2 | 4 | Memory | `/init`, `/memory` | A CLAUDE.md file exists and is loaded in every session |
| 3 | 4 | Context | `/context`, `/compact`, `/clear`, `claude -c`, `/model`, `/cost` | You see the conversation size, shrink it, and resume it |
| 4 | 5 | Custom slash command | Write `add-feature.md`, then `/add-feature ...` | You write the command, and it builds the low-stock report and its tests |
| 5 | 5 | Skill | Write `SKILL.md`, then "Make the report follow our style", `/report-style` | You write the skill, and the report follows the shop's format |
| 6 | 4 | Subagent | Write `reviewer.md`, then `@rev` to see it listed, "Use the reviewer ..." | A six-line review comes back from a separate worker |
| 7 | 5 | Hook | Write `settings.json`, then `/hooks`, an edit request | Tests run by themselves after every edit |
| 8 | 4 | MCP | `claude mcp add ...`, `/mcp` | Claude reads the supplier's numbers through a tool |
| 9 | 3 | Headless | `claude -p "..."` | An answer on the terminal, no chat |
| 10 | 2 | Wrap-up | none | The cheat table |

## Which building block for which job

| You want | Use | Why |
|---|---|---|
| Advice Claude should always know: layout, commands, rules | **CLAUDE.md** | Loaded at the start of every session, so you never repeat yourself |
| A prompt you type again and again | **Slash command** | One file in `.claude/commands/`; you type `/name args`, and it runs when you say so |
| Know-how Claude should pick up only when the work needs it | **Skill** | A folder in `.claude/skills/`; the description lets Claude load it when relevant, and you can also type `/name` |
| A second worker with its own desk, tools and context | **Subagent** | A file in `.claude/agents/`; the long reading stays out of your main conversation |
| A rule that must happen every time, with no asking | **Hook** | Run by the program, not by the model, so it cannot be forgotten |
| Data or actions that live outside the project | **MCP server** | One standard plug to a database, an API or a service |
| One answer inside a script or a pipeline | **Headless `claude -p`** | No chat: a prompt in, an answer out |

## Commands you will meet

Every command has two reasons: what it does, and why we run it here. The run sheet repeats both under each command.

| Command | What it does | Why we run it here | Part |
|---|---|---|---|
| `claude` | Starts an interactive session in the current folder (`claude --version` first shows that it is installed) | Every part happens inside a session, and the folder tells Claude which project it is working on | 1 |
| `/help` | Lists the commands, including your own | It is the map of what you can type, and your own commands appear in it | 1 |
| `@path` | Mentions a file so Claude reads it | Claude reads the real file instead of guessing from a description | 1 |
| `!command` | Runs a shell command and puts the output in the conversation | You check things, such as the tests, without leaving Claude | 1 |
| Shift+Tab | Cycles the permission mode: default, accept edits, plan | It sets how much freedom Claude has before it edits files. In plan mode Claude reads and plans, and nothing changes | 1 |
| `/permissions` | Shows and edits the allow, ask and deny rules | It makes the safety rules visible and changeable | 1 |
| `/init` | Writes a CLAUDE.md for the project | The handbook is created for you, and every session reads it | 2 |
| `/memory` | Shows the memory files that are loaded, and opens them | It proves what Claude remembers, and where | 2 |
| `/context` | Shows what fills the context window | Claude knows only what is in the window, so this shows why long sessions need care | 3 |
| `/compact` | Replaces the conversation with a summary | It frees window space and keeps the facts you name | 3 |
| `/clear` | Starts a fresh conversation | A clean desk, with CLAUDE.md read again | 3 |
| `claude -c` | Continues the most recent conversation in this folder | You come back to the work after a restart, without retelling it | 3 |
| `claude --resume` | Opens a list of past conversations to pick from | You pick an older conversation, not only the last one | 3 |
| `/model` | Shows or changes the model | The model is a choice with cost and quality trade-offs | 3 |
| `/cost` | Shows what the session has used (newer versions also have `/usage`; verify on your Claude Code version) | Cost is part of the design, so you should know where to look | 3 |
| `/add-feature ...` | Your own slash command, which you write in `.claude/commands/add-feature.md` | A prompt written once and reused, so every feature gets built, tested and reported the same way | 4 |
| `/report-style` | Your own skill, run by name | It shows that a skill can start by hand as well as on its own | 5 |
| `@rev` (then Esc) | Opens the list of files and subagents, matching what you type | It shows that Claude Code found your `reviewer` subagent (older versions have `/agents`) | 6 |
| `/hooks` | Shows the hooks that are set up | It makes the rules that run by themselves visible | 7 |
| `claude mcp add` | Registers an MCP server | It connects Claude to data and tools outside the project | 8 |
| `/mcp` | Shows MCP servers and their status | It proves the connection works before you rely on it | 8 |
| `claude -p "..."` | Runs one prompt and exits | It makes Claude a plain command that scripts and CI jobs can call | 9 |
| `--output-format json` | Prints a JSON object with the answer and run details | Another program can read it, which a CI gate needs | 9 |

## Run the demo

1. Run the key-free self-check from this folder, and confirm that it ends with `ALL OK`:

    ```
    python check_offline.py
    ```

    **What it does:** Runs the sample project's tests at every part, parses every file, and runs the hook script on sample input. **Why we run it:** It tells you the files are correct before you go live, so any surprise during the demo comes from Claude Code and not from the files.

2. Build the working copy, and open Claude Code in it:

    ```
    python reset.py
    cd workspace\bookshop
    claude
    ```

    **What it does:** `reset.py` builds a clean working copy of the bookshop project. `cd` moves into it, and `claude` starts a session there. **Why we run it:** You work in a copy, so the original files stay clean and you can rebuild the start state any time.

3. Follow **RUN_SHEET.md**. It gives the prompts to type, what each one does and why we run it, what to expect on screen, and what to say.

4. In parts 4 to 7, you type each small file live. If typing goes wrong, copy the same file from **LIVE_TYPED**. To rebuild the project as it is at the start of a part (for example part 5), run `python reset.py --to 5` from this folder. This is the catch-up route if a live run drifts: it puts the project back where the part expects it.

> **Note**: The run sheet uses Windows `xcopy`. On macOS or Linux, use `cp -r ../../PART_04_slash_command/add/. .` instead.

## What to expect

Claude Code's wording differs on every run, so say what you observe. These patterns are what the demo is built around:

- `/init` writes a CLAUDE.md that names the layout and the test command. Yours will differ from **PART_02_memory/add/CLAUDE.md**, which is the catch-up copy.
- The low-stock report, written by `/add-feature`, lists four books: Small Gardens (0), The Quiet Engine (2), Night Ferry (3) and Harbour Lights (4).
- After part 5 the report starts with `=== LOW STOCK (BELOW 5) ===` and ends with `Total: 4 titles`.
- The supplier server answers from a fixed table, so the numbers in part 8 are always the same.

What is verified offline: the sample project's tests (6 at the start, 11 at the end), every part's files, the hook script on sample input, and the supplier functions. What needs a pre-flight run: Claude Code's own behaviour, wording, approval screens, and the commands marked "verify on your Claude Code version" in the run sheet.

## Design notes

- **Each part adds one building block and one small piece of the same feature.** The use case never changes, so students see what each block adds.
- **The skill is where the shop's format lives.** CLAUDE.md says how to work. The skill says what a finished report looks like, and it loads only when a report is being written.
- **The hook is one line.** Students type the hook live as an inline command, `python -m unittest discover -s tests`, so they can read the whole rule. **PART_07_hook** also holds a fuller version, a small script `run_tests.py` that prints one line, as a catch-up.
- **The MCP server wraps plain functions.** `supplier.py` holds the logic, and `supplier_server.py` only puts it behind MCP.

## More information

- This demo stands alone and has no matching lab. You can run it before any other Day 4 material.
- Practise later (optional, not needed for this demo): the Day 4 demos and labs go deeper on plan mode, CLAUDE.md and rules, skills, hooks, subagents, MCP and headless use.
