# src/rewards notes

This file loads when Claude works on files in this folder.

- `points.py` is the only place that computes points.
- `ledger.py` is in memory. Call `ledger.reset()` in tests.
- Log through `log_event` only. Do not call `print` or `logging` directly.
- Read secrets with `config.get_api_key()`. Never write a key in source.
