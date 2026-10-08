---
lab:
    title: 'Instructor Run Sheet: Demo 4.0, Intro to Claude Code'
    module: 'Day 4 - Claude Code in the Development Workflow'
---

# Instructor Run Sheet: Demo 4.0, Intro to Claude Code

This run sheet covers Demo 4.0, which takes about 43 minutes in full, or about 30 minutes on the core path, and runs live in Claude Code on a tiny sample project, `bookshop`. It uses one story from the first command to the last: a bookshop owner hires a new assistant, and the assistant is shown how the shop works, one tool at a time. The use case is "add a low-stock report". The demo stands alone: it needs no other Day 4 demo, and every term is explained when it first appears. This demo has no matching Python script to run: you work in Claude Code. In parts 4 to 7 you write one short file live, and the **LIVE_TYPED** folder holds the same files as a safety net. The **PART** folders hold catch-up copies.

## Core path card

- **The pitch**: A new assistant gets the tour: handbook, sticky note, style binder, back-room colleague and door chime.
- **The one thing students must remember**: Each building block answers one question. Always loaded: CLAUDE.md. A prompt you type: slash command. Loads only when needed: skill. Own desk: subagent. Must happen every time: hook. Outside the project: MCP.
- **Full run**: About 43 minutes, with all ten parts and the timings in the steps below.
- **Core path**: About 30 minutes, as in the table.

| Part | Minutes | What students see |
|---|---|---|
| 1. Start and look around | 5 | `claude`, a project question, `@file`, `!tests`, `/permissions`, Shift+Tab modes and a quick plan-mode question |
| 2. Memory | 3 | `/init` writes CLAUDE.md, and you add one rule by hand |
| 4. Custom slash command | 5 | You write `/add-feature` as one markdown file, then use it to build the low-stock report |
| 5. Skill | 4 | You write the `report-style` skill, and the report follows the shop's format |
| 6. Subagent | 4 | You write a read-only `reviewer`, and it sends back six lines |
| 7. Hook | 4 | You write a hook in `settings.json`, and the tests run by themselves after every edit |
| 8. MCP (mention only) | 1 | One sentence and a look at `.mcp.json`, with no live run |
| 9. Headless | 3 | `claude -p`, a pipe and JSON output: Claude as a plain command for scripts and CI |
| 10. Wrap-up | 1 | The cheat table |

**Optional**:

- **Part 3, context** (4 minutes in the full run): `/context`, `/compact`, `/model`, `/cost` and `claude -c`. Skip it, or give it one sentence.
- **Part 8, MCP, full run** (4 minutes in the full run): In the core path, spend one minute: open `.mcp.json`, and say "MCP is the phone line to outside data and tools." Run the steps below only if time allows.

> **Note**: The step headings below show the full-run minutes. On the core path, follow the table above, and skip the optional parts. In parts 4 to 7 you write each part's small file live. The ready-made copies in **LIVE_TYPED** and the **PART** folders are the catch-up if typing goes wrong. Use `claude -c` to continue the conversation.

## Before class

1. Run `python check_offline.py` from this folder, and confirm that it ends with `ALL OK`.

2. Run `claude --version` to confirm that Claude Code is installed, and start `claude` once in any folder to confirm that you are signed in.

3. Run `pip install -r requirements.txt` so that part 8 can start the supplier server.

4. Build the working copy with `python reset.py`. Open two terminals in **workspace\bookshop**: one for Claude Code, and one for running commands yourself.

5. Run the whole demo once as a pre-flight. Claude Code's wording differs on every run, so note what it did. Then run `python reset.py` again.

6. Make the terminal font large. Keep **FINAL** open in an editor to compare against what Claude writes.

## Prompts and commands

Type these in this order. Each one is also used in the steps below. Every command has two lines under it: what it does, and why we run it here. Read both out loud for the first few commands, so students learn to ask "why am I running this?".

**Part 1, start and look around**

```
claude
```

**What it does:** Starts an interactive Claude Code session in the current folder.
**Why we run it here:** Everything in this demo happens inside a session. Starting it inside the project folder lets Claude see the project. (Before you start, `claude --version` shows that Claude Code is installed, and the first `claude` asks you to sign in.)

```
What does this project do? Answer in four lines.
```

**What it does:** Asks Claude to read the project and explain it.
**Why we run it here:** It shows the first thing a new assistant does: look around before touching anything.

```
Explain @bookshop/reports.py in two sentences.
```

