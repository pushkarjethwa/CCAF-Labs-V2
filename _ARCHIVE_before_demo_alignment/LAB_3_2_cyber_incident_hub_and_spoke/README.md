# Lab 3.2 - Cyber incident response: hub and spoke (about 40 minutes)

At 03:14 a SIEM raised **INC-7741** at Nordlicht Logistics: a brute-forced SSH login on `bastion-02`, an unsigned binary, 38 MB leaving to an external address.
A **hub** (the orchestrator) delegates to four specialists: **triage -> log analysis -> threat intel -> containment plan**.
The hub also holds **private context** (honeypot names, a legal hold, a customer email) that must never reach a specialist or the final summary.

**The log analyst is a real Claude call.** The other three are scripted stand-ins. The delegation loop is provided.
**Your job: write six small rules** (about 28 lines): what a valid hand-off is, what each specialist may see, when to retry, and who depends on whom.

## Set up

```
pip install -r requirements.txt
```

Put `ANTHROPIC_API_KEY=...` in a `.env` file next to `lab.py` (only needed for Step 3).

## Your files

| File | What it is |
|---|---|
| `lab.py` | The only file you edit. Sections 1 to 3 hold your six TODOs. Section 4 is plumbing: do not edit. |
| `check.py` | Tests your functions with hand-made inputs (no key), then checks the scenario results |
| `data.json`, `claude_client.py` | The incident and the Claude helper. Leave alone. |

## Steps

1. **Run the naive starter first.** `python lab.py` hands the full history to every specialist. Look at the scenario table, then at `results/scenarios.json`: find the private text.
2. **Write the TODOs in order** (1 to 3 contracts, 4 briefs, 5 to 6 failure rules). After each one run `python check.py` (no key).
3. **Run the real thing.** `python lab.py` runs four scenarios (Claude does the log analysis). Then `python check.py`: Part B checks leaks, validation, bounded retries and honest failure.
4. Try two experiments from `BREAK_IT.md`.

## The four scenarios

| Id | What goes wrong | What the hub must do |
|---|---|---|
| S1 | nothing | complete; isolate `bastion-02`, disable `deploy`; a human approves the high-risk isolation |
| S2 | threat_intel backend is down | retry once, then continue: status `partial`, failure recorded, containment still runs |
| S3 | log_analysis answers malformed once | reject, re-ask once with a CORRECTION, then complete |
| S4 | log_analysis answers malformed every time | one rework, then stop: status `failed`, nothing downstream runs, a human is flagged |

S3 and S4 inject the malformed answer into Claude's reply (a missing field and a wrong type) so the failure is repeatable.

## Done when

`python check.py` ends with `RESULT: 34/34 checks passed`.

## Stuck?

Each TODO's docstring spells out the rule; a red check line says what was expected. Last resort: `SOLUTION/SOLUTION_GUIDE.md`.
