# Day 3 Quick Guide and Recap: Agentic Architecture and Orchestration

## What this day is about

- You learn how to choose the simplest design that works: a conversation, a workflow, or an agent.
- You learn how to split work across specialists, keep agents safe, and build them with the SDKs.
- Use this page as a short recap. The full guides (linked at the end) hold the detail.

## Your day at a glance

Your trainer runs the demos while you watch. You do the labs yourself.

| Demo (watch) | Lab (you build) | Idea you practise |
|---|---|---|
| 3A: Should This Even Be an Agent? | Lab 3.1: Review Expense Claims Two Ways | Pick the architecture by who decides the next step |
| 3B: From One Do-Everything Agent to a Multi-Agent Desk | Lab 3.2: Harden the Research Desk | Specialists, small briefs, checked hand-offs, escalation |
| 3C: Warranty Claims Agent | Lab 3.3: Build the Warranty Claims Agent | Well-shaped tools, a turn limit, a decision you can verify |
| 3D: Supplier-Payment Release Gate with Human Approval | Lab 3.4: Build a Supplier-Payment Release Gate with Human Approval | Gate rules, a reviewer, a release hook, an audit trail |
| 3E: Your First Agent with the Claude Agent SDK | Lab 3.5: Build Your First Agent with the Claude Agent SDK | A goal-driven, read-only agent in one config object |
| 3F: Four Ways to Build the Same Agent | Lab 3.6: Build the Same Agent Two Ways with the Anthropic SDK | Who runs the loop: you, or the SDK |
| 3G: The Research Desk as a Multi-Agent System | Lab 3.7: Build the Research Desk as a Multi-Agent System | A thin coordinator with specialists that have small toolboxes |

## 1. Workflow or agent: which one do I need?

**In one line:** Ask "who decides the next step?" and use the least powerful design that works.

**Analogy:** You can make one phone call, hand someone a checklist, or send a new hire off with a goal. Do not hire for a phone call.

**Tiny example:**

| Who decides the next step? | Use |
|---|---|
| A person typing each message | Conversation |
| A written process (your code) | Workflow |
| Claude, based on what it just found | Agent |

- A **workflow** is a fixed path of steps in code. Claude may do work inside a step.
- An **agent** is Claude in a loop that picks its own next tool.

**Recap**
- "It calls tools" does not mean "it is an agent". A workflow can call tools too.
- Agents cost more tokens (the text you pay for), take longer, and are harder to explain later.
- Let Claude read messy text. Let plain code make exact decisions such as limits.
- Measure first: same cases, same scorer, several runs. Record cost as well as accuracy.

## 2. Multi-agent design

**In one line:** Fix the tools first. Then split into specialists only if it pays for the hand-offs.

**Analogy:** A newsroom. The editor does not report. Each reporter has only the tools for one job.

**Tiny example:** the research desk in Demos 3B and 3G.

```
Coordinator (only tool: delegate)
  -> Searcher, Analyst, Fact-checker, Writer
Each gets a small brief and returns a short, checked result.
```

- A **specialist** (sub-agent) has a clear job, a small toolbox and its own prompt.
- A **hand-off** is a brief going out and a result coming back. A **contract** is the agreed shape of the result.
- Independent tasks can run in parallel. A step that needs the last result runs in a row.

**Recap**
- Most agent problems are architecture problems, not model problems.
- Keep the coordinator thin. If it researches itself, you have a one-person desk.
- If two reliable sources disagree, report both values and escalate by a rule in code. A human decides.
- Multi-agent costs more tokens. The case for it is checking, small briefs and a readable trace.

## 3. Task decomposition and planning

**In one line:** Split a big request into small steps, each with a clear input, output and check.

**Analogy:** A house move. You write the list first. Some jobs can happen on the same day. Some must wait.

**Tiny example:**

| Weak step | Strong step |
|---|---|
| "Look into the market" | "Find two reliable sources for Acme's 2025 revenue. Return the document id and figure for each." |

**Recap**
- Before you split, answer four questions: goal, what you know, what is missing, success criteria.
- A **dependency** means step B needs the output of step A. Steps with no dependency can run together.
- Start with a static plan (steps fixed in code). If the model proposes a plan, code checks it before it runs.
- If a request is unclear, ask when a wrong guess is costly. Otherwise state your assumptions in the answer.
- Limit the plan size and the number of replans. At the limit, hand over to a human.

## 4. Safety and failure handling

**In one line:** Code enforces the limits. The prompt only asks.

**Analogy:** A cashier can refund a small amount. A large refund needs the manager's key, and the till counts the total.

**Tiny example:** the release gate idea from Demo 3D.

```python
if amount >= LIMIT:            # rule in code, not in the prompt
    queue_for_reviewer(case)   # a person approves first
else:
    release(case)              # the money moves only when approved
```

