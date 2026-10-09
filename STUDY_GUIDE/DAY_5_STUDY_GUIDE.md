# Day 5 Quick Guide and Recap: Memory, Guardrails and Evals

## What this day is about

An AI agent forgets everything between calls, so you must decide what it remembers.
An agent can also fail or be fooled, so the rules that matter must live in code.
And you cannot say a prompt is better until a fixed set of tests says so.

## The day in plain English

**The big picture:** An agent is like a shop assistant with a very short memory who also works unsupervised. You must decide what it remembers, protect it from mistakes and tricks, and prove with tests that any change you make is an improvement.

- **Conversation.** The model remembers nothing, so you resend the chat each time. Like re-reading the whole notebook before every reply.
- **Context window.** The model can only read so much at once. Past that, old turns must be trimmed or summarised, and facts can be lost. Like a desk that holds only so many papers.
- **Memory.** Facts that must last, such as a customer's name or allergy, go in a file or database outside the window and are loaded when needed. Like a filing cabinet next to the desk.
- **Guardrails.** Rules that must hold are written in code, not only in the prompt. A prompt asks, and code decides. Like a till that will not give a refund over a limit, whatever the clerk says.
- **Least privilege and approval.** An agent gets only the tools its role needs, and risky actions wait for a person. Like a junior who can take orders but needs a manager to approve a big discount.
- **Errors, retries and fallbacks.** When something breaks, retry what is safe to retry, use a backup source, say clearly that you did, and pass the case to a person if needed. Like using the paper menu when the screen is down, and telling the customer.
- **Evals.** A fixed set of test cases with expected answers, graded by code. You run them before and after a change. Like a class test used to compare two teaching methods.
- **Provenance and a release gate.** Record where each answer came from, and block a release when scores drop. Like footnotes in a report and a quality check before shipping.

Remember this: memory is something you build, safety is something you enforce, and "better" is something you measure.

## Your day at a glance

Brew & Bean is the small coffee shop used in the demos. Your trainer runs the demos while you watch. You do the labs yourself.

| Item | What it is | Idea it practises |
|---|---|---|
| Demo 5.0 Intro | Pip, the shop assistant, built up in five parts | Conversation, context, memory, safeguard, eval |
| Demo 5D Guardrails across the stack | A support desk with an orchestrator and two subagents | One control per layer, enforced in code |
| Demo 5E Pip on the Agent SDK | You chat with Pip | What the SDK handles and what stays your job |
| Demo 5F Catering workflow | An order moves through five fixed steps | Small state, checkpoints, a workflow agent |
| Demo 5G Stock detective | An agent chooses its own steps | Bounded reads, working notes, an autonomous agent |
| Demo 5H Catering team | A manager and three subagents | Separate context, shared ledger, multi-agent |
| Demos 5A, 5B, 5C | Support memory, safeguards around an agent, evals | The ideas behind Labs 5.1 to 5.3 |
| Lab 5.1 Support memory | A hotel agent that must remember "no marketing email" | Save, load, compact, pin a rule |
| Lab 5.2 Refund guardrails | A refund agent with five tickets | Fallback, untrusted text, approval, human queue |
| Lab 5.3 Invoice evals | An invoice checker, two prompt versions | Grader, source check, release gate |
| Lab 5.4 Context management (extra) | An ops assistant reads 10 long reports | Shrink old turns, keep the key line |

## 1. Conversation, context window and memory

**In one line:** The model remembers nothing, so your code resends the conversation, and anything that must last goes into memory.

**Analogy:** Context is your desk, and memory is the filing cabinet. You work only on what is on the desk.

**Tiny example:**
```
Context  = system prompt + tools + all messages so far + the reply
Memory   = a file or database you keep outside the request
Pattern  = load the facts you need, do the work, save what changed
```

The window is the context window. It has a hard size limit. Quality can also drop long before it is full. The docs call this context rot.

A summary is lossy. Compaction means the model writes that summary for you. It may drop the one rule that mattered, such as "never phone this customer". So pin hard rules in their exact words and check in code that they survived.

The Claude Agent SDK handles the conversation (sessions), compaction near the limit, and reading a `CLAUDE.md` of standing rules. Your code still owns the memory per customer, the pinned rules, the token limit and the tier rules. Demo 5E shows this split.

**Recap:**
- Move facts, not whole transcripts, into memory.
- Pin hard rules, then test that they survived a summary.
- Retrieve only what the question needs, and only for the right customer.
- Compaction and clearing options are beta features, so check the docs page for current names.

## 2. Three kinds of agent, and where memory lives

**In one line:** Who chooses the next step decides where context and memory sit.

