# Lab 2.1 - Facilities assistant: fix the tool boundaries

**Time:** 60-75 min | **Needs API key:** `lab.py` yes (64 small calls, under $1); `check.py` Part A no | **Exam:** D2 Tool Design

## Story
The facilities assistant has 11 overlapping tools with descriptions like "Look up a room." Staff say it keeps doing the wrong thing. You fix the tools, not the prompt.

## What you do
Edit **`toolset.py`** only (read `HOW_THE_CODE_WORKS.md` first if the SDK is new to you).
- D1 Rewrite descriptions: when to use AND when NOT to use (name the sibling tool).
- D2 Consolidate overlapping tools (e.g. one `space` tool with `action = search | get | hold`).
- D3 Prune tools that duplicate another.
- D4 Keep `CAPABILITY_MAP` honest for every tool you rename, merge or remove.
- D5 Scope tools per desk (7 or fewer each).

## Run
```
pip install -r requirements.txt
python check.py     # lint your toolset, no key needed. Start here and iterate
python lab.py       # real Claude, 16 prompts x legacy vs yours, both models
python check.py     # now also checks the evidence
```

## Files
| File | Role |
|---|---|
| `toolset.py` | **You edit this** |
| `toolset_original.py` | The legacy 11 tools. Read only |
| `lab.py` | Eval harness: shows Claude the tools (`tool_choice` auto), grades the capability reached |
| `toolset_lint.py` | Static rules used by lab.py and check.py |
| `data/` | 16 eval prompts, capability definitions |

## Expect
Modern models handle many ambiguous tools better than older ones, so the legacy score may already be high. Read the confusion list and the lint output, and report the real numbers honestly. Pass bar: balanced >= 85%, fast >= 75%, no regression, no scope miss.

## Stuck?
Try the lab first. If you need a hint or want to compare, open `SOLUTION/SOLUTION_GUIDE.md` (solutions, expected results, answers to BREAK_IT).