**Recap**
- Every loop needs a turn limit and a spend limit. When one is hit, say so. Do not invent an answer.
- Check outputs against facts: does the decision match what the tools returned?
- Never hide a failure. Pass it on, use a labelled fallback or a partial result, or escalate with a complete request.
- **Human approval:** a gate rule in code, a reviewer chosen by limit, a release hook, and an audit trail.
- **Least privilege:** give the agent only the tools the job needs. `allowed_tools` only pre-approves. To remove a tool, deny it.
- **Prompt injection** means orders hidden in data the agent reads. Treat documents as data, use few tools, and gate risky actions.
- Make write tools safe to repeat, so the same request twice does one thing.

## 5. Building agents with the SDKs

**In one line:** The goal, prompt and tools stay the same. Only "who runs the loop, and where" changes.

**Analogy:** Four ways to cross town: a manual car, an automatic car, a taxi, or a professional driver in your own car.

**Tiny example:**

| Build | Who runs the loop |
|---|---|
| 1. Manual loop (`anthropic`) | You, in your code |
| 2. Tool Runner (`anthropic`, beta) | The SDK, in your program |
| 3. Managed Agents (`anthropic`, beta) | Anthropic, in its cloud |
| 4. Claude Agent SDK (`claude-agent-sdk`) | The Claude Code engine, on your machine |

**Recap**
- An agent is a goal, instructions, tools and limits. Start read-only.
- In the Claude Agent SDK you configure the agent and read the stream from `query()`. You do not write the loop.
- Set `max_turns` and `max_budget_usd`. Check the result's `subtype` before you read an answer.
- Sub-agents use `AgentDefinition`. Always set `tools`, or the sub-agent inherits every tool.
- Versions and platform feature lists change, so check the docs page before you design.

## Common mix-ups

- **Tools mean agent.** No. The deciding question is who chooses the next step.
- **`anthropic` and `claude-agent-sdk` are the same package.** No. They are installed, imported and versioned separately. The Agent SDK also needs the Claude Code command-line tool.
- **`allowed_tools` hides other tools.** No. It only pre-approves the ones you list.
- **A prompt rule is a safety control.** No. A limit, a hook or a check in code is.
- **Parallel agents are cheaper.** No. Parallel is faster, not cheaper.

## Day recap: remember these

1. Ask "who decides the next step?" before you pick a design.
2. Stay on the lowest rung: conversation, then workflow, then agent.
3. Claude reads the messy text. Code makes the exact decisions.
4. Fix the tools first, then split into specialists with small toolboxes.
5. Pass a small brief, return a checked result, and keep the coordinator thin.
6. Conflicting reliable sources go to a human by a rule in code.
7. Split a task into steps that each have an input, an output and a check.
8. Code enforces limits. Use turn limits, spend limits and approval gates.
9. Give agents the fewest tools they need. Report failures, never hide them.
10. The four builds differ in one thing: who runs the loop, and where.

## Quick self-check

1. Which question separates a conversation, a workflow and an agent?
2. Why does an agent usually cost more tokens than a workflow?
3. Why should a specialist have a small toolbox?
4. What two limits stop a runaway loop?
5. You set `allowed_tools=["Read"]`. Is the agent now limited to reading? Why?

Answers:
1. Who decides the next step: a person, a written process, or the model.
2. Every turn re-sends the whole conversation, so input grows turn by turn.
3. A tool it does not have is a tool it cannot misuse. This is least privilege.
4. A turn limit and a spend limit, both set in code or SDK options.
5. No. It only pre-approves that tool. Deny the others, or use a strict permission mode.

## Go deeper

Full guides (about 15 to 20 minutes each):
- [Choosing an agent architecture](../STUDY_GUIDES/DAY_3/CHOOSING_AN_AGENT_ARCHITECTURE.md): open with Demo 3A and Lab 3.1.
- [Multi-agent design](../STUDY_GUIDES/DAY_3/MULTI_AGENT_DESIGN.md): open with Demos 3B and 3G, Labs 3.2 and 3.7.
- [Task decomposition and planning](../STUDY_GUIDES/DAY_3/TASK_DECOMPOSITION_AND_PLANNING.md): the sample planner has no lab, so try it yourself.
- [Agent safety and failure handling](../STUDY_GUIDES/DAY_3/AGENT_SAFETY_AND_FAILURE_HANDLING.md): open with Demos 3C and 3D, Labs 3.3 and 3.4.
- [Building agents with SDKs](../STUDY_GUIDES/DAY_3/BUILDING_AGENTS_WITH_SDKS.md): open with Demos 3E and 3F, Labs 3.5 and 3.6.
- [Anthropic SDK vs Claude Agent SDK](../DAY_3/ANTHROPIC_SDK_VS_CLAUDE_AGENT_SDK.md): a comparison page to read next to Demo 3F.
