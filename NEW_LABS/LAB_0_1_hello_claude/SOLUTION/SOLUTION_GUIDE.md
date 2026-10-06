# Solution guide: LAB 0.1 - Hello Claude: the Messages API from scratch

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

The Messages API from scratch: one call, a follow-up that needs conversation history, `max_tokens` cut-off (`stop_reason`), a deliberate API error, and token cost.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def step1_single_call()

What the TODO asks:

> TODO 1: call ask() with one user message containing TICKET, and pass system=SYSTEM.

Solution:

```python
response = ask([{"role": "user", "content": TICKET}], system=SYSTEM)
```

### Block 2: def step2_second_turn()

What the TODO asks:

> TODO 2: build a messages list with 3 entries: the first user message (TICKET), Claude's first
> answer as an "assistant" message, then FOLLOW_UP as a new "user" message. Call ask().

Solution:

```python
messages = [
    {"role": "user", "content": TICKET},
    {"role": "assistant", "content": text_of(first_response)},
    {"role": "user", "content": FOLLOW_UP},
]
response = ask(messages, system=SYSTEM)
```

### Block 3: def step3_truncated_answer()

What the TODO asks:

> TODO 3: call ask() with the TICKET but max_tokens=20 (Sonnet 5.5 may need more room to start answering;
> if you get an empty answer that is also fine). Then set was_cut_off = True when
> response.stop_reason == "max_tokens".

Solution:

```python
response = ask([{"role": "user", "content": TICKET}], system=SYSTEM, max_tokens=20)
was_cut_off = response.stop_reason == "max_tokens"
```

### Block 4: def step4_handle_error()

What the TODO asks:

> TODO 4: call ask(bad_messages) inside try/except anthropic.BadRequestError as error.
> On error, save str(error) in error_text. If no error happens, error_text stays "".

Solution:

```python
error_text = ""
try:
    ask(bad_messages, system=SYSTEM)
except anthropic.BadRequestError as error:
    error_text = str(error)
```

### Block 5: def step5_total_cost()

What the TODO asks:

> TODO 5: total = sum of cost_usd(r) for every response in the list.

Solution:

```python
total = sum(cost_usd(response) for response in responses)
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- STEP 1: Claude answered
- STEP 1: stop_reason is end_turn
- STEP 2: follow-up answered
- STEP 3: max_tokens=20 cut the answer and you detected it
- STEP 4: BadRequestError caught and message saved
- STEP 5: total cost is a small positive number

## 4. Common mistakes

- Sending only the new user message in step 2. Claude has no memory between calls: you must resend the earlier user message AND Claude's earlier answer as an assistant message.
- Reading `response.content` as a string. It is a list of blocks; use `text_of(response)`.
- Treating `stop_reason == 'max_tokens'` as success. A cut-off answer is incomplete: detect it and raise `max_tokens` or ask for brevity.
- Catching a bare `Exception` for step 4. Catch `anthropic.BadRequestError` so real bugs are not hidden.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Without `system`, the answer loses the persona and format rules from the system prompt (usually longer, more generic).
2. Two user messages in a row: current API versions merge consecutive same-role turns, so Claude sees both texts but never its own earlier reply. Conversation state is what YOU send, and a missing assistant turn can change the answer.
3. `max_tokens=0` raises `anthropic.BadRequestError` (HTTP 400): the value must be at least 1.
4. A made-up model name raises `anthropic.NotFoundError` (HTTP 404).
5. `temperature=0` raises a `TypeError` from the SDK before any request is sent: this SDK version has no such argument, and Sonnet/Opus 5.5 reject sampling parameters anyway.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
