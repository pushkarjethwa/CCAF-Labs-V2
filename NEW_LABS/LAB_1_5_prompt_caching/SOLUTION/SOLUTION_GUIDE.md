# Solution guide: Lab 1.5 - Prompt caching (new)

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Prompt caching hands-on: mark a long, repeated prefix with `cache_control`, read `cache_creation_input_tokens` and `cache_read_input_tokens`, measure the saving, and learn that anything volatile must come after the cached block.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def cached_system()

What the TODO asks:

> TODO 1: return [{"type": "text", "text": ..., "cache_control": {"type": "ephemeral"}}] holding INSTRUCTIONS + POLICY.
> Only the block that carries cache_control (and everything before it) is cached.

Solution:

```python
return [{"type": "text", "text": f"{INSTRUCTIONS}\n\n{POLICY}", "cache_control": {"type": "ephemeral"}}]
```

### Block 2: def system_with_time()

What the TODO asks:

> TODO 2: put the time in a SECOND block placed AFTER the cached policy block, with no cache_control of its own.
> The starter puts the time first, so the prefix differs on every call and nothing is ever reused.

Solution:

```python
return cached_system() + [{"type": "text", "text": f"The current time is {now}."}]
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- run 1: nothing cached when the system prompt is a plain string
- run 2: the first call WROTE the cache (cache_write > 0)
- run 2: every later call READ the cache (cache_read > 0)
- run 2: caching cut the total cost by at least 40%
- run 3: a changing time AFTER the cached block still hits the cache
- every call returned an answer

## 4. Common mistakes

- Passing `system` as a plain string and expecting caching: only a block carrying `cache_control` marks a breakpoint.
- Putting the changing time before the cached block, so the prefix differs on every call and nothing is ever read.
- Putting `cache_control` on the volatile block.
- Expecting a cache hit on the very first call: the first call writes (1.25x), later calls read (0.1x).

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Minimum prefix: with a prefix below 512 tokens `cache_write` stays 0 and no error is raised. A saving you planned on silently does not exist, so always check the usage numbers.
2. One changing character at the START of the prefix changes everything after it: reads drop to 0 and you pay write prices.
3. `cache_control` on the small second block: the cached prefix is everything up to and including that block, which here includes the changing time, so it never matches again: no reads. It would work only if that block were stable.
4. After about 5 minutes without a hit the cache entry expires: the next call writes again (`cache_write > 0`, `cache_read == 0`).

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
