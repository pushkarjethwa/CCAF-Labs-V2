# Break it (after check.py is green)

Change one thing, run `python lab.py` and `python check.py`, predict first, then read what happened. Undo each change afterwards.

1. **Blanket retry.** Make `decide_recovery` return `"backoff_retry"` for the `tool` class. What happens to F2 (empty CI)? Why does asking again not help?
2. **Trust any cache.** Make `cache_is_usable` return `cache is not None`. Which scenario changes, and what verdict does a release with scanner evidence from an older version get?
3. **Degraded go.** In Section 4, remove the `degraded` rule in `assess`. Is F6 still safe? Which stage should own that rule, and why is a rule in code better than a sentence in a prompt?
4. **Happy-path validator.** Make `validate_enrich` accept an empty CI record. Run F2. What does the report say, and who would be fooled by it?
5. **No backoff.** Make `backoff_delay` return `0.0`. Which check catches it? In real life, what does hammering a struggling service do?
6. **Classify by message text.** Make `classify` return `"environment"` whenever the message contains "unavailable". It passes F6. Now find an input where it gives the wrong answer. Why are status codes safer?

Write one sentence per experiment: what broke, and which rule stopped it before.
