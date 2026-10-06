# Solution guide: Lab 2.5 - Build a tool and the tool loop from scratch (new)

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Building the tool-use loop yourself with the raw SDK: a schema, a dispatcher, tool errors that do not kill the loop, and a loop that appends the assistant turn, answers every tool_use in ONE user message, and always has an exit.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: CHECK_DUE_DATE_TOOL

What the TODO asks:

> TODO 1: write the schema for check_due_date(member_id). Needs: name, a description that says when to use it,
> and an input_schema with a required string property member_id (format M-123). Mirror FIND_BOOK_TOOL.

Solution:

```python
CHECK_DUE_DATE_TOOL = {
    "name": "check_due_date",
    "description": "Look up the book a library member currently has on loan and its due date. Use when someone asks when something is due or what a member has borrowed. Read-only.",
    "input_schema": {"type": "object", "properties": {"member_id": {"type": "string", "description": "Member id in the form M-123"}}, "required": ["member_id"]},
}
```

### Block 2: def run_tool()

Solution:

```python
if name == "check_due_date":
    return check_due_date(**tool_input)
```

### Block 3: def run_tool_safely()

What the TODO asks:

> TODO 4: wrap run_tool in try/except Exception. On a crash return (json string of {"error": "tool_crashed", "detail": str(exc)}, True).
> Also return is_error True when the result dict has an "error" key (for example book_not_found), so Claude knows the call failed.

Solution:

```python
try:
    result = run_tool(name, tool_input)
except Exception as exc:  # noqa: BLE001 - a tool crash is reported to the model, not raised
    return json.dumps({"error": "tool_crashed", "detail": str(exc)}), True
return json.dumps(result), "error" in result
```

### Block 4: def answer()

What the TODO asks:

> TODO 3: if response.stop_reason is not "tool_use", return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}.
> Otherwise: (a) append {"role": "assistant", "content": response.content} to messages,
> (b) for EVERY block in tool_calls_of(response) run run_tool_safely(block.name, block.input) and build
> {"type": "tool_result", "tool_use_id": block.id, "content": <string>} (add "is_error": True on errors),
> (c) append ONE user message whose content is the list of ALL those tool_result blocks. Then loop.

Solution:

```python
if response.stop_reason != "tool_use":
    return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}
messages.append({"role": "assistant", "content": response.content})
results = []
for block in tool_calls_of(response):
    content, is_error = run_tool_safely(block.name, dict(block.input))
    tools_used.append(block.name)
    result = {"type": "tool_result", "tool_use_id": block.id, "content": content}
    if is_error:
        result["is_error"] = True
    results.append(result)
messages.append({"role": "user", "content": results})
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- TODO 1: check_due_date schema has name, a real description, and required member_id
- TODO 2: dispatcher runs find_book
- TODO 2: dispatcher runs check_due_date
- TODO 2: unknown tool name returns an error dict, no crash
- TODO 4: an error result is flagged is_error=True
- TODO 4: a crashing tool is caught and reported
- TODO 4: a good result is a JSON string with is_error False
- TODO 3: no tool needed, loop ends after 1 turn
- TODO 3: one tool call, then the final answer in turn 2
- TODO 3: turn 2 sends user, assistant (tool_use), user (tool_result)
- TODO 3: tool_result carries the SAME id as the tool_use
- TODO 3: two tool calls in one turn -> ONE user message with both tool_results
- the loop has an exit: it stops after MAX_TURNS tool-requesting turns
- Dune question: find_book used, answer has shelf SF-12
- due-date question: check_due_date used, answer has the date
- combined question: both tools used
- France question: no tool, Claude answered directly

## 4. Common mistakes

- Sending each tool_result in a separate message when Claude requested two tools in one turn.
- Forgetting to append the assistant turn (`response.content`) before the tool_results.
- Returning a Python dict instead of a string in `content`.
- No `is_error` flag, so Claude cannot tell a failed lookup from a result.
- Letting an exception inside a tool crash the loop.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Vague descriptions: with two clearly named tools Claude often still picks correctly; the 'both' question and larger tool sets fail first.
2. A made-up `tool_use_id`: HTTP 400, every `tool_use` needs a `tool_result` with the same id in the next user message.
3. Split results for a two-tool turn: HTTP 400 for the same reason: all tool_results for one assistant turn must come in ONE user message.
4. No exit: each turn is one API call and the whole history is resent every time, so cost grows roughly quadratically; keep `MAX_TURNS` small and stop on repeated errors.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
