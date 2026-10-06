# Lab 1.4 - PO Reconciliation: a validated, cached, batched service

**Time:** 40 min | **Day 1** | **Exam domain:** D4 Prompt and Structured Output | **Topic:** cost engineering: prompt caching, token counting, Message Batches
Needs an API key. New here? Read `../../../HOW_THE_CODE_WORKS.md` first.
**Cost:** two normal calls plus a 40-request batch of about 6.5k input tokens each. Roughly $0.10 to $0.50 on the fast model. The budget gate refuses to submit a batch projected above `RUN_BUDGET_USD` ($0.50).

## Scenario
Hartwell's accounts-payable team receives about 100,000 supplier invoices a month. Each invoice must be matched against its purchase order and goods receipt under a long procurement policy (duplicates, no PO, vendor mismatch, price tolerance, billed vs received quantity, freight caps).

A prototype exists and "works", but it re-sends the whole ~6,000-token policy at full price on every call, never reads the cache, joins batch results by position, and has no cost gate. You turn it into a cached, batched, cost-aware service and write a short memo.

## Goal
1. Find and remove a silent cache invalidator in the system prompt and prove it with `cache_read_input_tokens > 0` on the second call.
2. Count tokens for two models and gate a batch on a worst-case budget.
3. Submit a 40-invoice batch and join the results on `custom_id`, not by position.
4. Read the 100,000-invoices-a-month projection (normal, cached, batch, batch plus cached) and choose the service model.

## Files
| File | What |
|---|---|
| `lab.py` | The service. Three TODOs: TODO 1 `build_system`, TODO 2 `run_batch`, TODO 3 `count_for_models` and `budget_gate`. Validation and projection are provided |
| `claude_client.py` | The only file that talks to Claude (the batch and token-count calls use its `get_client()`) |
| `check.py` | Part A needs no key. Part B reads `evidence/evidence.json` |
| `data/` | The ~24k-character policy (the cached prefix), 40 invoices, purchase orders, ground truth, planted bad decisions |

## Steps
1. `python check.py` fails on the starter (Part A). Read `lab.py` top to bottom first.
2. **TODO 1.** Fix `build_system` so the cached prefix is identical on every call. Part A should now pass its prompt check.
3. **TODO 3b.** Write `budget_gate`. Part A should pass the gate check. (Worst case: batch price, no cache hits.)
4. **TODO 3a.** Write `count_for_models`.
5. **TODO 2.** Rebuild the batch join on `custom_id`.
6. `python lab.py`. Read each numbered section of the output. Is `cache_read_input_tokens` above zero on call 2?
7. Write `evidence/capstone_day1.md` (150+ words): a section "What the service does", a section "Model choice" naming the chosen model class with $ figures from the projection table, and what you learned about caching and batch.
8. `python check.py`. Then try `BREAK_IT.md`.

## Checkpoints
| # | You can show | Proof |
|---|---|---|
| 1 | Call 1 wrote the cache; call 2 read it | Part B |
| 2 | The gate refuses an over-budget batch and flags a prefix below the model's cache floor | Part A |
| 3 | 40 of 40 results joined by `custom_id` with no mismatches | Part B |
| 4 | A written model choice backed by the projection table | memo |

## Expected results
- Fast model cache floor is 4096 tokens and the policy is larger than that, so caching works. A shorter prefix would silently never cache (see Break 3).
- Projection order for each model: batch plus cached is cheapest, then batch, then cached, then normal. Exact dollars depend on measured tokens.
- Batch cache hits are best effort, so `cache_read_input_tokens` in the batch can be lower than in the normal calls.

## Clean up
Delete `evidence/` to reset. Never commit `.env`.
