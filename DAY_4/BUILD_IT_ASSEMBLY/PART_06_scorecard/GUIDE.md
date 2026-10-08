---
lab:
    title: 'Part 6 - Read your scorecard'
    module: 'Day 4 - Build-It Assembly'
---

# Part 6 - Read your scorecard

You built one project with five kinds of Claude Code capability: rules, a skill and a command, a hook, an MCP server and a CI review gate. In this part you ask the assembly to check all of it at once, read the evidence, and take a short quiz. This part takes about 6 minutes.

## Run the scorecard

1. In the **BUILD_IT_ASSEMBLY** folder, check every part.

    **Run:**
    ```
    python verify.py
    ```
    **What it does:** Runs the check of each part against **work/brewbean-rewards** and prints a summary.
    **Why we do it here:** It turns what you did in the last 100 minutes into evidence you can read line by line.
    **You should see:** `[PASS]` lines for each part and a summary that ends with ALL PARTS PASS.

2. Read the evidence against the Day 4 topics. Use the lines you just saw.

    Topic 16, Claude Code architecture. Parts 0 and 1 gave you a repository, a trusted workspace and a plan. You used `@` and `!`, saw plan mode read without changing anything, and used a content search (grep) and a file-name search (glob) for different questions. In the exam, this is the idea that Claude Code is an agent loop with tools, and plan mode is the safe way to start work that touches money.

    Topic 17, CLAUDE.md and rules. Part 2 checks showed the project memory, the nested **src/rewards/CLAUDE.md**, the private **CLAUDE.local.md** that stays out of git, and three rule files whose `paths:` decide when they load. In the exam, this is the layering of memory and why path-scoped rules keep the context small.

    Topic 18, extending Claude Code. Part 3 checks showed a slash command, two skills (one with `context: fork`), a read-only subagent, and hooks. You saw the same rule as advice in CLAUDE.md and as a PreToolUse hook that blocks the edit. In the exam, this is choosing between a prompt, a skill, a subagent and a hook, and knowing that only a hook enforces.

    Topic 19, MCP and context. Part 4 checks showed the menu MCP server, the `.mcp.json` file for project scope, and the commands for sessions: `/compact`, `claude -c`, `claude -r` and `--fork-session`. In the exam, this is picking a scope for a server and managing a long session.

    Topic 20, CI/CD and automation. Part 5 checks showed the workflow on `pull_request`, the headless review, the gate exit codes 0, 1, 2 and 3, and the three patches. You watched a flawed change get blocked and a fixed one pass. In the exam, this is structured output, parsed decisions, least privilege and untrusted pull request content.

3. Look at the five pieces together in your repository.

    **Run (PowerShell):**
    ```
    Get-ChildItem work/brewbean-rewards/.claude -Recurse -Name
    Get-ChildItem work/brewbean-rewards/.ci, work/brewbean-rewards/.github -Recurse -Name
    ```
    **What it does:** Lists the files under **.claude**, **.ci** and **.github**.
    **Why we do it here:** It shows the finale in one view: rules, skills and commands, hooks, and the CI gate all live in one repository.
    **You should see:** Rule files, a command, skills, an agent, hook files and settings under **.claude**. The review scripts under **.ci**. The workflow under **.github/workflows**. The MCP server is in **mcp_server** and its project entry is in **.mcp.json**.

    **Run (bash):**
    ```
    find work/brewbean-rewards/.claude work/brewbean-rewards/.ci work/brewbean-rewards/.github -type f
    ```
    **What it does:** Does the same thing in bash.
    **Why we do it here:** It is the bash form of the PowerShell command.
    **You should see:** The same files.

The Build-It finale in one sentence: a team rule can live in the project as memory that Claude reads, a skill or command that Claude follows, a hook that Claude cannot skip, an MCP server that gives Claude data, and a CI gate that checks every pull request, and all of it travels with the repository.

## Take the quiz

1. Open the quiz and answer the ten questions on paper before you read the answer key at the bottom.

    **Run (PowerShell):**
    ```
    Get-Content PART_06_scorecard/QUIZ.md
    ```
    **What it does:** Prints the quiz in the terminal.
    **Why we do it here:** The questions are in the style of the exam and cover Day 4 topics 16 to 20.
    **You should see:** Ten questions with four choices each, and an answer key at the end.

    **Run (bash):**
    ```
    cat PART_06_scorecard/QUIZ.md
    ```
    **What it does:** Does the same thing in bash.
    **Why we do it here:** It is the bash form of the PowerShell command.
    **You should see:** The same text. You can also open the file in an editor.

## Clean up

If you used a throwaway GitHub repository, delete it when you are done and revoke the token. Open **Settings** on the repository and use **Delete this repository**. Then delete the **brewbean-lab** token in your developer settings.