**What it does:** Mentions one file with `@` so Claude reads exactly that file.
**Why we run it here:** Pointing at a file is faster and more accurate than describing it, and it keeps Claude from guessing.

```
!python -m unittest discover -s tests
```

**What it does:** Runs a shell command from inside the session and puts the output in the conversation.
**Why we run it here:** It proves the project's tests pass before we change anything, without leaving Claude.

```
Plan how you would add a low-stock report to this app. Do not change any file.
```

**What it does:** Asks for a plan while Claude Code is in plan mode, so it can read and think but not edit.
**Why we run it here:** It shows the safest way to start any change: look first, plan, and only then allow edits.

```
/permissions
```

**What it does:** Shows the rules for what Claude may always do, must ask about, or may never do.
**Why we run it here:** It makes the safety controls visible: students see that Claude does not have unlimited freedom.

**Part 2, memory**

```
/init
```

**What it does:** Looks at the project and writes a first CLAUDE.md.
**Why we run it here:** CLAUDE.md is the handbook Claude reads at the start of every session, so we never repeat the project basics.

```
/memory
```

**What it does:** Lists the memory files that are loaded and offers to open them.
**Why we run it here:** It proves the new CLAUDE.md is really loaded, and shows where memory lives.

**Part 3, context**

```
/context
```

**What it does:** Shows what fills the context window: system prompt, tools, memory and the conversation.
**Why we run it here:** Claude only knows what is in this window. The fuel gauge explains why long sessions get worse and why we compact.

```
/compact Keep the project layout and the goal: add a low-stock report.
```

**What it does:** Replaces the long conversation with a short summary, keeping what you name.
**Why we run it here:** It frees space in the window while keeping the facts we still need. The instruction tells it what matters.

```
/model
```

**What it does:** Shows which model is working for you, and lets you change it.
**Why we run it here:** The model is a choice with cost and quality trade-offs, and it is good to know where to set it.

```
/cost
```

**What it does:** Shows what the session has used so far.
**Why we run it here:** Cost is part of the design. Students should know where to look.

**Part 4, custom slash command** (you first create `.claude\commands\add-feature.md`, as in the steps below)

```
/add-feature a low-stock report: list the books with fewer than 5 copies left, fewest first
```

**What it does:** Runs your own slash command, with the text after it filled into `$ARGUMENTS`.
**Why we run it here:** A command is a prompt you wrote once and reuse. It builds the low-stock report with the same steps every time: build, test, report.

**Part 5, skill** (you first create `.claude\skills\report-style\SKILL.md`)

```
Make the low-stock report follow our shop's report style.
```

**What it does:** Asks for a change that matches the skill's description.
**Why we run it here:** Claude should load the `report-style` skill by itself, because the work matches the description. This shows a skill starting on its own.

```
/report-style
```

**What it does:** Runs the same skill by name.
**Why we run it here:** It shows that a skill can also be started by hand, which is the difference from CLAUDE.md, which is always loaded.

**Part 6, subagent** (you first create `.claude\agents\reviewer.md`)

```
@rev
```

**What it does:** Typing `@` and the start of a name opens a list of files and subagents. Do not press Enter: look for `reviewer` (marked as an agent) in the list, and press Esc.
**Why we run it here:** It proves Claude Code found the new `reviewer` file. (Older versions have an `/agents` command for this. Newer versions do not.)

```
Use the reviewer subagent to review low_stock_report and its tests.
```

**What it does:** Hands a task to the subagent. To make sure it is the subagent that runs, start the sentence with `@agent-reviewer` instead of "Use the reviewer subagent".
**Why we run it here:** The reviewer reads in its own context and sends back a short answer, so our main conversation stays small.

**Part 7, hook** (you first create `.claude\settings.json`)

```
/hooks
```

**What it does:** Shows the hooks that are set up.
**Why we run it here:** It makes the door chime visible: students see the rule that runs after every edit.

```
Add a low-stock command to bookshop/cli.py, so that python -m bookshop low-stock prints the report. Add a test for it.
```

**What it does:** Asks for a real change that edits and writes files.
**Why we run it here:** Each edit triggers the hook, so students watch the tests run on their own, with nobody asking.

**Part 8, MCP**

```
claude mcp add --transport stdio --scope project supplier -- python mcp_server/supplier_server.py
```

**What it does:** Registers the supplier server with this project. `--scope project` saves it in `.mcp.json` so everyone who clones the project gets it.
**Why we run it here:** Claude cannot reach the supplier's numbers on its own. MCP is the standard plug that connects it.

