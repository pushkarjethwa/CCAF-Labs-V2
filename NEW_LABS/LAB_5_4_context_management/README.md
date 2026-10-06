# Lab 5.4 - Context management for a long run (new)

**Time:** 40 min | **Needs API key** (about 30-50 cents; two runs of 11 calls, up to 16k tokens each) | **Exam:** D5 Context and Reliability

## Story
An ops assistant reads 10 long incident reports in one conversation. Every call re-sends the whole history, so cost and latency grow every turn. You write the step that shrinks old bulky turns to their key line, then prove that the facts you need later survive.

## What you do (edit `lab.py`)
- TODO 1: `estimate_tokens(messages)`, a cheap 4-characters-per-token estimate.
- TODO 2: `compact(messages)`: shrink old long user messages to their first line; never touch assistant messages, the last 2 messages, or the input list.

## Run
```
pip install -r requirements.txt
python check.py     # Part A: your functions on hand-made messages, no key
python lab.py       # run 1: no compaction, run 2: compaction; prints input tokens per call
python check.py
```

## What to look at
The input-token list for run 1 climbs every call. Run 2 flattens once the budget is passed. The final question asks about reports 2 and 9: Claude can only answer because line 1 of each report (the FINDING) was kept. Decide what to keep BEFORE you compact.

## Stuck?
Try the lab first. If you need a hint or want to compare, open `SOLUTION/SOLUTION_GUIDE.md` (solutions, expected results, answers to BREAK_IT).
