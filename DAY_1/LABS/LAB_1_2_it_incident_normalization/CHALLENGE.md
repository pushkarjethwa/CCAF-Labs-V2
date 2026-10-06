# LAB 1.2 challenge - repair loop and a split rule (open-ended, no solution code)

Two extensions; do one.

**A. Corrective retry.** `common.schema_utils.issues_to_feedback` turns validation issues into a compact message. Add an optional second attempt to the harness: when a reply fails `target_schema.json` (or violates a semantic rule you define, e.g. `users_affected < 0`, `needs_followup == false` while `users_affected` is null), send one corrective follow-up turn that contains the issues, then re-validate. Measure: how many first-pass failures does the retry fix, what does it cost in tokens and latency, and when is a retry the wrong tool (refusal, truncation, injection)?

**B. One ticket, many incidents.** Your v4 rule returns a single merged record for a multi-incident ticket and sets `needs_followup`. Design the better contract: change the target to `{"incidents": [ ... ]}` (keep it within the structured-output rules: required-but-nullable, `additionalProperties: false`, no `minItems` above 1). Update `DATA`-side scoring in a copy of the harness, and explain how you would score set-valued output (matching incidents between prediction and truth) and what the schema cost is (more union types, more tokens).

Deliverable: `evidence/challenge.md` with the design, the measured numbers, and one residual failure you could not remove.
