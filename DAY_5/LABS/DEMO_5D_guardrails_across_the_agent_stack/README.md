---
lab:
    title: 'Demo 5D: Guardrails Across the Agent Stack'
    module: 'Day 5 - Reliability, Resilience and Guardrails'
---

# Demo 5D: Guardrails across the agent stack

Northwind Support uses an orchestrator agent to handle customer tickets. The orchestrator delegates to two subagents: an account reader that can only read, and a refund processor that can only issue refunds. Both use one small `customers` MCP server. This demo follows ordinary tickets through the stack, and each stage adds one real, production-style control: the prompt, the tools, the MCP server, the agent gate, and the audit log. The lesson is that every layer has its own job, and the limits that matter are enforced in code, not in the prompt. The whole demo takes about 40 minutes. There is no matching lab yet.

**Where it fits**: Run it after Demo 5.0 (the intro). It gives the whole map of guardrails, and Demos 5A to 5C then go deep on memory, one safeguard story and evals.

## The stages

**The idea**: The prompt asks. The code decides, at every layer.

Run stages 1 to 4 (about 30 minutes, including a two-minute introduction and a one-minute recap):

| Stage | Layer | What you see | Minutes | Key needed |
|-------|-------|-------------|---------|------------|
| Intro | none | The story and the three agents | 2 | no |
| 1 | Prompt | A short role prompt, untrusted tags, a schema check | 5 | yes |
| 2 | Tools | Least privilege, argument limits, masked results, idempotency | 7 | no |
| 3 | MCP | Scoped tokens, allow-list, server-side validation, redacted logs | 7 | no |
| 4 | Agent, subagent, orchestrator | The policy gate, limits, hand-off check, approval queue | 9 | yes |
| Recap | none | The scorecard idea and the one thing to remember | 1 | no |

The commands:

```
python check_offline.py
python guardrails_stack.py --stage 1
python guardrails_stack.py --stage 2
python guardrails_stack.py --stage 3
python guardrails_stack.py --stage 4
```

Stage 5 (audit and scorecard, about 5 minutes) is optional: `python guardrails_stack.py --stage 5`.

Attack and failure detail (prompt injection tricks, outages, retries and breakers) is taught in the study guides, not here. Every case in this demo is an ordinary ticket, and where a control denies something, that is the guardrail doing its job.

## What the demo shows

1. **Stage 1, the prompt layer** (live, about 6 minutes): A short role prompt with no secrets, no limits and no policy numbers. The customer's words are passed inside `<customer_message>` tags that mark them as untrusted data. The reply is a fixed JSON shape that code validates. A short note says what a prompt can and cannot guarantee.
2. **Stage 2, the tool layer** (no key, about 8 minutes): Each agent's tool list is its least privilege. `read_customer` accepts only allowed countries and well-formed ids. `issue_refund` accepts only positive amounts under a cap. Results carry only the fields the job needs, with the email masked. An idempotency key makes a repeated refund do one thing.
3. **Stage 3, the MCP layer** (no key, about 8 minutes): The server checks a scoped token read from `CUSTOMERS_READ_TOKEN` or `CUSTOMERS_WRITE_TOKEN`. The read token cannot call `issue_refund`. Tools are allowed by full name (`mcp__customers__read_customer`). The server validates arguments again. Tool results go to the model as untrusted data. Logs are redacted.
4. **Stage 4, the agent, subagent and orchestrator layer** (live, about 10 minutes): A `PreToolUse` hook is the policy gate. It denies by default, with rules for each role and each argument, and the deny message goes back to the model. `max_turns` and `max_budget_usd` cap the run. Each subagent has its own tool list, and the orchestrator has only the `Agent` delegation tool. The account reader's hand-off is validated against a schema before a refund can follow it. A refund above the approval limit goes to a queue file for a person. The default run uses three tickets: T-9001 (a normal refund), T-9002 (a refund above the limit) and T-9003 (a ticket whose text contains an instruction).
5. **Stage 5, audit and proof** (optional, no key, about 5 minutes): Every tool call from stage 4 is in an audit log with the agent, the tool, masked arguments, the decision and the reason. A check proves that no secret or personal data is in the log, and a one-page scorecard lists every control, its layer, where it is enforced and what it protects.

> **Note**: The tickets are ordinary. T-9003 asks where an order is, and its text also contains an instruction to refund 900. T-9004 is a normal refund. T-9005 is from a customer in a country this agent may not read. When a control refuses something, that is the guardrail doing its job.

## Files in this folder