```
/mcp
```

**What it does:** Shows the MCP servers and whether they are connected.
**Why we run it here:** It proves the connection works before we rely on it.

```
For each book in the low-stock report, ask the supplier how many copies they have, and tell me which to reorder first.
```

**What it does:** Asks Claude to use the supplier tool for real data.
**Why we run it here:** It ties every part together: the report we built, plus outside data, gives a useful business answer.

**Part 9, headless**

```
claude -p "In one sentence, what is a hook in Claude Code?"
```

**What it does:** Runs one prompt and exits, with no chat.
**Why we run it here:** It shows Claude as a plain command, which is what a script or a CI job needs.

```
python -m bookshop low-stock | claude -p "Write a three-line reorder email from this report."
```

**What it does:** Pipes the report into Claude as input.
**Why we run it here:** Claude can work on the output of other programs, which is how a build pipeline can use it, for example to review a code change.

```
python -m bookshop low-stock | claude -p "Count the titles in this report." --output-format json
```

**What it does:** Asks for a JSON answer with the result and run details.
**Why we run it here:** Another program can read JSON, which a CI gate needs. It also shows the cost and session fields.

## Run the demo

Run every shell command from **workspace\bookshop** unless the step says otherwise. In the commands below, `..\..` is this demo folder.

1. **Minutes 0-7, part 1, start and look around**: Open the project in the second terminal, and show the layout, so students see how small it is: four Python files, one data file, six tests. Then, in the first terminal, run `claude`, and paste the prompts for part 1 in order.

    > **Say**: "Picture a bookshop. The owner has hired a new assistant. Today the assistant gets the tour, and so do you. This is the whole shop: four small files and a few tests. The assistant is Claude, and the front desk is this terminal."

    > **Say**: "Four things to type before anything else. Slash commands start with a slash. `/help` lists them. `@` points at a file, so Claude reads it instead of guessing. `!` runs a shell command right here and puts the output in the conversation, so I do not leave Claude."

    Press Shift+Tab once, and read the mode at the bottom of the screen. Press it again, and read it. Stop in plan mode, and paste the plan-mode prompt from the prompts list. Then press Shift+Tab until you are back in the normal mode, and run `/permissions`.

    > **Say**: "Shift+Tab is the lever for how much freedom Claude has. Normal mode asks before it edits. Accept-edits mode lets file edits through. Plan mode lets Claude read and think, and not edit. Watch: I ask for a plan, and nothing in the project changes. `/permissions` is the list of rules: what is always allowed, what asks, what is never allowed."

    > **Note**: Expect a short plan that lists the files it would change and no edits at all. Expect a four-line description of an inventory app, a two-sentence explanation of `inventory_summary`, and `Ran 6 tests ... OK` from the shell shortcut. The modes cycle default, accept edits, plan, and the exact labels differ a little by version (verify on your Claude Code version). Stay in the normal mode for the rest of the demo, unless a step says otherwise.

2. **Minutes 7-11, part 2, memory**: Run `/init`, and approve the file it writes. Then run `/memory`.

    > **Say**: "A good assistant has a handbook on the desk. For Claude, the handbook is a file called CLAUDE.md. `/init` looks at the project and writes a first draft for me. Every session starts by reading it, so I never have to say 'the tests run like this' again."

    Open **CLAUDE.md** in an editor, and add this line at the end of the file by hand. Save it.

    ```
    - Keep every function under 20 lines.
    ```

    > **Say**: "I can edit the handbook like any file. Here is the difference from just telling Claude in the chat: a chat message lives for this conversation. A line in CLAUDE.md is there tomorrow, and for everyone who clones the repository. Advice that should always be true goes in the file."

    > **Note**: `/memory` lists the memory files that are loaded, with CLAUDE.md among them, and offers to open one. Your generated CLAUDE.md differs from **PART_02_memory\add\CLAUDE.md**. That file is the catch-up copy: if you need it, run `xcopy ..\..\PART_02_memory\add . /E /Y /I`.

