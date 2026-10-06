# Solution guide: Lab 2.6 - Use an MCP server from an agent (new)

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Being the MCP client: start a server over stdio, list its tools, convert MCP tool objects to Claude tool definitions, forward Claude's tool requests with `session.call_tool`, and convert results (and errors) back to `tool_result` content.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def mcp_tool_to_claude()

What the TODO asks:

> TODO 1: return that dict from the MCP tool object. name and description are attributes with those names.
> The JSON schema is `tool.input_schema` on SDK 2.x (older SDKs call it `tool.inputSchema`): try both.

Solution:

```python
schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
return {"name": tool.name, "description": tool.description or "", "input_schema": schema}
```

### Block 2: def result_to_text()

What the TODO asks:

> TODO 2: join the .text of every item in result.content that has type "text". is_error comes from `result.is_error`
> (older SDKs: `result.isError`). If there is no text at all return ("(empty result)", is_error).

Solution:

```python
text = "\n".join(item.text for item in result.content if getattr(item, "type", "") == "text")
is_error = bool(getattr(result, "is_error", getattr(result, "isError", False)))
return (text or "(empty result)"), is_error
```

### Block 3: async def answer()

What the TODO asks:

> TODO 3: result = await session.call_tool(block.name, dict(block.input)); then (text, is_error) = result_to_text(result);
> record block.name in tools_used and append a tool_result block (same tool_use_id, "is_error": True on errors).

Solution:

```python
result = await session.call_tool(block.name, dict(block.input))
text, is_error = result_to_text(result)
tools_used.append(block.name)
item = {"type": "tool_result", "tool_use_id": block.id, "content": text}
if is_error:
    item["is_error"] = True
results.append(item)
```

### Block 4: async def answer()

What the TODO asks:

> <<<SOLUTION

Solution:

```python
messages.append({"role": "user", "content": results})
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- TODO 1: an MCP tool becomes {name, description, input_schema}
- TODO 1: no extra keys (the API rejects unknown tool fields)
- TODO 1: also works with the older `inputSchema` attribute and a missing description
- TODO 2: joins several text items, is_error False
- TODO 2: keeps the error flag
- TODO 2: empty result gets a placeholder
- TODO 3: Claude's tool request was forwarded to the MCP session
- TODO 3: loop ends with Claude's final answer
- TODO 3: the server's text went back as a tool_result with the same id
- the client discovered both server tools
- on-call question answered from the notes via the server
- expense question answered from the notes via the server
- unknown note id: the server's error reached Claude and the loop ended cleanly

## 4. Common mistakes

- Passing the MCP tool object itself to Claude: it needs `{name, description, input_schema}` only (extra keys are rejected).
- Using `inputSchema` vs `input_schema` without checking the SDK version: the solution tries both.
- Dropping the error flag: Claude cannot tell a missing note from a note.
- Treating whatever the server returns as trustworthy instructions.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Only `search_notes`: Claude can find note ids and titles but cannot read the text, so it either says it cannot read them or guesses: a hallucination risk when a needed tool is missing.
2. Hiding the error flag: Claude may still say the note does not exist, but less reliably; sometimes the error text is treated as the note's content.
3. Wrong schema key (`inputSchema`) sent to the API: HTTP 400 (the tool's `input_schema` is required).
4. Untrusted server text: Claude may or may not follow an injected instruction in a tool result. Mitigations: tell the model tool results are data, allow-list tools, least privilege, human confirmation for sensitive actions, never give a server tools that can leak secrets.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
