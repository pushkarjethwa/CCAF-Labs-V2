# Lab 3.3 - Release readiness pipeline (about 40 minutes)

A release goes through four stages: **EXTRACT** (Claude reads tickets) -> **ENRICH** (tools fetch CI, vulnerability and on-call data) -> **ASSESS** (rules) -> **REPORT**.
Things break. A model invents a category. A tool returns nothing. A scanner goes down. The wrong response (retry everything, trust any cache, ship on empty data) leads to bad release decisions.

**Your job: write six small decisions.** About 35 lines in total. The loops, bookkeeping, mock tools and the Claude call are already written.

## Set up

```
pip install -r requirements.txt
```

Put `ANTHROPIC_API_KEY=...` in a `.env` file next to `lab.py` (only needed for Step 3).

## Your files

| File | What it is |
|---|---|
| `lab.py` | The only file you edit. Sections 1 to 3 hold your six TODOs. Section 4 is plumbing: do not edit, you never need to read it. |
| `check.py` | Tests your functions with hand-made inputs (no key), then checks the scenario results |
| `data.json`, `claude_client.py` | Data and the Claude helper. Leave alone. |

## Steps

1. **Run the naive starter first.** `python lab.py` accepts everything, retries everything and trusts any cache. Read the table it prints.
2. **Write the TODOs in order** (1 and 2 validate, 3 classify, 4 to 6 recover). After each one run `python check.py` (no key). The lines for that TODO turn green.
3. **Run the real thing.** `python lab.py` (key needed) runs eight scenarios. Claude does the real EXTRACT step. Then `python check.py` again: Part B compares each scenario with the expected table.
4. Read `BREAK_IT.md`, try two experiments, then look at `CHALLENGE.md` if you have time.

## The eight scenarios you should end up with

| Id | What goes wrong | Class | Recovery | Outcome |
|---|---|---|---|---|
| F0 | nothing | - | - | completed |
| F1 | first CI call uses a sloppy id; the error carries a hint | tool | retry with changed args | completed |
| F2 | CI returns an empty record | tool | escalate | escalated, no verdict |
| F3 | model invents a category once | reasoning | corrective re-prompt | completed |
| F4 | model invents a category every time | reasoning | escalate after 2 corrections | escalated |
| F5 | scanner times out twice | environment | backoff retry | completed |
| F6 | scanner down; cache is for this version | environment | fallback to cache | completed_degraded, never `go` |
| F7 | scanner down; cache is for an older version | environment | pause and alert | paused, one alert |

F3 and F4 inject a bad category into Claude's reply (labelled "[injected fault]" in the output) so the failure is repeatable. Everything else in EXTRACT is the model's real answer.

## Done when

`python check.py` ends with `RESULT: 47/47 checks passed`.

## Stuck?

Each TODO's docstring spells out the rule. If a check line is red, its text says what was expected. Last resort: `SOLUTION/SOLUTION_GUIDE.md`.
