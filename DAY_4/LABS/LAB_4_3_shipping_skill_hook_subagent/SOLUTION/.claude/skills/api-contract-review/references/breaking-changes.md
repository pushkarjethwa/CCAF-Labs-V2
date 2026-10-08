# What counts as breaking (shipcalc public API)

- A public function removed or renamed. `get_quote` is the only public entry point.
- A parameter removed, reordered or made required.
- A new optional parameter with a default is compatible, but it needs a test and a line in docs/API_CONTRACT.json.
- Parcel fields removed or reordered are breaking. A new optional field with a default is compatible.
- A return type change is breaking: `get_quote` returns integer cents, never a float or a Decimal.
- A breaking change needs a version note in README.md before it merges.
