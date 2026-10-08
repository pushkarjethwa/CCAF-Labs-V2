# Architecture

brewbean-rewards is a small Python service with no third-party packages. The entry point is `handle_purchase` in `src/rewards/api.py`. It takes a request dictionary and returns a response dictionary, so any web layer can call it later.

Points math lives in one place, `src/rewards/points.py`. It uses integer math only: one point per whole currency unit, and a whole-number bonus for members. Balances are kept in `src/rewards/ledger.py`, an in-memory ledger that a database can replace later without changing the callers.

Logging goes through `log_event` in `src/rewards/logging_utils.py`, which accepts a customer id and refuses personal fields. The API key is read from the `REWARDS_API_KEY` environment variable in `src/rewards/config.py`. The script `scripts/check_rules.py` scans changes for the four team rules and is used by hooks and by the CI gate.
