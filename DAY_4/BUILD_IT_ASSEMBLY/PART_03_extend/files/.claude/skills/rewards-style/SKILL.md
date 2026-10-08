---
name: rewards-style
description: The house style for Brew & Bean rewards code. Use when writing or changing points, ledger, logging or api code in src/rewards, or the tests for it.
---

# Rewards code style

Follow these habits so every change looks like the code around it.

1. Amounts are in cents and points are whole numbers. Divide with `//`. Never use `float`, a decimal literal or `round()` for points.
2. Put numbers that the business may change in a named constant at the top of the file, like `MEMBER_PERCENT` in `points.py`.
3. Reject bad input early with a `ValueError` that says what was wrong in one short sentence.
4. Log with `log_event(event, customer_id, **fields)`. Pass the customer id and numbers only. No email, phone, address or name.
5. Read keys and tokens from environment variables through `config.py`. Never type one into source.
6. Tests use `unittest`. Name each test after the behaviour, like `test_member_bonus_is_integer`, and reset shared state in `setUp`.

After a change, run `python -m unittest discover -s tests` and report the result in one line.
