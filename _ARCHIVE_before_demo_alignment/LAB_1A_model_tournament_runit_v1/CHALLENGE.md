# Challenge - Lab 1A
1. Add 6 invoices of your own to `data/invoices.json` and `data/ground_truth.json` (include two that should be `hold`). Does any tier miss them?
2. Make the router cheaper without losing hold recall: try `min_confidence` 0.6 and 0.9 and plot cost against hold recall.
3. Replace the loop in stage 3 with the Message Batches API and compare cost and time (Lab 1.4 shows how).
4. Add a deterministic pre-check (duplicate invoice number with a different amount) that forces `hold` before any model is called. How many model calls does it save?
