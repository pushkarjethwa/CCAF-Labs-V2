---
name: report-style
description: The bookshop's house format for text reports. Use when writing or changing any report, summary or listing that the shop owner reads.
---

# Bookshop report style

Every report in `bookshop/reports.py` follows the same shape, so the owner can read them all the same way.

1. The first line is the title in capitals between three equals signs on each side: `=== LOW STOCK (BELOW 5) ===`.
2. The second line is the column header: the title column is 28 characters wide, number columns are right-aligned.
3. Rows are sorted by title, A to Z.
4. Prices show a dollar sign and two decimals, like `$14.50`.
5. The last line starts with `Total:` and counts the titles, like `Total: 4 titles`.
6. Plain ASCII only. No emoji, no colours.

When you change a report, update its tests so they check the first and last lines.