**Analogy:** A chat with one clerk, an assembly line, a detective with a notebook, and a kitchen brigade.

**Tiny example:**
```
Conversational (5E)  you type, the SDK keeps the chat, your file keeps the card
Workflow (5F)        your code picks 5 fixed steps, a small state + checkpoint after each
Autonomous (5G)      the model picks steps, notes on disk, bounded views of big logs
Multi-agent (5H)     a manager gives each subagent a short brief, a shared ledger
```

In 5E, a new SDK session starts from the saved memory file. In 5F, each step sees only the fields it needs. You can stop and resume from a saved checkpoint. In 5G, the notes live on disk, so they survive compaction and a restart. In 5H, each subagent starts fresh and never sees the others' tickets. Only code writes the ledger.

**Recap:**
- Use a workflow when you can write the steps in advance. It is cheaper and easier to test.
- Autonomous agents need limits on tools, result size, turns and cost.
- Subagents keep big reads out of the manager's context.
- In every shape, durable facts go to disk, not only into the chat.

## 3. Guardrails and safety by layer

**In one line:** The prompt asks, and the code decides, at every layer.

**Analogy:** A "keep off the grass" sign versus a locked gate. A prompt rule is the sign.

**Tiny example (Demo 5D, one control per layer):**
```
Prompt        short role prompt, outside text in untrusted tags, schema check
Tools         each agent lists only the tools it needs, argument limits, masked results
MCP           scoped token, allow-list of tool names, server-side validation
Agent         a gate that denies by default, turn and budget limits, approval queue
Subagent      its own tool list, checked again by the gate
Orchestrator  can only delegate, and a hand-off is checked before the next step
Audit         one log line per call, with secrets and personal data masked
```

Role and tier access is the same idea. In 5E a guest, a member and a gold customer get different tools. A hook checks every call, so a denial is the guardrail doing its job. The test for any rule is simple: if the model were fully fooled, would the rule still hold? If yes, code enforces it. If no, it is only guidance.

Prompt injection means hidden orders in text the model reads, such as a ticket or a web page. Defend in layers: treat outside text as data, give least privilege, check in code, and ask a human before risky actions. For the full security design, see the extra guide [MCP_SECURITY_ARCHITECTURE.md](MCP_SECURITY_ARCHITECTURE.md).

**Recap:**
- Least privilege and deny by default.
- Limits, allow-lists and approvals are code, not prompt text.
- Tokens come from the environment and never go in code or logs.
- Log every decision, with secrets masked.

## 4. Errors, retries, fallback and escalation

**In one line:** Give every failure a planned response: retry, fall back, or ask a human.

**Analogy:** A fire drill. You plan the exits before the fire.

**Tiny example:**
```
Temporary error (429, 5xx, timeout)  -> retry with backoff, up to a budget
Still failing, safe alternative      -> fall back, and label the answer "degraded"
No safe path, or big risk            -> stop and escalate to a human
```

Backoff means waiting a little longer after each try. Retry only temporary errors. A 400, 401 or 403 will not fix itself. Own the retry budget in one place. The SDK already retries twice, so adding three more tries in your code means up to nine calls. A circuit breaker works like a fuse. After repeated failures it stops calling the broken service for a while.

A fallback hides the failure from the user, never from you, so log it. An old cached answer must say it is old. When a human takes over, send the full case: who, what, evidence, what was tried, and why you stopped. Demo 5B and Lab 5.2 show a fallback lookup and a human queue, using ordinary tickets.

**Recap:**
- Retry only temporary errors, within a budget.
- Label degraded answers and log every fallback.
- Fail closed: an outage must never become "approved".
- Escalate by a code rule, not because the model "sounds unsure".

## 5. Evals, provenance and a release gate

**In one line:** An eval scores a fixed set of test cases, and provenance shows where each claim came from.

**Analogy:** A marking scheme for an exam, and a food label with a batch number.

**Tiny example (Lab 5.3 idea):**
```
8 labelled invoices -> run prompt v1 and v2 -> grade each case in code
Gate: no case that passed before may fail now, and every cited line id exists
Risky or unsure cases -> written to a human review queue
```

Grade with the fastest reliable method. Code first, for things like exact match or "does this id exist". A model judge second, for tone. Humans for labels and spot checks. A model judge can favour long answers, so test it first. Compare per case, not only by average. A better average can hide one broken high-risk case.

Provenance records the claim, its source id and where in the source it sits. A citation that exists may still not support the claim, so check both. Keep a prompt version with every score.

**Recap:**
- Write the pass target before you run the eval.
- Never tune against the held-out test set.
- Release only when the gate passes.
- Every claim needs a source id that really exists.

