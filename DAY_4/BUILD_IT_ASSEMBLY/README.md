# Build-It Assembly: Brew & Bean Rewards

An optional, ready-to-run assembly for Day 4. You do not write code. You run commands and watch Claude Code work on one small service from the first prompt to a CI review gate. It takes about 100 minutes.

## Scenario

Brew & Bean is a cafe chain. **brewbean-rewards** is its small rewards service: customers earn points for purchases. The team has four rules:

1. Points are whole numbers (integers), never floats. 1 point per whole currency unit spent, with a bonus multiplier for members.
2. Never log customer emails or any personal data. Log the customer id only.
3. No secrets in source code. Keys come from environment variables.
4. Every change to `src/` needs a test.

Each part adds one Claude Code capability that helps the team keep these rules.

## Parts

- Part 0, Setup (10 min): workspace trust, a throwaway GitHub repository, a token, and the working repo.
- Part 1, Explore and plan (12 min): `@`, `!`, search by content and by file name, modes, thinking, `/context`, and a plan for a birthday bonus.
- Part 2, Memory (12 min): the CLAUDE.md hierarchy, path-scoped rules, imports, `/memory`.
- Part 3, Extend (20 min): a slash command, skills, a read-only subagent, and hooks.
- Part 4, MCP and sessions (15 min): a menu MCP server, scopes, and `/compact`, resume and fork.
- Part 5, CI/CD signature moment (25 min): headless `claude -p`, a review gate (rule scanner plus Claude, exit codes 0 to 3), a workflow on `pull_request`, a no-GitHub local runner, and three pull requests from the patches in DATA.
- Part 6, Scorecard (6 min): `python verify.py` evidence mapped to topics 16 to 20, and a 10-question quiz with an answer key.

## Prerequisites

- Claude Code command-line tool, signed in.
- Git.
- GitHub CLI (`gh`).
- Python 3.10 or later. The service uses only the standard library.
- A GitHub account. Without one you can still follow along; see the end of the Part 0 guide.
- An `ANTHROPIC_API_KEY`, used only for the CI step in Part 5.

## Cost

A few dollars at most. Parts 0 to 4 use your Claude Code sign-in. Part 5 makes a small number of short review calls with a budget cap.

## How to start

Open a terminal in this folder and run the following command. Then follow the guide in each part folder, in order.

    python assemble.py --part 0

Other helpful commands:

    python assemble.py --list          show the parts
    python assemble.py --upto 3        apply parts 0 to 3 at once
    python assemble.py --part 3 --step b   apply the second stage of Part 3 (the blocking hook)
    python verify.py                   check every part that is present
    python verify.py --upto 2          check parts 0 to 2

The working repository is created in **work/brewbean-rewards**. Each part folder has a **GUIDE.md** (what you do) and a **verify_part.py** (the check). Part folders are found by the pattern `PART_NN_name`.
