---
description: Decide DIRECT or PLAN for a change request
---

Triage this change request: $ARGUMENTS

Do not edit any file. Look at the repo with read-only tools, then answer `DIRECT` or `PLAN`, followed by the signals that fired.
Plan first if ANY of these is true: the change touches 4 or more files, a shared symbol has 3 or more callers, it involves money, it is hard to reverse, test coverage is weak, or the scope is unknown. Otherwise it is DIRECT.
