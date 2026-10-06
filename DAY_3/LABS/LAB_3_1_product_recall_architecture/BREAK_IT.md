# Break it (after check.py is green)

Change one thing, run `python check.py`, predict first, write one sentence on what it predicts in real life. Undo after each.

1. **Make R2 (notify regulators) an agent** with a plausible-sounding reason. Which rule fires? Why is a good-sounding reason not enough when the path is known?
2. **Switch DATA_FLOW to `one_shared_db`.** Which rule fires? Describe the real bug: two components update the affected-lot list in different orders.
3. **Give R1 (the agent) an `exact` test.** Why can't an exact test check a component whose output varies?
4. **Give R4 (a tool) a `rubric` test.** What does that say about the component?
5. **Make R7 a tool.** The report needs words from numbers. Which kind is allowed one model call, and why not an agent?
6. **Set RB-2 (nightly regulator filing) to agentic.** The rules reject it. Now imagine a checker that only looked at your reason text. What could an eloquent paragraph get past it, and what does that say about what automated checks can judge?
7. **Ask Claude to critique a design that fails the rules** (comment out the early stop in `main`). Does Claude catch what the rules caught?
