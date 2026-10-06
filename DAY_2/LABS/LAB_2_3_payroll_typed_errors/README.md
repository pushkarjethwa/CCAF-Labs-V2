# Lab 2.3 - Payroll agent: typed errors, bounded retries, escalation

**Time:** 75-90 min | **Key:** `check.py` Part A needs none; `lab.py` needs one (6 short runs, a few cents) | **Exam:** D2 Tool Design (errors), D5 Reliability

## Story
A payroll agent applies pay adjustments. When a call fails, a bare string like `Error: pay period closed` gives Claude nothing to act on, and the starter retries everything forever. You make failures **typed** (so Claude can branch), **bounded** (retry only what is transient) and **safe** (permission errors escalate to a human, never retry).

## What you do (all in `lab.py`)
Section 2: TODO 1 error catalog, TODO 2 retry table, TODO 3 fail-closed `policy_for`, TODO 4 structured `to_tool_result`, TODO 5 approval request.
Section 3: TODO A block repeats, B bounded retry with backoff, C budget-exhausted result, D escalate permission errors.
Sections 1 and 4 (tools, agent loop) are given. `payroll_db.py` is a mock back end with a **simulated clock**: waiting is instant. Do not edit it.

## Run
```
pip install -r requirements.txt
python check.py     # Part A: tests your code with hand-made failures, no key. Iterate here
python lab.py       # real Claude runs 6 scenarios
python check.py     # Part B adds the real-run checks
```
Scenarios: S1 happy path, S2 closed period, S3 wrong employee id, S4 amount over threshold, S5 lock that clears, S6 lock that never clears.

## Notes
Claude may behave sensibly in S2-S4 even with poor errors. The difference shows in DB attempt counts, wait time and escalations, which `lab.py` prints. Part A is what proves your policy holds when a model misbehaves.
