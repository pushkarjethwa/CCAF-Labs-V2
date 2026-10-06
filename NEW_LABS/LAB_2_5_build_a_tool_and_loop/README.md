# Lab 2.5 - Build a tool and the tool loop from scratch (new)

**Time:** 45 min | **Needs API key** for `lab.py` (4 short chats); `check.py` Part A needs none | **Exam:** D2 Tool Design, D1 agentic loop

## Story
A library assistant needs facts it cannot know: where a book is shelved and when a loan is due. You write the tool schema, the dispatcher and the loop by hand with the plain Anthropic SDK, so there is no magic left.

## What you do (edit `lab.py`, top to bottom)
- STEP 1 (given): two plain Python functions.
- TODO 1: write the schema for `check_due_date` (the text Claude reads to decide when to use it).
- TODO 2: dispatcher: run the right function; unknown tool name gives an error, not a crash.
- TODO 3: the loop: send, check `stop_reason`, run tools, send ALL tool_results back in ONE user message, repeat; it always has an exit.
- TODO 4: crashes and error results become `is_error` tool_results instead of killing the loop.

## Run
```
pip install -r requirements.txt
python check.py     # Part A tests your loop with hand-made replies; no key
python lab.py       # real Claude; 4 questions: needs one tool, the other, both, none
python check.py
```
Read `claude_client.py` once (about 70 lines) to see where the key and the `messages.create` call live.
