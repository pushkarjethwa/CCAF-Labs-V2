# carriers/
- Every adapter starts with `units.to_metric(parcel)`; after that, everything is kg and cm.
- A new carrier is one module here plus a divisor in `rates.DIVISORS`.
