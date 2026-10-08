---
lab:
    title: 'Build an API-Contract Review Skill, Hook and Subagent'
    module: 'Day 4 - Claude Code Configuration and Workflows'
---

# Build an API-contract review skill, hook and subagent

In Demo 4C, you turned a long architecture-review prompt into a reusable capability for a billing service: a skill, a script, a hook and a read-only subagent. In this lab, you do the same for a different repository. **shipcalc** is a small shipping-quote library at a logistics company. Its public API is described in **docs/API_CONTRACT.json**, but reviews of API changes are inconsistent, because each reviewer checks different things. You build one reusable `/api-contract-review` capability for it, live in Claude Code.

You will complete four small pieces of the repository, which add up to 22 lines, and this guide gives you every line. The lab takes about 40 minutes. At the end, one command reviews a change, a script supplies the evidence, a hook logs the work, and a read-only subagent answers the hard question.

This lab continues Demo 4C, so you will recognize the following:

- A skill is a folder with a **SKILL.md**. Its front matter has a name and a description that says when to use it, and the references load only when a step reads them.
- A script finds the evidence without a model, and Claude confirms and explains it.
- A hook is configured in **.claude/settings.json**. Claude Code runs it at a lifecycle event, and it works quietly.
- A subagent has its own context and only the tools you list, so a read-only reviewer cannot edit anything.

## Set up the lab folder

> **Note**: This lab needs the Claude Code command-line tool and Python 3.10 or later. No API key is needed for **check.py**. The live steps use your Claude Code sign-in.

1. Open a terminal in the **STUDENT_V2/DAY_4/LABS/LAB_4_3_shipping_skill_hook_subagent** folder.

2. Install the required package by running the following command:

    ```
    pip install -r requirements.txt
    ```

3. Verify that the Claude Code command-line tool is installed by running the following command:

    ```
    claude --version
    ```

4. Open a second terminal in the **STARTER** folder of the lab. This is the **shipcalc** repository, and it is where you run Claude Code. Keep the first terminal for the checker.

5. Notice the files you will work with, all inside **STARTER**:

    - **.claude/skills/api-contract-review/SKILL.md**: the skill. Its front matter has a blank to fill.
    - **.claude/skills/api-contract-review/scripts/diff_contract.py**: the script that compares the contract with the code. One loop is blank.
    - **.claude/settings.json**: the hook configuration. The hooks block is blank.
    - **.claude/hooks/audit_log.py**: the hook script. It is finished, so you only read it.
    - **.claude/agents/contract-reviewer.md**: the subagent. Its description and tool list are blank.

    > **Note**: The skill's three reference files are already in the **references** folder, and **docs/API_CONTRACT.json** is the contract the review compares against.

## Create the skill

A skill is a folder with a **SKILL.md**. Claude holds only the name and the description until you invoke it, so the description has to say what the skill does and when to use it.

1. Open **STARTER/.claude/skills/api-contract-review/SKILL.md** in your code editor.

2. Search for the comment **TODO 1 of 4**. It sits in the front matter, under the `name` line.

3. Replace that comment line with the following lines:

    ```yaml
    description: Review a change to the shipcalc public API against docs/API_CONTRACT.json - parameters, return type, units and errors. Use when the user asks for an API, contract or breaking-change review of a diff, branch or module.
    argument-hint: "[path-or-branch]"
    allowed-tools: Read Grep Glob Bash(python *diff_contract.py *)
    ```

4. Save the file, and then run the following command in the first terminal:

    ```
    python check.py --stage 1
    ```

5. Verify that the five lines under **Stage 1** show `[PASS]`.