3. **Minutes 11-15, part 3, context**: Run `/context`. Then run `/compact` with the instruction from the prompts list. Run `/context` again. Then run `/model`, press Esc to leave it unchanged, and run `/cost`. Then exit with `/exit`, and run:

    ```
    claude -c
    ```

    Then run `/clear`.

    > **What it does and why**: `/exit` leaves the session on purpose, so `claude -c` can show that the last conversation comes back. `/clear` then shows the opposite: a clean start with CLAUDE.md read again.

    > **Say**: "Claude does not remember by magic. Everything it knows in a session sits in a window of fixed size, called the context. `/context` is the fuel gauge. It shows the parts: the system prompt, the tools, my CLAUDE.md, and our conversation. When the gauge gets full, `/compact` replaces the long conversation with a short summary, and I can tell it what to keep."

    > **Say**: "`claude -c` walks back into the shop and continues the last conversation in this folder. `claude --resume` shows a list when I want an older one. `/clear` is the opposite: a clean desk. CLAUDE.md is read again, and the old chat is gone. `/model` picks which model works for me, and `/cost` shows what this session has used."

    > **Note**: After `/compact`, the second `/context` shows a smaller conversation. `/cost` may show a subscription message instead of dollars, depending on how you signed in. Newer versions also have `/usage` (verify on your Claude Code version). After `claude -c` the earlier messages are back on screen. After `/clear` they are not. If a command in this part does not exist on your version, skip it and keep the story.

4. **Minutes 15-20, part 4, write a custom slash command**: Exit Claude Code with `/exit`. Make the folder that holds custom commands:

    ```
    mkdir .claude\commands
    ```

    > **What it does and why**: `mkdir` creates the folder, and `.claude` with it if it is missing. Claude Code looks for custom commands in `.claude\commands`, so the file has to live there.

    In the editor, create the file **.claude\commands\add-feature.md**, paste in the text below, and save it. (If typing goes wrong, `copy ..\..\LIVE_TYPED\add-feature.md .claude\commands\add-feature.md` puts the same file there.)

    ```
    ---
    description: Add a small feature the shop way (look, build, test, summarise)
    argument-hint: <feature in one sentence>
    ---

    Add this feature to the bookshop app: $ARGUMENTS

    Work in this order:

    1. Read the code that the feature touches. Say in one sentence where it will go.
    2. Write the code, keeping to the style of the files around it.
    3. Add tests for it in `tests/`.
    4. Run `python -m unittest discover -s tests` and show me the result.
    5. Finish with a three-line summary: what changed, which files, how to run it.
    ```

    Start Claude Code again so that it sees the new file, then type `/help` and point at `/add-feature` in the list:

    ```
    claude
    ```

    Then paste the `/add-feature` prompt. Press Shift+Tab to accept edits when the first edit appears, or approve the edits one by one.

    > **Say**: "The owner asks the assistant for the same kind of job every week: add a feature, test it, report back. So I write it once on a sticky note. A slash command is just a markdown file in `.claude/commands`. The file name is the command name. The top has a one-line description. `$ARGUMENTS` is the blank to fill in: whatever I type after the command lands there. Nothing runs until I type the command."

    > **Note**: Expect Claude to read `reports.py`, add `low_stock_report` and a test file, run the tests, and finish with a three-line summary. The report lists four books: Small Gardens, The Quiet Engine, Night Ferry and Harbour Lights. The code will differ from **PART_04_slash_command\reference**. To catch up, run `xcopy ..\..\PART_04_slash_command\reference . /E /Y /I`. To undo what Claude changed, press Esc twice (or type `/rewind`) and pick the point to go back to.

5. **Minutes 20-25, part 5, write a skill**: Exit Claude Code with `/exit`. Make the skill's folder:

    ```
    mkdir .claude\skills\report-style
    ```

    > **What it does and why**: A skill is a folder with one file named SKILL.md inside. The folder name is the skill's name, and Claude Code looks in `.claude\skills`.

    In the editor, create **.claude\skills\report-style\SKILL.md**, paste in the text below, and save it. (Safety net: `copy ..\..\LIVE_TYPED\report-style_SKILL.md .claude\skills\report-style\SKILL.md`.)

    ```
    ---
    name: report-style
    description: The bookshop's house format for text reports. Use when writing or changing any report, summary or listing that the shop owner reads.
    ---

    # Bookshop report style

    1. The first line is the title in capitals between `===` marks, like `=== LOW STOCK (BELOW 5) ===`.
    2. The second line is a column header.
    3. Rows are sorted by title, A to Z.
    4. The last line starts with `Total:` and counts the titles, like `Total: 4 titles`.

    When you change a report, update its tests so they check the first and last lines.
    ```

    Continue the conversation, paste the part 5 prompt, and when Claude finishes type `/report-style`:

    ```
    claude -c
    ```

    > **What it does and why**: `claude -c` starts Claude Code again so that it sees the new skill, and keeps the earlier conversation.

    > **Say**: "The shop has a house style for reports: a title line, a column header, sorted rows and a Total line. I could paste that into every request. Instead I put it in a skill. The top of the file has a name and a description. Claude reads only the description at first. When the work matches it, here a report is being written, Claude opens the whole binder. That keeps my context small."

    > **Say**: "Slash command or skill? A slash command starts when I type it. A skill can start by itself, because the description tells Claude when it is useful. And I can still call it by name, as I just did."

    > **Note**: Expect Claude to mention or show that it loaded the `report-style` skill, and to change the report so that it starts with `=== LOW STOCK (BELOW 5) ===`, has a column header, and ends with `Total: 4 titles`, with the tests updated. If your version does not show the skill loading, the changed output is the proof. To catch up, run `xcopy ..\..\PART_05_skill\reference . /E /Y /I`. Open the README table "Which building block for which job" for 20 seconds.

