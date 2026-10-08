---
paths:
  - "src/shipcalc/**/*.py"
---
- Never use float, round() or a float literal for a price; apply zone multipliers as integer permille.
- Round half-up once, at the end: (cents * permille + 500) // 1000.
