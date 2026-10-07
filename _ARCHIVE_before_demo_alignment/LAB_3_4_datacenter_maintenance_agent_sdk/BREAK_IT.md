# Break it (after check.py is green)

Change one thing, run `python lab.py --dry-run` and `python check.py`, predict first, then note which check caught it and what real outage it predicts. Undo after each.

1. **Fail open.** In `pre_tool_use`, make the `except` branch return `"allow"`. Which check catches it? What real bug causes a hook to throw (a payload shape change after an SDK upgrade)?
2. **List a mutating tool in `allowed_tools`.** Add `set_power_state`. Which check fails? Why does listing it skip `can_use_tool` entirely, so the pause never happens?
3. **Interrupt instead of pause.** Return `interrupt=True` from the pause. What does that do to the rest of the agent's work, and why is resumability worth `False`?
4. **Reason without the rack.** Drop the rack from the R2 reason. Which check fails, and what does the on-call engineer lose at 3 a.m.?
5. **Move R4 above R2.** Does the dry run change? Which of the two rules should win when both apply, and why?
6. **Audit only the allows.** Skip the audit record for denied calls. Which check fails? Which calls matter most to an auditor?
7. **Prompt only.** Rate `prompt_only` enforcement as `high` and run `python check.py`. What does the dry run of the starter show that argues against it?
