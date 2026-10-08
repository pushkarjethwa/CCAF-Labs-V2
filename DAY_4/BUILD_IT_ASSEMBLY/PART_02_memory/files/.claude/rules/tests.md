---
paths:
  - "tests/**"
---

# Tests rule

- Use `unittest` from the standard library.
- Every change to `src/` comes with a test in the same change.
- Reset shared state in `setUp` (for example `ledger.reset()`).
- Test names say what they check, for example `test_member_bonus_is_integer`.
