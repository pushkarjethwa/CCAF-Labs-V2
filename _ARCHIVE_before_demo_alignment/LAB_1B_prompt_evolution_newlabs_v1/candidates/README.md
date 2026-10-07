# Failure 03 - three candidate "v7" prompts for the regression gate

All three start from `prompts/v6.md` (production). Run all of them: `python FINAL/prompt_vault/gate_demo.py`.
One at a time: `python FINAL/prompt_vault/cli.py gate --baseline v6 --candidate-file FAILURE_CASES/03_regression_candidates/<file>`
(exit code 1 = rejected).

| File | The edit someone would call reasonable | Designed verdict | Why (offline, scripted illustration) |
|---|---|---|---|
| `v7_reordered.md` | "put the rules after the examples" | PASS | same content, same measured behaviour; the gate must not be a change detector |
| `v7_trim_rules.md` | "save tokens: rules 4-6 are obvious" | FAIL | currency/European-number/multi-page rules deleted: accuracy 98.2 % -> 81.6 %, worst field currency -33 pt, 7 documents worse |
| `v7_extra_example.md` | "more examples are better" - adds the Kestrel example back as a third | FAIL | one leak (D10.po_number) and null handling 8/9, although overall accuracy only drops 0.8 pt (inside the 1 pt tolerance) |

The third case is the reason the gate has more than one check. Live: the numbers will differ; the *checks* are what you keep.
