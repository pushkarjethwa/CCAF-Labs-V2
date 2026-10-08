# shipcalc
Tests: `python -m pytest`. Money rule check: `python .claude/hooks/invariants.py src`.
- Internal units are kilograms and centimetres.
- Money is integer cents everywhere.
- Diagnostics go through `logging`, never `print()`.
Architecture: @docs/ARCHITECTURE.md
