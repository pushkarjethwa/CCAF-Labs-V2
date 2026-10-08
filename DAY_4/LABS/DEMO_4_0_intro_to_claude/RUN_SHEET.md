---
lab:
    title: 'Instructor Run Sheet: Demo 4.0, Intro to Claude Code'
    module: 'Day 4 - Claude Code in the Development Workflow'
---

# Instructor Run Sheet: Demo 4.0, Intro to Claude Code

This run sheet covers Demo 4.0, which takes about 38 minutes and runs live in Claude Code on a tiny sample project, `bookshop`. It uses one story from the first command to the last: a bookshop owner hires a new assistant, and the assistant is shown how the shop works, one tool at a time. The use case is "add a low-stock report". It comes before Demo 4A. This demo has no matching Python script to run: you work in Claude Code, and the **PART** folders hold the files you add at each part.

## Before class

1. Run `python check_offline.py` from this folder, and confirm that it ends with `ALL OK`.

2. Run `claude --version` to confirm that Claude Code is installed, and start `claude` once in any folder to confirm that you are signed in.

3. Run `pip install -r requirements.txt` so that part 8 can start the supplier server.

4. Build the working copy with `python reset.py`. Open two terminals in **workspace\bookshop**: one for Claude Code, and one for running commands yourself.

5. Run the whole demo once as a pre-flight. Claude Code's wording differs on every run, so note what it did. Then run `python reset.py` again.

6. Make the terminal font large. Keep **FINAL** open in an editor to compare against what Claude writes.

## Prompts and commands

Type these in this order. Each one is also used in the steps below.

**Part 1, start and look around**

```
claude
```

```
What does this project do? Answer in four lines.
```

```
Explain @bookshop/reports.py in two sentences.
```

```
!python -m unittest discover -s tests
```

```
/permissions
```

**Part 2, memory**

```
/init
```

```
/memory
```

**Part 3, context**

```
/context
```

```
/compact Keep the project layout and the goal: add a low-stock report.
```

```
/model
```

```
/cost
```

**Part 4, custom slash command**

```
/add-feature a low-stock report: list the books with fewer than 5 copies left, fewest first
```

**Part 5, skill**

```
Make the low-stock report follow our shop's report style.
```

```
/report-style
```

**Part 6, subagent**

```
/agents
```

```
Use the reviewer subagent to review low_stock_report and its tests.
```

**Part 7, hook**

```
/hooks
```

```
Add a low-stock command to bookshop/cli.py, so that python -m bookshop low-stock prints the report. Add a test for it.
```

**Part 8, MCP**

```
claude mcp add --transport stdio --scope project supplier -- python mcp_server/supplier_server.py
```

```
/mcp
```

```
For each book in the low-stock report, ask the supplier how many copies they have, and tell me which to reorder first.
```

**Part 9, headless**

```
claude -p "In one sentence, what is a hook in Claude Code?"
```

```
python -m bookshop low-stock | claude -p "Write a three-line reorder email from this report."
```

```
python -m bookshop low-stock | claude -p "Count the titles in this report." --output-format json
```

## Run the demo

Run every shell command from **workspace\bookshop** unless the step says otherwise. In the commands below, `..\..` is this demo folder.

1. **Minutes 0-6, part 1, start and look around**: Open the project in the second terminal, and show the layout, so students see how small it is: four Python files, one data file, six tests. Then, in the first terminal, run `claude`, and paste the prompts for part 1 in order.

    > **Say**: "Picture a bookshop. The owner has hired a new assistant. Today the assistant gets the tour, and so do you. This is the whole shop: four small files and a few tests. The assistant is Claude, and the front desk is this terminal."

    > **Say**: "Four things to type before anything else. Slash commands start with a slash. `/help` lists them. `@` points at a file, so Claude reads it instead of guessing. `!` runs a shell command right here and puts the output in the conversation, so I do not leave Claude."

    Press Shift+Tab once, and read the mode at the bottom of the screen. Press it again, and read it. Press it until you are back in the normal mode. Then run `/permissions`.

    > **Say**: "Shift+Tab is the lever for how much freedom Claude has. Normal mode asks before it edits. Accept-edits mode lets file edits through. Plan mode lets Claude read and think, and not edit. You will see plan mode properly in the next demo. `/permissions` is the list of rules: what is always allowed, what asks, what is never allowed."

    > **Note**: Expect a four-line description of an inventory app, a two-sentence explanation of `inventory_summary`, and `Ran 6 tests ... OK` from the shell shortcut. The modes cycle default, accept edits, plan, and the exact labels differ a little by version (verify on your Claude Code version). Stay in the normal mode for the rest of the demo, unless a step says otherwise.

