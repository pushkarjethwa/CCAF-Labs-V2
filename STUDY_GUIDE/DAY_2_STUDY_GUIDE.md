# Day 2 Quick Guide and Recap: Tool Design and MCP

## What this day is about
Claude cannot run your code. It asks for a tool call, and your program does the work.
Today you learn to design good tools, run the loop safely, handle failures, and share tools through MCP.
Use this page as a quick recap. The full guides (linked at the end) hold the detail.

## Your day at a glance
You watch the demos run. You do the labs yourself.

| Demo or lab | What it covers | Idea it practises |
|---|---|---|
| Lab 2.0: Intro to tool use | Run a small tool round trip and read it | Claude asks, your code acts |
| Demo: Intro to MCP | A pizza kitchen with three apps, with and without MCP | One standard plug (N x M becomes N + M) |
| Demo: MCP server and client as separate apps | Two programs that share no code | Client and server only share the standard |
| Demo 2A: Bad to good tool architecture | 12 overlapping tools fixed in steps | Tool descriptions and boundaries |
| Lab 2.1: Facilities tool boundaries | Rewrite, merge and scope tools, then measure | Claude picks the right tool |
| Demo 2B: The tool-use loop as a state machine | A refund assistant that fails and recovers | Typed errors, bounded retries |
| Lab 2.3: Payroll typed errors | Make the payroll agent fail safely | Errors are information |
| Demo 2C: Parallel tools without a double charge | Fast reads, ordered writes | Which calls may run together |
| Lab 2.2: Travel disruption tool loop | Run one turn's calls safely | Concurrent reads, gated writes |
| Demo 2D: MCP from zero to enterprise-shaped | A CRM server with sign-in and roles | MCP security |
| Lab 2.4: Procurement MCP server | Build and lock down a server | 401, 403, no keys in logs |
| Lab 2.5 and 2.6 (optional) | Build the loop yourself, then use an MCP server | The loop, and MCP as a client |

## 1. The tool-use loop
**In one line:** Claude replies `stop_reason: "tool_use"`, your code runs the tool, and you send the result back until Claude says `end_turn`.

**Analogy:** A diner orders from a menu. The kitchen cooks and returns the dish with the same ticket number. The diner never enters the kitchen.

**Tiny example:**
```python
for turn in range(1, MAX_TURNS + 1):                    # your own exit
    response = client.messages.create(model=MODEL, max_tokens=2048, tools=tools, messages=messages)
    if response.stop_reason != "tool_use":
        break
    messages.append({"role": "assistant", "content": response.content})
    results = [{"type": "tool_result", "tool_use_id": b.id, "content": run(b)}
               for b in response.content if b.type == "tool_use"]
    messages.append({"role": "user", "content": results})   # ALL results, ONE message
```

**Recap:**
- Claude asks. Your code acts. Send `tools` in every request.
- Each `tool_result` uses the same id as its `tool_use`. All results go in one user message, results first.
- Break a rule and the API answers HTTP 400.
- Always add a turn limit. The API never stops a loop for you.

## 2. Tool design and selection
**In one line:** Claude sees only the name, description and schema, so a wrong pick is usually a menu problem.

**Analogy:** A menu with three dishes called "Chicken", "Chicken dish" and "Chicken special". The diner guesses. The menu is bad, not the cook.

**Tiny example:**
- Before: `"Look up a book."`
- After: `"Look up one book by title: its shelf code. Use when someone asks where a book is. Read-only."`

**Recap:**
- A good description says what the tool does, when to use it, when not to, and its limits.
- One verb on one noun. Split reads from writes. Merge same-kind operations behind an `action` enum. Remove old duplicates.
- Measure first: run a fixed prompt set with `tool_choice` on `auto`, and read the confusion pairs (wanted X, got Y).
- Give each desk only the tools it needs, and keep a handoff to a human. Return only the fields Claude needs.

## 3. Tool errors, retries and escalation
**In one line:** A failure is information. Send it back as a typed error with `is_error: true`, and let your code own the retry rules.

**Analogy:** A kitchen that says "we are out of fish, try the chicken" instead of shouting "Error!".

**Tiny example (a typed error, a small note with fixed fields):**
```json
{"error_code": "PERMISSION_DENIED", "category": "permission", "retryable": false,
 "hint": "Do not retry. Tell the customer a supervisor will review the case."}
```

**Recap:**
- Ask who can fix it. Bad input: Claude corrects it. Temporary problem: your code retries. Permission: a human decides. Broken tool: stop and alert.
- A safe retry has a gate (only retryable environment errors), a budget (a fixed number of tries) and backoff (wait longer each time).
- When the budget ends, tell Claude "do not call this again". Unknown errors should fail closed: not retryable.
- A write that times out may already have happened. Use an idempotency key (a receipt number) before any retry.

## 4. Parallel tool calls and ordering
**In one line:** Claude decides how many calls go in one turn. Your code decides which of them may overlap.

**Analogy:** Many people can look at a shop window at once. Two people cannot both buy the last jacket.

**Tiny example:**
- Four independent reads at 1 second each: 4 seconds one by one, about 1 second together.
- Reserve stock, then charge, then confirm: one at a time, in order.

**Recap:**
- Independent reads can run together. The time is the slowest call, not the sum.
- Dependent writes run one at a time, with a gate before each. Refuse any reference that no tool returned.
- However you run them, answer once: all results in one user message, one per ticket.
- `disable_parallel_tool_use` and a turn limit help, but a gate and an idempotency key do the real protecting.

