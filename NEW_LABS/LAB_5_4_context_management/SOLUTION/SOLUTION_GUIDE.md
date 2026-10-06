# Solution guide: Lab 5.4 - Context management for a long run (new)

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Context management for a long run: estimate tokens cheaply, compact old bulky user turns to the line that matters, never touch assistant turns or the newest messages, and prove the facts you need still survive.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def estimate_tokens()

What the TODO asks:

> TODO 1: return the sum over all messages of len(message_text(m)) // 4.

Solution:

```python
return sum(len(message_text(m)) // 4 for m in messages)
```

### Block 2: def compact()

What the TODO asks:

> TODO 2: for every message EXCEPT the last `keep_last`:
> - assistant messages stay exactly as they are
> - a user message whose text is longer than 400 characters becomes {"role": "user", "content": "[compacted] " + its first line}
> - shorter messages stay as they are
> The last `keep_last` messages are copied unchanged.

Solution:

```python
result = []
cutoff = len(messages) - keep_last
for index, message in enumerate(messages):
    text = message_text(message)
    if index < cutoff and message["role"] == "user" and len(text) > 400:
        result.append({"role": "user", "content": "[compacted] " + text.splitlines()[0]})
    else:
        result.append(dict(message))
return result
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- TODO 1: 400 characters estimate to 100 tokens
- TODO 1: handles a message whose content is a list of blocks
- TODO 2: the input list is not modified
- TODO 2: same number of messages (roles keep alternating)
- TODO 2: an old bulky user message shrinks to its first line, which keeps the finding
- TODO 2: assistant messages are never changed
- TODO 2: the last 2 messages are untouched, even though the last user message is bulky
- TODO 2: short messages stay as they are
- compaction really reduces the estimated size
- without compaction the input grows on every call
- with compaction total input tokens are at least 30% lower
- with compaction the peak context is smaller
- with compaction Claude still answers about reports 2 and 9 (TLS certificate, full disk)

## 4. Common mistakes

- Mutating the input list in `compact` (the lab and `check.py` test for it).
- Compacting assistant messages or the last `keep_last` messages.
- Dropping messages instead of shrinking them: roles must keep alternating and facts must survive.
- Keeping the wrong part: the first line holds the FINDING; the rest is noise.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Dropping old messages: cost falls, but the answer about report 2 becomes wrong or invented ('I don't have that').
2. Keeping the last line instead of the first: you keep log noise and lose the finding, so Claude cannot name the cause (a hallucination risk).
3. Adjacent user messages: the current API combines consecutive same-role turns (older versions returned HTTP 400). Do not rely on that: keep roles alternating.
4. `KEEP_LAST = 0`: the newest bulky report is shrunk before Claude has read it. The one-sentence reply may survive because line 1 holds the finding, but any question that needs detail would fail. `keep_last` protects the turn being worked on.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
