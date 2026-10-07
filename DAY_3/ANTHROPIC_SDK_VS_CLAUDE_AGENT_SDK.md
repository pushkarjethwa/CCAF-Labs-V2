---
lab:
    title: 'Comparison: Anthropic SDK vs Claude Agent SDK'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Comparison: Anthropic SDK vs Claude Agent SDK

Two Python packages can build the same agent, and their names are easy to mix up. This page compares them in tables. The example agent is the incident-triage agent of Demo 3E and Demo 3F (Labs 3.5 and 3.6).

## In one minute

| | Anthropic SDK | Claude Agent SDK |
|---|---|---|
| Install | `pip install anthropic` | `pip install claude-agent-sdk` |
| What it is | The client for the Claude API | A ready-made agent engine (the loop behind Claude Code, as a library) |
| Who builds the agent | **You** build the loop around it | **It** runs the loop, and you configure it |
| Picture | A box of parts | An agent kit |
| Extra tool needed | None (an API key) | The Claude Code command-line tool, and an API key |

An agent is a model that keeps asking for tools until it has an answer. The cycle is the agent loop. Both packages do it, and the difference is **who writes and runs the loop**.

## The four builds at a glance

The Anthropic SDK gives you three ways to build an agent. The Claude Agent SDK gives you one. Demo 3F builds the same agent all four ways.

| | Build 1: Manual loop | Build 2: Tool Runner | Build 3: Managed Agents | Build 4: Claude Agent SDK |
|---|---|---|---|---|
| Package | `anthropic` | `anthropic` | `anthropic` | `claude-agent-sdk` |
| Main call | `client.messages.create(...)` | `client.beta.messages.tool_runner(...)` | `client.beta.sessions...` | `query(prompt, options)` |
| Status | Stable | Beta | Beta | Separate package, pin the version |
| Who writes the loop | You | The SDK | Anthropic (server side) | The SDK and the Claude Code engine |
| Where the loop runs | Your process | Your process | An Anthropic cloud session | A helper process on your machine |
| Where your tools run | Your process | Your process | Custom tools on your side, through events | Your process (and built-in file and shell tools, if allowed) |
| Conversation state | Your `messages` list | In memory, for one run | Held in the session | Held by the agent process (a session id comes back) |
| Limits | Whatever you code | `max_iterations` | Session budget | `max_turns`, `max_budget_usd` |
| Hooks and permissions | You write the check | None built in | Not covered in this course | Built in (`PreToolUse` hooks, allow and deny lists) |
| Subagents | You build them | You build them | A coordinator with a roster (beta) | Built in (`AgentDefinition`) |
| Setup | API key | API key | API key, plus agent, environment and session objects | API key and the Claude Code command-line tool |
| Code you write | The most (about 25 lines for the loop) | Tool functions and settings | Event handling | The options |
| Best for | Fixed workflows, strict audit trail, learning | Simple tool calling inside an app | Long or hosted tasks | Agents that need hooks, permissions, subagents or files |
| Watch out for | You own retries, `stop_reason` and context growth | Beta, little control inside the loop | Beta, vendor-hosted, rate limits | The helper-process dependency, API-key sign-in only |

## The same agent, line by line

Every build has the same goal, prompt and three read-only tools: `list_alerts`, `get_log_lines` and `lookup_indicator`. Only the wiring changes.

| Job | Manual loop | Tool Runner | Claude Agent SDK |
|---|---|---|---|
| Start | `messages = [{"role": "user", "content": GOAL}]` | `messages=[{"role": "user", "content": GOAL}]` | `query(prompt=GOAL, options=options)` |
| Call the model | `client.messages.create(...)` inside a `for` loop | Done by the runner | Done inside `query()` |
| Stop the loop | `if response.stop_reason != "tool_use": break` | Done by the runner | Done inside `query()` |
| Run a tool | You loop over `tool_use` blocks and call your function | The runner calls your function | The SDK calls your in-process tool |
| Send results back | Append **one** user message with **all** the `tool_result` blocks | Done by the runner | Done inside `query()` |
| Turn limit | `for turn in range(1, MAX_TURNS + 1)` | `max_iterations=MAX_TURNS` | `max_turns=MAX_TURNS` |
| Budget limit | You write it | Not set in the demo | `max_budget_usd=1.00` |
| Choose the tools | `tools=TOOLS` | `tools=[as_runner_tool(t) for t in TOOLS]` | `allowed_tools=["mcp__soc__list_alerts", ...]`, and `tools=[]` for no built-in tools |

The manual loop, in full:

```python
messages = [{"role": "user", "content": GOAL}]

for turn in range(1, MAX_TURNS + 1):
    response = client.messages.create(
        model=MODEL, max_tokens=4096,
        system=SYSTEM_PROMPT, tools=TOOLS, messages=messages,
    )
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason != "tool_use":      # end_turn: Claude is finished
        break

    results = []
    for block in response.content:
        if block.type == "tool_use":
            text, is_error = run_tool(block.name, block.input)
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": text, "is_error": is_error})
    messages.append({"role": "user", "content": results})   # ALL results in ONE message
```

