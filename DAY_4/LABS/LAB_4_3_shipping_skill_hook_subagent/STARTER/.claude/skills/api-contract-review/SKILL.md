---
name: api-contract-review
# TODO 1 of 4 - paste the description, argument-hint and allowed-tools lines here
---
# API contract review: $ARGUMENTS

Work in this order. Do not skip step 2: it is deterministic evidence, not opinion.

1. Read [references/breaking-changes.md](references/breaking-changes.md) and keep only the rules that apply to the scope.
2. Run `python .claude/skills/api-contract-review/scripts/diff_contract.py --root .` and treat each line it prints as a finding candidate to confirm in the code.
3. Read [references/semantics.md](references/semantics.md) and check the behaviour rules against the scope yourself.
4. Report using [references/output-format.md](references/output-format.md). Every finding needs file:line, a severity and the evidence that supports it.

You review, you do not edit.