6. **Minutes 25-29, part 6, write a subagent**: Exit Claude Code with `/exit`. Make the folder for agents:

    ```
    mkdir .claude\agents
    ```

    > **What it does and why**: Claude Code looks for subagent files in `.claude\agents`. Each file is one worker.

    In the editor, create **.claude\agents\reviewer.md**, paste in the text below, and save it. (Safety net: `copy ..\..\LIVE_TYPED\reviewer.md .claude\agents\reviewer.md`.)

    ```
    ---
    name: reviewer
    description: Read-only code reviewer for the bookshop app. Use after a feature is written, to check it and report problems without changing any file.
    tools: Read, Grep, Glob
    ---

    You are a careful code reviewer for a small Python bookshop app.

    Check three things:

    1. Is there a test for each new function?
    2. Are the names clear and the functions short?
    3. If the code is a report, does it follow the report-style skill?

    You cannot edit files. Reply with at most six lines: one line per finding, starting with the file name, then a last line that starts with `Verdict:`.
    ```

    Continue the conversation, type `@rev` and point at `reviewer` in the list (do not press Enter), press Esc, and paste the part 6 prompt:

    ```
    claude -c
    ```

    > **What it does and why**: `claude -c` starts Claude Code again so that it sees the new agent file, and keeps the earlier conversation.

    > **Say**: "Sometimes the assistant needs a colleague. A subagent is a second worker with its own desk: its own instructions, its own tools and its own context. Look at the `tools:` line. This reviewer can only read, search and list files, so it cannot change anything. It does the reading in the back room and sends me six lines. My own conversation stays small."

    > **Note**: Expect a block in the transcript that shows the subagent working, and then a review of at most six lines that ends with `Verdict:`. The wording differs on every run. To catch up, copy the file as in the safety net above.

7. **Minutes 29-34, part 7, write a hook**: Exit Claude Code with `/exit`. In the editor, create **.claude\settings.json**, paste in the text below, and save it. (Safety net: `copy ..\..\LIVE_TYPED\settings.json .claude\settings.json`.)

    ```
    {
      "permissions": {
        "allow": [
          "Bash(python -m unittest:*)",
          "Bash(python -m bookshop:*)"
        ]
      },
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write",
            "hooks": [
              {"type": "command", "command": "python -m unittest discover -s tests"}
            ]
          }
        ]
      }
    }
    ```

    > **What it does and why**: `settings.json` is where a project keeps its rules. The `allow` lines let Claude run the tests and the report without stopping to ask. The `hooks` part says: after the tool `Edit` or `Write` finishes, run the tests. Claude Code reads settings when it starts, so we restart it next.

    ```
    claude -c
    ```

    Type `/hooks` and point at the `PostToolUse` entry. Press Esc. Then paste the part 7 prompt.

    > **Say**: "The shop has a door chime. Every time someone walks in, it rings, and nobody has to remember. A hook is the same: a rule the program runs at a set moment. This one says: after Claude edits or writes a file, run the tests. It is not a request to the model. It is Claude Code running my command, so it happens every time. That is the difference from a line in CLAUDE.md, which is advice."

    > **Note**: Expect Claude to edit `cli.py` and the tests. After each edit, the tests run by themselves. Hook output may show only in the transcript view (press Ctrl+O to open it, and verify on your Claude Code version). To catch up with a fuller version of the same hook (a small script that prints one line), run `xcopy ..\..\PART_07_hook\reference . /E /Y /I`.

