# Lab 1.1 - HR Roster Classification: which model is good enough, and what does it cost at scale?

**Time:** 30 min | **Day 1** | **Exam domain:** D4 Prompt and Structured Output | **Topic:** the Claude mental model and the Messages API
Needs an API key. New here? Read `../../../HOW_THE_CODE_WORKS.md` first.
**Cost:** a full run is well under $0.50. Measure your own (the table prints it).

## Scenario
People-Ops has a 100,000-row export of HR roster records. Titles are free text ("Sr. (acting) Engineering Manager", "DevOps Engineer ... contract-to-hire", "0.8 FTE"). Payroll routing, approval chains and headcount reports need three clean fields per row: `job_family`, `level` (L1-L6) and `employment_type`.

You must **measure** which model is the cheapest one that is accurate enough, and write the decision down with numbers.

## Goal
1. Run one classifier against three model tiers and compare exact-match accuracy, schema compliance, latency, tokens and cost per 1k rows.
2. Learn which sampling parameters this SDK and each model accept (the `temperature` crash that old tutorials cause).
3. Keep the expensive model on a short leash in code: only the 8 "hard" rows, with a hard call ceiling.
4. Project the 100,000-row cost from measured tokens and write a decision memo with one rejected alternative and a numeric reason.

## Files
| File | What |
|---|---|
| `lab.py` | The harness. Edit the `PLAN` list in `main()` (TODO 1 and TODO 2) |
| `claude_client.py` | The only file that talks to Claude |
| `decision_template.md` | Memo skeleton. Copy to `evidence/decision.md` |
| `check.py` | Validates your evidence and memo, no API key needed |
| `data/roster.jsonl` | 40 messy rows with ground truth; 8 flagged `"hard": true` |
| `data/break_rows.jsonl` | 3 hostile rows for `BREAK_IT.md` |

## Steps
1. Read `claude_client.py`, then `lab.py` top to bottom. Find the one line where a row is sent to Claude (`classify`).
2. `python lab.py --probe`. Which way of sending `temperature` fails on which model, and with which error? Write it in `evidence/notes.md`.
3. `python lab.py`. The starter measures the fast model only. Note its exact accuracy and cost per 1k rows.
4. **TODO 1:** add the balanced model on all 40 rows to `PLAN`. Run again.
5. **TODO 2:** add the premium model on the 8 hard rows only. Think about the spending limit first. Run again.
6. Read `evidence/results_table.md`. Compare accuracy, hard-row accuracy, latency and cost per 1k rows.
7. Copy `decision_template.md` to `evidence/decision.md` and fill every `[[placeholder]]`. Keep the labels `Decision:`, `Rejected:` and `Projection` at the start of their lines.
8. `python check.py`.
9. Try `BREAK_IT.md`.

## Checkpoints
| # | You can show | Proof |
|---|---|---|
| 1 | The temperature probe result and why each form fails | `evidence/param_probe.json` |
| 2 | At least two models measured on all 40 rows | `check.py` |
| 3 | Premium measured on exactly the 8 hard rows, 8 calls at most | `check.py` |
| 4 | A decision memo with a rejected alternative and the projected 100,000-row cost | `check.py` |
| 5 | Break-It tried and noted | your notes |

## Expected results
- Exact accuracy usually rises from fast to balanced to premium, but not always, and the gap on the 8 hard rows matters most. Your numbers will differ per run.
- The balanced model costs roughly 2x per token what the fast model does; premium roughly 4x.
- `python check.py` ends with all checks PASS once the memo is filled.

## Clean up
Delete `evidence/` to reset. Never commit `.env`.
