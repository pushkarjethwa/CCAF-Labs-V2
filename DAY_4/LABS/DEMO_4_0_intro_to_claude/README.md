---
lab:
    title: 'Demo 4.0: Intro to Claude Code'
    module: 'Day 4 - Claude Code in the Development Workflow'
---

# Demo 4.0: Intro to Claude Code

A bookshop owner hires a new assistant. On day one the assistant needs a handbook on the desk (CLAUDE.md), a sticky note for a task the owner asks for every week (a slash command), a style binder to open when writing a report (a skill), a colleague in the back room who checks the work (a subagent), a door chime that rings every time someone walks in (a hook), and a phone line to the supplier (MCP). In this demo you meet each of these in Claude Code, one at a time, on one small use case: **add a low-stock report to a tiny bookshop app**. The demo takes about 38 minutes, runs live in Claude Code, and comes before Demo 4A. Students who have never used Claude Code leave knowing what each building block is and when to reach for it. Every part is short and everything works the first time: this is a tour, not a test.

## What the demo shows

1. **Start and look around** (6 minutes): Start `claude`, ask about the project, mention a file with `@`, run a shell command with `!`, and switch permission modes with Shift+Tab.
2. **Memory** (4 minutes): `/init` writes CLAUDE.md. You add one rule by hand, and see why a file beats a chat message.
3. **Context** (4 minutes): See what fills the conversation with `/context`, shrink it with `/compact`, and pick it up again with `claude -c`.
4. **A custom slash command** (4 minutes): One markdown file becomes `/add-feature`. You run it to build the low-stock report.
5. **A skill** (4 minutes): The shop's report format sits in a skill. Claude loads it when the work calls for it.
6. **A subagent** (3 minutes): A read-only reviewer works in its own context and reports back in six lines.
7. **A hook** (4 minutes): The tests run after every edit, without anyone asking.
8. **MCP** (4 minutes): A small local server gives Claude the supplier's stock numbers.
9. **Headless** (3 minutes): `claude -p` runs one prompt with no chat. This is the bridge to Demo 4D.
10. **Wrap-up** (2 minutes): One table: feature, when to use it, and which Day 4 demo goes deeper.

## Files in this folder

- **START_STATE/**: The sample project, `bookshop`: four small Python files, a JSON data file, six passing tests, and a README.
- **PART_02_memory/** to **PART_08_mcp/**: One folder for each part that adds files. The **add** folder holds the files you copy in. The **reference** folder holds the code Claude is expected to write, so you can compare or catch up. The **catch_up** folder holds what a command creates (the `.mcp.json` file).
- **FINAL/**: The finished project after part 10.
- **reset.py**: Rebuilds the working copy in **workspace/bookshop** at the start of any part: `python reset.py --to 5`, or `python reset.py --final`.
- **check_offline.py**: A key-free self-check. It does not need Claude Code. It runs the sample project's tests at every point, parses every file, and runs the hook script on sample input.
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
| 1 | 6 | Start, `@`, `!`, modes, permissions | `claude`, `/help`, `@file`, `!cmd`, Shift+Tab, `/permissions` | Claude explains the project, runs the tests, and shows who may do what |
| 2 | 4 | Memory | `/init`, `/memory` | A CLAUDE.md file exists and is loaded in every session |
| 3 | 4 | Context | `/context`, `/compact`, `/clear`, `claude -c`, `/model`, `/cost` | You see the conversation size, shrink it, and resume it |
| 4 | 4 | Custom slash command | `/add-feature ...` | The low-stock report and its tests are written |
| 5 | 4 | Skill | "Make the report follow our style", `/report-style` | The report follows the shop's format |
| 6 | 3 | Subagent | `/agents`, "Use the reviewer ..." | A six-line review comes back from a separate worker |
| 7 | 4 | Hook | `/hooks`, an edit request | Tests run by themselves after every edit |
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
| `claude` | Starts an interactive session in the current folder | Every part happens inside a session, and the folder tells Claude which project it is working on | 1 |
| `/help` | Lists the commands, including your own | It is the map of what you can type, and your own commands appear in it | 1 |
| `@path` | Mentions a file so Claude reads it | Claude reads the real file instead of guessing from a description | 1 |
| `!command` | Runs a shell command and puts the output in the conversation | You check things, such as the tests, without leaving Claude | 1 |
| Shift+Tab | Cycles the permission mode: default, accept edits, plan | It sets how much freedom Claude has before it edits files | 1 |
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
| `/add-feature ...` | Your own slash command, from `.claude/commands/add-feature.md` | A prompt written once and reused, so every feature gets built, tested and reported the same way | 4 |
| `/report-style` | Your own skill, run by name | It shows that a skill can start by hand as well as on its own | 5 |
| `/agents` | Lists and manages subagents | It shows the separate workers and the tools each may use | 6 |
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

4. To rebuild the project as it is at the start of a part (for example part 5), run `python reset.py --to 5` from this folder. This is the catch-up route if a live run drifts: it puts the project back where the part expects it.

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
- **The hook is plain Python.** `.claude/hooks/run_tests.py` is about 20 lines, so students can read the whole rule.
- **The MCP server wraps plain functions.** `supplier.py` holds the logic, and `supplier_server.py` only puts it behind MCP, in the same style as the Day 2 intro server.

## More information

- This demo has no matching lab. Students run it before the Day 4 labs.
- The demos that go deeper: 4A (plan mode, exploring), 4B (CLAUDE.md and rules), 4C (skill, hook, subagent and MCP), 4D (headless CI).