8. **Minutes 34-38, part 8, MCP**: Exit Claude Code. Copy the server in, and register it:

    ```
    xcopy ..\..\PART_08_mcp\add . /E /Y /I
    claude mcp add --transport stdio --scope project supplier -- python mcp_server/supplier_server.py
    claude
    ```

    Say yes if Claude Code asks you to approve the project server. Type `/mcp`, and point at `supplier`. Then paste the part 8 prompt, and approve the tool call when asked.

    > **Say**: "The assistant needs the supplier's numbers, and the supplier is not in the project. MCP is the phone line: one standard plug that connects Claude to outside tools and data. This server is 25 lines. It wraps two plain functions. `claude mcp add` registered it, and the scope decides who gets it: `local` is you in this project, `project` is everyone who clones it, saved in `.mcp.json`, and `user` is you in every project."

    > **Note**: Expect `supplier` to show as connected in `/mcp`, and Claude to call `supplier_stock` for each low-stock book, then answer with a short list. Small Gardens has 0 at the supplier and ships in 21 days, so a sensible answer reorders the others first. Open **.mcp.json**: the command you typed wrote it. If it is missing, run `xcopy ..\..\PART_08_mcp\catch_up . /E /Y /I`.

9. **Minutes 38-41, part 9, headless**: Exit Claude Code, and run the three headless commands from the prompts list in the shell.

    > **Say**: "So far I have been in a conversation. `claude -p` is the same assistant with no conversation: one prompt in, one answer out, and the program ends. That makes it a command like any other, so a script, a scheduler or a pipeline can call it. I can pipe a file in, and I can ask for JSON so another program can read the answer."

    > **Note**: Expect a one-sentence answer, a three-line email, and a JSON object. In the JSON, find the `result` field, which holds the answer, and the cost and session fields (names can differ by version, verify on your Claude Code version). Say: "This is how Claude runs inside a build pipeline: a script calls it, and reads the JSON."

10. **Minutes 41-43, part 10, wrap-up**: Show the table below on a slide or in the README, and read it down once.

    | Building block | Use it when | Practise later (optional) |
    |---|---|---|
    | CLAUDE.md | Advice should always be loaded | Demo 4B, Lab 4.2 |
    | Slash command | You type the same prompt again and again | Demo 4A (`/triage`, `/plan-check`) |
    | Skill | Know-how should load only when the work needs it | Demo 4C, Lab 4.3 |
    | Subagent | You want a separate worker with its own context | Demo 4C, Lab 4.3 |
    | Hook | A rule must run every time, without asking | Demo 4C, Lab 4.3 |
    | MCP | Claude needs outside tools and data | Demo 4C, Lab 4.3 |
    | Permission modes and plan mode | You want to read and plan before any edit | Demo 4A, Lab 4.1 |
    | Headless `claude -p` | A script or a CI job calls Claude | Demo 4D, Lab 4.4 |

    > **Say**: "Six building blocks, and one question for each. Should it always be loaded? CLAUDE.md. Is it a prompt I type? A slash command. Should it load only when needed? A skill. Does it need its own desk? A subagent. Must it happen every time? A hook. Does it live outside the project? MCP.."

## Audience questions

1. "Is a skill the same as a slash command?" Close. A slash command is a prompt you start by typing its name. A skill is a folder of know-how that Claude can load itself when the description matches, and you can also type its name.

2. "Does the subagent see my whole conversation?" No. It starts with its own context and the task you give it, and it returns a summary. That is why it keeps your main conversation small.

3. "Why a hook and not a line in CLAUDE.md saying 'run the tests'?" A line in CLAUDE.md is advice, and the model may skip it. A hook is code that the program runs every time.

4. "Where do these files live?" Project files go in the repository's `.claude` folder, so the team shares them. Personal versions go in `~/.claude`, which only you have.

5. "Do I need MCP for everything outside the project?" No. For one quick command, a shell command is simpler. MCP pays off when the connection is reused and described once.

## Clean up

Run `python reset.py` to rebuild **workspace\bookshop** at the start state. Run `python reset.py --final` to rebuild it as it is at the end. If you registered the server in another scope on this machine, `claude mcp remove supplier` takes it away.

## Notes after your pre-flight run

Write down the following:

- Did `/init` write a CLAUDE.md that names the test command? ____________
- Did Claude show the `report-style` skill loading? ____________
- Did the hook line show on screen, or only in the transcript view? ____________
- Did `/cost` or `/usage` work on your version? ____________
- What fields did `--output-format json` print? ____________

## More information

- Optional next step: Demo 4A, repository exploration and Plan Mode.
- For the parts table, the commands table and the files, see **README.md** in this folder.
