# shipcalc architecture

quote.get_quote -> carriers/<carrier>.quote -> (units.to_metric, packaging.billable_weight_kg, rates.price_cents)

* `units.py` converts customer units to kilograms and centimetres.
* `packaging.py` owns volumetric weight.
* `rates.py` owns the band table, the zone multipliers and the per-carrier dimensional divisors.
* A quote is an integer number of cents, and it is the price the customer is invoiced.
