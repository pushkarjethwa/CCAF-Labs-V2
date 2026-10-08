# shipcalc

Small shipping-quote library: two carrier adapters (acme, zipfast) price parcels entered in pounds/inches or kg/cm.

## Layout
- `src/shipcalc/` library code, `tests/` unit tests, `scripts/` helper scripts, `docs/` design notes.

## Commands
- Run the tests: `python -m unittest discover -s tests`
- Acceptance script (not part of the test suite): `python scripts/hidden_regression_units.py`

## Working agreement
- Read before you edit: search for every definition and every caller first.
- Keep unrelated findings out of the change; report them separately.
