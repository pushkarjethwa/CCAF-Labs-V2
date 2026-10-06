# LAB 0.1 - Hello Claude: the Messages API from scratch

**Time:** 20 minutes | **Needs:** an API key (see `../../HOW_THE_CODE_WORKS.md`) | **Exam domain:** D4 Prompt and Structured Output, D1 foundations

## Goal
Make your first calls to Claude with the plain SDK. By the end you can explain what goes into a request, what comes back, why you must send the whole conversation each time, and what to do when a call fails.

## What you do
Open `lab.py`. Five steps, each with one `TODO`:

| Step | You practise |
|---|---|
| 1 | One call: `system` + one user message |
| 2 | A second turn: the API has no memory, so you resend the conversation |
| 3 | `max_tokens` too small: detect `stop_reason == "max_tokens"` |
| 4 | A bad request: catch `anthropic.BadRequestError` |
| 5 | Cost: add up `cost_usd()` for each call |

## Before you start
1. Read `claude_client.py` (70 lines). Find the key, the client and `client.messages.create`.
2. Run `python claude_client.py`. You should see a greeting.

## Run
```
python lab.py
python check.py
```
`check.py` needs `evidence/evidence.json`, which `lab.py` writes. Expect `RESULT: 6/6 checks passed`. Total cost is a fraction of a cent.

## Checkpoints
- After step 1: you see Claude's answer and a `[usage]` line.
- After step 3: the answer ends mid-sentence and `was_cut_off = True`.
- After step 4: you see the error text, and the program keeps running.

## Files
`lab.py` (you edit), `claude_client.py` (read it), `check.py`, `BREAK_IT.md`, `CHALLENGE.md`, `requirements.txt`.
