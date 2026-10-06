# LAB 1.1 challenge - route instead of choosing (open-ended, no solution code provided)

Your memo picked one model for all rows. A two-tier router might beat it: cheap model first, bigger model only when a row looks risky.

**Goal:** design and measure a router that keeps the Balanced model's accuracy on the 40 rows at a lower projected cost for 100,000 rows, or reaches the Premium model's hard-row accuracy at a cost below "Premium for everything".

**Constraints**
* The Premium model is still capped at 8 calls in this lab. Your router must therefore be evaluated on the 8 hard rows for the escalation tier, plus a simulated escalation rate for the rest (state the assumption).
* Risk signals must be computed **without** looking at the ground truth: for example keywords in `title`/`note` (acting, interim, c2h, FTE fractions), disagreement between two cheap passes, or `stop_reason != end_turn`.
* No sampling parameters. Show your router's cost with `common.cost.project_cost` for 100,000 rows.

**Deliverables:** `evidence/router.md` with (1) the escalation rule, (2) escalation rate on the 40 rows and its precision/recall against the `hard` flag, (3) projected $/100k vs your single-model memo, (4) one failure mode of your rule and how you would monitor it.

**Stretch:** estimate how many rows per day the Message Batches API would need for a 24-hour turnaround, and what you do with rows whose batch result is `errored`.
