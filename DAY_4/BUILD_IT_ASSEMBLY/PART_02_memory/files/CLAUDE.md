# brewbean-rewards

Small rewards service for Brew & Bean, a cafe chain. Customers earn points for purchases.

## Architecture
@docs/ARCHITECTURE.md

## Team rules
1. Points are whole numbers (integers), never floats.
2. Never log customer emails or any personal data. Log the customer id only.
3. No secrets in source code. Keys come from environment variables.
4. Every change to `src/` needs a test.

## Commands
- Run tests: `python -m unittest discover -s tests`
- Check the rules: `python scripts/check_rules.py --files <files>`

## Working style
- Python 3.10+, standard library only.
- Keep changes small and explain them in one short paragraph.
