# Break It - Lab 1.3

Work on a copy of `lab.py` (`copy lab.py lab_backup.py`) so you can restore your working version. Use `--only GR-005,GR-017` to keep each run small and cheap.

## Break 1 - the vague retry
In `build_corrective_messages`, replace the failure list with the single sentence `"That was wrong, try again."` (keep the assistant turn). Run `python lab.py --only GR-005,GR-017,GR-011`.

Predict first: will the model repair its mistake without being told what was wrong?
Observe: compare `attempts` and the log `feedback` with your working version. A retry that does not name the failed rule gives the model nothing new, so it tends to repeat the mistake and you pay for it twice. Restore your version.

## Break 2 - a validator that checks format, not truth
In `check_po`, replace the digit-in-email grounding test with `re.fullmatch(r"PO-\d{5}", po_number)`. Run `python check.py`.

Predict: a made-up PO number that is well-formed and exists in `purchase_orders.json` but is NOT in the email. Will your format-only check catch it?
Observe: no. The planted case `invented_po` stops firing and `check.py` fails. A grounding check must compare against the source text, not against a pattern or a registry that the invented value also satisfies. Restore your version.

## Break 3 (optional) - cap off by one
Change `range(1, MAX_ATTEMPTS + 1)` to `range(1, MAX_ATTEMPTS + 2)`. Which check catches it, and why is the number of **model calls** (not loop iterations) the number to audit?
