# Decision memo - classify 100,000 roster rows

Copy this file to `evidence/decision.md`, then replace every `[[...]]` placeholder. check_lab.py parses three
labelled lines (Decision / Rejected / Projection) - keep each label at the very start of its line.

Decision: [[fast | balanced | premium - or the model family name]]

Accuracy target and why: [[e.g. "exact match >= 0.90 because a wrong employment_type changes payroll routing"]]

Evidence (from evidence/results_table.md): [[2-3 sentences quoting YOUR measured exact accuracy, hard-subset accuracy,
schema compliance, latency and $ per 1k rows for the chosen model]]

Rejected: [[a different model]] - [[numeric reason, e.g. "scored 0.78 exact vs the 0.90 target" or "costs 2.0x per row for +0.05 accuracy"]]

Projection (100,000 rows): [[chosen model]] costs about $[[sync figure from evidence]] synchronous or $[[batch figure]] via the
Message Batches API (50% discount; results are unordered - join on custom_id). Measured from [[N]] rows, so it is an estimate.

Routing / risks: [[would you escalate the hard-looking rows (acting / interim / contract-to-hire) to a bigger model?
What escalation rate and added cost? What would make you re-run this study: model retirement, new title formats?]]