2. **Minutes 6-10, part 2, memory**: Run `/init`, and approve the file it writes. Then run `/memory`.

    > **Say**: "A good assistant has a handbook on the desk. For Claude, the handbook is a file called CLAUDE.md. `/init` looks at the project and writes a first draft for me. Every session starts by reading it, so I never have to say 'the tests run like this' again."

    Open **CLAUDE.md** in an editor, and add this line at the end of the file by hand. Save it.

    ```
    - Keep every function under 20 lines.
    ```

    > **Say**: "I can edit the handbook like any file. Here is the difference from just telling Claude in the chat: a chat message lives for this conversation. A line in CLAUDE.md is there tomorrow, and for everyone who clones the repository. Advice that should always be true goes in the file."

    > **Note**: `/memory` lists the memory files that are loaded, with CLAUDE.md among them, and offers to open one. Your generated CLAUDE.md differs from **PART_02_memory\add\CLAUDE.md**. That file is the catch-up copy: if you need it, run `xcopy ..\..\PART_02_memory\add . /E /Y /I`. The next demo, 4B, goes much deeper on CLAUDE.md.

3. **Minutes 10-14, part 3, context**: Run `/context`. Then run `/compact` with the instruction from the prompts list. Run `/context` again. Then run `/model`, press Esc to leave it unchanged, and run `/cost`. Then exit with `/exit`, and run:

    ```
    claude -c
    ```

    Then run `/clear`.

    > **Say**: "Claude does not remember by magic. Everything it knows in a session sits in a window of fixed size, called the context. `/context` is the fuel gauge. It shows the parts: the system prompt, the tools, my CLAUDE.md, and our conversation. When the gauge gets full, `/compact` replaces the long conversation with a short summary, and I can tell it what to keep."

    > **Say**: "`claude -c` walks back into the shop and continues the last conversation in this folder. `claude --resume` shows a list when I want an older one. `/clear` is the opposite: a clean desk. CLAUDE.md is read again, and the old chat is gone. `/model` picks which model works for me, and `/cost` shows what this session has used."

    > **Note**: After `/compact`, the second `/context` shows a smaller conversation. `/cost` may show a subscription message instead of dollars, depending on how you signed in. Newer versions also have `/usage` (verify on your Claude Code version). After `claude -c` the earlier messages are back on screen. After `/clear` they are not. If a command in this part does not exist on your version, skip it and keep the story.

4. **Minutes 14-18, part 4, a custom slash command**: Exit Claude Code with `/exit`. Copy the part 4 files in, and start Claude Code again so that it sees them:

    ```
    xcopy ..\..\PART_04_slash_command\add . /E /Y /I
    claude
    ```

    Type `/help`, and point at `/add-feature` in the list. Open **.claude\commands\add-feature.md** in the editor. Then paste the `/add-feature` prompt. Press Shift+Tab to accept edits when the first edit appears, or approve the edits one by one.

    > **Say**: "The owner asks the assistant for the same kind of job every week: add a feature, test it, report back. I wrote it once on a sticky note. A slash command is just a markdown file in `.claude/commands`. The file name is the command name. `$ARGUMENTS` is the blank to fill in: whatever I type after the command lands there."

    > **Note**: Expect Claude to read `reports.py`, add `low_stock_report` and a test file, run the tests, and finish with a three-line summary. The report lists four books: Small Gardens, The Quiet Engine, Night Ferry and Harbour Lights. The code will differ from **PART_04_slash_command\reference**. To catch up, run `xcopy ..\..\PART_04_slash_command\reference . /E /Y /I`. Point out that a slash command is a prompt that you start: nothing happens until you type it.

5. **Minutes 18-22, part 5, a skill**: Exit Claude Code with `/exit`. Copy the part 5 files in, and continue the conversation:

    ```
    xcopy ..\..\PART_05_skill\add . /E /Y /I
    claude -c
    ```

    Paste the part 5 prompt. When Claude finishes, type `/report-style`.

    > **Say**: "The shop has a house style for reports: a title line, a column header, sorted rows and a Total line. I could paste that into every request. Instead I put it in a skill, a folder with one file, SKILL.md. The top of the file has a name and a description. Claude reads only the description at first. When the work matches it, here a report is being written, Claude opens the whole binder."

    > **Say**: "Slash command or skill? A slash command starts when I type it. A skill can start by itself, because the description tells Claude when it is useful. And I can still call it by name, as I just did."

    > **Note**: Expect Claude to mention or show that it loaded the `report-style` skill, and to change the report so that it starts with `=== LOW STOCK (BELOW 5) ===`, has a column header, and ends with `Total: 4 titles`, with the tests updated. If your version does not show the skill loading, the changed output is the proof. To catch up, run `xcopy ..\..\PART_05_skill\reference . /E /Y /I`. Open the README table "Which building block for which job" for 20 seconds.

6. **Minutes 22-25, part 6, a subagent**: Exit Claude Code with `/exit`. Copy the part 6 files in, and continue the conversation:

    ```
    xcopy ..\..\PART_06_subagent\add . /E /Y /I
    claude -c
    ```

    Type `/agents`, and point at `reviewer`. Press Esc. Then paste the part 6 prompt.

    > **Say**: "Sometimes the assistant needs a colleague. A subagent is a second worker with its own desk: its own instructions, its own tools and its own context. This reviewer can only read, search and list files, so it cannot change anything. It does the reading in the back room and sends me six lines. My own conversation stays small."

    > **Note**: Expect a block in the transcript that shows the subagent working, and then a review of at most six lines that ends with `Verdict:`. Open **.claude\agents\reviewer.md** and point at the `tools:` line: that line is what makes it read-only. The whole file is a name, a description, a tool list and instructions. Demo 4C builds this kind of file in more depth.

