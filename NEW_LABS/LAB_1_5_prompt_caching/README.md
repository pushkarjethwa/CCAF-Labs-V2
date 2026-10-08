# Lab 1.5 - Prompt caching (new)

**Time:** 30 min | **Needs API key** (15 short calls, about 10-20 cents) | **Exam:** D4/D5 cost and latency, prompt caching

## Story
A support bot answers many questions with the same 7,000-word policy in the system prompt. You mark the policy as cacheable, read the cache numbers in the response, measure the saving, and learn what silently breaks the cache.

## What you do (edit `lab.py`)
- TODO 1: return the system prompt as a list of blocks, with `cache_control` on the policy block.
- TODO 2: add the current time as a second block AFTER the cached block (the starter puts it first, so nothing is ever reused).

## Run
```
pip install -r requirements.txt
python lab.py      # three runs of 5 questions; prints input / cache_write / cache_read / cost per call
python check.py
```

## What to look at
`cache_write` on the first call (you pay 1.25x once), `cache_read` on the rest (0.1x). If `cache_read` stays 0, the prefix is not identical from character 1, or it is below the minimum size (512 tokens on Sonnet 5.5 and Haiku 5.5; some older models need more, such as 4096 on Haiku 4.5).

Caches live for about 5 minutes and are refreshed on each hit. `lab.py` adds a unique first line per run, so one run never hits the cache of an earlier run.

## Stuck?
Try the lab first. If you need a hint or want to compare, open `SOLUTION/SOLUTION_GUIDE.md` (solutions, expected results, answers to BREAK_IT).