The Claude Agent SDK, in full. The agent is a configuration:

```python
options = ClaudeAgentOptions(
    model=MODEL,
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={"soc": server},          # your three tools
    tools=[],                             # no built-in file or shell tools
    allowed_tools=["mcp__soc__list_alerts", "mcp__soc__get_log_lines", "mcp__soc__lookup_indicator"],
    max_turns=MAX_TURNS,
    max_budget_usd=1.00,
    setting_sources=[],                   # ignore local settings
)

async for message in query(prompt=GOAL, options=options):   # the loop runs inside query()
    ...
```

## Who controls what

| Control | Anthropic SDK (manual loop) | Claude Agent SDK |
|---|---|---|
| Stop a runaway loop | Your `for` loop limit | `max_turns` |
| Cap the spend | Your own check of the token usage | `max_budget_usd` |
| Limit which tools are used | You pass only those tools | `allowed_tools`, and `tools=[]` |
| Refuse a tool call before it runs | A check in your code, before you run the tool | A `PreToolUse` hook that allows, asks or denies |
| Ask a human first | You write the pause | The permission callback |
| Split work between agents | You build the hand-offs | `agents={...}` with `AgentDefinition` |
| Keep the agent from reading local settings | Not applicable | `setting_sources=[]` |

A sentence in a prompt does not enforce any of these. Use a limit, a permission, a hook, or a check in code.

## What you gain and what you give up

| | Anthropic SDK | Claude Agent SDK |
|---|---|---|
| You gain | Full control of every step, an exact audit trail, a small and visible amount of code, no extra dependency | A tested loop, permissions, hooks, subagents and built-in tools, with very little code |
| You give up | The time to write and test the loop, the retries, the limits and the hooks, for every agent | Some control inside the loop, and you take on the helper process, a separate package version, and API-key sign-in only |

## How to choose

Ask the questions in order, and stop at the first yes.

| # | Question | If yes |
|---|---|---|
| 1 | Is the path fixed and known? | It is a workflow, not an agent. Use plain code with one model call per step (Lab 3.1). |
| 2 | Do you need exact control of every step, or a strict audit trail? | Anthropic SDK, manual loop |
| 3 | Do you only need a model that can call a few functions inside your app? | Anthropic SDK, Tool Runner |
| 4 | Do you want Anthropic to host the loop, and accept a beta, vendor-hosted runtime? | Anthropic SDK, Managed Agents |
| 5 | Do you need hooks, permissions, subagents, or file and shell tools, under your control? | Claude Agent SDK |

The rule behind the table: **use the least powerful option that works**, and move up only when you need what the next one adds.

## Examples from this course

| Demo | What it needs | Which package fits |
|---|---|---|
| 3A, expense review | A fixed series of steps with one model call | Neither agent feature. A workflow with the Anthropic SDK. |
| 3C, failure recovery | Retry and recovery rules around each tool call | Either. The rules are your code, in a loop or around the runner. |
| 3D, payment guard | A rule that runs before the release tool | Claude Agent SDK gives you the hook. With a manual loop you call the same rule yourself. |
| 3E, first agent | One agent in one configuration object | Claude Agent SDK |
| 3F, four builds | The same agent, to compare | All four builds |
| 3G, research desk | Subagents, and a hook that refuses a leak | Claude Agent SDK (3B built the same desk by hand with the Anthropic SDK) |

## Common mistakes

| Mistake | What to do instead |
|---|---|
| Mixing up the packages | `anthropic` and `claude-agent-sdk` are installed, imported and versioned separately. |
| Forgetting the helper process | The Claude Agent SDK needs the Claude Code command-line tool. Check it with `claude --version`. |
| Returning tool results one at a time | In a manual loop, all results of one turn go back in one user message. |
| No limits | Always set the maximum turns, and a budget where you can. |
| Giving the agent every tool | Turn off built-in file and shell tools unless needed, and list only the tools it may use. |
| Trusting the prompt to enforce a rule | Use a hook, a permission, or a check in code. |
| Treating beta as stable | The Tool Runner and Managed Agents are beta. Test again when you upgrade. |

## Quick check

| Question | Answer |
|---|---|
| Which package shows you what an agent loop really is? | The Anthropic SDK, with a manual loop. |
| Which package gives you hooks and subagents without writing them? | The Claude Agent SDK. |
| Where does the loop run in a manual loop? | In your Python process. |
| What does the Claude Agent SDK need besides the package? | The Claude Code command-line tool. |
| A task has a fixed series of steps. Do you need an agent? | No. Use a workflow. |

## More information

- Demo 3F builds the same agent four ways. Its folder is `TRAINER_V2/DAY_3/DEMOS/DEMO_3F_four_ways_to_build_an_agent`, with a longer `COMPARISON.md` and a `DEPLOYMENT.md` checklist.
- Lab 3.5 builds an agent with the Claude Agent SDK, and Lab 3.6 builds one with the Anthropic SDK.
- Lab 3.7 builds a multi-agent desk with the Claude Agent SDK.
- The versions used in the demos are `anthropic==1.11.0` and `claude-agent-sdk==0.2.163`.
