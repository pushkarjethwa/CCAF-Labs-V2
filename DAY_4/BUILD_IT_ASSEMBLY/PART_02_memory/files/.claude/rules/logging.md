---
paths:
  - "src/**/*.py"
---

# Logging rule

- Never log an email, phone number, address or name.
- Log the customer id only, through `log_event`.
- Do not put a key or token in source. Read it from the environment.
