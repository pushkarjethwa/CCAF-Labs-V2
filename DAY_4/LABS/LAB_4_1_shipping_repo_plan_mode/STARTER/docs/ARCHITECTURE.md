# shipcalc architecture

quote.get_quote -> carriers/<carrier>.quote -> (units, packaging.billable_weight_kg, rates.price_cents)

- `rates.py` owns the band table, the zone multipliers and the per-carrier dimensional divisors.
- `packaging.py` owns volumetric weight.
- Known debt: each adapter re-implements its own unit handling.
