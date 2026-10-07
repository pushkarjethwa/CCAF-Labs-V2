# Challenge - Lab 1B
1. Add three invoices of your own (with ground truth) to `data/` and see which prompt version breaks first.
2. Add a gate check of your own to `vault.py` (for example: no document may lose more than 20 points).
3. Wire `python demo.py --stage gate` into a CI job that exits non-zero when a candidate fails (hint: return the verdicts as the exit code).
4. Try the cascade with a different escalation rule (for example escalate only on arithmetic errors). Does the escalation rate fall without losing accuracy?
