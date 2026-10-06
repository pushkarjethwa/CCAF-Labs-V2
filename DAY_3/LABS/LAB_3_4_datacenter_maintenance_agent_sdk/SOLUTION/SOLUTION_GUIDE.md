# Lab 3.4 solution guide

The full working file is `lab_solution.py` (same folder).

| TODO | Decision | Why |
|---|---|---|
| 1 `decide` | Order: unknown rack, read-only, unknown tool, tier-0 production, closed window, lab/staging, then the production approval record | Deny rules come before allow rules, and R2 outranks R4. Reasons name the rule and the rack |
| 2 `pre_tool_use` | `{}` for tools that are not ours; otherwise `decide`, audit with event `pre`, return `hook_output`; any exception becomes a deny | A broken guard must never mean "allowed" (fail closed) |
| 3 `can_use_tool` | approved: allow; rejected: deny and do not retry; none: record a pending request, deny with `PAUSED ... CHG-...` and `interrupt=False` | The pause is a state change, not a crash: the run goes on and the step resumes after a human decides. Asking twice makes one request |
| 4 `post_tool_use` | audit record `post` with the status the tool returned | The audit trail shows what really happened, not only what was decided |
| 5 `sdk_options` | `setting_sources=[]`, `tools=[]`, `allowed_tools` = only the read tool, hooks for Pre and PostToolUse, `can_use_tool`, bounded `max_turns` | A mutating tool in `allowed_tools` would be auto-approved and skip `can_use_tool` |
| 6 matrix | prompt_only `low`; the other three `high` | A sentence is a request; code you control is enforcement |

## Why the table comes out as it does

- Pass 1: the tier-0 change is denied by R2; the production changes ask and pause (nothing runs); staging is denied by the closed window; the unknown rack is denied; lab work runs.
- The human approves the firmware change and rejects the reboot.
- Pass 2: the firmware change is now allowed and runs; the reboot is denied. Pass 3: everything is already applied or denied, so nothing changes.

## Common mistakes

- Listing a mutating tool in `allowed_tools`.
- `interrupt=True` on the pause.
- A hook that returns `{}` on error (the SDK reads that as "no opinion", so the call is allowed).
- Putting R4 before R2, or forgetting the approval record lookup.