- **guardrails_stack.py**: The entry script. The prompts, the five stages, the subagents, the policy gate, the audit log and the scorecard. Run `python guardrails_stack.py --stage N`.
- **policy.py**: The rules as plain functions, with no model and no SDK: argument checks, the gate decision, the untrusted-text wrapper, the schema check and redaction.
- **customers_server.py**: The `customers` server. The tool bodies (stage 2) and the front door with tokens, scopes and the allow-list (stage 3). The data is in memory.
- **check_offline.py**: A key-free self-check. It plays a scripted fake of the Agent SDK through the real gate and the real server.
- **data/**: **customers.json** (five customers), **tickets.json** (five tickets) and **policy.json** (limits, roles, scopes and schemas). All of it is author-written sample data, not real people.
- **GUARDRAILS_BY_LAYER.md**: A one-page reference card, with a short mapping to the OWASP Top 10 for LLM applications.
- **results/**: Created when you run stage 4. It holds **audit_log.jsonl** and **approval_queue.json**.

## Run the demo

1. Install the package, and check that the Claude Code command-line tool is available. Stages 1 and 4 need them. Stages 2, 3 and 5 do not.

    ```
    pip install claude-agent-sdk==0.2.163
    claude --version
    ```

    **What it does**: It installs the Agent SDK and prints the version of the Claude Code tool that the SDK starts as a helper process.

    **Why we run it here**: The live stages drive the Claude Code tool, so a missing tool stops stages 1 and 4 at the first call.

2. Set your key. In bash, use `export ANTHROPIC_API_KEY=sk-ant-...`. In PowerShell, use `$env:ANTHROPIC_API_KEY="sk-ant-..."`.

    **What it does**: It puts the key in the terminal's environment.

    **Why we run it here**: The SDK reads the key from the environment, so the key never appears in the code.

3. Optional: set your own scoped tokens. Without them, the server makes safe demo tokens for each run and never prints them in full.

    ```
    export CUSTOMERS_READ_TOKEN=demo-read-yourvalue
    export CUSTOMERS_WRITE_TOKEN=demo-write-yourvalue
    ```

    **What it does**: It gives the server two tokens, one for each scope.

    **Why we run it here**: Real credentials come from the environment or a secret store, never from the code. This shows where they come from.

4. Run the key-free check, and confirm that it ends with `ALL OK`:

    ```
    python check_offline.py
    ```

    **What it does**: It runs every stage against a scripted fake of the SDK, and checks the guardrails with PASS and FAIL lines.

    **Why we run it here**: It proves that the files are intact and that the guardrails hold, before you spend a live call.

5. Run the stages from this folder, one after another:

    ```
    python guardrails_stack.py --stage 1
    python guardrails_stack.py --stage 2
    python guardrails_stack.py --stage 3
    python guardrails_stack.py --stage 4
    ```

    **What it does**: Stage 1 asks the model to triage the five tickets and checks each reply in code. Stage 2 calls the tools directly and shows their limits. Stage 3 calls the server with different tokens. Stage 4 runs three tickets through the orchestrator, the subagents and the gate.

    **Why we run it here**: Each stage adds one layer to the same ticket flow, so you see what each layer catches that the one before it did not.

6. Optional: run all five tickets in stage 4, then show the audit and the scorecard:

    ```
    python guardrails_stack.py --stage 4 --all
    python guardrails_stack.py --stage 5
    ```

    **What it does**: The first command adds T-9004 and T-9005 to the run. The second reads **results/audit_log.jsonl**, checks it for secrets and personal data, and prints the scorecard.

    **Why we run it here**: The audit log is the proof that every call was seen, and the scorecard is the one page to keep.

## What was verified

- **Offline (done)**: `python check_offline.py` ends with `ALL OK`. It checks the data, the argument limits, the masked results, the idempotency key, the tokens and scopes, the allow-list, the gate rules and all five stages against a scripted fake of the SDK. It also confirms directly that: the instruction in the ticket text did not cause a refund, the read token cannot refund, a read in a denied country never returned data, the over-limit refund went to the approval queue and not to `issue_refund`, a repeated idempotency key refunded once, and the audit log has no secret or personal data in clear. The fake model's tool calls are author-written fixtures, and one fixture plays a model that follows the instruction in T-9003, to prove that the code holds even then.
- **Not run live**: Nothing was run against the real API or the real Claude Code tool. The sandbox had no key and no CLI. The prompts, the subagent behaviour and the hook inputs on your SDK version have not been tried with a real model.
- **Check on your SDK version**: That the `PreToolUse` hook input carries `agent_type` for calls made inside a subagent (the gate uses it to find the role, and if it is missing, subagent calls are denied as orchestrator calls, which fails safe). That `HookMatcher` without a matcher covers every tool. That `AgentDefinition` accepts `maxTurns`. That the `UserMessage` and `ToolResultBlock` messages arrive in time for the hand-off check. Your first live run is the first time they are tried.

## Design notes

- **One request, five layers.** The same ticket flow gets one control per stage. You can say which layer caught what.
- **The prompt holds no numbers.** The refund cap, the approval limit and the allowed countries are only in **data/policy.json** and in code. A check in the demo scans every prompt for them.
- **The gate is plain code.** `gate_decision` in **policy.py** is one function. The hook only asks it and reports the answer, so a person can read the rules in one screen.
- **Deny by default.** A tool that no rule allows is denied. An unknown role has no tools.
- **The server does not trust the client.** The server checks the token, the scope, the allow-list and the argument types itself, even though the gate already checked.
- **Tokens are scoped.** In production the token travels in an `Authorization` header to a remote MCP server. Here the server runs inside the script, so each tool wrapper holds only its own token. The checks are the same.
- **Subagents inherit the main model.** The subagents are not given a model of their own. The triage calls in stage 1 use the fast model.
- **No approval screen.** The queue file is the hand-off to a person. Building the screen is outside this demo.
- **Happy path only.** No attack, outage or failure drill is staged. See the study guides for those.