7. **Minutes 25-29, part 7, a hook**: Exit Claude Code with `/exit`. Copy the part 7 files in, and continue the conversation, so that Claude Code reads the settings:

    ```
    xcopy ..\..\PART_07_hook\add . /E /Y /I
    claude -c
    ```

    Type `/hooks`, and point at the `PostToolUse` entry. Press Esc. Then paste the part 7 prompt.

    > **Say**: "The shop has a door chime. Every time someone walks in, it rings, and nobody has to remember. A hook is the same: a rule the program runs at a set moment. This one says: after Claude edits or writes a file, run the tests. It is not a request to the model. It is the harness running my script, so it happens every time."

    > **Note**: Expect Claude to edit `cli.py` and the tests, and after each edit a short `[hook] tests passed after editing ...` line. Hook output may show only in the transcript view (press Ctrl+O to open it, and verify on your Claude Code version). The same `settings.json` also allows the test command, so Claude does not stop to ask before running it. Open **.claude\hooks\run_tests.py**: it reads the JSON that Claude Code sends on stdin, and runs the tests. To catch up, run `xcopy ..\..\PART_07_hook\reference . /E /Y /I`.

8. **Minutes 29-33, part 8, MCP**: Exit Claude Code. Copy the server in, and register it:

    ```
    xcopy ..\..\PART_08_mcp\add . /E /Y /I
    claude mcp add --transport stdio --scope project supplier -- python mcp_server/supplier_server.py
    claude
    ```

    Say yes if Claude Code asks you to approve the project server. Type `/mcp`, and point at `supplier`. Then paste the part 8 prompt, and approve the tool call when asked.

    > **Say**: "The assistant needs the supplier's numbers, and the supplier is not in the project. MCP is the phone line: one standard plug that connects Claude to outside tools and data. This server is 25 lines. It wraps two plain functions, the same shape as the Day 2 kitchen server. `claude mcp add` registered it, and the scope decides who gets it: `local` is you in this project, `project` is everyone who clones it, saved in `.mcp.json`, and `user` is you in every project."

    > **Note**: Expect `supplier` to show as connected in `/mcp`, and Claude to call `supplier_stock` for each low-stock book, then answer with a short list. Small Gardens has 0 at the supplier and ships in 21 days, so a sensible answer reorders the others first. Open **.mcp.json**: the command you typed wrote it. If it is missing, run `xcopy ..\..\PART_08_mcp\catch_up . /E /Y /I`. Demo 4C goes deeper on MCP in Claude Code.

9. **Minutes 33-36, part 9, headless**: Exit Claude Code, and run the three headless commands from the prompts list in the shell.

    > **Say**: "So far I have been in a conversation. `claude -p` is the same assistant with no conversation: one prompt in, one answer out, and the program ends. That makes it a command like any other, so a script, a scheduler or a pipeline can call it. I can pipe a file in, and I can ask for JSON so another program can read the answer."

    > **Note**: Expect a one-sentence answer, a three-line email, and a JSON object. In the JSON, find the `result` field, which holds the answer, and the cost and session fields (names can differ by version, verify on your Claude Code version). Say: "This is how Claude runs inside a CI job. Demo 4D uses exactly this."

10. **Minutes 36-38, part 10, wrap-up**: Show the table below on a slide or in the README, and read it down once.

    | Building block | Use it when | Goes deeper in |
    |---|---|---|
    | CLAUDE.md | Advice should always be loaded | Demo 4B, Lab 4.2 |
    | Slash command | You type the same prompt again and again | Demo 4A (`/triage`, `/plan-check`) |
    | Skill | Know-how should load only when the work needs it | Demo 4C, Lab 4.3 |
    | Subagent | You want a separate worker with its own context | Demo 4C, Lab 4.3 |
    | Hook | A rule must run every time, without asking | Demo 4C, Lab 4.3 |
    | MCP | Claude needs outside tools and data | Demo 4C, Lab 4.3 |
    | Permission modes and plan mode | You want to read and plan before any edit | Demo 4A, Lab 4.1 |
    | Headless `claude -p` | A script or a CI job calls Claude | Demo 4D, Lab 4.4 |

    > **Say**: "Six building blocks, and one question for each. Should it always be loaded? CLAUDE.md. Is it a prompt I type? A slash command. Should it load only when needed? A skill. Does it need its own desk? A subagent. Must it happen every time? A hook. Does it live outside the project? MCP. Demo 4A starts with the lever from part 1, plan mode."

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

- The next demo is Demo 4A, repository exploration and Plan Mode.
- For the parts table, the commands table and the files, see **README.md** in this folder.
