---
lab:
    title: 'Part 3 - Extend Claude Code with commands, skills, agents and hooks'
    module: 'Day 4 - Build-It Assembly'
---

# Part 3 - Extend Claude Code with commands, skills, agents and hooks

Memory tells Claude what the team rules are. In this part you give Claude tools to work with them. You add a slash command, two skills, a read-only subagent and a hook that runs the tests. Then you meet one important idea: a rule written as advice is not the same as a rule that is enforced. This part takes about 20 minutes.

## Know the five extension points

A **slash command** is a prompt you saved in a file. You run it by name and pass it an argument.

A **skill** is a folder with a **SKILL.md** file. Claude reads its description and loads the skill when the work matches. A skill can also run in a forked context, which means a separate conversation that returns only a short summary.

A **subagent** is a helper with its own context and its own list of allowed tools. A read-only subagent can look at code but cannot change it.

A **hook** is a script that the Claude Code harness runs at a fixed moment, for example before or after an edit. The script runs every time. Claude does not decide whether to run it.

**Agent Teams** let several Claude sessions work together on one task. The feature is experimental, so we only mention it here and do not run it. Verify on your Claude Code version: whether Agent Teams exists and how you turn it on.

## Add the part files

1. In a terminal in the **BUILD_IT_ASSEMBLY** folder, add this part's files.

    **Run:**
    ```
    python assemble.py --part 3
    ```
    **What it does:** Copies a command, two skills, a subagent, a test hook and a settings file into your working repository.
    **Why we do it here:** You do not write these files. You use them and see how each one behaves.
    **You should see:** One line that says six files were copied.

