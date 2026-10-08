# Plan - fix imperial-unit quotes in shipcalc

## Files to change
- NEW `tests/test_characterization.py`: pins today's correct behaviour (metric parcels, light imperial parcel on acme) before any change.
- `src/shipcalc/units.py`: add `parcel_kg` and `parcel_dims_cm`, so ONE module converts pounds to kilograms and inches to centimetres. It is the only file that holds the constants.
- `src/shipcalc/carriers/zipfast.py`: stops passing raw pounds into a kilogram-only rate table; uses `units.parcel_kg`.
- `src/shipcalc/carriers/acme.py`: converts weight correctly but passes inches into the centimetre-based dimensional formula; uses `units.parcel_dims_cm`.
- `src/shipcalc/packaging.py`: parameter rename only (`dims_cm`) to state the canonical-unit contract; no behaviour change.
- NEW `tests/test_imperial_regression.py`: regression tests for both carriers.

## Callers and blast radius
`quote.get_quote` calls `carriers.acme.quote` and `carriers.zipfast.quote`; both call `packaging.billable_weight_kg` and `rates.price_cents`. Tests touching them: test_quote.py and test_packaging.py. The visible suite does NOT exercise the bug: `test_acme_pounds_light_parcel` passes only because a 2x2x2 inch parcel has almost no volume. `scripts/hidden_regression_units.py` pins imperial quotes and is red today.

## Risks
1. Fixing only the zipfast pound conversion leaves acme dimensional weight wrong (inches treated as centimetres, about 16 times too small); a one-line fix looks complete.
2. Dividing by 2.2 inline duplicates constants and drifts from `units.KG_PER_LB`.
3. Changing band edges or divisors in rates.py would "fix" one quote and break every other.

## Order of changes
1. Write a characterization test that pins today's correct behaviour. It must pass on the untouched code.
2. Add the regression tests for imperial parcels and watch them fail for the right reason.
3. Add the two helpers to `units.py`; switch zipfast.py, then acme.py; run the tests after each file.
4. Clarify the `packaging.py` contract; run the tests.
5. Separate change: unknown zone numbers raise `KeyError` from `rates.zone_multiplier`; make it a `ValueError`. Found while reading rates.py, out of scope here, do not mix.

## Verification
- `python -m unittest discover -s tests` after every step.
- `python scripts/hidden_regression_units.py`: 4 tests green after step 4.
- Search `src/` for `0.4535` and `2.54`: only `units.py`.
- Diff review: only the files above, plus rates.py in step 5.

## Rollback
Each step is its own commit; revert the adapter commits to restore the old behaviour. No data migration is involved.
