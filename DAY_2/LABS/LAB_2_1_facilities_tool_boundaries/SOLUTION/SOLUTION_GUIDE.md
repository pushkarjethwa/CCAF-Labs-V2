# Solution guide: Lab 2.1 - Facilities assistant: fix the tool boundaries

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Tool boundaries: rewrite descriptions (when to use, when NOT to use), consolidate overlapping tools behind an `action` enum, prune duplicates, keep the capability map honest, and scope tools per desk, then prove the change with a before/after eval.

## 2. The solution

This lab has no marker-by-marker TODOs: you rewrite `toolset.py`. The complete reference answer is `toolset_solution.py` in this folder. Design decisions:

- Four room tools become one `space` tool with `action = search | get | hold`; three ticket tools become `maintenance_ticket` with `action = create | list_open | log`.
- `book_room` stays separate from `space`: it is the one binding, side-effecting room action (it sends invites). Mixing it into a read-mostly tool hides the commit point from permissions and review.
- Duplicate tools (`find_room`, `room_lookup`, `reserve_slot`, `ticket_open`, `maintenance_log`) are removed.
- Every description states when to use the tool AND when NOT to, naming the sibling to use instead.
- Scopes give each desk at most 4 tools: workplace_booking has `space` and `book_room`; maintenance_desk has `maintenance_ticket`, `asset_lookup`, `vendor_lookup`, `space`; security_desk has `badge_grant`, `vendor_lookup`, `space`.

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- toolset is smaller than the 11-tool legacy set
- evidence is fresh (toolset.py unchanged since lab.py ran)
- the eval used tool_choice=auto only (never forced)
- both model classes were evaluated (fast and balanced)
- lint: {name}
- no regression versus the legacy toolset
- inal score >= {FINAL_MIN.get(alias, 85.0):.0f}%
- {alias}: no prompt lost its correct tool to scoping

## 4. Common mistakes

- Merging the one side-effecting action (`book_room`) into a read-mostly tool: it hides the commit point from permissions and review.
- Descriptions that say what a tool does but not when NOT to use it (and which sibling to use instead).
- Forgetting to update `CAPABILITY_MAP` after renaming or merging tools (lint `capability_map_valid` fails).
- Scoping so tightly that a desk loses a tool it needs (a SCOPE MISS): scoping can lower accuracy too.
- Expecting a big score jump: modern models often handle many tools well; report the real before/after and the lint gains.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Forced `tool_choice` `any`: HTTP 400 on the balanced model; it would also hide the confusion you are measuring. Keep `auto`.
2. Removing `book_room` from `workplace_booking`: SCOPE MISS appears and `check.py` fails.
3. Two tools with the same 'Use when' text: lint `no_duplicate_purpose_text` fails and the confusion list names the pair.
4. Renaming a tool without updating the map: lint `capability_map_valid` fails.

## 6. Files in this folder

- `toolset_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
