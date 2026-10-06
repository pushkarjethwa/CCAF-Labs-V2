# Lab 2.2 - Travel Disruption Assistant: the tool loop, parallel reads, safe writes

**Time:** 35 min | **Day 2** | **Exam domain:** D2 Tool Design and MCP (also D1 Agentic Architecture) | **Topics:** the tool-use loop, parallel tools
Needs an API key for the final run only. New here? Read `../../../HOW_THE_CODE_WORKS.md` first.
**Cost:** about 6 short turns on the balanced model: a few cents.

## Scenario
Flight XA482 (LHR-JFK) was cancelled. The assistant must, for traveler T-1001: check the flight, list alternatives, check airport hotels and look up the loyalty tier (four **independent reads**), then **rebook, book a hotel, notify** (three **dependent writes**, each needing the reference returned by the one before).

The starter loop is wrong in four ways, and one tool definition is missing:

| # | Defect | What goes wrong |
|---|---|---|
| 0 | the `loyalty_tier` tool is not defined | Claude cannot look up the hotel rate cap |
| A | tool results go back one message at a time | the API rejects the next turn (400) |
| B | every tool call runs at once, even dependent writes | a hotel is booked with a reference that does not exist yet |
| C | a timed-out write is retried without an idempotency key | the traveler is rebooked twice |
| D | `while True` with no iteration guard | a model that never stops loops forever |

## Goal
1. Write a tool definition (name, description, schema) from scratch.
2. Return ALL `tool_result` blocks of one assistant turn in ONE user message, ids matching.
3. Run independent reads concurrently; run dependent writes one at a time behind a dependency gate.
4. Make a retried write safe with an idempotency key, and report an unknown outcome in a structured way.
5. Bound the loop.

## Files
| File | What |
|---|---|
| `lab.py` | The only file you edit. Search for `TODO`. The loop is in `run_agent`, tool execution in `run_tools` and `call_one` |
| `travel_services.py` | The mock airline, hotel and CRM (read it, do not edit). Its first rebooking commits and then times out, on purpose |
| `claude_client.py` | The only file that talks to Claude |
| `check.py` | Part A tests your code with hand-made inputs: no key, no model. Part B checks your real run |
| `data/scenario.json` | Flight, travelers, options, hotels, latencies |

## Steps
1. Read `lab.py` top to bottom, then skim `travel_services.py`. Run `python check.py`: it fails, as designed.
2. **TODO 0.** Write the `loyalty_tier` tool definition. Copy the style of the other tools.
3. **TODO A.** One user message with all results. Part A should pass the bundling check.
4. **TODO D.** Bound the loop.
5. **TODO B.** Concurrent reads, sequential gated writes.
6. **TODO C1 and C2.** Idempotency key on writes, and a structured timeout error.
7. `python check.py` until Part A is all PASS.
8. `python lab.py` with your key. Read the turn trace. Which reads did Claude request together? Did it hit the timeout and retry? Then `python check.py` for Part B.
9. Try `BREAK_IT.md`.

## Checkpoints
| # | You can show | Proof |
|---|---|---|
| 1 | Your own tool definition used by Claude | Part B |
| 2 | One user message carrying every tool_result of a turn | Part A |
| 3 | Reads ran concurrently, writes sequentially and gated | Part A |
| 4 | A timed-out rebooking retried with the same key: exactly one booking | Part A and B |
| 5 | A runaway model is stopped | Part A |

## Expected results
- Part A: 11 PASS lines. Part B: all PASS after a real run.
- A real model may or may not hit every trap (for example it may not send dependent writes together). That is why Part A tests your code with hand-made inputs.
- Typical live run: 4 to 6 turns, the four reads in one turn, one timeout, one retry, one summary.

## Clean up
Delete `evidence/` to reset. Never commit `.env`.

## Stuck?
Try the lab first. If you need a hint or want to compare, open `SOLUTION/SOLUTION_GUIDE.md` (solutions, expected results, answers to BREAK_IT).
