# Guardrails by layer: a one-page reference card

Use this card with Demo 5D (Northwind Support: an orchestrator, an account reader and a refund processor, with one `customers` MCP server). The rule for every row: **the prompt asks, the code decides.** Put each control at the layer where it cannot be skipped.

## The controls, layer by layer

| Layer | The control | Where it is enforced | What it protects |
|---|---|---|---|
| Prompt | A short role prompt with no secrets, no limits and no policy numbers | The system prompt | Nothing sensitive can leak from the prompt |
| Prompt | Customer text inside untrusted-data tags | `wrap_untrusted()` in **policy.py** | Marks outside text as data, not orders (a help, not a guarantee) |
| Prompt | A fixed JSON output shape, validated | `check_schema()` in **policy.py** | Malformed or unexpected output reaching code |
| Tools | Least privilege: each agent lists only the tools its job needs | `roles` in **policy.json**, `tools=` on each subagent | An agent using a tool it does not need |
| Tools | Argument limits: allowed countries, id format, positive amount, refund cap | The tool bodies in **customers_server.py** | Invalid, oversized or out-of-region requests |
| Tools | Minimal, masked results | `read_customer()` | Personal data leaving the server |
| Tools | An idempotency key on every refund | `issue_refund()` | The same refund happening twice |
| MCP | A scoped token from the environment (read or write) | `CustomersServer.handle()` | A read credential doing writes, and keys in code |
| MCP | An allow-list by full tool name (`mcp__customers__read_customer`) | `SCOPE_OF_TOOL` | Tools nobody approved |
| MCP | Server-side validation of arguments | `CustomersServer.run()` | Trusting the client's own checks |
| MCP | Tool results treated as untrusted data, and secrets redacted in logs | `reply_text()`, `redact()` | Instructions hidden in data, and secrets in log files |
| Agent | A policy gate that denies by default, with rules per role and per argument | `make_gate()` (a `PreToolUse` hook) and `gate_decision()` | The wrong tool or the wrong argument for a role |
| Agent | Turn and budget limits | `max_turns`, `max_budget_usd` | Runaway loops and cost |
| Agent | A human approval queue for refunds over the limit | `add_to_queue()` | Large refunds that cannot be undone |
| Subagent | Its own tool list, enforced again by the gate | `build_subagents()`, `gate_decision()` | One subagent doing another's job |
| Orchestrator | Only the delegation tool, and a hand-off checked against a schema before the next step | `tools=["Agent"]`, `accept_handoff()` | The coordinator touching data or money, and unchecked facts driving a refund |
| Audit | A log row for every call: agent, tool, masked arguments, decision, reason | `audit()` | No record of who did what, and personal data in logs |

## The ten practices in one line each

1. **Least privilege**: give each agent only the tools its job needs.
2. **Deny by default**: if no rule allows a call, the answer is no.
3. **Enforce in code, not in the prompt**: a prompt can be talked round.
4. **Validate inputs and outputs**: check arguments going in and replies coming out.
5. **Treat outside text as untrusted**: customer text and tool results are data.
6. **Scoped, short-lived credentials from the environment**: one token, one job, never in code.
7. **Redact secrets in logs**: remove tokens and personal data before writing.
8. **Human approval for irreversible actions**: a person signs what cannot be undone.
9. **Budgets and turn limits**: stop a runaway loop early.
10. **Idempotency and audit logging**: a repeat does one thing, and every call is recorded.

## Mapping to the OWASP Top 10 for LLM applications

The list below is the 2025 edition, read from the OWASP GenAI Security Project page (genai.owasp.org) on 2026-10-09. Check it against the current OWASP list before you rely on it. This mapping is a teaching aid, and it covers what Demo 5D shows, not everything the risk covers.

| OWASP risk | Where Demo 5D helps |
|---|---|
| LLM01 Prompt Injection | Untrusted tags (prompt), the gate and the tool limits (agent and tools), tool results as data (MCP). The code holds even if the model is fooled |
| LLM02 Sensitive Information Disclosure | Minimal, masked results (tools), redacted logs (MCP), masked arguments in the audit log |
| LLM03 Supply Chain | Not covered. Related: the allow-list by full tool name, and pinning the SDK version |
| LLM04 Data and Model Poisoning | Not covered |
| LLM05 Improper Output Handling | Schema check on replies (prompt), server-side validation (MCP), the hand-off schema (orchestrator) |
| LLM06 Excessive Agency | Least privilege, scoped tokens, the deny-by-default gate, the approval queue |
| LLM07 System Prompt Leakage | No secrets, limits or numbers in any prompt |
| LLM08 Vector and Embedding Weaknesses | Not covered (there is no retrieval in this demo) |
| LLM09 Misinformation | Not covered. The refund is compared with the order amount from the hand-off, which is a data check, not a fix for this risk |
| LLM10 Unbounded Consumption | `max_turns` and `max_budget_usd` |

## Where to read more

- `STUDENT_V2/STUDY_GUIDES/DAY_3/AGENT_SAFETY_AND_FAILURE_HANDLING.md` covers attacks, failures and recovery.
- `STUDENT_V2/STUDY_GUIDES/DAY_2/MCP_SECURITY_AND_GOVERNANCE.md` covers tokens, scopes and logs.
- `STUDENT_V2/STUDY_GUIDE/MCP_SECURITY_ARCHITECTURE.md` covers the full security architecture.
