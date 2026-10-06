# Challenge - Tiered routing with escalation

The service currently runs everything on one model. Design and build a two-tier router:

1. Every invoice goes to the cheaper model in a batch, validated as today.
2. Invoices whose decision fails validation, or whose decision is `reject`, are re-run on the other model (synchronously, cached) and the final record stores which model produced it and why it escalated.
3. Report: cost of the tiered run against all-fast and all-balanced for the same 40 invoices, using real usage numbers from the `usage` fields, plus a monthly projection for 100,000 invoices under an escalation rate you must state as an assumption (and justify how you would measure it live).
4. Add a "shadow" check: send 5 invoices to both models and compare decisions; define what disagreement rate would make you stop trusting the cheap tier.

Constraints: every request still shares the cached prefix; `custom_id` joins remain; the budget gate must account for the second-tier calls. Define at least four tests (one for an `expired` batch entry that must be retried). No reference solution is provided.