## 6. The capstone in a nutshell

**In one line:** Build one small, complete system, then defend your decisions with evidence.

**Analogy:** An architect's design review. A plan that fits, with inspection reports.

**Tiny example (the five decisions):**
```
Pattern, Models, Tools, Safety, Proof
Pick the simplest design: single call, then workflow, then agent
Use the cheapest model tier that passes, and show the numbers
Keep a one-page design record, a before and after run, and a list of limits
```

Read the brief first, and run any starter system to find its failures. Keep the scope small but finished. Put exact rules in code. Give each reason for a choice, and each rejected option. Your trainer's capstone pack is the final word on requirements and scoring.

**Recap:**
- Small and complete beats large and half-proven.
- Every claim of "safe" or "works" should point to a file.
- Fail closed, and state what your evidence does not cover.

## Common mix-ups

- **Caching versus shrinking.** Prompt caching makes a long prompt cheaper. It does not make it shorter.
- **Compaction versus memory.** Compaction summarises. Memory keeps exact facts. Use both.
- **Prompt rule versus guardrail.** A prompt rule guides. Only code guarantees.
- **Valid citation versus true citation.** The id can exist while the passage does not support the claim.
- **Average score versus safety.** A better average can still hide a broken high-risk case.

## Day recap: remember these

1. The API remembers nothing. Your code resends the history.
2. Context is the desk, and memory is the filing cabinet.
3. Summaries are lossy, so pin hard rules and test that they survived.
4. The Agent SDK keeps the session and CLAUDE.md. You keep memory, limits and tier rules.
5. Workflow, autonomous and multi-agent designs keep context and memory in different places.
6. The prompt asks, and the code decides, at every layer.
7. Give each agent and subagent only the tools its job needs, and deny by default.
8. Retry temporary errors only, label fallbacks, and escalate when no safe path is left.
9. Grade in code first, compare per case, and release only through a gate.
10. A claim without a real source is only a guess.

## Quick self-check

1. Why must your code resend the messages on every turn?
2. A summary dropped "never phone me". Name two things that protect the rule.
3. What does "deny by default" mean at the agent gate?
4. Why is stacking SDK retries and your own retries risky?
5. Why can a better average score still block a release?
6. Why do a guest and a gold customer get different tools, and who enforces it?

**Answers**

1. The API keeps nothing between requests.
2. A pinned rule in its exact words, and a retention check after summarising.
3. If no rule allows a tool call, the answer is no.
4. Retries multiply. One request can become many calls to a struggling service.
5. One high-risk case may have broken, and the gate looks per case.
6. Least privilege. Code, such as a hook that checks every call, enforces it.

## Go deeper

Full guides (about 20 minutes each):
- [CONTEXT_AND_MEMORY.md](../STUDY_GUIDES/DAY_5/CONTEXT_AND_MEMORY.md): context, compaction, memory governance, retrieval.
- [RELIABILITY_AND_RESILIENCE.md](../STUDY_GUIDES/DAY_5/RELIABILITY_AND_RESILIENCE.md): errors, retries, fallbacks, breakers, injection.
- [EVALUATION_AND_PROVENANCE.md](../STUDY_GUIDES/DAY_5/EVALUATION_AND_PROVENANCE.md): eval sets, judges, gates, citations.
- [CAPSTONE_DESIGN.md](../STUDY_GUIDES/DAY_5/CAPSTONE_DESIGN.md): the capstone playbook.
- [MCP_SECURITY_ARCHITECTURE.md](MCP_SECURITY_ARCHITECTURE.md): the security design around MCP.

Where to practise:
- Memory: [Lab 5.1](../DAY_5/LABS/LAB_5_1_support_memory/README.md), then [Lab 5.4](../NEW_LABS/LAB_5_4_context_management/README.md).
- Guardrails: [Lab 5.2](../DAY_5/LABS/LAB_5_2_refund_guardrails/README.md). Keep the card [GUARDRAILS_BY_LAYER.md](../DAY_5/LABS/DEMO_5D_guardrails_across_the_agent_stack/GUARDRAILS_BY_LAYER.md) next to you.
- Evals: [Lab 5.3](../DAY_5/LABS/LAB_5_3_invoice_evals/README.md).
- Agent shapes: [Demo 5E](../DAY_5/LABS/DEMO_5E_pip_with_the_agent_sdk/README.md), [5F](../NEW_LABS/DEMO_5F_catering_workflow_agent/README.md), [5G](../NEW_LABS/DEMO_5G_stock_detective_agent/README.md), [5H](../NEW_LABS/DEMO_5H_catering_team_multi_agent/README.md).
