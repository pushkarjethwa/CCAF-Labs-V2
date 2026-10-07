# Lab 1.3 - Warehouse Receiving Emails: Validate and Retry

**Time:** 35 min | **Day 1** | **Exam domain:** D4 Prompt and Structured Output (also D5 Reliability) | **Topics:** structured extraction, validation and retry
New here? Read `../../../HOW_THE_CODE_WORKS.md` first.

## Scenario
Hartwell Distribution's dock staff write free-text emails when a truck arrives ("30 bundles of PLT-STD-48 ... a few are dusty"). Receiving clerks must turn each email into a goods-receipt record and compare it with the purchase order (PO). Schema-valid JSON is not enough: a model can return perfectly shaped JSON that says 400 received against 360 ordered with `condition: "ok"`, or that invents a PO number the email never mentioned.

You build the **semantic validators** that catch those mistakes, and a **bounded corrective retry loop** that tells the model exactly what it got wrong. Emails that cannot be fixed go to `needs_review`, so nothing unverified reaches the ERP.

## Goal
1. Implement the semantic validators (SKU, quantity vs condition, unit conversion, dates, PO grounding, follow-up flag).
2. Replace an unbounded retry-with-the-same-prompt loop with a bounded corrective retry (original request + invalid output + exact failures).
3. Log every attempt and route exhausted emails to `needs_review`.
4. Read the validator hit table as an engineering signal.

## Files
| File | What |
|---|---|
| `lab.py` | The only file you edit. STEP 0 schema and prompt (provided), STEP 2 validators (TODO 1-4), STEP 3 retry loop (TODO 5-6), STEP 4 runner (provided) |
| `claude_client.py` | The only file that talks to Claude. Read it once |
| `check.py` | Part A tests your validators with no API key. Part B tests the loop from `evidence/evidence.json` |
| `data/` | 20 emails, 10 purchase orders, ground truth, 15 planted bad outputs |
| `BREAK_IT.md`, `CHALLENGE.md` | Deliberate failures and a stretch task |

## Steps
1. `python check.py` - it FAILS on the starter, as designed.
2. Do TODO 1-4 (validators). Re-run `python check.py` until Part A is all PASS. No API key needed.
3. Set up your key, then `python lab.py --only GR-005,GR-017` to see the broken loop on two emails (the starter loop has no cap; a safety net stops it after 12 calls).
4. Do TODO 5-6 (retry loop). Run `python lab.py` (all 20 emails, up to 3 attempts each; costs a few cents).
5. `python check.py` - Part B should PASS.
6. Read the validator hit table. Which rule fired most? Which email needed 3 attempts?
7. Try `BREAK_IT.md`. Then compare `python lab.py --model fast`.

## Checkpoints
| # | You can show | Proof |
|---|---|---|
| 1 | Baseline: you can name the defects in the starter loop (no cap, same prompt resent, no log, no fallback) | `lab.py --only ...` output |
| 2 | Every validator fires on its planted case; no false alarms on the 20 correct records | Part A all PASS |
| 3 | Retry sends original request + invalid output + exact failures | `feedback` check in Part B |
| 4 | Attempts bounded by `MAX_ATTEMPTS` (write down: why 3, what would 10 cost?) | Part B |
| 5 | `needs_review` only when attempts are exhausted | Part B |
| 6 | Break-It tried and the effect noted | your notes |

## Expected results
- Part A: 17 PASS lines (15 planted cases, the false-alarm check, the failure-shape check).
- Part B: all PASS. Exact counts of retries and `needs_review` depend on the live model and will vary between runs. A strong model may need few retries.
- Cost: well under $0.50 for a full run on the balanced model.

## Clean up
Delete `evidence/` to reset. Never commit your `.env`.

## Stuck?
Try the lab first. If you need a hint or want to compare, open `SOLUTION/SOLUTION_GUIDE.md` (solutions, expected results, answers to BREAK_IT).
