# brewbean-rewards

The small rewards service of Brew & Bean, a cafe chain. Customers earn points for purchases.

## Team rules

1. Points are whole numbers (integers), never floats. 1 point per whole currency unit spent. Members get a bonus multiplier.
2. Never log customer emails or any personal data. Log the customer id only.
3. No secrets in source code. Keys come from environment variables.
4. Every change to `src/` needs a test.

## Run the tests

    python -m unittest discover -s tests

## Check the rules

    python scripts/check_rules.py --files src/rewards/points.py
    python scripts/check_rules.py --diff change.patch

The scanner prints JSON. It needs no API key.
