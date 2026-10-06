# Solution guide: Lab 2.0 - Intro to tool use: why tools, how to create one, how Claude uses it (new)

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Why an agent needs tools and how Claude uses them: a tool is a function, a schema and a dispatcher; Claude only asks for a call (stop_reason `tool_use`), your code runs it and returns a `tool_result`.

## 2. Answer key for the run-it-yourself stages

This lab has no TODOs: you run stages and read results. These are the answers to the PREDICT prompts and what the output should show. Your numbers will differ run to run and by model version; the shape should match.

- Before step 1 (can Claude answer?): No. The order data lives in your system.
- Step 1 observation: Claude says it cannot see the order (or invents a plausible one: both are the argument for tools).
- Step 2: `stop_reason` is `tool_use` on the first response and `end_turn` on the second. Claude did NOT run the lookup; it wrote a request with an id.
- Step 3 expected tools: order question -> `get_order_status`; policy question -> `get_return_policy`; combined question -> both (usually in one turn); greeting -> none.

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- dispatcher runs get_order_status
- dispatcher runs get_return_policy
- unknown order returns an error dict
- unknown tool name returns an error dict
- each schema has a name, a 'when to use' description and an object input_schema
- step 1: no tools, so Claude could not know the order's carrier
- step 2: Claude REQUESTED get_order_status(ORD-1001) (stop_reason tool_use)
- step 2: after the tool_result, Claude finished (end_turn)
- step 2: the final answer uses the data our code returned
- step 3: order question used only the order tool
- step 3: policy question used only the policy tool
- step 3: combined question used both tools
- step 3: a greeting used no tool

## 4. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Vague descriptions: with two clearly named tools Claude often still picks correctly, but the 'needs both' question and any larger tool set degrade first. Descriptions are how Claude decides.
2. Wrong `tool_use_id`: HTTP 400. Every `tool_use` must be answered by a `tool_result` with the same id in the very next user message.
3. Skipping the tool_result message: HTTP 400 for the same reason (a `tool_use` without a matching `tool_result`).
4. Removing the order tool but keeping the system prompt: a good model refuses to invent the carrier and says it cannot look it up; a weaker one may guess. That is why 'never invent details' belongs in the system prompt.

## 5. Files in this folder

- `SOLUTION_GUIDE.md`: this file
