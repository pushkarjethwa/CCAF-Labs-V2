# Behaviour beyond signatures

- Units: kilograms and centimetres are canonical below the adapters (docs/UNITS.md). Changing that is breaking even when no signature changes.
- Errors: an unknown carrier raises ValueError. Changing the exception type breaks callers that catch it.
- Rounding: prices are integer cents, rounded half-up inside `rates.price_cents`.
- Carrier adapters keep the `(parcel, zone)` signature, because `quote.CARRIERS` depends on it.
