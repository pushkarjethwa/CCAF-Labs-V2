# Lab 1.2 - IT Incident Normalization: evolve a prompt and a schema, and measure

**Time:** 35 min | **Day 1** | **Exam domain:** D4 Prompt and Structured Output | **Topics:** prompt design, structured outputs
Needs an API key. New here? Read `../../../HOW_THE_CODE_WORKS.md` first.
**Cost:** about 190 short calls on the fast model plus 30 on the balanced model. Roughly $0.10 to $0.60. Measure your own.

## Scenario
The service desk receives free-text tickets ("Sev-2", "P2", "urgent!!", three systems in one sentence, no user count, other languages). The ops dashboard needs one clean record per ticket: `severity` (S1-S4), `category`, `affected_systems[]`, `impact{users_affected|null, business_unit|null}`, `reported_at` (ISO or null) and `needs_followup`.

The starter prompt and schema are naive. You evolve them version by version (v0 to v4), **measure** each change on 30 tickets, then attack the final version with five hostile tickets.

## Goal
1. Fix four schema defects: enum drift, optional-vs-nullable confusion, a keyword the structured-output grammar does not support, missing `additionalProperties: false`.
2. Improve the prompt one idea per version and track field accuracy per version.
3. Measure schema compliance against the downstream contract (`data/target_schema.json`), not against your own schema.
4. Break and harden: instruction injection, empty ticket, other language, three incidents in one ticket, very long ticket.

## Files
| File | What |
|---|---|
| `lab.py` | The harness. Three TODOs (message rendering, trimming, failed-case file). The `VERSIONS` list is where you register each version |
| `versions/` | `v0.prompt.txt` and `v0.schema.json` (the defective baseline; do not edit). You add v1..v4 here |
| `claude_client.py` | The only file that talks to Claude |
| `schema_lint.py` | Offline schema linter, no key needed: `python schema_lint.py versions/v1.schema.json` |
| `check.py` | Run after `lab.py` |
| `data/` | 30 tickets with ground truth, 5 hostile tickets, the downstream contract |

## Steps
1. **Inspect (4 min).** Read `v0.prompt.txt`, `v0.schema.json`, `data/target_schema.json`, and tickets T-1004, T-1012, T-1023, T-1026. Run `python schema_lint.py versions/v0.schema.json`. Which of the four defect families does each LINT line belong to?
2. **Baseline (2 min).** `python lab.py`. v0 is `REJECTED by API` (a 400 naming a schema keyword). Accuracy 0.000. You now have a measured starting point. Copy the error message into `evidence/notes.md`. Why is a rule like `minimum: 0` better enforced after the call than in the schema?
3. **v1: repair the schema only (6 min).** Copy v0's schema into `versions/v1.schema.json` and fix it by hand (use the contract only to check, not as a copy source). Copy v0's prompt unchanged into `versions/v1.prompt.txt`. Add the v1 line to `VERSIONS` in `lab.py`. `python schema_lint.py versions/v1.schema.json` must print `LINT CLEAN`.
4. **Measure v1 (2 min).** `python lab.py`. Which field is worst? That decides v2.
5. **Break it on purpose (3 min).** Read `data/break_it.jsonl` and `BREAK_IT.md`. Predict which cases v1 fails, then compare with the `BREAK_IT v...: x/5` line.
6. **Diagnose (3 min).** For each failing field name the root cause in one phrase in `evidence/notes.md`. Never fix by pasting a ticket from the data into the prompt as an example: that is example leakage and `check.py` detects copied text.
7. **Harden v2, v3, v4 (9 min).** One idea per version:
   - v2 vocabulary: map Sev-N and P-N to S-N, an impact-based rubric, "urgent!!!" is mood not impact, category definitions, canonical system names.
   - v3 nulls and rules: `users_affected` and `business_unit` null rules, `reported_at` only when date and time are stated, `needs_followup` rule.
   - v4 edge cases: injection defence, other languages, long tickets, several incidents, empty ticket. Also finish **TODO 1** (wrap the ticket as untrusted data) and **TODO 2** (keep head and tail of a long ticket).
8. **Measure and compare (4 min).** Do **TODO 3**. Run `python lab.py --compare-balanced` and compare accuracy and cost of fast vs balanced in `evidence/evidence.json`. Then `python check.py`.

## Architecture questions (answer in `evidence/notes.md`)
1. Why measure compliance against `target_schema.json` and not your own schema?
2. Structured outputs guarantee shape. Name two things they cannot guarantee that your harness measured.
3. A downstream team wants `users_affected >= 0`. Where does that rule live, and what happens to a row that breaks it?
4. Changing `output_config.format` between versions: what is the cost implication for compile latency and prompt caching?

## Checkpoints and expected results
- v0 rejected by the API; v1 not rejected and non-zero accuracy; at least four measured versions.
- Final overall field accuracy >= 0.80, schema compliance >= 0.95, BREAK_IT >= 3/5, final schema lints clean.
- Typical live range for the final version is 0.80 to 0.95. Your numbers will differ from run to run.
- `python check.py` ends with all checks PASS.

## Clean up
Delete `evidence/` to reset. Never commit `.env`.