## 5. MCP basics
**In one line:** MCP (Model Context Protocol) is an open standard, so you build one server and any MCP app can use it.

**Analogy:** USB-C. One plug replaces a drawer of chargers: N x M pieces of glue become N + M.

**Tiny example (a server, with logs on stderr):**
```python
mcp = MCPServer("library")
@mcp.tool()                      # the docstring becomes the tool description
def find_book(title: str) -> str:
    """Look up one book by title and return its shelf code. Read-only."""
    ...
mcp.run(transport="stdio")       # never print() to stdout on stdio
```

**Recap:**
- Host = the AI app. Client = one connection to one server. Server = offers tools, resources (read-only data) and prompts (templates).
- Claude does not know MCP exists. Your loop copies the tool list to Claude and forwards its calls with `tools/call`. The loop stays the same.
- Two transports: stdio (local, one user) and Streamable HTTP (shared, needs sign-in). Old SSE is deprecated.
- Start with a custom tool. Move to MCP when a second app needs the same capability.

## 6. MCP security and governance
**In one line:** Security lives in the server code, not in the prompt.

**Analogy:** A sign saying "Staff only" is advice. A lock stops people.

**Tiny example (check in this order):**
1. No key or a bad key: `401` (who are you?).
2. Known caller, role not allowed: `403` (you may not do this).
3. Input fails validation: a typed error with no details leaked.
4. Everything passes: run the tool and write an audit line.

**Recap:**
- Least privilege: map roles to tools, deny by default, use one key per role.
- Keep keys in environment variables or a secret store. Never in code, prompts or committed config.
- Log only safe fields and redact secrets. Validate every input on the server.
- Treat tool results as data, not orders (prompt injection). Ask a human before payments or deletions.
- Use an allow-list of approved servers, and pin versions. Check the docs page for current settings.

## Common mix-ups
- **"The model runs my tool."** It does not. It asks. Your code runs it and returns the result.
- **"Retries are Claude's job."** Retry rules belong in your code, with a gate, a budget and backoff.
- **"Forcing a tool tests selection."** It hides the confusion. Keep `auto`. On the 5.5 models, forcing gives HTTP 400.
- **"A description saying 'approvers only' protects a tool."** It is only advice. Check the role in server code.
- **"A stray print is harmless."** On a stdio server it breaks the connection. Log to stderr.

## Day recap: remember these
1. Claude asks for a tool. Your code runs it.
2. Loop while `stop_reason` is `tool_use`, and set a turn limit.
3. Every ticket gets one `tool_result` with the same id, all in one message.
4. The description is the most important part of a tool.
5. Measure tool selection with a fixed prompt set before you change anything.
6. A failure is information: send a typed error with `is_error: true`.
7. Your code owns retries. Writes need an idempotency key.
8. Run independent reads together. Keep dependent writes in order.
9. MCP is one standard plug: host, client, server. The loop stays the same.
10. Enforce security in the server: 401, 403, least privilege, no keys in logs.

## Quick self-check
1. Who runs `find_book`, Claude or your code?
2. Claude picks the wrong tool. Name two fixes before you change the model.
3. A tool times out. When may your code retry it, and what must a write tool have first?
4. Which calls in one turn may run together?
5. What is the difference between a 401 and a 403?

Answers:
1. Your code. Claude only asks.
2. Rewrite the descriptions (say when to use each tool). Merge or remove overlapping tools.
3. Only if the error is temporary and retryable, within a budget. A write needs an idempotency key.
4. Independent reads. Dependent writes run one at a time, in order.
5. 401: the caller is unknown or has no valid key. 403: the caller is known but not allowed.

## Go deeper
- Tool-use loop: [TOOL_USE_LOOP.md](../STUDY_GUIDES/DAY_2/TOOL_USE_LOOP.md). Do [Lab 2.0](../NEW_LABS/LAB_2_0_intro_to_tool_use/README.md) first, then [Lab 2.5](../DAY_2/LABS/LAB_2_5_build_a_tool_and_loop/README.md).
- Tool design: [TOOL_DESIGN.md](../STUDY_GUIDES/DAY_2/TOOL_DESIGN.md). Open [Lab 2.1](../DAY_2/LABS/LAB_2_1_facilities_tool_boundaries/README.md).
- Errors and retries: [TOOL_ERRORS_AND_RETRIES.md](../STUDY_GUIDES/DAY_2/TOOL_ERRORS_AND_RETRIES.md). Open [Lab 2.3](../DAY_2/LABS/LAB_2_3_payroll_typed_errors/README.md).
- Parallel calls: [PARALLEL_TOOL_CALLS.md](../STUDY_GUIDES/DAY_2/PARALLEL_TOOL_CALLS.md). Open [Lab 2.2](../DAY_2/LABS/LAB_2_2_travel_disruption_tool_loop/README.md).
- MCP basics: [MCP_BASICS.md](../STUDY_GUIDES/DAY_2/MCP_BASICS.md). Open [Lab 2.6](../DAY_2/LABS/LAB_2_6_use_an_mcp_server/README.md).
- MCP security: [MCP_SECURITY_AND_GOVERNANCE.md](../STUDY_GUIDES/DAY_2/MCP_SECURITY_AND_GOVERNANCE.md). Open [Lab 2.4](../DAY_2/LABS/LAB_2_4_procurement_mcp_server/README.md).
- Extra reading: [MCP_BEST_PRACTICES.md](MCP_BEST_PRACTICES.md) and [MCP_SECURITY_ARCHITECTURE.md](MCP_SECURITY_ARCHITECTURE.md).
