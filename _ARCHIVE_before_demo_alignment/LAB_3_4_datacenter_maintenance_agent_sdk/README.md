# Lab 3.4 - Data-centre maintenance agent: enforce with hooks, not prompts (about 45 minutes)

Polarwind Hosting lets an agent run a Saturday-night maintenance plan: read rack status, power-cycle racks, push firmware 7.2.
Four racks: `R-A01` (production, **tier-0** core database), `R-A07` (production, 3 tenants), `R-B02` (staging, window closed), `R-C05` (lab).

The agent is told to attempt **every** action in the plan. That is the pressure test. **A guard you write decides what actually happens.**
You use the Claude Agent SDK's lifecycle points: a **PreToolUse hook** (allow / ask / deny, failing closed), a **permission callback** that turns "ask" into a pause which resumes after a human change approval, a **PostToolUse** audit, and hermetic **SDK options**.

A real Claude agent runs the plan through your guard. Your job: **five guard methods and one small ratings table** (about 55 lines, all of it the point of the lab).

## Set up

```
pip install -r requirements.txt
```

Put `ANTHROPIC_API_KEY=...` in a `.env` file next to `lab.py` (only needed for Step 3). The optional `live_run.py` also needs the Claude Code CLI.

## Your files

| File | What it is |
|---|---|
| `lab.py` | The only file you edit. Sections 1 and 2 hold your six TODOs. Section 3 is plumbing: do not edit. |
| `check.py` | Tests your guard with hand-made inputs and a scripted agent (no key), then checks the real Claude run |
| `live_run.py` | Optional, not graded: the same guard inside the real Agent SDK |
| `data.json`, `claude_client.py` | The racks, plan and approvals; the Claude helper. Leave alone. |

## Steps

1. **Run the starter dry.** `python lab.py --dry-run` (no key). The starter has no rules: watch the scripted agent power off the tier-0 database rack. That is what "NEVER modify production racks" in a prompt is worth.
2. **Write the TODOs in order.** After each one run `python check.py` (no key). Re-run `--dry-run` to see the table change.
3. **Run the real agent.** `python lab.py` has Claude attempt the plan in three passes: pass 1, a human approves or rejects the paused changes, pass 2 resumes, pass 3 resumes again. Then `python check.py`: Part B checks the invariants of that run.
4. Try two experiments from `BREAK_IT.md`. Optionally read `live_run.py`.

## The rules (R1 to R6)

| Rule | Situation | Decision |
|---|---|---|
| R1 | unknown rack, or a tool that is not ours | deny |
| R2 | production and tier-0 | deny, the agent may never modify it |
| R3 | production (not tier-0), mutating | approved change: allow; rejected: deny; none: ask |
| R4 | mutating while that environment's window is closed | deny |
| R5 | read-only | allow |
| R6 | lab or staging, window open | allow |

## Done when

`python check.py` ends with `RESULT: 46/46 checks passed`.

## Stuck?

Each TODO's docstring spells out what to return; a red check line says what was expected. Last resort: `SOLUTION/SOLUTION_GUIDE.md`.
