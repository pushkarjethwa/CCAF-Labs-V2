---
lab:
    title: 'Part 2 - Give Claude project memory'
    module: 'Day 4 - Build-It Assembly'
---

# Part 2 - Give Claude project memory

In Part 1, Claude learned the team rules only because you pointed it at the README. In this part you write the rules down where Claude loads them by itself. This is memory: files named **CLAUDE.md** and rule files in **.claude/rules** that Claude reads at the start of a session or when it works on matching files. This part takes about 12 minutes.

## Understand what loads when

Claude Code reads memory from several places. They are layered, from broad to narrow, and more specific files add to the broader ones.

First comes the managed policy file. An organization places it on every machine, and a user cannot turn it off. Second comes your own user file in **~/.claude/CLAUDE.md**, which applies to all your projects. Third is the project file, **CLAUDE.md** in the repository root, which is committed and shared by the team. Fourth is **CLAUDE.local.md**, your private notes for this project, which stays out of git.

Two more kinds load at different times. A **CLAUDE.md** in a subfolder, such as **src/rewards/CLAUDE.md**, loads when Claude works on files in that folder. A rule file in **.claude/rules** with a `paths:` list loads only when Claude touches a file that matches one of the patterns.

At the start of a session, Claude loads the broad files. During the session, the narrow files join in the moment they become relevant. This keeps the context small, because the money rule does not need to be in memory while Claude edits a test.

An `@` line inside a **CLAUDE.md**, such as `@docs/ARCHITECTURE.md`, imports another file, so a short memory file can point to longer documents.

## Add the memory files

1. In a terminal in the **BUILD_IT_ASSEMBLY** folder, add this part's files.

    **Run:**
    ```
    python assemble.py --part 2
    ```
    **What it does:** Copies the memory files into your working repository.
    **Why we do it here:** The files hold the four team rules in the places where Claude loads them.
    **You should see:** One line that says six files were copied.

2. Move into the repository and look at what was added.

    **Run:**
    ```
    cd work/brewbean-rewards
    git status --short
    ```
    **What it does:** Lists the new files that are not committed yet.
    **Why we do it here:** It shows exactly what this part added, and nothing else changed.
    **You should see:** **CLAUDE.md**, **CLAUDE.local.md.example**, a **.claude/** folder, and **src/rewards/CLAUDE.md**.

3. Read the project memory file.

    **Run (PowerShell):**
    ```
    Get-Content CLAUDE.md
    ```
    **What it does:** Prints the project memory file.
    **Why we do it here:** You should know what Claude will read about your project.
    **You should see:** The four team rules, the test command, and a line `@docs/ARCHITECTURE.md` that imports the architecture notes.

    **Run (bash):**
    ```
    cat CLAUDE.md
    ```
    **What it does:** Does the same thing in bash.
    **Why we do it here:** It is the bash form of the PowerShell command.
    **You should see:** The same text.

## Look at the path-scoped rules

Each rule file starts with front matter. The `paths:` list says which files make the rule load.

1. Print the money rule.

    **Run (PowerShell):**
    ```
    Get-Content .claude/rules/money.md
    ```
    **What it does:** Prints the money rule file.
    **Why we do it here:** It shows the `paths:` list that limits the rule to **src/rewards/points.py**.
    **You should see:** A `paths:` list with one pattern, followed by three bullet points about integer points.

    **Run (bash):**
    ```
    cat .claude/rules/money.md
    ```
    **What it does:** Does the same thing in bash.
    **Why we do it here:** It is the bash form.
    **You should see:** The same text.

    The logging rule uses the pattern `src/**/*.py`, so it applies to every Python file under **src**. The tests rule uses `tests/**`, so it applies to everything in **tests**.

## Keep private notes out of git

1. Make your private memory file from the example.

    **Run (PowerShell):**
    ```
    Copy-Item CLAUDE.local.md.example CLAUDE.local.md
    git status --short
    ```
    **What it does:** Copies the example to **CLAUDE.local.md** and shows the git status again.
    **Why we do it here:** Personal preferences belong in a file that is never committed, and **.gitignore** already lists it.
    **You should see:** **CLAUDE.local.md** does not appear in the list, because git ignores it.

    **Run (bash):**
    ```
    cp CLAUDE.local.md.example CLAUDE.local.md
    git status --short
    ```
    **What it does:** Does the same thing in bash.
    **Why we do it here:** It is the bash form.
    **You should see:** The same result.

## See memory in a live session

1. Start Claude Code.

    **Run:**
    ```
    claude
    ```
    **What it does:** Opens a new session that loads the memory files.
    **Why we do it here:** Memory is read at session start, so a fresh session is needed to see it.
    **You should see:** The Claude Code prompt.

2. Open the memory view.

    **Type in Claude Code:**
    ```
    /memory
    ```
    **What it does:** Lists the memory files that are loaded and lets you open one to edit.
    **Why we do it here:** It proves which layers Claude is using right now.
    **You should see:** The project **CLAUDE.md** and your **CLAUDE.local.md**, and possibly your user file. Press Escape to leave the view.

    Verify on your Claude Code version: the exact layout of the `/memory` view differs between releases.

3. Ask Claude what it already knows, with no file reference.

    **Type in Claude Code:**
    ```
    What are the team rules for this project, and what does the architecture document say about logging?
    ```
    **What it does:** Asks a question that can be answered only from memory.
    **Why we do it here:** In Part 1 you had to point Claude to the README. Now it knows the rules and the imported architecture notes by itself.
    **You should see:** The four rules, and an answer about `log_event` and customer ids from **ARCHITECTURE.md**.

4. Ask for a small read-only look at the points file, and watch the rule load.

    **Type in Claude Code:**
    ```
    Read src/rewards/points.py and tell me which rules apply when I change it. Do not edit.
    ```
    **What it does:** Makes Claude open the points file, which matches the path in the money rule.
    **Why we do it here:** It is the moment the narrow memory joins in. The nested **src/rewards/CLAUDE.md** and the money and logging rules become relevant.
    **You should see:** An answer that mentions integer math and no floats, and that points are computed only in **points.py**.

    Verify on your Claude Code version: some versions show a note when a rule file is loaded, and others do not.

5. Learn what `/init` does, without running it.

    **Type in Claude Code:**
    ```
    In two sentences, what would the /init command do in a new project?
    ```
    **What it does:** Asks Claude to explain `/init`.
    **Why we do it here:** `/init` scans a repository and writes a first **CLAUDE.md** for it. We already wrote ours by hand, so we only explain it.
    **You should see:** A short explanation that it analyzes the codebase and creates a starting **CLAUDE.md** with commands and conventions.

6. Leave the session.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the session.
    **Why we do it here:** The next part adds more files, and a new session will pick them up.
    **You should see:** Your terminal prompt.

## Commit the memory files

1. Save this part in git.

    **Run:**
    ```
    git add -A
    git commit -m "Add project memory and rules"
    ```
    **What it does:** Commits the memory files. Git leaves out **CLAUDE.local.md**.
    **Why we do it here:** Team memory is shared through git, and a clean tree makes the pull requests in Part 5 simple.
    **You should see:** A commit summary that lists the new files.

## Verify the part

1. Go back to the **BUILD_IT_ASSEMBLY** folder and run the verification.

    **Run:**
    ```
    cd ../..
    python verify.py --upto 2
    ```
    **What it does:** Checks the memory files, the import line and the `paths:` front matter of the three rules.
    **Why we do it here:** It checks the structure you will rely on in the next parts.
    **You should see:** `[PASS]` lines and the line ALL PARTS PASS.