6. Review the file, noting the following details:

    - The `description` starts with what the skill does and ends with a `Use when` clause. Claude uses that clause to decide when to load the skill.
    - The skill is named `api-contract-review`, never `review`, because `review` collides with a bundled command. Verify on your Claude Code version.
    - `allowed-tools` pre-approves the tools for the turn, including the one script command. It does not restrict the other tools.
    - The body uses `$ARGUMENTS`, which Claude Code replaces with whatever you type after the command.
    - The body is short. The rules are in three files in **references/**, which Claude reads only when a step tells it to.

7. In the second terminal, start Claude Code in the **STARTER** folder, and enter the following prompt:

    ```
    /api-contract-review src/shipcalc/quote.py
    ```

    > **Note**: Claude reads the references and reports in the format that **output-format.md** asks for. The script is not finished yet, so it reports no candidates. Stage 2 fixes that.

## Add the supporting script

The script is the deterministic part of the review. It compares the contract with the code and prints one line for each difference, so the evidence does not depend on what the model notices.

1. Open **STARTER/.claude/skills/api-contract-review/scripts/diff_contract.py**.

2. Search for the comment **TODO 2 of 4**. It sits inside the loop `for entry in contract["public"]:`.

3. Replace that comment line with the following code. Keep the eight-space indent, because the code sits inside the loop:

    ```python
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == entry["function"]:
                    params = [arg.arg for arg in node.args.args]
                    if params != entry["params"]:
                        hits.append((entry["file"], node.lineno, "%s params %s != contract %s" % (node.name, params, entry["params"])))
    ```

4. Save the file, and then run `python check.py --stage 2` in the first terminal.

5. Verify that the five lines under **Stage 2** show `[PASS]`.

6. In the **STARTER** folder, run the script yourself:

    ```
    python .claude/skills/api-contract-review/scripts/diff_contract.py --root .
    ```

7. Verify that the output reads:

    ```
    src/shipcalc/quote.py:8 get_quote params ['parcel', 'carrier', 'zone', 'rush'] != contract ['parcel', 'carrier', 'zone']
    contract scan: 1 candidate(s)
    ```

    > **Note**: A teammate added an optional `rush` parameter to `get_quote`, and the contract was not updated. This is the issue the scanner exists to find.

8. In Claude Code, enter `/exit`, start `claude` again in the **STARTER** folder, and run the review again:

    ```
    /api-contract-review src/shipcalc/quote.py
    ```

9. Verify that the script line `src/shipcalc/quote.py:8 ...` appears in the tool output, and that Claude reports it as a finding with the file and line.

    > **Note**: Claude Code reads skills when it starts, so restart it after each stage. Verify on your Claude Code version whether a restart is still needed.

10. Review the script, noting the following details:

    - The script reads **docs/API_CONTRACT.json** and parses the code with `ast`, so it needs no model and gives the same answer every time.
    - It always exits with code 0. The output is evidence for the reviewer, not a verdict.
    - The same line is printed by the script, and Claude confirms it by reading the code. Deterministic where you can be, model where you must be.

## Configure the hook

A hook is a script that Claude Code runs at a lifecycle event, whatever Claude decides to do. The script receives the tool call as JSON on its standard input. Here the hook works quietly: it writes one audit line for every edit and command.

1. Open **STARTER/.claude/hooks/audit_log.py**, and read it. It reads the JSON from stdin, builds one entry with the tool, its target and an `ok` flag, and appends it to **.claude/logs/tool_audit.jsonl**.

    > **Note**: The result of a PostToolUse call arrives under the `tool_response` key. The script prints nothing and always exits with code 0.

2. Open **STARTER/.claude/settings.json**. Search for the line `"hooks": {}`.

3. Replace that line with the following code:

    ```json
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write|MultiEdit|Bash",
            "hooks": [
              {"type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/audit_log.py\"", "timeout": 10}
            ]
          }
        ]
      }
    ```

4. Save the file, and then run `python check.py --stage 3` in the first terminal.

5. Verify that the six lines under **Stage 3** show `[PASS]`.

6. Review the configuration, noting the following details:

    - An event (`PostToolUse`), a matcher that names the tools, and a command: these are the three parts of every hook.
    - The command uses `$CLAUDE_PROJECT_DIR`, so it works from any folder, and it has a `timeout` in seconds.
    - The `permissions` block that was already in the file keeps the fake carrier keys in **config/credentials** out of Claude's reach. It is not part of the hook.
    - A line in a skill that asks for an audit trail is advice. This hook is the guarantee, because Claude Code runs it for every matching call.

7. In Claude Code, enter `/exit`, start `claude` again, and run `/hooks` to see the configured hook. Then enter these prompts, one at a time:

    ```
    /api-contract-review src/shipcalc/quote.py
    ```

    ```
    Write the review you just gave to reports/api-contract-review.md
    ```

    > **Note**: Nothing interrupts the review. You may be asked for the usual permission to write the file. Verify the `/hooks` output and the hook command on Windows on your Claude Code version.

8. In the first terminal, show the audit log. On Windows, run `type STARTER\.claude\logs\tool_audit.jsonl`. On macOS or Linux, run `cat STARTER/.claude/logs/tool_audit.jsonl`.

9. Verify that the log has at least two lines: one for the script run (`"tool": "Bash"`) and one for the report (`"tool": "Write"`).

## Add the read-only subagent

A subagent is its own session with its own system prompt and only the tools you list. It does not see your conversation. It can read as many files as it needs, and only its short summary comes back to the main conversation.

1. Open **STARTER/.claude/agents/contract-reviewer.md**.

2. Search for the comment **TODO 4a of 4**. It sits in the front matter, under the `name` line.

3. Replace that comment line with the following lines:

    ```yaml
    description: Read-only specialist that answers one question about whether a shipcalc change keeps the public API contract and returns a short evidence-backed summary. Use proactively when a review touches quote.py, models.py or a carrier adapter.
    tools: Read, Grep, Glob
    maxTurns: 12
    ```

4. Open **STARTER/.claude/skills/api-contract-review/SKILL.md** again. Search for the step that starts with `3. Read`, and replace the whole line with the following line:

    ```markdown
    3. Read [references/semantics.md](references/semantics.md) and delegate the behaviour question to the `contract-reviewer` subagent (read-only). Use its summary, not its transcript.
    ```

5. Save both files, and then run `python check.py --stage 4` in the first terminal.

6. Verify that the five lines under **Stage 4** show `[PASS]`.

7. Review the agent, noting the following details:

    - `tools: Read, Grep, Glob` is the boundary. The reviewer cannot edit files or run commands, because a reviewer that can write is not a reviewer. If the line were missing, the subagent would inherit every tool.
    - `maxTurns` limits how long the subagent can work.
    - The prompt asks for at most 15 lines with a file and line for every claim, so the answer stays small.

8. In Claude Code, enter `/exit`, start `claude` again, type `@contract` and look for `contract-reviewer` in the list (do not press Enter, and press Esc to close it), and then enter this prompt:

    ```
    Use the contract-reviewer subagent: does get_quote in quote.py still match docs/API_CONTRACT.json, and is the new rush parameter tested?
    ```

9. Verify that the answer is about 15 lines or fewer, cites `quote.py` with a line number, and says that `rush` is missing from the contract and from **tests/test_quote.py**.

    > **Note**: The files the subagent opened do not appear in your main conversation. Only its summary does.

10. Run the whole capability once more:

    ```
    /api-contract-review src/shipcalc/quote.py
    ```

11. Verify that the review runs the script, delegates to the subagent, and reports the `rush` finding in the format from **output-format.md**.

## Check your work

1. Run the checker one last time, from the first terminal:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 21/21 checks passed
    ```

3. Submit your **STARTER/.claude** folder as your evidence. There is nothing else to write up.

## Clean up

Delete the **STARTER/.claude/logs** and **STARTER/reports** folders to reset the lab.

## More information

The **SOLUTION** folder is the finished repository. This guide already contains every line you need, so use it only to find a typo.
