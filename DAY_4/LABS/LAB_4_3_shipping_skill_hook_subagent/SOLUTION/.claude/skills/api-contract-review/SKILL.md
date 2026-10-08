---
name: api-contract-review
description: Review a change to the shipcalc public API against docs/API_CONTRACT.json - parameters, return type, units and errors. Use when the user asks for an API, contract or breaking-change review of a diff, branch or module.
argument-hint: "[path-or-branch]"
allowed-tools: Read Grep Glob Bash(python *diff_contract.py *)
---
# API contract review: $ARGUMENTS

Work in this order. Do not skip step 2: it is deterministic evidence, not opinion.

1. Read [references/breaking-changes.md](references/breaking-changes.md) and keep only the rules that apply to the scope.
2. Run `python .claude/skills/api-contract-review/scripts/diff_contract.py --root .` and treat each line it prints as a finding candidate to confirm in the code.
3. Read [references/semantics.md](references/semantics.md) and delegate the behaviour question to the `contract-reviewer` subagent (read-only). Use its summary, not its transcript.
4. Report using [references/output-format.md](references/output-format.md). Every finding needs file:line, a severity and the evidence that supports it.

You review, you do not edit.
