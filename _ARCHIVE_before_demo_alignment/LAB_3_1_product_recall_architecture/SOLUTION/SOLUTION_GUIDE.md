# Lab 3.1 solution guide

The full working file is `lab_solution.py` (same folder).

## Table 1

| Brief | Pick | Deciding fact |
|---|---|---|
| RB-1 customer chat | conversational | the customer decides each turn |
| RB-2 nightly regulator filing | workflow | the regulators publish the procedure; steps never change |
| RB-3 retailer reply triage | workflow | one label, then a fixed routing table; replies are independent |
| RB-4 contamination trace | agentic | which record to query next depends on what the last one revealed |

Only RB-4 needs an agent. An agentic answer elsewhere is more power than the facts need.

## Table 2

| Step | Kind | Why |
|---|---|---|
| R1 identify lots | agent | path not known in advance; needs free-text judgment |
| R2 regulators | fixed_step | published templates, fixed procedure (tool is also accepted) |
| R3 notify | fixed_step | fixed text and contact list (tool also accepted) |
| R4 quarantine | tool | one deterministic WMS call (fixed_step also accepted) |
| R5 returns | tool | deterministic capacity calculation (fixed_step also accepted) |
| R6 tracking | tool | arithmetic across two databases (fixed_step also accepted) |
| R7 exec status | fixed_step | free text from known numbers: one scripted model call, never an agent |

Tests: the agent gets a rubric (its output varies); everything else gets an exact or schema test. Data flows through explicit hand-offs, never one shared mutable database.

## Common mistakes

- "Agents are more flexible" as a reason. Flexibility is a cost when the path is known.
- A rubric test on a deterministic component, which means it was never deterministic.
- Two tables that disagree: an agentic brief but no agent step, or the other way round.
