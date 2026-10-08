# Units policy

Customers may enter pounds/inches or kilograms/centimetres (`Parcel.weight_unit`, `Parcel.dim_unit`).
Everything below the adapters works in kilograms and centimetres. Each carrier adapter must convert at
the boundary, and `rates.price_cents` only ever sees a billable weight in kilograms.
