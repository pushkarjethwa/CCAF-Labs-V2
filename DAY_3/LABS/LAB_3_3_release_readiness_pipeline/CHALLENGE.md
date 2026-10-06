# Challenges (optional)

1. **Circuit breaker.** After 3 environment failures across different releases in one run, stop calling the scanner at all and go straight to the cache or a pause. Where does the counter live, and which function should read it?
2. **Jitter.** Add up to 25% random variation to `backoff_delay`. Why do many clients retrying on the same doubling schedule make an outage worse? How do you keep `check.py` deterministic?
3. **Parallel enrich.** CI, on-call and dependency scan do not depend on each other. Run them concurrently. What happens to your retry accounting when two of them fail at once?
4. **A new class.** Add a `permission` error class (status 403) that must never be retried or cached. Which three functions change?
