---
name: audit-readonly
description: Audit the rewards code for the four team rules in a separate context and report a short summary. Use when the user wants a full rules audit without filling the main conversation.
context: fork
allowed-tools: Read Grep Glob Bash(python scripts/check_rules.py:*)
---

# Rules audit (runs in its own context)

Audit all files under `src/rewards` against the four team rules in CLAUDE.md.

1. Run `python scripts/check_rules.py --files` with every Python file under `src/rewards` and `tests`.
2. Confirm each finding by reading the line it points to.
3. Answer in at most eight lines: one line per rule with PASS or CHECK and the file and line if any, then a last line that starts with `Verdict:`.

You audit only. Do not edit any file.
