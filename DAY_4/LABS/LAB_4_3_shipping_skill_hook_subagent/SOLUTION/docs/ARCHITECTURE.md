# shipcalc architecture

quote.get_quote -> carriers/<carrier>.quote -> (units, packaging.billable_weight_kg, rates.price_cents)

* `rates.py` owns the band table and per-carrier dimensional divisors (config/carriers.yaml).
* `packaging.py` owns volumetric weight.
* The public API is described in `docs/API_CONTRACT.json`.
