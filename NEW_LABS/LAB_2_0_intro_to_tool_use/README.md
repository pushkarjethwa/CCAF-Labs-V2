# Lab 2.0 - Intro to tool use: why tools, how to create one, how Claude uses it (new)

**Time:** 20-25 min | **Needs API key** for `lab.py` (about 10 short calls, a few cents); `check.py` Part A needs none | **Exam:** D2 Tool Design (foundation for all of Day 2)

This is the self-contained, run-it-yourself version of the trainer's Demo 2.0. Do it before Lab 2.1. It has no TODOs: you run each step, read the printed round trip, and match it to the code. Lab 2.5 is the follow-up where you write a tool and the loop yourself.

## Story
A store support assistant. A customer asks "Where is my order ORD-1001?" Claude cannot know that: the orders live in your system.

## The one idea
> Claude never runs your code. It **asks** for a tool call. Your program runs it and sends the result back.

```
question -> Claude: "please call get_order_status(ORD-1001)"   (stop_reason = tool_use)
         -> YOUR code runs the real function
         -> you send the result back -> Claude writes the answer (stop_reason = end_turn)
```

## The three steps
| Step | Command | What you see |
|---|---|---|
| 1 | `python lab.py --step 1` | Same question, **no tools**: Claude cannot see order data |
| 2 | `python lab.py --step 2` | **Create** one tool, then the full round trip stage by stage: definition, Claude's request, our code runs it, result sent back, final answer |
| 3 | `python lab.py --step 3` | Two tools attached. Four questions: needs the order tool, the policy tool, both, none. You never pick; Claude reads the descriptions |

## Where the tool-creation code is
Open `lab.py` and read **PART A**. A tool is three parts: (1) a plain function, (2) a schema (`name`, `description`, `input_schema`), the only thing Claude sees, (3) a dispatcher `run_tool()` that maps the name Claude chose to your function. The loop in step 2 is spelled out line by line; `answer_with_tools()` is the same loop packaged for step 3.

## Run
```
pip install -r requirements.txt
python lab.py --step 1      # then 2, then 3 (or just: python lab.py)
python check.py
```
Read `claude_client.py` once (about 70 lines): it is where the key, the client and `messages.create` live.

## Predict first
Before step 1: can Claude answer this? (No.) Before step 2C: did Claude run the lookup? (No: it only wrote a request.) Before step 3: for the question with both topics, how many tool calls? (Two, in one turn.)

## Next
Lab 2.1: what happens when tool names and descriptions are bad. Lab 2.5: write a tool and the loop yourself.