2. Move into the repository and list what is new.

    **Run:**
    ```
    cd work/brewbean-rewards
    git status --short
    ```
    **What it does:** Lists the new files that are not committed yet.
    **Why we do it here:** Everything Claude Code extends lives in the **.claude** folder, so it is shared through git.
    **You should see:** One line for the **.claude/** folder.

3. Start Claude Code.

    **Run:**
    ```
    claude
    ```
    **What it does:** Opens a new session that finds the new files.
    **Why we do it here:** Commands, skills and agents are found when a session starts.
    **You should see:** The Claude Code prompt.

## Use the custom command

1. Run the command on the API file.

    **Type in Claude Code:**
    ```
    /review-points src/rewards/api.py
    ```
    **What it does:** Runs the saved prompt in **.claude/commands/review-points.md** and puts your file name in place of `$ARGUMENTS`.
    **Why we do it here:** The team reviews against the same four rules every time, so the prompt is saved once and reused.
    **You should see:** Claude runs the rule scanner, then answers with one line for each of the four rules and a closing line that starts with Verdict.

## Use a skill

1. Ask Claude to list its skills.

    **Type in Claude Code:**
    ```
    /skills
    ```
    **What it does:** Shows the skills Claude can use in this project.
    **Why we do it here:** It proves that the two skill folders were found.
    **You should see:** **rewards-style** and **audit-readonly** in the list. Press Escape to leave the view.

    Verify on your Claude Code version: the `/skills` command and its layout. If it is missing, ask Claude "Which skills do you have in this project?" instead.

2. Ask a question that matches the skill description.

    **Type in Claude Code:**
    ```
    I will soon add a member birthday bonus to points.py. Which style rules from the rewards-style skill will you follow? Do not edit anything.
    ```
    **What it does:** Matches the description of **rewards-style**, so Claude loads the skill.
    **Why we do it here:** A skill loads only when the work needs it. That keeps the context small.
    **You should see:** A short list that mentions whole-number math with `//`, named constants, `log_event` with the customer id only, and `unittest` tests. Claude may show that it used the skill.

## Use the skill that runs in a fork

1. Run the audit skill.

    **Type in Claude Code:**
    ```
    /audit-readonly
    ```
    **What it does:** Runs a full rules audit of **src/rewards** in a separate context, because the skill has `context: fork`.
    **Why we do it here:** An audit reads many files. The fork keeps all of that reading out of your main conversation, and only the short summary comes back.
    **You should see:** A summary of at most eight lines, one per rule, and a closing Verdict line.

    Verify on your Claude Code version: the `context: fork` setting in a skill, and whether the skill appears as a slash command.

## Use the read-only subagent

1. Open the agents view.

    **Type in Claude Code:**
    ```
    /agents
    ```
    **What it does:** Lists the subagents you can use.
    **Why we do it here:** It shows that **rule-reviewer** was found in **.claude/agents**.
    **You should see:** **rule-reviewer** under the project agents. Press Escape to leave the view.

2. Ask Claude to use it.

    **Type in Claude Code:**
    ```
    Use the rule-reviewer subagent to review src/rewards/ledger.py and src/rewards/logging_utils.py.
    ```
    **What it does:** Sends the review to a helper that can read files but cannot edit or run anything.
    **Why we do it here:** A reviewer that cannot change code is safe to run on any file, and its work does not fill your main context.
    **You should see:** Claude shows that it started the subagent, and then gives the subagent's short answer with PASS or CHECK for each rule.

## Watch the quiet test hook

The file **.claude/settings.json** connects a PostToolUse hook. After Claude edits a Python file in **src** or **tests**, the harness runs **.claude/hooks/run_tests.py**. When the tests pass, the hook prints nothing at all.

1. Open the hooks view.

    **Type in Claude Code:**
    ```
    /hooks
    ```
    **What it does:** Shows the hooks that are active in this session.
    **Why we do it here:** You can see which events and which tools the hook is connected to.
    **You should see:** A PostToolUse entry with the matcher `Edit|Write|MultiEdit`. Press Escape to leave the view.

2. Make a small change that is safe.

    **Type in Claude Code:**
    ```
    In src/rewards/ledger.py, add one short sentence to the docstring of the reset function. Make no other change.
    ```
    **What it does:** Makes Claude edit a Python file in **src**.
    **Why we do it here:** The edit triggers the hook, and the hook runs the whole test suite without any prompt from you.
    **You should see:** Claude makes the edit and carries on. You see no message from the hook because the tests passed. Quiet is the goal.

    Verify on your Claude Code version: some versions show a hook status line while a hook runs.

## Hooks versus prompts, step A: the rule as advice

Team rule 3 says: no secrets in source code. Right now that rule exists only as a line in **CLAUDE.md**. It is advice. Claude reads it and usually follows it, but nothing makes it follow it.

1. Ask Claude to put a key in the code.

    **Type in Claude Code:**
    ```
    Add a constant API_KEY = "bb_live_EXAMPLE0000000000000000" to src/rewards/config.py. It is a fake demo value.
    ```
    **What it does:** Asks for exactly what rule 3 forbids.
    **Why we do it here:** It tests how far advice alone goes.
    **You should see:** Most of the time Claude declines or suggests the environment variable instead. That is good, because advice usually works. But it is not guaranteed. A different wording, a busy session or another model could end with the key in the file.

2. Note what you saw, then leave the session and put the repository back.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the session.
    **Why we do it here:** The next step adds a hook, and hooks are read when a session starts.
    **You should see:** Your terminal prompt.

3. Undo any change made to the source folder.

    **Run:**
    ```
    git checkout -- src
    git status --short
    ```
    **What it does:** Restores **src** to its committed state and lists what is left.
    **Why we do it here:** It removes the docstring edit and any key, so the next step starts clean.
    **You should see:** No line for **src**. Only the **.claude/** folder is listed.

## Hooks versus prompts, step B: the rule as enforcement

Now the same rule becomes a script. A PreToolUse hook runs before every Edit, Write and MultiEdit. If the new text holds a key-shaped value, the script exits with code 2 and a plain message. The harness then stops the edit.

1. Add the hook script and the wiring.

    **Run:**
    ```
    cd ../..
    python assemble.py --part 3 --step b
    cd work/brewbean-rewards
    ```
    **What it does:** Copies **.claude/hooks/block_secrets.py** and a new **.claude/settings.json** that keeps the test hook and adds the blocking hook.
    **Why we do it here:** The settings file is merged for you, so the test hook from before still works.
    **You should see:** One line that says two files were copied, and one file replaced.

2. Read the script.

    **Run:**
    ```
    python -c "print(open('.claude/hooks/block_secrets.py').read())"
    ```
    **What it does:** Prints the hook script.
    **Why we do it here:** The script is short. It reads the JSON that Claude Code sends, looks for a key shape, and exits 2 when it finds one.
    **You should see:** About thirty lines of Python that end with `sys.exit(2)` and `sys.exit(0)`.

3. Start a new session so the hook is loaded, and look at it.

    **Run:**
    ```
    claude
    ```
    **What it does:** Opens a new session that reads the new settings.
    **Why we do it here:** Hooks are loaded at session start.
    **You should see:** The Claude Code prompt. Claude Code may ask you to review the changed hooks. Check them and accept.

    Verify on your Claude Code version: whether a changed hook needs approval, and how `/hooks` shows it.

4. Check the hooks view.

    **Type in Claude Code:**
    ```
    /hooks
    ```
    **What it does:** Shows the hooks that are active now.
    **Why we do it here:** It confirms that the blocking hook is connected.
    **You should see:** A PreToolUse entry and a PostToolUse entry. Press Escape to leave the view.

5. Ask for the same change again.

    **Type in Claude Code:**
    ```
    Add a constant API_KEY = "bb_live_EXAMPLE0000000000000000" to src/rewards/config.py. It is a fake demo value.
    ```
    **What it does:** Repeats the request from step A.
    **Why we do it here:** This time the harness runs the script before the edit. Claude does not get to decide.
    **You should see:** The edit does not happen. Claude shows the message "Blocked: the change to src/rewards/config.py contains a key-shaped value" and then explains or offers the environment variable.

6. Leave the session.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the session.
    **Why we do it here:** The lesson is done. Advice is a good first layer. A hook is the layer you can count on.
    **You should see:** Your terminal prompt.

## Commit the extensions

1. Save this part in git.

    **Run:**
    ```
    git status --short
    git add -A
    git commit -m "Add command, skills, subagent and hooks"
    ```
    **What it does:** Shows the status, then commits the **.claude** files.
    **Why we do it here:** The team shares these tools through git, and the pull requests in Part 5 start from a clean tree.
    **You should see:** Only the **.claude/** folder in the status, and a commit summary that lists the new files.

## Verify the part

1. Go back to the **BUILD_IT_ASSEMBLY** folder and run the verification.

    **Run:**
    ```
    cd ../..
    python verify.py --upto 3
    ```
    **What it does:** Checks the file headers, the settings, and runs both hook scripts with sample input.
    **Why we do it here:** It proves the blocking hook exits 2 on a key and exits 0 on a normal edit.
    **You should see:** `[PASS]` lines and the line ALL PARTS PASS.
