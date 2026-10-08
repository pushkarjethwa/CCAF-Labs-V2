---
description: Run the plan gate on a saved plan and explain every missing item
argument-hint: <path to the plan, for example docs/PLAN.md>
---

Run `python tools/plan_check.py $ARGUMENTS` and show the output.

If the plan is REJECTED, list each failed check in plain words and say which part of the repo would be at risk without it. Do not edit any file.
