# Challenge - Lab 2.3
1. Add jitter to the backoff and explain why a real system needs it (the lab clock is simulated, so test it with a seeded random).
2. Add a circuit breaker: after 3 locked failures across scenarios, stop calling the DB for 60 simulated seconds.
3. Add a scenario where Claude passes a malformed `period` (for example `Sept 2026`) and give it a typed `INVALID_INPUT` error with a corrective hint.
