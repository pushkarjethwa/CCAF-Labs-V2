---
description: Review a file against the four Brew & Bean team rules
argument-hint: <file path>
allowed-tools: Read, Grep, Glob, Bash(python scripts/check_rules.py:*)
---

Review this file against the four team rules in CLAUDE.md: $ARGUMENTS

Work in this order:

1. Read the file.
2. Run `python scripts/check_rules.py --files $ARGUMENTS` and treat each finding as a lead to confirm in the code.
3. Check each rule in turn: integer points, no personal data in logs, no secrets in source, a test for the change.
4. Reply with one line per rule, starting with PASS or CHECK, then one closing line that starts with `Verdict:`.

Review only. Do not edit any file.
