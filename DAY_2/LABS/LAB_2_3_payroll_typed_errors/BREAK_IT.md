# Break it - Lab 2.3
Do these after `check.py` is green. Restore each change afterwards.
1. **Remove the repeat guard.** Comment out TODO A. Run `python check.py`: the repeat test fails. Why can't this rule live only in the prompt? (A model can ignore a hint; the harness cannot.)
2. **Over-eager retry.** Add `HR_APPROVAL_REQUIRED` to `RETRY_POLICY` with 3 attempts and set its catalog entry to `retryable: True`. Which check fails first? Is the user-facing status affected, or only the trace and approval count?
3. **Same idempotency key twice.** In `data/scenarios.json` give S1 and S5 the same `key`; run `lab.py` and read `adjustments written`. What happened to the second request? Write one rule for who generates idempotency keys (model, harness or ticket system) and why.
4. **Reflection (3 sentences).** Which breakage would a unit test on `to_tool_result()` alone catch, and which needed the agent trace?
